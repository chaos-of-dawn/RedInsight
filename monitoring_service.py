"""
后台监控服务
监控Reddit帖子的互动情况，包括新回复、点赞等
"""
import logging
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from database import DatabaseManager
from reddit_scraper import RedditScraper

logger = logging.getLogger(__name__)

class MonitoringService:
    """后台监控服务"""
    
    def __init__(self, db_manager: DatabaseManager, reddit_scraper: RedditScraper):
        self.db_manager = db_manager
        self.reddit_scraper = reddit_scraper
        self.is_running = False
        self.monitor_thread = None
        
        # 智能监控间隔设置（适配发帖场景）
        self.monitor_intervals = {
            'new_post': 1800,      # 30分钟 - 新帖子（发布24小时内）
            'active_post': 900,    # 15分钟 - 高互动帖子（评论数>10或分数>50）
            'normal_post': 3600,   # 1小时 - 普通帖子
            'old_post': 7200       # 2小时 - 老帖子（发布7天后）
        }
        
        # 默认使用普通帖子间隔
        self.check_interval = self.monitor_intervals['normal_post']
    
    def _determine_post_type(self, post_id: str) -> str:
        """
        根据帖子特征确定监控类型
        
        Args:
            post_id: 帖子ID
            
        Returns:
            帖子类型：new_post, active_post, normal_post, old_post
        """
        try:
            # 获取帖子信息
            submission = self.reddit_scraper.reddit.submission(id=post_id)
            
            # 计算帖子年龄（小时）
            post_age_hours = (datetime.utcnow().timestamp() - submission.created_utc) / 3600
            
            # 获取互动数据
            score = submission.score
            num_comments = submission.num_comments
            
            # 判断帖子类型
            if post_age_hours < 24:
                return 'new_post'  # 新帖子
            elif post_age_hours > 168:  # 7天
                return 'old_post'  # 老帖子
            elif score > 50 or num_comments > 10:
                return 'active_post'  # 高互动帖子
            else:
                return 'normal_post'  # 普通帖子
                
        except Exception as e:
            logger.error(f"确定帖子类型失败: {str(e)}")
            return 'normal_post'  # 默认普通帖子
    
    def _get_optimal_interval(self, post_id: str) -> int:
        """
        获取最优监控间隔
        
        Args:
            post_id: 帖子ID
            
        Returns:
            监控间隔（秒）
        """
        try:
            post_type = self._determine_post_type(post_id)
            return self.monitor_intervals.get(post_type, self.monitor_intervals['normal_post'])
        except Exception as e:
            logger.error(f"获取最优间隔失败: {str(e)}")
            return self.monitor_intervals['normal_post']
    
    def start_monitoring(self):
        """启动监控服务"""
        if self.is_running:
            logger.warning("监控服务已在运行")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("监控服务已启动")
    
    def stop_monitoring(self):
        """停止监控服务"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("监控服务已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                self._check_all_monitored_posts()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"监控循环出错: {str(e)}")
                time.sleep(60)  # 出错时等待1分钟再继续
    
    def _check_all_monitored_posts(self):
        """检查所有监控的帖子"""
        try:
            session = self.db_manager.get_session()
            try:
                # 获取所有活跃的监控记录
                monitors = session.query(self.db_manager.PostMonitoring).filter(
                    self.db_manager.PostMonitoring.is_active == True
                ).all()
                
                logger.info(f"检查 {len(monitors)} 个监控的帖子")
                
                for monitor in monitors:
                    try:
                        self._check_single_post(monitor)
                    except Exception as e:
                        logger.error(f"检查帖子 {monitor.post_id} 失败: {str(e)}")
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"检查监控帖子失败: {str(e)}")
    
    def _check_single_post(self, monitor):
        """检查单个帖子"""
        try:
            post_id = monitor.post_id
            monitor_types = monitor.monitor_type.split(',')
            
            # 获取帖子当前信息
            submission = self.reddit_scraper.reddit.submission(id=post_id)
            
            # 检查各种监控类型
            changes_detected = False
            
            if 'comments' in monitor_types:
                if self._check_comments_change(submission, monitor):
                    changes_detected = True
            
            if 'votes' in monitor_types:
                if self._check_votes_change(submission, monitor):
                    changes_detected = True
            
            if 'saves' in monitor_types:
                if self._check_saves_change(submission, monitor):
                    changes_detected = True
            
            # 更新最后检查时间
            session = self.db_manager.get_session()
            try:
                monitor.last_check_time = datetime.utcnow()
                session.commit()
            finally:
                session.close()
            
            if changes_detected:
                logger.info(f"检测到帖子 {post_id} 的变化")
                self._handle_post_changes(post_id, submission)
                
        except Exception as e:
            logger.error(f"检查单个帖子失败: {str(e)}")
    
    def _check_comments_change(self, submission, monitor) -> bool:
        """检查评论变化"""
        try:
            # 获取当前评论数
            current_comments = submission.num_comments
            
            # 从数据库获取上次的评论数
            session = self.db_manager.get_session()
            try:
                stats = session.query(self.db_manager.InteractionStats).filter(
                    self.db_manager.InteractionStats.post_id == submission.id
                ).first()
                
                if stats:
                    last_comments = stats.total_comments
                    if current_comments > last_comments:
                        # 更新评论数
                        stats.total_comments = current_comments
                        stats.last_updated = datetime.utcnow()
                        session.commit()
                        return True
                else:
                    # 创建新的统计记录
                    stats = self.db_manager.InteractionStats(
                        post_id=submission.id,
                        subreddit_name=str(submission.subreddit),
                        total_comments=current_comments
                    )
                    session.add(stats)
                    session.commit()
                
            finally:
                session.close()
            
            return False
            
        except Exception as e:
            logger.error(f"检查评论变化失败: {str(e)}")
            return False
    
    def _check_votes_change(self, submission, monitor) -> bool:
        """检查投票变化"""
        try:
            # 获取当前分数
            current_score = submission.score
            
            # 从数据库获取上次的分数
            session = self.db_manager.get_session()
            try:
                stats = session.query(self.db_manager.InteractionStats).filter(
                    self.db_manager.InteractionStats.post_id == submission.id
                ).first()
                
                if stats:
                    last_score = stats.total_upvotes - stats.total_downvotes
                    if abs(current_score - last_score) > 0:
                        # 更新分数（这里简化处理，实际应该区分点赞和点踩）
                        if current_score > last_score:
                            stats.total_upvotes += (current_score - last_score)
                        else:
                            stats.total_downvotes += (last_score - current_score)
                        
                        stats.last_updated = datetime.utcnow()
                        session.commit()
                        return True
                else:
                    # 创建新的统计记录
                    stats = self.db_manager.InteractionStats(
                        post_id=submission.id,
                        subreddit_name=str(submission.subreddit),
                        total_upvotes=max(0, current_score),
                        total_downvotes=max(0, -current_score)
                    )
                    session.add(stats)
                    session.commit()
                
            finally:
                session.close()
            
            return False
            
        except Exception as e:
            logger.error(f"检查投票变化失败: {str(e)}")
            return False
    
    def _check_saves_change(self, submission, monitor) -> bool:
        """检查保存变化"""
        try:
            # 这里需要特殊处理，因为Reddit API不直接提供保存数
            # 可以通过其他方式检测，比如检查帖子的热度变化
            return False
            
        except Exception as e:
            logger.error(f"检查保存变化失败: {str(e)}")
            return False
    
    def _handle_post_changes(self, post_id: str, submission):
        """处理帖子变化"""
        try:
            # 记录变化事件
            logger.info(f"帖子 {post_id} 发生变化:")
            logger.info(f"  - 标题: {submission.title}")
            logger.info(f"  - 分数: {submission.score}")
            logger.info(f"  - 评论数: {submission.num_comments}")
            logger.info(f"  - 子版块: r/{submission.subreddit}")
            
            # 这里可以添加更多处理逻辑，比如：
            # - 发送通知
            # - 更新分析数据
            # - 触发自动回复等
            
        except Exception as e:
            logger.error(f"处理帖子变化失败: {str(e)}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        try:
            session = self.db_manager.get_session()
            try:
                # 统计监控信息
                total_monitors = session.query(self.db_manager.PostMonitoring).count()
                active_monitors = session.query(self.db_manager.PostMonitoring).filter(
                    self.db_manager.PostMonitoring.is_active == True
                ).count()
                
                # 获取最近检查的帖子
                recent_checks = session.query(self.db_manager.PostMonitoring).filter(
                    self.db_manager.PostMonitoring.is_active == True
                ).order_by(
                    self.db_manager.PostMonitoring.last_check_time.desc()
                ).limit(5).all()
                
                recent_posts = []
                for monitor in recent_checks:
                    recent_posts.append({
                        'post_id': monitor.post_id,
                        'subreddit_name': monitor.subreddit_name,
                        'monitor_type': monitor.monitor_type,
                        'last_check_time': monitor.last_check_time,
                        'is_active': monitor.is_active
                    })
                
                return {
                    'is_running': self.is_running,
                    'total_monitors': total_monitors,
                    'active_monitors': active_monitors,
                    'check_interval': self.check_interval,
                    'recent_checks': recent_posts
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"获取监控状态失败: {str(e)}")
            return {
                'is_running': self.is_running,
                'error': str(e)
            }
    
    def set_check_interval(self, interval: int):
        """设置检查间隔（秒）"""
        if interval < 60:  # 最少1分钟
            interval = 60
        
        self.check_interval = interval
        logger.info(f"监控检查间隔设置为 {interval} 秒")
    
    def force_check_post(self, post_id: str) -> Dict[str, Any]:
        """强制检查指定帖子"""
        try:
            session = self.db_manager.get_session()
            try:
                monitor = session.query(self.db_manager.PostMonitoring).filter(
                    self.db_manager.PostMonitoring.post_id == post_id
                ).first()
                
                if monitor:
                    self._check_single_post(monitor)
                    return {
                        'success': True,
                        'message': f'已检查帖子 {post_id}'
                    }
                else:
                    return {
                        'success': False,
                        'error': f'未找到帖子 {post_id} 的监控记录'
                    }
                    
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"强制检查帖子失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
