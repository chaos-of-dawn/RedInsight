"""
自动发帖执行服务
负责执行发布计划中的发帖任务
"""
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from database import DatabaseManager
from reddit_scraper import RedditScraper
from modules.posting.shared.schedule_manager import ScheduleManager
from modules.posting.shared.post_manager import PostManager

logger = logging.getLogger(__name__)

class PostingExecutionService:
    """自动发帖执行服务"""
    
    def __init__(self, db_manager: DatabaseManager, scraper: RedditScraper):
        """
        初始化发帖执行服务
        
        Args:
            db_manager: 数据库管理器
            scraper: Reddit爬虫实例
        """
        self.db = db_manager
        self.scraper = scraper
        self.schedule_manager = ScheduleManager(db_manager)
        self.post_manager = PostManager(db_manager)
        
        # Reddit API频率限制：同一子版块发帖间隔至少10-15分钟
        self.min_post_interval = 10 * 60  # 10分钟（秒）
        self.last_post_time = {}  # 记录每个子版块的最后发帖时间
    
    def _wait_for_rate_limit(self, subreddit: str):
        """
        等待以满足频率限制
        
        Args:
            subreddit: 子版块名称
        """
        if subreddit in self.last_post_time:
            elapsed = time.time() - self.last_post_time[subreddit]
            if elapsed < self.min_post_interval:
                wait_time = self.min_post_interval - elapsed
                logger.info(f"等待 {wait_time:.1f} 秒以满足频率限制（子版块: r/{subreddit}）")
                time.sleep(wait_time)
        
        self.last_post_time[subreddit] = time.time()
    
    def execute_pending_schedules(self, limit: int = 1) -> Dict[str, Any]:
        """
        执行待发布的计划
        
        Args:
            limit: 每次执行的任务数量限制
        
        Returns:
            执行结果统计
        """
        try:
            # 检查Reddit API认证
            if not self.scraper or not self.scraper.is_authenticated():
                return {
                    'success': False,
                    'error': 'Reddit API未认证或认证已过期。请重新进行OAuth2认证，确保获取了submit权限。',
                    'error_type': 'authentication_required',
                    'executed': 0,
                    'succeeded': 0,
                    'failed': 0
                }
            
            # 获取待发布的计划
            pending_schedules = self.schedule_manager.get_pending_schedules(limit=limit)
            
            if not pending_schedules:
                return {
                    'success': True,
                    'message': '没有待发布的计划',
                    'executed': 0,
                    'succeeded': 0,
                    'failed': 0
                }
            
            executed = 0
            succeeded = 0
            failed = 0
            
            for schedule in pending_schedules:
                try:
                    # 更新状态为发布中
                    self.schedule_manager.update_schedule_status(
                        schedule['id'],
                        'posting'
                    )
                    
                    # 获取帖子内容
                    post = self.post_manager.get_post(schedule['post_content_id'])
                    if not post:
                        logger.error(f"无法获取帖子内容，计划ID: {schedule['id']}")
                        self.schedule_manager.update_schedule_status(
                            schedule['id'],
                            'failed',
                            {'error': '无法获取帖子内容'}
                        )
                        failed += 1
                        continue
                    
                    # 等待以满足频率限制
                    self._wait_for_rate_limit(schedule['subreddit'])
                    
                    # 执行发帖
                    result = self.scraper.submit_post(
                        subreddit_name=schedule['subreddit'],
                        title=post['title'],
                        content=post['content'],
                        flair_text=None,  # 可以从计划中获取
                        kind='self'
                    )
                    
                    if result.get('success'):
                        # 更新状态为已发布
                        posting_result = {
                            'post_id': result.get('post_id'),
                            'url': result.get('url'),
                            'permalink': result.get('url', ''),
                            'posted_at': datetime.utcnow().isoformat()
                        }
                        
                        self.schedule_manager.update_schedule_status(
                            schedule['id'],
                            'posted',
                            posting_result
                        )
                        
                        # 更新帖子状态为已发布
                        self.post_manager.update_post(
                            schedule['post_content_id'],
                            status='published'
                        )
                        
                        logger.info(f"✅ 计划 {schedule['id']} 发布成功: {result.get('post_id')}")
                        succeeded += 1
                    else:
                        # 更新状态为失败
                        error_msg = result.get('error', '未知错误')
                        error_type = result.get('error_type', '')
                        suggestion = result.get('suggestion', '')
                        
                        # 如果是认证错误，记录更详细的信息
                        if error_type == 'authentication_required':
                            logger.error(f"❌ 计划 {schedule['id']} 发布失败（认证问题）: {error_msg}")
                            if suggestion:
                                logger.warning(f"💡 建议: {suggestion}")
                        else:
                            logger.error(f"❌ 计划 {schedule['id']} 发布失败: {error_msg}")
                        
                        self.schedule_manager.update_schedule_status(
                            schedule['id'],
                            'failed',
                            {
                                'error': error_msg,
                                'error_type': error_type,
                                'suggestion': suggestion
                            }
                        )
                        failed += 1
                    
                    executed += 1
                    
                except Exception as e:
                    logger.error(f"执行计划 {schedule['id']} 时发生异常: {str(e)}", exc_info=True)
                    self.schedule_manager.update_schedule_status(
                        schedule['id'],
                        'failed',
                        {'error': str(e)}
                    )
                    failed += 1
                    executed += 1
            
            return {
                'success': True,
                'executed': executed,
                'succeeded': succeeded,
                'failed': failed
            }
            
        except Exception as e:
            logger.error(f"执行发布计划失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'executed': 0,
                'succeeded': 0,
                'failed': 0
            }

    def execute_next_batch(self) -> Dict[str, Any]:
        """
        执行下一个“批次”（同一 post_content_id 下的多个子版块计划，通常为3条）。
        目的：保证“同一篇帖子同时在3个子版块发布”时，不被2小时/8小时窗口的逻辑误伤（批次内允许秒级错峰）。
        
        Returns:
            {success, executed, succeeded, failed, post_content_id, schedule_ids}
        """
        try:
            if not self.scraper or not self.scraper.is_authenticated():
                return {'success': False, 'error': 'Reddit API未认证或认证已过期', 'executed': 0, 'succeeded': 0, 'failed': 0}

            # 取一批到期任务，选择最早的一条作为“下一个批次”的入口
            pending = self.schedule_manager.get_pending_schedules(limit=50)
            if not pending:
                return {'success': True, 'message': '没有待发布的计划', 'executed': 0, 'succeeded': 0, 'failed': 0}

            first = pending[0]
            post_content_id = first['post_content_id']

            # 拉取该post_content_id下的所有到期/即将到期（<= now+2min）的计划，按posting_order执行
            session = self.db.get_session()
            try:
                now = datetime.utcnow()
                grace = now + timedelta(minutes=2)
                schedules = session.query(self.db.PostingSchedule).filter(
                    self.db.PostingSchedule.post_content_id == post_content_id,
                    self.db.PostingSchedule.status.in_(['pending', 'approved']),
                    self.db.PostingSchedule.scheduled_time <= grace
                ).order_by(
                    self.db.PostingSchedule.scheduled_time.asc(),
                    self.db.PostingSchedule.posting_order.asc()
                ).all()
            finally:
                session.close()

            if not schedules:
                # 入口任务尚未到期（极少），让下次轮询处理
                return {'success': True, 'message': '批次未到期', 'executed': 0, 'succeeded': 0, 'failed': 0}

            executed = 0
            succeeded = 0
            failed = 0
            schedule_ids: List[int] = []

            # 获取帖子内容一次即可
            post = self.post_manager.get_post(post_content_id)
            if not post:
                # 标记这些计划为失败
                for sch in schedules:
                    try:
                        self.schedule_manager.update_schedule_status(sch.id, 'failed', {'error': '无法获取帖子内容'})
                    except Exception:
                        pass
                return {'success': False, 'error': '无法获取帖子内容', 'executed': len(schedules), 'succeeded': 0, 'failed': len(schedules), 'post_content_id': post_content_id}

            for sch in schedules:
                schedule_ids.append(sch.id)
                try:
                    self.schedule_manager.update_schedule_status(sch.id, 'posting')

                    # 子版块级限速（保留原逻辑）
                    self._wait_for_rate_limit(sch.subreddit)

                    result = self.scraper.submit_post(
                        subreddit_name=sch.subreddit,
                        title=post['title'],
                        content=post['content'],
                        flair_text=None,
                        kind='self'
                    )

                    if result.get('success'):
                        posting_result = {
                            'post_id': result.get('post_id'),
                            'url': result.get('url'),
                            'permalink': result.get('url', ''),
                            'posted_at': datetime.utcnow().isoformat()
                        }
                        self.schedule_manager.update_schedule_status(sch.id, 'posted', posting_result)
                        succeeded += 1
                    else:
                        # 保存完整的错误信息，包括 error_type 和 suggestion
                        error_msg = result.get('error', '未知错误')
                        error_type = result.get('error_type', 'unknown')
                        suggestion = result.get('suggestion', '')
                        error_info = {
                            'error': error_msg,
                            'error_type': error_type,
                            'suggestion': suggestion
                        }
                        self.schedule_manager.update_schedule_status(sch.id, 'failed', error_info)
                        logger.error(f"❌ 计划 {sch.id} 发布失败: {error_msg} (类型: {error_type}, 建议: {suggestion})")
                        failed += 1

                    executed += 1
                except Exception as e:
                    try:
                        self.schedule_manager.update_schedule_status(sch.id, 'failed', {'error': str(e)})
                    except Exception:
                        pass
                    executed += 1
                    failed += 1

            # 批次至少成功1个子版块则认为批次成功，并更新帖子状态
            if succeeded > 0:
                try:
                    self.post_manager.update_post(post_content_id, status='published')
                except Exception:
                    pass

            return {
                'success': True,
                'executed': executed,
                'succeeded': succeeded,
                'failed': failed,
                'post_content_id': post_content_id,
                'schedule_ids': schedule_ids
            }
        except Exception as e:
            logger.error(f"执行批次失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e), 'executed': 0, 'succeeded': 0, 'failed': 0}
    
    def execute_single_schedule(self, schedule_id: int) -> Dict[str, Any]:
        """
        执行单个发布计划
        
        Args:
            schedule_id: 计划ID
        
        Returns:
            执行结果
        """
        try:
            # 检查Reddit API认证
            if not self.scraper or not self.scraper.is_authenticated():
                return {
                    'success': False,
                    'error': 'Reddit API未认证或认证已过期'
                }
            
            # 获取计划信息
            session = self.db.get_session()
            try:
                schedule_obj = session.query(self.db.PostingSchedule).filter(
                    self.db.PostingSchedule.id == schedule_id
                ).first()
                
                if not schedule_obj:
                    return {
                        'success': False,
                        'error': '计划不存在'
                    }
                
                if schedule_obj.status not in ['pending', 'approved']:
                    return {
                        'success': False,
                        'error': f'计划状态不允许发布: {schedule_obj.status}'
                    }
                
                # 更新状态为发布中
                self.schedule_manager.update_schedule_status(schedule_id, 'posting')
                
                # 获取帖子内容
                post = self.post_manager.get_post(schedule_obj.post_content_id)
                if not post:
                    self.schedule_manager.update_schedule_status(
                        schedule_id,
                        'failed',
                        {'error': '无法获取帖子内容'}
                    )
                    return {
                        'success': False,
                        'error': '无法获取帖子内容'
                    }
                
                # 等待以满足频率限制
                self._wait_for_rate_limit(schedule_obj.subreddit)
                
                # 执行发帖
                result = self.scraper.submit_post(
                    subreddit_name=schedule_obj.subreddit,
                    title=post['title'],
                    content=post['content'],
                    flair_text=None,
                    kind='self'
                )
                
                if result.get('success'):
                    # 更新状态为已发布
                    posting_result = {
                        'post_id': result.get('post_id'),
                        'url': result.get('url'),
                        'permalink': result.get('url', ''),
                        'posted_at': datetime.utcnow().isoformat()
                    }
                    
                    self.schedule_manager.update_schedule_status(
                        schedule_id,
                        'posted',
                        posting_result
                    )
                    
                    # 重要：立即执行成功后，取消同一 post_content_id 下的所有其他 pending 计划
                    # 避免定时任务在原定时间重复执行
                    try:
                        other_schedules = session.query(self.db.PostingSchedule).filter(
                            self.db.PostingSchedule.post_content_id == schedule_obj.post_content_id,
                            self.db.PostingSchedule.id != schedule_id,
                            self.db.PostingSchedule.status.in_(['pending', 'approved'])
                        ).all()
                        
                        if other_schedules:
                            cancelled_count = 0
                            for other_sch in other_schedules:
                                try:
                                    self.schedule_manager.update_schedule_status(
                                        other_sch.id,
                                        'cancelled',
                                        {
                                            'reason': f'已通过立即执行完成发布（计划ID: {schedule_id}）',
                                            'cancelled_at': datetime.utcnow().isoformat()
                                        }
                                    )
                                    cancelled_count += 1
                                except Exception as cancel_e:
                                    logger.warning(f"取消计划 {other_sch.id} 失败: {str(cancel_e)}")
                            
                            if cancelled_count > 0:
                                logger.info(f"✅ 已取消 {cancelled_count} 个相关计划，避免重复发布")
                    except Exception as cancel_all_e:
                        logger.warning(f"取消相关计划时发生异常: {str(cancel_all_e)}")
                    
                    # 更新帖子状态为已发布
                    self.post_manager.update_post(
                        schedule_obj.post_content_id,
                        status='published'
                    )
                    
                    logger.info(f"✅ 计划 {schedule_id} 发布成功: {result.get('post_id')}")
                    return {
                        'success': True,
                        'post_id': result.get('post_id'),
                        'url': result.get('url')
                    }
                else:
                    # 更新状态为失败
                    error_msg = result.get('error', '未知错误')
                    self.schedule_manager.update_schedule_status(
                        schedule_id,
                        'failed',
                        {'error': error_msg}
                    )
                    logger.error(f"❌ 计划 {schedule_id} 发布失败: {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg
                    }
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"执行计划 {schedule_id} 失败: {str(e)}", exc_info=True)
            try:
                self.schedule_manager.update_schedule_status(
                    schedule_id,
                    'failed',
                    {'error': str(e)}
                )
            except:
                pass
            return {
                'success': False,
                'error': str(e)
            }


