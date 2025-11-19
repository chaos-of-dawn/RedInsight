"""
互动管理模块
管理Reddit互动功能，包括点赞、保存、关注等操作
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from database import DatabaseManager
from reddit_scraper import RedditScraper

logger = logging.getLogger(__name__)

class InteractionManager:
    """互动管理器"""
    
    def __init__(self, db_manager: DatabaseManager, reddit_scraper: RedditScraper):
        self.db_manager = db_manager
        self.reddit_scraper = reddit_scraper
    
    def upvote_post(self, post_id: str, subreddit_name: str = None) -> Dict[str, Any]:
        """
        点赞帖子并记录到数据库
        
        Args:
            post_id: 帖子ID
            subreddit_name: 子版块名称（可选）
            
        Returns:
            操作结果
        """
        try:
            # 调用Reddit API
            result = self.reddit_scraper.upvote_post(post_id)
            
            if result['success']:
                # 记录到数据库
                self._record_interaction(
                    post_id=post_id,
                    interaction_type='upvote',
                    target_subreddit=subreddit_name,
                    status='success'
                )
                
                # 更新统计
                self._update_post_stats(post_id, 'upvote')
                
                logger.info(f"成功点赞帖子 {post_id}")
            else:
                # 记录失败
                self._record_interaction(
                    post_id=post_id,
                    interaction_type='upvote',
                    target_subreddit=subreddit_name,
                    status='failed',
                    error_message=result.get('error')
                )
            
            return result
            
        except Exception as e:
            logger.error(f"点赞帖子失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def downvote_post(self, post_id: str, subreddit_name: str = None) -> Dict[str, Any]:
        """
        点踩帖子并记录到数据库
        
        Args:
            post_id: 帖子ID
            subreddit_name: 子版块名称（可选）
            
        Returns:
            操作结果
        """
        try:
            # 调用Reddit API
            result = self.reddit_scraper.downvote_post(post_id)
            
            if result['success']:
                # 记录到数据库
                self._record_interaction(
                    post_id=post_id,
                    interaction_type='downvote',
                    target_subreddit=subreddit_name,
                    status='success'
                )
                
                # 更新统计
                self._update_post_stats(post_id, 'downvote')
                
                logger.info(f"成功点踩帖子 {post_id}")
            else:
                # 记录失败
                self._record_interaction(
                    post_id=post_id,
                    interaction_type='downvote',
                    target_subreddit=subreddit_name,
                    status='failed',
                    error_message=result.get('error')
                )
            
            return result
            
        except Exception as e:
            logger.error(f"点踩帖子失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def save_post(self, post_id: str, subreddit_name: str = None) -> Dict[str, Any]:
        """
        保存帖子并记录到数据库
        
        Args:
            post_id: 帖子ID
            subreddit_name: 子版块名称（可选）
            
        Returns:
            操作结果
        """
        try:
            # 调用Reddit API
            result = self.reddit_scraper.save_post(post_id)
            
            if result['success']:
                # 记录到数据库
                self._record_interaction(
                    post_id=post_id,
                    interaction_type='save',
                    target_subreddit=subreddit_name,
                    status='success'
                )
                
                # 更新统计
                self._update_post_stats(post_id, 'save')
                
                logger.info(f"成功保存帖子 {post_id}")
            else:
                # 记录失败
                self._record_interaction(
                    post_id=post_id,
                    interaction_type='save',
                    target_subreddit=subreddit_name,
                    status='failed',
                    error_message=result.get('error')
                )
            
            return result
            
        except Exception as e:
            logger.error(f"保存帖子失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def unsave_post(self, post_id: str, subreddit_name: str = None) -> Dict[str, Any]:
        """
        取消保存帖子并记录到数据库
        
        Args:
            post_id: 帖子ID
            subreddit_name: 子版块名称（可选）
            
        Returns:
            操作结果
        """
        try:
            # 调用Reddit API
            result = self.reddit_scraper.unsave_post(post_id)
            
            if result['success']:
                # 记录到数据库
                self._record_interaction(
                    post_id=post_id,
                    interaction_type='unsave',
                    target_subreddit=subreddit_name,
                    status='success'
                )
                
                logger.info(f"成功取消保存帖子 {post_id}")
            else:
                # 记录失败
                self._record_interaction(
                    post_id=post_id,
                    interaction_type='unsave',
                    target_subreddit=subreddit_name,
                    status='failed',
                    error_message=result.get('error')
                )
            
            return result
            
        except Exception as e:
            logger.error(f"取消保存帖子失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def follow_user(self, username: str) -> Dict[str, Any]:
        """
        关注用户并记录到数据库
        
        Args:
            username: 用户名
            
        Returns:
            操作结果
        """
        try:
            # 调用Reddit API
            result = self.reddit_scraper.follow_user(username)
            
            if result['success']:
                # 记录到数据库
                self._record_user_follow(username, 'follow')
                
                logger.info(f"成功关注用户 {username}")
            else:
                logger.error(f"关注用户失败: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"关注用户失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def unfollow_user(self, username: str) -> Dict[str, Any]:
        """
        取消关注用户并记录到数据库
        
        Args:
            username: 用户名
            
        Returns:
            操作结果
        """
        try:
            # 调用Reddit API
            result = self.reddit_scraper.unfollow_user(username)
            
            if result['success']:
                # 记录到数据库
                self._record_user_follow(username, 'unfollow')
                
                logger.info(f"成功取消关注用户 {username}")
            else:
                logger.error(f"取消关注用户失败: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"取消关注用户失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def subscribe_subreddit(self, subreddit_name: str) -> Dict[str, Any]:
        """
        订阅子版块并记录到数据库
        
        Args:
            subreddit_name: 子版块名称
            
        Returns:
            操作结果
        """
        try:
            # 调用Reddit API
            result = self.reddit_scraper.subscribe_subreddit(subreddit_name)
            
            if result['success']:
                # 记录到数据库
                self._record_interaction(
                    post_id=None,
                    interaction_type='subscribe',
                    target_subreddit=subreddit_name,
                    status='success'
                )
                
                logger.info(f"成功订阅子版块 r/{subreddit_name}")
            else:
                # 记录失败
                self._record_interaction(
                    post_id=None,
                    interaction_type='subscribe',
                    target_subreddit=subreddit_name,
                    status='failed',
                    error_message=result.get('error')
                )
            
            return result
            
        except Exception as e:
            logger.error(f"订阅子版块失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def unsubscribe_subreddit(self, subreddit_name: str) -> Dict[str, Any]:
        """
        取消订阅子版块并记录到数据库
        
        Args:
            subreddit_name: 子版块名称
            
        Returns:
            操作结果
        """
        try:
            # 调用Reddit API
            result = self.reddit_scraper.unsubscribe_subreddit(subreddit_name)
            
            if result['success']:
                # 记录到数据库
                self._record_interaction(
                    post_id=None,
                    interaction_type='unsubscribe',
                    target_subreddit=subreddit_name,
                    status='success'
                )
                
                logger.info(f"成功取消订阅子版块 r/{subreddit_name}")
            else:
                # 记录失败
                self._record_interaction(
                    post_id=None,
                    interaction_type='unsubscribe',
                    target_subreddit=subreddit_name,
                    status='failed',
                    error_message=result.get('error')
                )
            
            return result
            
        except Exception as e:
            logger.error(f"取消订阅子版块失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def start_monitoring_post(self, post_id: str, subreddit_name: str, 
                            monitor_types: List[str] = None) -> Dict[str, Any]:
        """
        开始监控帖子
        
        Args:
            post_id: 帖子ID
            subreddit_name: 子版块名称
            monitor_types: 监控类型列表
            
        Returns:
            操作结果
        """
        try:
            # 1. 输入验证
            validation_result = self._validate_monitoring_input(post_id, subreddit_name)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error']
                }
            
            if monitor_types is None:
                monitor_types = ['comments', 'votes', 'saves']
            
            # 2. 获取帖子信息用于智能监控
            post_info = validation_result.get('post_info', {})
            
            session = self.db_manager.get_session()
            try:
                # 检查是否已经在监控
                existing = session.query(self.db_manager.PostMonitoring).filter(
                    self.db_manager.PostMonitoring.post_id == post_id
                ).first()
                
                if existing:
                    # 更新监控设置
                    existing.monitor_type = ','.join(monitor_types)
                    existing.is_active = True
                    existing.updated_at = datetime.utcnow()
                    session.commit()
                    
                    return {
                        'success': True,
                        'message': f'更新帖子 {post_id} 的监控设置',
                        'monitor_types': monitor_types,
                        'post_info': post_info
                    }
                else:
                    # 创建新的监控记录
                    new_monitor = self.db_manager.PostMonitoring(
                        post_id=post_id,
                        subreddit_name=subreddit_name,
                        monitor_type=','.join(monitor_types),
                        is_active=True,
                        notification_settings={'email': False, 'in_app': True}
                    )
                    session.add(new_monitor)
                    session.commit()
                    
                    return {
                        'success': True,
                        'message': f'开始监控帖子 {post_id}',
                        'monitor_types': monitor_types,
                        'post_info': post_info
                    }
                    
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"开始监控帖子失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _validate_monitoring_input(self, post_id: str, subreddit_name: str) -> Dict[str, Any]:
        """
        验证监控输入参数
        
        Args:
            post_id: 帖子ID
            subreddit_name: 子版块名称
            
        Returns:
            验证结果
        """
        try:
            # 1. 基本格式验证
            if not post_id or not post_id.strip():
                return {'valid': False, 'error': '帖子ID不能为空'}
            
            if not subreddit_name or not subreddit_name.strip():
                return {'valid': False, 'error': '子版块名称不能为空'}
            
            post_id = post_id.strip()
            subreddit_name = subreddit_name.strip()
            
            # 2. 帖子ID格式验证
            if not self._is_valid_post_id(post_id):
                return {'valid': False, 'error': f'帖子ID格式无效: {post_id}'}
            
            # 3. 验证帖子是否存在
            try:
                submission = self.reddit_scraper.reddit.submission(id=post_id)
                
                # 检查帖子是否可访问
                if hasattr(submission, 'title') and submission.title:
                    post_info = {
                        'title': submission.title,
                        'score': submission.score,
                        'num_comments': submission.num_comments,
                        'created_utc': submission.created_utc,
                        'subreddit': str(submission.subreddit),
                        'author': str(submission.author) if submission.author else 'Unknown'
                    }
                    
                    # 4. 验证子版块是否匹配
                    if str(submission.subreddit).lower() != subreddit_name.lower():
                        return {
                            'valid': False, 
                            'error': f'帖子实际在 r/{submission.subreddit}，与输入的 r/{subreddit_name} 不匹配'
                        }
                    
                    return {
                        'valid': True,
                        'post_info': post_info
                    }
                else:
                    return {'valid': False, 'error': '无法访问该帖子，可能已被删除或设为私有'}
                    
            except Exception as e:
                return {'valid': False, 'error': f'帖子不存在或无法访问: {str(e)}'}
                
        except Exception as e:
            logger.error(f"验证监控输入失败: {str(e)}")
            return {'valid': False, 'error': f'验证失败: {str(e)}'}
    
    def _is_valid_post_id(self, post_id: str) -> bool:
        """
        验证帖子ID格式
        
        Args:
            post_id: 帖子ID
            
        Returns:
            是否有效
        """
        try:
            # Reddit帖子ID通常是6-7个字符的字母数字组合
            if len(post_id) < 5 or len(post_id) > 10:
                return False
            
            # 检查是否只包含字母和数字
            if not post_id.isalnum():
                return False
            
            return True
            
        except Exception:
            return False
    
    def stop_monitoring_post(self, post_id: str) -> Dict[str, Any]:
        """
        停止监控帖子
        
        Args:
            post_id: 帖子ID
            
        Returns:
            操作结果
        """
        try:
            session = self.db_manager.get_session()
            try:
                monitor = session.query(self.db_manager.PostMonitoring).filter(
                    self.db_manager.PostMonitoring.post_id == post_id
                ).first()
                
                if monitor:
                    monitor.is_active = False
                    monitor.updated_at = datetime.utcnow()
                    session.commit()
                    
                    return {
                        'success': True,
                        'message': f'停止监控帖子 {post_id}'
                    }
                else:
                    return {
                        'success': False,
                        'error': '未找到监控记录'
                    }
                    
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"停止监控帖子失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_interaction_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取互动历史
        
        Args:
            limit: 返回数量限制
            
        Returns:
            互动历史列表
        """
        try:
            session = self.db_manager.get_session()
            try:
                interactions = session.query(self.db_manager.UserInteractions).order_by(
                    self.db_manager.UserInteractions.created_at.desc()
                ).limit(limit).all()
                
                result = []
                for interaction in interactions:
                    result.append({
                        'id': interaction.id,
                        'post_id': interaction.post_id,
                        'comment_id': interaction.comment_id,
                        'interaction_type': interaction.interaction_type,
                        'target_user': interaction.target_user,
                        'target_subreddit': interaction.target_subreddit,
                        'created_at': interaction.created_at,
                        'status': interaction.status,
                        'error_message': interaction.error_message
                    })
                
                return result
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"获取互动历史失败: {str(e)}")
            return []
    
    def get_post_stats(self, post_id: str) -> Dict[str, Any]:
        """
        获取帖子统计信息
        
        Args:
            post_id: 帖子ID
            
        Returns:
            统计信息
        """
        try:
            session = self.db_manager.get_session()
            try:
                stats = session.query(self.db_manager.InteractionStats).filter(
                    self.db_manager.InteractionStats.post_id == post_id
                ).first()
                
                if stats:
                    return {
                        'post_id': stats.post_id,
                        'subreddit_name': stats.subreddit_name,
                        'total_upvotes': stats.total_upvotes,
                        'total_downvotes': stats.total_downvotes,
                        'total_comments': stats.total_comments,
                        'total_saves': stats.total_saves,
                        'engagement_score': stats.engagement_score,
                        'last_updated': stats.last_updated
                    }
                else:
                    return {
                        'post_id': post_id,
                        'total_upvotes': 0,
                        'total_downvotes': 0,
                        'total_comments': 0,
                        'total_saves': 0,
                        'engagement_score': 0.0
                    }
                    
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"获取帖子统计失败: {str(e)}")
            return {}
    
    def _record_interaction(self, post_id: str, interaction_type: str, 
                          target_user: str = None, target_subreddit: str = None,
                          comment_id: str = None, status: str = 'success',
                          error_message: str = None):
        """记录互动到数据库"""
        try:
            session = self.db_manager.get_session()
            try:
                interaction = self.db_manager.UserInteractions(
                    post_id=post_id,
                    comment_id=comment_id,
                    interaction_type=interaction_type,
                    target_user=target_user,
                    target_subreddit=target_subreddit,
                    status=status,
                    error_message=error_message
                )
                session.add(interaction)
                session.commit()
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"记录互动失败: {str(e)}")
    
    def _record_user_follow(self, username: str, follow_type: str):
        """记录用户关注到数据库"""
        try:
            session = self.db_manager.get_session()
            try:
                follow = self.db_manager.UserFollows(
                    target_username=username,
                    follow_type=follow_type,
                    is_active=(follow_type == 'follow')
                )
                session.add(follow)
                session.commit()
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"记录用户关注失败: {str(e)}")
    
    def _update_post_stats(self, post_id: str, action: str):
        """更新帖子统计"""
        try:
            session = self.db_manager.get_session()
            try:
                stats = session.query(self.db_manager.InteractionStats).filter(
                    self.db_manager.InteractionStats.post_id == post_id
                ).first()
                
                if not stats:
                    # 创建新的统计记录
                    stats = self.db_manager.InteractionStats(
                        post_id=post_id,
                        subreddit_name='unknown'  # 可以从帖子信息获取
                    )
                    session.add(stats)
                
                # 更新统计
                if action == 'upvote':
                    stats.total_upvotes += 1
                elif action == 'downvote':
                    stats.total_downvotes += 1
                elif action == 'save':
                    stats.total_saves += 1
                
                # 计算互动评分
                stats.engagement_score = self._calculate_engagement_score(stats)
                stats.last_updated = datetime.utcnow()
                
                session.commit()
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"更新帖子统计失败: {str(e)}")
    
    def _calculate_engagement_score(self, stats) -> float:
        """计算互动评分"""
        try:
            # 简单的评分算法
            total_interactions = (stats.total_upvotes + stats.total_downvotes + 
                                stats.total_comments + stats.total_saves)
            
            if total_interactions == 0:
                return 0.0
            
            # 权重：点赞 > 评论 > 保存 > 点踩
            score = (stats.total_upvotes * 2.0 + 
                    stats.total_comments * 1.5 + 
                    stats.total_saves * 1.0 + 
                    stats.total_downvotes * 0.5)
            
            return round(score, 2)
            
        except Exception as e:
            logger.error(f"计算互动评分失败: {str(e)}")
            return 0.0
