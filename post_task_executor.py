"""
发帖任务执行器
执行自动发帖任务
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from database import DatabaseManager
from reddit_scraper import RedditScraper

logger = logging.getLogger(__name__)

class PostTaskExecutor:
    """发帖任务执行器"""
    
    def __init__(self, db_manager: DatabaseManager, scraper: RedditScraper):
        """
        初始化发帖任务执行器
        
        Args:
            db_manager: DatabaseManager实例
            scraper: RedditScraper实例
        """
        self.db = db_manager
        self.scraper = scraper
    
    def execute_post_task(self, task_id: int) -> Dict[str, Any]:
        """
        执行单个发帖任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            执行结果
        """
        try:
            session = self.db.SessionLocal()
            try:
                # 获取任务
                task = session.query(self.db.AutoPostQueue).filter_by(id=task_id).first()
                if not task:
                    return {'success': False, 'error': '任务不存在'}
                
                if task.status != 'pending':
                    return {'success': False, 'error': f'任务状态不是pending: {task.status}'}
                
                # 更新状态为执行中
                task.status = 'executing'
                session.commit()
                
                # 检查Reddit API认证状态
                if not self.scraper or not self.scraper.is_authenticated():
                    error_msg = "Reddit API未认证或认证已过期，无法执行发帖任务"
                    logger.error(error_msg)
                    self.db.update_post_task_status(task_id, 'failed', error_message=error_msg)
                    return {'success': False, 'error': error_msg}
                
                # 执行发帖
                result = self.scraper.submit_post(
                    subreddit_name=task.subreddit,
                    title=task.title,
                    content=task.content,
                    flair_text=task.flair,
                    kind='self'  # 文本帖子
                )
                
                if result.get('success'):
                    # 更新任务状态为完成
                    self.db.update_post_task_status(
                        task_id, 
                        'completed',
                        reddit_post_id=result.get('post_id'),
                        reddit_post_url=result.get('url')
                    )
                    logger.info(f"发帖任务 {task_id} 执行成功: {result.get('post_id')}")
                    return {
                        'success': True,
                        'post_id': result.get('post_id'),
                        'url': result.get('url')
                    }
                else:
                    error_msg = result.get('error', '未知错误')
                    logger.warning(f"发帖任务 {task_id} 执行失败: {error_msg}")
                    self.db.update_post_task_status(task_id, 'failed', error_message=error_msg)
                    return {'success': False, 'error': error_msg}
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"执行发帖任务失败: {str(e)}")
            # 更新任务状态为失败
            try:
                self.db.update_post_task_status(task_id, 'failed', error_message=str(e))
            except:
                pass
            
            return {'success': False, 'error': str(e)}




