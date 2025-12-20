"""
帖子管理逻辑
"""
import streamlit as st
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import uuid

logger = logging.getLogger(__name__)

class PostManager:
    """帖子管理器"""
    
    def __init__(self, db_manager):
        """
        初始化帖子管理器
        
        Args:
            db_manager: 数据库管理器
        """
        self.db = db_manager
    
    def create_post(self, 
                    title: str, 
                    content: str,
                    content_type: str = 'text',
                    media_files: List[Dict[str, Any]] = None,
                    source: str = 'manual',
                    keywords: str = None,
                    status: str = 'draft',
                    is_ai_generated: bool = False,
                    original_ai_prompt: str = None,
                    generation_batch_id: str = None,
                    generation_metadata: Dict[str, Any] = None) -> Optional[int]:
        """
        创建帖子内容
        
        Args:
            title: 标题
            content: 内容
            content_type: 内容类型
            media_files: 媒体文件列表
            source: 来源
            keywords: 关键词
            is_ai_generated: 是否AI生成
            original_ai_prompt: 原始AI提示词
            generation_batch_id: 生成批次ID
            generation_metadata: 生成元数据（增强模式的分析结果等）
        
        Returns:
            帖子ID，如果创建失败返回None
        """
        session = self.db.get_session()
        try:
            # 将generation_metadata存储到edit_history字段（JSON类型）
            # edit_history 应该是列表格式，每个元素是一个编辑记录
            edit_history = None
            if generation_metadata:
                edit_history = [{
                    'generation_metadata': generation_metadata,
                    'created_at': datetime.utcnow().isoformat()
                }]
            
            post = self.db.PostContent(
                title=title,
                content=content,
                content_type=content_type,
                media_files=json.dumps(media_files) if media_files else None,
                source=source,
                keywords=keywords,
                is_ai_generated=is_ai_generated,
                original_ai_prompt=original_ai_prompt,
                generation_batch_id=generation_batch_id,
                edit_history=edit_history,
                status=status or 'draft',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(post)
            session.commit()
            return post.id
        except Exception as e:
            logger.error(f"创建帖子失败: {str(e)}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def update_post(self, 
                   post_id: int,
                   title: str = None,
                   content: str = None,
                   content_type: str = None,
                   media_files: List[Dict[str, Any]] = None,
                   status: str = None) -> bool:
        """
        更新帖子内容
        
        Args:
            post_id: 帖子ID
            title: 标题
            content: 内容
            content_type: 内容类型
            media_files: 媒体文件列表
            status: 状态
        
        Returns:
            是否成功
        """
        session = self.db.get_session()
        try:
            post = session.query(self.db.PostContent).filter(
                self.db.PostContent.id == post_id
            ).first()
            
            if not post:
                return False
            
            if title is not None:
                post.title = title
            if content is not None:
                post.content = content
            if content_type is not None:
                post.content_type = content_type
            if media_files is not None:
                post.media_files = json.dumps(media_files)
            if status is not None:
                post.status = status
            
            post.updated_at = datetime.utcnow()
            
            # 记录编辑历史
            # 处理 edit_history：可能是字符串（JSON）或字典（SQLAlchemy JSON字段自动解析）
            if post.edit_history:
                if isinstance(post.edit_history, str):
                    edit_history = json.loads(post.edit_history)
                elif isinstance(post.edit_history, dict):
                    # 如果是字典，可能是单个编辑记录，转换为列表
                    edit_history = [post.edit_history] if not isinstance(post.edit_history, list) else post.edit_history
                elif isinstance(post.edit_history, list):
                    edit_history = post.edit_history
                else:
                    edit_history = []
            else:
                edit_history = []
            
            edit_history.append({
                'edit_time': datetime.utcnow().isoformat(),
                'editor': 'user',
                'changes': {
                    'title': title,
                    'content': content,
                    'status': status
                }
            })
            # SQLAlchemy JSON字段可以直接存储字典，但为了兼容性，也可以存储JSON字符串
            # 这里直接存储字典，让SQLAlchemy自动处理序列化
            post.edit_history = edit_history
            
            session.commit()
            return True
        except Exception as e:
            logger.error(f"更新帖子失败: {str(e)}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def delete_post(self, post_id: int) -> bool:
        """
        删除帖子（软删除，改为archived状态）
        
        Args:
            post_id: 帖子ID
        
        Returns:
            是否成功
        """
        return self.update_post(post_id, status='archived')
    
    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """
        获取帖子内容
        
        Args:
            post_id: 帖子ID
        
        Returns:
            帖子数据字典
        """
        session = self.db.get_session()
        try:
            post = session.query(self.db.PostContent).filter(
                self.db.PostContent.id == post_id
            ).first()
            
            if not post:
                return None
            
            return {
                'id': post.id,
                'title': post.title,
                'content': post.content,
                'content_type': post.content_type,
                'media_files': json.loads(post.media_files) if post.media_files else [],
                'status': post.status,
                'source': post.source,
                'keywords': post.keywords,
                'is_ai_generated': post.is_ai_generated,
                'created_at': post.created_at,
                'updated_at': post.updated_at
            }
        except Exception as e:
            logger.error(f"获取帖子失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def list_posts(self, 
                  status = None,  # 可以是 str 或 List[str]
                  source: str = None,
                  limit: int = 100) -> List[Dict[str, Any]]:
        """
        列出帖子
        
        Args:
            status: 状态筛选（可以是单个状态字符串或状态列表，如果为None，默认排除archived状态的帖子）
            source: 来源筛选
            limit: 限制数量
        
        Returns:
            帖子列表
        """
        session = self.db.get_session()
        try:
            query = session.query(self.db.PostContent)
            
            if status:
                if isinstance(status, list):
                    # 多个状态：使用 in_ 查询
                    query = query.filter(self.db.PostContent.status.in_(status))
                else:
                    # 单个状态
                    query = query.filter(self.db.PostContent.status == status)
            else:
                # 默认排除已归档的帖子
                query = query.filter(self.db.PostContent.status != 'archived')
            
            if source:
                query = query.filter(self.db.PostContent.source == source)
            
            posts = query.order_by(
                self.db.PostContent.created_at.desc()
            ).limit(limit).all()
            
            result = []
            for post in posts:
                result.append({
                    'id': post.id,
                    'title': post.title,
                    'content': post.content,  # 返回完整内容，不截断
                    'content_type': post.content_type,
                    'status': post.status,
                    'source': post.source,
                    'is_ai_generated': post.is_ai_generated,
                    'created_at': post.created_at,
                    'updated_at': post.updated_at
                })
            
            return result
        except Exception as e:
            logger.error(f"列出帖子失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def create_temp_post(self, title: str, content: str) -> Dict[str, Any]:
        """
        创建临时帖子（用于AI生成结果，未保存到数据库）
        
        Args:
            title: 标题
            content: 内容
        
        Returns:
            临时帖子字典
        """
        return {
            'temp_id': str(uuid.uuid4()),
            'title': title,
            'content': content,
            'content_type': 'text',
            'status': 'draft',
            'source': 'ai_generated',
            'is_ai_generated': True,
            'created_at': datetime.utcnow()
        }
    
    def save_temp_posts(self, temp_posts: List[Dict[str, Any]]) -> List[int]:
        """
        保存临时帖子到数据库
        
        Args:
            temp_posts: 临时帖子列表
        
        Returns:
            保存后的帖子ID列表
        """
        saved_ids = []
        for temp_post in temp_posts:
            post_id = self.create_post(
                title=temp_post.get('title', ''),
                content=temp_post.get('content', ''),
                content_type=temp_post.get('content_type', 'text'),
                source=temp_post.get('source', 'ai_generated'),
                is_ai_generated=temp_post.get('is_ai_generated', False),
                generation_batch_id=temp_post.get('generation_batch_id')
            )
            if post_id:
                saved_ids.append(post_id)
        return saved_ids
    
    def find_duplicate_posts(self, similarity_threshold: float = 1.0) -> Dict[str, List[Dict[str, Any]]]:
        """
        查找重复的帖子
        
        Args:
            similarity_threshold: 相似度阈值（1.0表示完全相同，0.9表示90%相似）
        
        Returns:
            字典，key为重复组的标识（标题+内容的hash），value为重复帖子列表
        """
        session = self.db.get_session()
        try:
            # 获取所有帖子（排除已归档的）
            all_posts = session.query(self.db.PostContent).filter(
                self.db.PostContent.status != 'archived'
            ).all()
            
            # 使用字典快速分组（基于标题和内容的标准化值）
            post_groups = {}
            
            for post in all_posts:
                # 标准化标题和内容（去除首尾空格，转小写）
                title_normalized = post.title.strip().lower() if post.title else ''
                content_normalized = post.content.strip().lower() if post.content else ''
                
                # 创建唯一标识（基于标题和完整内容）
                identifier = f"{title_normalized}_{content_normalized}"
                
                # 将帖子添加到对应的组
                if identifier not in post_groups:
                    post_groups[identifier] = []
                
                post_groups[identifier].append({
                    'id': post.id,
                    'title': post.title,
                    'content': post.content[:200] + '...' if len(post.content) > 200 else post.content,
                    'status': post.status,
                    'source': post.source,
                    'created_at': post.created_at,
                    'updated_at': post.updated_at
                })
            
            # 只返回有重复的组（组内帖子数 > 1）
            duplicate_groups = {
                key: posts for key, posts in post_groups.items() 
                if len(posts) > 1
            }
            
            return duplicate_groups
        except Exception as e:
            logger.error(f"查找重复帖子失败: {str(e)}")
            return {}
        finally:
            session.close()
    
    def delete_duplicate_posts(self, post_ids: List[int], keep_oldest: bool = True) -> int:
        """
        删除重复的帖子
        
        Args:
            post_ids: 要删除的帖子ID列表
            keep_oldest: 是否保留最早的帖子（如果为False，则保留最新的）
        
        Returns:
            成功删除的数量
        """
        if not post_ids:
            return 0
        
        session = self.db.get_session()
        deleted_count = 0
        try:
            # 获取所有要删除的帖子
            posts = session.query(self.db.PostContent).filter(
                self.db.PostContent.id.in_(post_ids)
            ).all()
            
            if not posts:
                logger.warning(f"未找到要删除的帖子，ID列表: {post_ids}")
                return 0
            
            # 如果 keep_oldest=True，保留最早创建的，删除其他的
            # 如果 keep_oldest=False，保留最新创建的，删除其他的
            if keep_oldest:
                # 按创建时间排序，保留第一个（最早的）
                posts_sorted = sorted(posts, key=lambda p: p.created_at)
                to_delete = posts_sorted[1:]  # 删除除第一个外的所有
                kept_post = posts_sorted[0] if posts_sorted else None
            else:
                # 按创建时间排序，保留最后一个（最新的）
                posts_sorted = sorted(posts, key=lambda p: p.created_at)
                to_delete = posts_sorted[:-1]  # 删除除最后一个外的所有
                kept_post = posts_sorted[-1] if posts_sorted else None
            
            # 删除重复帖子
            for post in to_delete:
                post.status = 'archived'  # 软删除
                post.updated_at = datetime.utcnow()  # 显式更新更新时间
                deleted_count += 1
                logger.info(f"标记帖子 {post.id} 为已归档（重复删除）")
            
            if kept_post:
                logger.info(f"保留帖子 {kept_post.id}（创建时间: {kept_post.created_at}）")
            
            session.commit()
            logger.info(f"成功删除 {deleted_count} 条重复帖子")
            return deleted_count
        except Exception as e:
            logger.error(f"删除重复帖子失败: {str(e)}", exc_info=True)
            session.rollback()
            return 0
        finally:
            session.close()


