"""
自动化调度器 - 精简版
负责扫描新帖、评分、加入队列
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, time as dt_time
from database import DatabaseManager
from reddit_scraper import RedditScraper
from rpta_scorer import RPTAScorer
from task_executor import TaskExecutor
from auto_config import AutoConfig

logger = logging.getLogger(__name__)

class AutoScheduler:
    """自动化任务调度器"""
    
    def __init__(self, db_manager: DatabaseManager,
                 scraper: RedditScraper,
                 scorer: RPTAScorer,
                 executor: TaskExecutor,
                 config: AutoConfig):
        """
        初始化调度器
        
        Args:
            db_manager: DatabaseManager实例
            scraper: RedditScraper实例
            scorer: RPTAScorer实例
            executor: TaskExecutor实例
            config: AutoConfig实例
        """
        self.db = db_manager
        self.scraper = scraper
        self.scorer = scorer
        self.executor = executor
        self.config = config
    
    def scan_and_score_posts(self, subreddit: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        扫描子版块新帖并评分
        
        Args:
            subreddit: 子版块名称
            limit: 扫描数量限制
            
        Returns:
            评分后的帖子列表（按评分降序）
        """
        try:
            # 获取新帖
            posts = self.scraper.get_subreddit_posts(subreddit, limit=limit, sort='new')
            
            if not posts:
                logger.warning(f"子版块 {subreddit} 没有获取到帖子")
                return []
            
            # 获取配置
            rpta_config = self.config.get_rpta_config() or self.config.get_default_config()
            s_min = rpta_config.get('thresholds', {}).get('s_min', 0.5)
            
            scored_posts = []
            
            # 优化方案3：使用批量评分
            try:
                batch_results = self.scorer.calculate_batch_scores(posts, provider="deepseek")
                for post, score_result in zip(posts, batch_results):
                    try:
                        total_score = score_result.get('total_score', 0.0)
                        if total_score >= s_min:
                            scored_posts.append({
                                'post': post,
                                'score_result': score_result,
                                'total_score': total_score
                            })
                    except Exception as e:
                        logger.error(f"处理评分结果失败 {post.get('id', 'unknown')}: {str(e)}")
                        continue
            except Exception as e:
                logger.warning(f"批量评分失败，回退到单独评分: {str(e)}")
                # 回退到单独评分
                for post in posts:
                    try:
                        score_result = self.scorer.calculate_total_score(post)
                        total_score = score_result.get('total_score', 0.0)
                        if total_score >= s_min:
                            scored_posts.append({
                                'post': post,
                                'score_result': score_result,
                                'total_score': total_score
                            })
                    except Exception as e:
                        logger.error(f"评分帖子失败 {post.get('id', 'unknown')}: {str(e)}")
                        continue
            
            # 按评分降序排序
            scored_posts.sort(key=lambda x: x['total_score'], reverse=True)
            
            logger.info(f"扫描 {subreddit}: 共 {len(posts)} 个帖子，{len(scored_posts)} 个通过阈值")
            return scored_posts
            
        except Exception as e:
            logger.error(f"扫描子版块失败: {str(e)}")
            return []
    
    def search_and_score_by_keywords(self, keywords: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        根据关键词搜索Reddit帖子并评分
        
        Args:
            keywords: 搜索关键词（逗号分隔或单个关键词）
            limit: 搜索数量限制
            
        Returns:
            评分后的帖子列表（按评分降序）
        """
        try:
            # 使用全站搜索，限制6个月内
            posts = self.scraper.search_all_posts(query=keywords, limit=limit, sort='new', months_back=6)
            
            if not posts:
                logger.warning(f"关键词 '{keywords}' 没有搜索到帖子")
                return []
            
            # 获取配置
            rpta_config = self.config.get_rpta_config() or self.config.get_default_config()
            s_min = rpta_config.get('thresholds', {}).get('s_min', 0.5)
            
            scored_posts = []
            
            # 优化方案3：使用批量评分
            try:
                batch_results = self.scorer.calculate_batch_scores(posts, provider="deepseek")
                
                # 调试：统计评分分布
                total_scores = [r.get('total_score', 0.0) for r in batch_results if r]
                if total_scores:
                    avg_score = sum(total_scores) / len(total_scores)
                    max_score = max(total_scores)
                    min_score = min(total_scores)
                    passed_count = sum(1 for s in total_scores if s >= s_min)
                    logger.info(f"评分统计: 总数={len(total_scores)}, 平均={avg_score:.3f}, 最高={max_score:.3f}, 最低={min_score:.3f}, 通过阈值={passed_count} (阈值={s_min:.2f})")
                    
                    # 如果所有评分都很低，记录详细信息
                    if max_score < s_min and len(total_scores) > 0:
                        logger.warning(f"⚠️ 所有帖子评分都低于阈值 {s_min:.2f}，最高分={max_score:.3f}")
                        # 记录前5个最高分的详细信息
                        sorted_results = sorted(zip(posts, batch_results), key=lambda x: x[1].get('total_score', 0), reverse=True)
                        for i, (post, score_result) in enumerate(sorted_results[:5]):
                            logger.debug(f"  帖子{i+1}: score={score_result.get('total_score', 0):.3f}, R={score_result.get('r_score', 0):.3f}, P={score_result.get('p_score', 0):.3f}, T={score_result.get('t_score', 0):.3f}, A={score_result.get('a_score', 0):.3f}")
                
                for post, score_result in zip(posts, batch_results):
                    try:
                        total_score = score_result.get('total_score', 0.0)
                        if total_score >= s_min:
                            scored_posts.append({
                                'post': post,
                                'score_result': score_result,
                                'total_score': total_score
                            })
                    except Exception as e:
                        logger.error(f"处理评分结果失败 {post.get('id', 'unknown')}: {str(e)}")
                        continue
            except Exception as e:
                logger.warning(f"批量评分失败，回退到单独评分: {str(e)}", exc_info=True)
                # 回退到单独评分
                for post in posts:
                    try:
                        score_result = self.scorer.calculate_total_score(post)
                        total_score = score_result.get('total_score', 0.0)
                        if total_score >= s_min:
                            scored_posts.append({
                                'post': post,
                                'score_result': score_result,
                                'total_score': total_score
                            })
                    except Exception as e:
                        logger.error(f"评分帖子失败 {post.get('id', 'unknown')}: {str(e)}")
                        continue
            
            # 按评分降序排序
            scored_posts.sort(key=lambda x: x['total_score'], reverse=True)
            
            logger.info(f"关键词搜索 '{keywords}': 共 {len(posts)} 个帖子，{len(scored_posts)} 个通过阈值")
            return scored_posts
            
        except Exception as e:
            logger.error(f"关键词搜索失败: {str(e)}")
            return []
    
    def process_keywords(self, keywords: str, limit: int = 100, progress_callback=None) -> Dict[str, Any]:
        """
        处理关键词：搜索、评分、加入队列
        
        Args:
            keywords: 搜索关键词
            limit: 搜索数量
            progress_callback: 进度回调函数，接收(status, message)参数
            
        Returns:
            处理结果统计
        """
        try:
            # 步骤1: 搜索帖子
            if progress_callback:
                progress_callback('info', f"🔍 开始搜索关键词: {keywords}")
            
            posts = self.scraper.search_all_posts(query=keywords, limit=limit, sort='new', months_back=6)
            total_posts = len(posts) if posts else 0
            
            if progress_callback:
                progress_callback('info', f"📊 搜索完成: 找到 {total_posts} 个帖子（6个月内）")
            
            if not posts:
                return {
                    'success': True,
                    'keywords': keywords,
                    'total_searched': 0,
                    'scored': 0,
                    'added_to_queue': 0,
                    'message': '未找到相关帖子'
                }
            
            # 步骤2: 评分
            if progress_callback:
                progress_callback('info', f"📝 开始评分 {total_posts} 个帖子...")
            
            rpta_config = self.config.get_rpta_config() or self.config.get_default_config()
            s_min = rpta_config.get('thresholds', {}).get('s_min', 0.5)
            
            scored_posts = []
            scored_count = 0
            
            # 优化方案3：使用批量评分
            try:
                # 批量评分所有帖子
                batch_results = self.scorer.calculate_batch_scores(posts, provider="deepseek")
                
                # 处理批量评分结果
                for i, (post, score_result) in enumerate(zip(posts, batch_results)):
                    try:
                        total_score = score_result.get('total_score', 0.0)
                        scored_count += 1
                        
                        if total_score >= s_min:
                            scored_posts.append({
                                'post': post,
                                'score_result': score_result,
                                'total_score': total_score
                            })
                        
                        # 每10个帖子报告一次进度
                        if (i + 1) % 10 == 0 and progress_callback:
                            progress_callback('info', f"📝 已评分 {i + 1}/{total_posts} 个帖子，通过 {len(scored_posts)} 个")
                            
                    except Exception as e:
                        logger.error(f"处理评分结果失败 {post.get('id', 'unknown')}: {str(e)}")
                        continue
            except Exception as e:
                logger.warning(f"批量评分失败，回退到单独评分: {str(e)}")
                # 回退到单独评分
                for i, post in enumerate(posts):
                    try:
                        score_result = self.scorer.calculate_total_score(post)
                        total_score = score_result.get('total_score', 0.0)
                        scored_count += 1
                        
                        if total_score >= s_min:
                            scored_posts.append({
                                'post': post,
                                'score_result': score_result,
                                'total_score': total_score
                            })
                        
                        if (i + 1) % 10 == 0 and progress_callback:
                            progress_callback('info', f"📝 已评分 {i + 1}/{total_posts} 个帖子，通过 {len(scored_posts)} 个")
                            
                    except Exception as e:
                        logger.error(f"评分帖子失败 {post.get('id', 'unknown')}: {str(e)}")
                        continue
            
            # 按评分降序排序
            scored_posts.sort(key=lambda x: x['total_score'], reverse=True)
            
            if progress_callback:
                progress_callback('info', f"✅ 评分完成: 共评分 {scored_count} 个，通过阈值 {len(scored_posts)} 个（阈值: {s_min:.2f}）")
            
            # 步骤3: 添加到队列
            if progress_callback:
                progress_callback('info', f"📥 开始将 {len(scored_posts)} 个帖子加入执行队列...")
            
            added_count = 0
            for i, item in enumerate(scored_posts):
                try:
                    task_id = self.add_to_queue(
                        item['post'],
                        item['score_result'],
                        item['post'].get('subreddit', 'unknown')
                    )
                    if task_id:
                        added_count += 1
                    
                    # 每10个报告一次进度
                    if (i + 1) % 10 == 0 and progress_callback:
                        progress_callback('info', f"📥 已加入队列 {i + 1}/{len(scored_posts)} 个任务")
                        
                except Exception as e:
                    logger.error(f"加入队列失败: {str(e)}")
                    continue
            
            if progress_callback:
                progress_callback('success', f"✅ 处理完成: 搜索 {total_posts} 个 → 评分 {scored_count} 个 → 通过 {len(scored_posts)} 个 → 加入队列 {added_count} 个")
            
            return {
                'success': True,
                'keywords': keywords,
                'total_searched': total_posts,
                'scored': scored_count,
                'passed_threshold': len(scored_posts),
                'added_to_queue': added_count
            }
            
        except Exception as e:
            logger.error(f"处理关键词失败: {str(e)}")
            if progress_callback:
                progress_callback('error', f"❌ 处理失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'keywords': keywords
            }
    
    def add_to_queue(self, post_data: Dict[str, Any], 
                    score_result: Dict[str, Any],
                    subreddit: str) -> Optional[int]:
        """
        将帖子添加到执行队列
        
        Args:
            post_data: 帖子数据
            score_result: 评分结果
            subreddit: 子版块名称
            
        Returns:
            队列任务ID
        """
        try:
            # 获取配置
            rpta_config = self.config.get_rpta_config() or self.config.get_default_config()
            thresholds = rpta_config.get('thresholds', {})
            
            total_score = score_result.get('total_score', 0.0)
            
            # 确定互动类型
            if total_score >= thresholds.get('deep', 0.85):
                interaction_type = 'deep'
            elif total_score >= thresholds.get('standard', 0.65):
                interaction_type = 'standard'
            elif total_score >= thresholds.get('light', 0.50):
                interaction_type = 'light'
            else:
                return None  # 低于最低阈值，不加入队列
            
            # 确保帖子数据保存到数据库（防止恢复执行时找不到数据）
            try:
                self.db.save_posts([post_data])
            except Exception as e:
                logger.warning(f"保存帖子数据到数据库失败: {str(e)}")
                # 继续执行，因为可能已经存在
            
            # 生成AI评论（如果需要）
            ai_comment = None
            if interaction_type in ['deep', 'standard']:
                ai_comment = self.executor.generate_ai_comment(
                    post_data, 
                    interaction_type
                )
            
            # 添加到队列
            task_id = self.db.add_to_interaction_queue(
                post_id=post_data.get('id'),
                subreddit=subreddit,
                interaction_type=interaction_type,
                post_score=total_score,
                ai_comment=ai_comment
            )
            
            return task_id
            
        except Exception as e:
            logger.error(f"添加到队列失败: {str(e)}")
            return None
    
    def process_subreddit(self, subreddit: str, limit: int = 50) -> Dict[str, Any]:
        """
        处理单个子版块：扫描、评分、加入队列
        
        Args:
            subreddit: 子版块名称
            limit: 扫描数量
            
        Returns:
            处理结果统计
        """
        try:
            # 扫描并评分
            scored_posts = self.scan_and_score_posts(subreddit, limit)
            
            # 添加到队列
            added_count = 0
            for item in scored_posts:
                task_id = self.add_to_queue(
                    item['post'],
                    item['score_result'],
                    subreddit
                )
                if task_id:
                    added_count += 1
            
            return {
                'success': True,
                'subreddit': subreddit,
                'scanned': len(scored_posts),
                'added_to_queue': added_count
            }
            
        except Exception as e:
            logger.error(f"处理子版块失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'subreddit': subreddit
            }
    
    def is_scan_time(self) -> bool:
        """检查当前是否在扫描时间段内"""
        try:
            rpta_config = self.config.get_rpta_config() or self.config.get_default_config()
            scan_time = rpta_config.get('scan_time', {})
            
            start_str = scan_time.get('start', '08:00')
            end_str = scan_time.get('end', '17:00')
            
            # 解析时间
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
            current_time = datetime.now().time()
            
            return start_time <= current_time <= end_time
            
        except Exception as e:
            logger.error(f"检查扫描时间失败: {str(e)}")
            return True  # 默认允许扫描
    
    def is_execution_time(self) -> bool:
        """检查当前是否在执行时间段内"""
        try:
            scheduler_config = self.config.get_scheduler_config() or self.config.get_default_scheduler_config()
            exec_time = scheduler_config.get('execution_time', {})
            
            start_str = exec_time.get('start', '08:00')
            end_str = exec_time.get('end', '20:00')
            
            # 解析时间
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
            current_time = datetime.now().time()
            
            return start_time <= current_time <= end_time
            
        except Exception as e:
            logger.error(f"检查执行时间失败: {str(e)}")
            return True  # 默认允许执行
    
    def get_today_execution_count(self, interaction_type: str) -> int:
        """获取今日已执行的指定类型任务数"""
        try:
            today = datetime.now().date()
            session = self.db.SessionLocal()
            try:
                # 统计今日已完成的指定类型任务
                count = session.query(self.db.AutoInteractionQueue).filter(
                    self.db.AutoInteractionQueue.interaction_type == interaction_type,
                    self.db.AutoInteractionQueue.status == 'completed',
                    self.db.AutoInteractionQueue.executed_at >= datetime.combine(today, datetime.min.time())
                ).count()
                return count
            finally:
                session.close()
        except Exception as e:
            logger.error(f"获取今日执行次数失败: {str(e)}")
            return 0
    
    def can_execute_task(self, interaction_type: str) -> bool:
        """检查是否可以执行指定类型的任务"""
        try:
            # 1. 检查是否在执行时间段内
            if not self.is_execution_time():
                return False
            
            # 2. 检查每日执行次数限制
            scheduler_config = self.config.get_scheduler_config() or self.config.get_default_scheduler_config()
            exec_limits = scheduler_config.get('execution_limits', {})
            
            limit_key = interaction_type  # 'deep', 'standard', 'light'
            limit = exec_limits.get(limit_key, 0)
            
            # 如果限制为0，表示不允许执行该类型任务
            if limit == 0:
                logger.debug(f"{interaction_type}类型任务限制为0，跳过执行")
                return False
            
            # 如果限制大于0，检查是否已达上限
            if limit > 0:
                today_count = self.get_today_execution_count(interaction_type)
                if today_count >= limit:
                    logger.info(f"{interaction_type}类型任务今日已达上限: {today_count}/{limit}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查执行条件失败: {str(e)}")
            return False
    
    def get_next_pending_task(self) -> Optional[Dict[str, Any]]:
        """获取下一个待执行的任务"""
        try:
            # 取一批任务，避免队列头部任务因“配额=0/达上限”导致一直卡住
            pending_tasks = self.db.get_pending_interactions(limit=50)
            if not pending_tasks:
                return None

            # 计算当前可执行的类型集合（基于时间段+每日次数限制）
            allowed_types = set()
            for t in ['deep', 'standard', 'light']:
                if self.can_execute_task(t):
                    allowed_types.add(t)

            if not allowed_types:
                # 当前没有任何类型可执行（可能是配额为0/已达上限/不在执行时间段）
                return None

            for task in pending_tasks:
                if task.get('interaction_type') in allowed_types:
                    return task
            # 有待执行任务，但全都属于不可执行类型
            return None
        except Exception as e:
            logger.error(f"获取待执行任务失败: {str(e)}")
            return None
    
    def execute_next_task(self) -> Dict[str, Any]:
        """执行下一个符合条件的任务"""
        try:
            # 获取下一个待执行任务
            task = self.get_next_pending_task()
            if not task:
                # 可能是“没有任务”，也可能是“任务都不可执行”
                pending_preview = self.db.get_pending_interactions(limit=5)
                if pending_preview:
                    return {
                        'success': False,
                        'error': '不满足执行条件（时间或次数限制）',
                        'blocked': True,
                        'pending_preview': pending_preview
                    }
                return {'success': False, 'error': '没有待执行任务'}
            
            # 检查是否可以执行
            if not self.can_execute_task(task['interaction_type']):
                return {'success': False, 'error': '不满足执行条件（时间或次数限制）'}
            
            # 执行任务
            result = self.executor.execute_task(task['id'])
            
            # 更新统计
            if result.get('success'):
                try:
                    status = self.db.get_status()
                    if status:
                        self.db.update_status(total_executed=(status.get('total_executed', 0) + 1))
                except:
                    pass
            
            return result
            
        except Exception as e:
            logger.error(f"执行任务失败: {str(e)}")
            return {'success': False, 'error': str(e)}

