"""
数据库模块 - 使用SQLAlchemy管理本地数据库
存储Reddit帖子和评论数据
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging
import json
import numpy as np
from typing import List, Tuple
from config import Config

Base = declarative_base()

class RedditPost(Base):
    """Reddit帖子数据表"""
    __tablename__ = 'reddit_posts'
    
    id = Column(String, primary_key=True)
    title = Column(Text, nullable=False)
    author = Column(String)
    score = Column(Integer)
    upvote_ratio = Column(Float)
    num_comments = Column(Integer)
    created_utc = Column(DateTime)
    url = Column(String)
    selftext = Column(Text)
    subreddit = Column(String)
    flair = Column(String)
    is_self = Column(Boolean)
    over_18 = Column(Boolean)
    search_query = Column(String)  # 如果是搜索获得的帖子
    scraped_at = Column(DateTime, default=datetime.utcnow)
    analyzed = Column(Boolean, default=False)  # 是否已分析

class RedditComment(Base):
    """Reddit评论数据表"""
    __tablename__ = 'reddit_comments'
    
    id = Column(String, primary_key=True)
    post_id = Column(String, nullable=False)
    author = Column(String)
    body = Column(Text, nullable=False)
    score = Column(Integer)
    created_utc = Column(DateTime)
    parent_id = Column(String)
    is_submitter = Column(Boolean)
    stickied = Column(Boolean)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    analyzed = Column(Boolean, default=False)  # 是否已分析

class SubredditInfo(Base):
    """子版块信息表"""
    __tablename__ = 'subreddit_info'
    
    name = Column(String, primary_key=True)
    title = Column(String)
    description = Column(Text)
    subscribers = Column(Integer)
    created_utc = Column(DateTime)
    over18 = Column(Boolean)
    public_description = Column(Text)
    last_updated = Column(DateTime, default=datetime.utcnow)

class AnalysisResult(Base):
    """分析结果表"""
    __tablename__ = 'analysis_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    content_id = Column(String, nullable=False)  # 帖子或评论ID
    content_type = Column(String, nullable=False)  # 'post' 或 'comment'
    analysis_type = Column(String, nullable=False)  # 分析类型
    result = Column(Text, nullable=False)
    model_used = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 添加唯一约束，防止重复分析
    __table_args__ = (
        {'extend_existing': True}
    )

class PromptTemplate(Base):
    """提示词模板表"""
    __tablename__ = 'prompt_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)  # 提示词名称
    description = Column(Text)  # 提示词描述
    prompt_content = Column(Text, nullable=False)  # 综合提示词内容
    is_default = Column(Boolean, default=False)  # 是否为默认提示词
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StructuredExtraction(Base):
    """结构化抽取结果表"""
    __tablename__ = 'structured_extractions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String, nullable=False)  # 关联的帖子ID
    title = Column(Text)
    content = Column(Text)
    author = Column(String)
    subreddit = Column(String)
    created_utc = Column(DateTime)
    score = Column(Integer)
    upvote_ratio = Column(Float)
    
    # 结构化字段
    main_topic = Column(String)
    pain_points = Column(JSON)  # 存储为JSON数组
    user_needs = Column(JSON)   # 存储为JSON数组
    sentiment = Column(String)
    sentiment_score = Column(Float)
    key_phrases = Column(JSON)  # 存储为JSON数组
    mentioned_tools = Column(JSON)  # 存储为JSON数组
    evidence_sentences = Column(JSON)  # 存储为JSON数组
    confidence_score = Column(Float)
    long_tail_keywords = Column(JSON)  # 长尾关键词，存储为JSON数组
    
    # 元数据
    extraction_timestamp = Column(DateTime, default=datetime.utcnow)
    extraction_model = Column(String)
    
    # 添加唯一约束
    __table_args__ = (
        {'extend_existing': True}
    )

class VectorizedText(Base):
    """向量化文本表"""
    __tablename__ = 'vectorized_texts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    text_id = Column(String, nullable=False)  # 文本唯一标识
    text = Column(Text, nullable=False)
    vector = Column(Text)  # 存储为JSON字符串的向量
    model_name = Column(String)
    vectorization_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # 添加唯一约束
    __table_args__ = (
        {'extend_existing': True}
    )

class ClusteringResult(Base):
    """聚类结果表"""
    __tablename__ = 'clustering_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(String, nullable=False)  # 分析批次ID
    cluster_id = Column(Integer, nullable=False)
    center_vector = Column(Text)  # 存储为JSON字符串的向量
    member_indices = Column(JSON)  # 成员索引列表
    member_count = Column(Integer)
    avg_similarity = Column(Float)
    representative_samples = Column(JSON)  # 代表样本
    keywords = Column(JSON)  # 关键词列表
    dominant_sentiment = Column(String)
    avg_sentiment_score = Column(Float)
    
    # 元数据
    clustering_timestamp = Column(DateTime, default=datetime.utcnow)
    model_name = Column(String)
    
    # 添加唯一约束
    __table_args__ = (
        {'extend_existing': True}
    )

class BusinessInsight(Base):
    """业务洞察表"""
    __tablename__ = 'business_insights'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(String, nullable=False)  # 分析批次ID
    total_clusters = Column(Integer)
    total_samples = Column(Integer)
    overall_sentiment = Column(String)
    dominant_themes = Column(JSON)  # 主导主题列表
    top_pain_points = Column(JSON)  # 主要痛点列表
    key_opportunities = Column(JSON)  # 关键机会列表
    strategic_recommendations = Column(JSON)  # 战略建议列表
    cluster_insights = Column(JSON)  # 簇级洞察
    action_priority_matrix = Column(JSON)  # 行动优先级矩阵
    
    # 元数据
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
    model_name = Column(String)
    
    # 添加唯一约束
    __table_args__ = (
        {'extend_existing': True}
    )

class KeywordStatistic(Base):
    """关键词统计表（全局去重）"""
    __tablename__ = 'keyword_statistics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String, nullable=False)  # 关键词
    category = Column(String)  # 类别: all, main_topic, pain_point, user_need
    frequency = Column(Integer, default=1)  # 出现频率
    tfidf_score = Column(Float, default=0.0)  # TF-IDF得分
    first_seen = Column(DateTime, default=datetime.utcnow)  # 首次出现时间
    last_seen = Column(DateTime, default=datetime.utcnow)  # 最后出现时间
    
    # 添加唯一约束
    __table_args__ = (
        {'extend_existing': True}
    )

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        """初始化数据库连接"""
        self.engine = create_engine(Config.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.logger = logging.getLogger(__name__)
        
        # 添加模型类作为属性
        self.RedditPost = RedditPost
        self.RedditComment = RedditComment
        self.SubredditInfo = SubredditInfo
        self.AnalysisResult = AnalysisResult
        self.PromptTemplate = PromptTemplate
        
        self.create_tables()
    
    def create_tables(self):
        """创建数据库表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("数据库表创建成功")
        except Exception as e:
            self.logger.error(f"创建数据库表失败: {str(e)}")
    
    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()
    
    def save_posts(self, posts: list):
        """批量保存帖子数据"""
        session = self.get_session()
        try:
            for post_data in posts:
                # 检查是否已存在
                existing_post = session.query(RedditPost).filter(RedditPost.id == post_data['id']).first()
                if not existing_post:
                    post = RedditPost(**post_data)
                    session.add(post)
            
            session.commit()
            self.logger.info(f"成功保存 {len(posts)} 个帖子到数据库")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存帖子失败: {str(e)}")
        finally:
            session.close()
    
    def save_comments(self, comments: list):
        """批量保存评论数据"""
        session = self.get_session()
        try:
            for comment_data in comments:
                # 检查是否已存在
                existing_comment = session.query(RedditComment).filter(RedditComment.id == comment_data['id']).first()
                if not existing_comment:
                    comment = RedditComment(**comment_data)
                    session.add(comment)
            
            session.commit()
            self.logger.info(f"成功保存 {len(comments)} 个评论到数据库")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存评论失败: {str(e)}")
        finally:
            session.close()
    
    def save_subreddit_info(self, subreddit_info: dict):
        """保存子版块信息"""
        session = self.get_session()
        try:
            existing = session.query(SubredditInfo).filter(SubredditInfo.name == subreddit_info['name']).first()
            if existing:
                # 更新现有记录
                for key, value in subreddit_info.items():
                    setattr(existing, key, value)
                existing.last_updated = datetime.utcnow()
            else:
                # 创建新记录
                info = SubredditInfo(**subreddit_info)
                session.add(info)
            
            session.commit()
            self.logger.info(f"成功保存 r/{subreddit_info['name']} 信息")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存子版块信息失败: {str(e)}")
        finally:
            session.close()
    
    def save_analysis_result(self, content_id: str, content_type: str, analysis_type: str, 
                           result: str, model_used: str):
        """保存分析结果"""
        session = self.get_session()
        try:
            # 检查是否已存在相同的分析结果
            existing = session.query(AnalysisResult).filter(
                AnalysisResult.content_id == content_id,
                AnalysisResult.content_type == content_type,
                AnalysisResult.analysis_type == analysis_type
            ).first()
            
            if existing:
                # 更新现有结果
                existing.result = result
                existing.model_used = model_used
                existing.created_at = datetime.utcnow()
            else:
                # 创建新结果
                analysis = AnalysisResult(
                    content_id=content_id,
                    content_type=content_type,
                    analysis_type=analysis_type,
                    result=result,
                    model_used=model_used
                )
                session.add(analysis)
            
            # 更新对应内容的analyzed状态
            if content_type == "post":
                post = session.query(RedditPost).filter(RedditPost.id == content_id).first()
                if post:
                    post.analyzed = True
            elif content_type == "comment":
                comment = session.query(RedditComment).filter(RedditComment.id == content_id).first()
                if comment:
                    comment.analyzed = True
            
            session.commit()
            self.logger.info(f"成功保存分析结果: {content_id} - {analysis_type}")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存分析结果失败: {str(e)}")
        finally:
            session.close()
    
    def get_unanalyzed_posts(self, limit: int = 100):
        """获取未分析的帖子"""
        session = self.get_session()
        try:
            posts = session.query(RedditPost).filter(RedditPost.analyzed == False).limit(limit).all()
            return posts
        except Exception as e:
            self.logger.error(f"获取未分析帖子失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_posts_for_analysis(self, analysis_type: str, limit: int = 100):
        """获取需要特定类型分析的帖子"""
        session = self.get_session()
        try:
            # 获取所有帖子
            all_posts = session.query(RedditPost).all()
            
            # 过滤出没有该类型分析结果的帖子
            posts_to_analyze = []
            for post in all_posts:
                existing_analysis = session.query(AnalysisResult).filter(
                    AnalysisResult.content_id == post.id,
                    AnalysisResult.content_type == 'post',
                    AnalysisResult.analysis_type == analysis_type
                ).first()
                
                if not existing_analysis:
                    posts_to_analyze.append(post)
                    
                if len(posts_to_analyze) >= limit:
                    break
            
            return posts_to_analyze
        except Exception as e:
            self.logger.error(f"获取需要分析的帖子失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_unanalyzed_comments(self, limit: int = 100):
        """获取未分析的评论"""
        session = self.get_session()
        try:
            comments = session.query(RedditComment).filter(RedditComment.analyzed == False).limit(limit).all()
            return comments
        except Exception as e:
            self.logger.error(f"获取未分析评论失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_analysis_results(self, content_id: str = None, analysis_type: str = None):
        """获取分析结果"""
        session = self.get_session()
        try:
            query = session.query(AnalysisResult)
            
            if content_id:
                query = query.filter(AnalysisResult.content_id == content_id)
            if analysis_type:
                query = query.filter(AnalysisResult.analysis_type == analysis_type)
            
            return query.all()
        except Exception as e:
            self.logger.error(f"获取分析结果失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_posts_with_analysis(self, limit: int = 100, subreddit: str = None):
        """获取帖子及其分析结果"""
        session = self.get_session()
        try:
            query = session.query(RedditPost)
            if subreddit:
                query = query.filter(RedditPost.subreddit == subreddit)
            
            posts = query.limit(limit).all()
            
            # 为每个帖子获取分析结果
            posts_with_analysis = []
            for post in posts:
                analyses = session.query(AnalysisResult).filter(
                    AnalysisResult.content_id == post.id,
                    AnalysisResult.content_type == 'post'
                ).all()
                
                post_data = {
                    'post': post,
                    'analyses': {analysis.analysis_type: analysis for analysis in analyses}
                }
                posts_with_analysis.append(post_data)
            
            return posts_with_analysis
        except Exception as e:
            self.logger.error(f"获取帖子及分析结果失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_analysis_statistics(self):
        """获取分析统计信息"""
        session = self.get_session()
        try:
            stats = {}
            
            # 总帖子数
            stats['total_posts'] = session.query(RedditPost).count()
            
            # 总评论数
            stats['total_comments'] = session.query(RedditComment).count()
            
            # 各类型分析结果数量
            analysis_types = ['sentiment', 'topic', 'quality', 'comprehensive', 'community_report']
            for analysis_type in analysis_types:
                count = session.query(AnalysisResult).filter(
                    AnalysisResult.analysis_type == analysis_type
                ).count()
                stats[f'{analysis_type}_count'] = count
            
            # 总分析结果数
            stats['total_analysis'] = session.query(AnalysisResult).count()
            
            return stats
        except Exception as e:
            self.logger.error(f"获取分析统计失败: {str(e)}")
            return {}
        finally:
            session.close()
    
    def delete_post(self, post_id: str):
        """删除指定帖子及其相关数据"""
        session = self.get_session()
        try:
            # 删除相关分析结果
            session.query(AnalysisResult).filter(
                AnalysisResult.content_id == post_id,
                AnalysisResult.content_type == 'post'
            ).delete()
            
            # 删除相关评论
            session.query(RedditComment).filter(
                RedditComment.post_id == post_id
            ).delete()
            
            # 删除帖子
            deleted_count = session.query(RedditPost).filter(
                RedditPost.id == post_id
            ).delete()
            
            session.commit()
            self.logger.info(f"成功删除帖子: {post_id}")
            return deleted_count > 0
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"删除帖子失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def delete_analysis_result(self, result_id: int):
        """删除指定分析结果"""
        session = self.get_session()
        try:
            deleted_count = session.query(AnalysisResult).filter(
                AnalysisResult.id == result_id
            ).delete()
            
            session.commit()
            self.logger.info(f"成功删除分析结果: {result_id}")
            return deleted_count > 0
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"删除分析结果失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def clear_all_data(self):
        """清空所有数据"""
        session = self.get_session()
        try:
            # 删除所有分析结果
            analysis_count = session.query(AnalysisResult).count()
            session.query(AnalysisResult).delete()
            
            # 删除所有评论
            comment_count = session.query(RedditComment).count()
            session.query(RedditComment).delete()
            
            # 删除所有帖子
            post_count = session.query(RedditPost).count()
            session.query(RedditPost).delete()
            
            session.commit()
            self.logger.info(f"成功清空所有数据: {post_count}个帖子, {comment_count}个评论, {analysis_count}个分析结果")
            return True
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"清空数据失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_posts_for_batch_analysis(self, subreddit: str = None, limit: int = 50):
        """获取用于批量分析的帖子数据"""
        session = self.get_session()
        try:
            query = session.query(RedditPost)
            if subreddit:
                query = query.filter(RedditPost.subreddit == subreddit)
            
            posts = query.limit(limit).all()
            
            # 转换为适合大模型分析的格式
            posts_data = []
            for post in posts:
                post_data = {
                    'id': post.id,
                    'title': post.title,
                    'content': post.selftext or '',
                    'author': post.author,
                    'score': post.score,
                    'subreddit': post.subreddit,
                    'created_time': post.created_utc.strftime('%Y-%m-%d %H:%M:%S') if post.created_utc else '',
                    'num_comments': post.num_comments
                }
                posts_data.append(post_data)
            
            return posts_data
        except Exception as e:
            self.logger.error(f"获取批量分析数据失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_subreddit_list(self):
        """获取所有子版块列表"""
        session = self.get_session()
        try:
            subreddits = session.query(RedditPost.subreddit).distinct().all()
            return [subreddit[0] for subreddit in subreddits if subreddit[0]]
        except Exception as e:
            self.logger.error(f"获取子版块列表失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_posts_grouped_by_date_subreddit(self):
        """获取按搜索日期和板块分组的帖子数据"""
        session = self.get_session()
        try:
            # 获取所有帖子，按抓取日期和子版块分组
            posts = session.query(RedditPost).order_by(
                RedditPost.scraped_at.desc(), 
                RedditPost.subreddit
            ).all()
            
            # 按日期和子版块分组
            grouped_data = {}
            for post in posts:
                # 使用抓取日期作为分组键
                date_key = post.scraped_at.strftime('%Y-%m-%d')
                subreddit = post.subreddit or 'unknown'
                
                group_key = f"{date_key}_{subreddit}"
                
                if group_key not in grouped_data:
                    grouped_data[group_key] = {
                        'date': date_key,
                        'subreddit': subreddit,
                        'posts': [],
                        'total_posts': 0,
                        'total_comments': 0
                    }
                
                grouped_data[group_key]['posts'].append(post)
                grouped_data[group_key]['total_posts'] += 1
                grouped_data[group_key]['total_comments'] += post.num_comments or 0
            
            return grouped_data
            
        except Exception as e:
            self.logger.error(f"获取分组帖子数据失败: {str(e)}")
            return {}
        finally:
            session.close()
    
    def get_posts_by_group(self, date, subreddit):
        """根据日期和子版块获取帖子列表"""
        session = self.get_session()
        try:
            posts = session.query(RedditPost).filter(
                RedditPost.subreddit == subreddit,
                RedditPost.scraped_at >= datetime.strptime(date, '%Y-%m-%d'),
                RedditPost.scraped_at < datetime.strptime(date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            ).all()
            
            return posts
            
        except Exception as e:
            self.logger.error(f"获取指定分组帖子失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def delete_posts_by_group(self, date, subreddit):
        """删除指定日期和子版块的所有帖子"""
        session = self.get_session()
        try:
            # 获取要删除的帖子
            posts = self.get_posts_by_group(date, subreddit)
            post_ids = [post.id for post in posts]
            
            if not post_ids:
                return 0
            
            # 删除相关分析结果
            session.query(AnalysisResult).filter(
                AnalysisResult.content_id.in_(post_ids),
                AnalysisResult.content_type == 'post'
            ).delete(synchronize_session=False)
            
            # 删除相关评论
            session.query(RedditComment).filter(
                RedditComment.post_id.in_(post_ids)
            ).delete(synchronize_session=False)
            
            # 删除帖子
            deleted_count = session.query(RedditPost).filter(
                RedditPost.id.in_(post_ids)
            ).delete(synchronize_session=False)
            
            session.commit()
            self.logger.info(f"成功删除 {deleted_count} 个帖子 (日期: {date}, 子版块: {subreddit})")
            return deleted_count
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"删除分组帖子失败: {str(e)}")
            return 0
        finally:
            session.close()
    
    def save_prompt_template(self, name: str, description: str, prompt_content: str, is_default: bool = False):
        """保存提示词模板"""
        session = self.get_session()
        try:
            # 检查是否已存在同名提示词
            existing = session.query(PromptTemplate).filter(PromptTemplate.name == name).first()
            
            if existing:
                # 更新现有提示词
                existing.description = description
                existing.prompt_content = prompt_content
                existing.is_default = is_default
                existing.updated_at = datetime.utcnow()
            else:
                # 创建新提示词
                template = PromptTemplate(
                    name=name,
                    description=description,
                    prompt_content=prompt_content,
                    is_default=is_default
                )
                session.add(template)
            
            session.commit()
            self.logger.info(f"成功保存提示词模板: {name}")
            return True
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存提示词模板失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_prompt_templates(self):
        """获取提示词模板列表"""
        session = self.get_session()
        try:
            templates = session.query(PromptTemplate).order_by(
                PromptTemplate.is_default.desc(), 
                PromptTemplate.created_at.desc()
            ).all()
            return templates
        except Exception as e:
            self.logger.error(f"获取提示词模板失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_prompt_template(self, template_id: int):
        """获取指定提示词模板"""
        session = self.get_session()
        try:
            template = session.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
            return template
        except Exception as e:
            self.logger.error(f"获取提示词模板失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def delete_prompt_template(self, template_id: int):
        """删除提示词模板"""
        session = self.get_session()
        try:
            template = session.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
            if template and not template.is_default:  # 不能删除默认模板
                session.delete(template)
                session.commit()
                self.logger.info(f"成功删除提示词模板: {template.name}")
                return True
            else:
                self.logger.warning("不能删除默认提示词模板")
                return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"删除提示词模板失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def initialize_default_prompts(self):
        """初始化默认提示词模板"""
        default_prompt = {
            "name": "Reddit数据分析-综合版",
            "description": "针对Reddit数据的综合分析提示词，包含主题、情感、洞察和结构化分析",
            "prompt_content": """你是一位专业的社交媒体数据分析师。你的任务是深度分析Reddit社区中关于指定主题的讨论。

请根据下面提供的原始Reddit帖子和评论数据，完成以下四个部分的结构化分析和总结。

---
### 原始数据：{text}
---

### **任务一：情感与立场分析 (Sentiment & Stance)**

1. **整体情绪：** 总结这段数据流中用户讨论的整体情绪倾向（例如：70% 积极，20% 负面，10% 中立）。
2. **核心情感识别：** 识别讨论中最突出的三种情感（例如：沮丧、希望、感激、焦虑）。
3. **争议点（如果存在）：** 如果用户在讨论某个特定方法或产品时存在显著争议，请明确指出该争议的核心焦点。

### **任务二：主题与痛点提取 (Topic & Pain Points)**

1. **主要讨论主题：** 将这段数据内容归纳为 2 到 3 个最集中的讨论主题或焦点。
2. **提取核心痛点：** 总结用户遇到的最常见、最迫切的问题或挑战（即用户主要在抱怨什么或寻求什么帮助）。

### **任务三：实用建议和技巧归纳 (Actionable Advice)**

1. **Top 5 实用建议：** 从评论和回复中提取并整理出五条最具操作性、最实用的建议、技巧或步骤。请以简洁的列表形式呈现。
2. **工具/品牌提及：** 提取数据中被提及最频繁的工具、产品或品牌名称，并指出用户对它们的态度。

### **任务四：结构化摘要与总结 (Structured Output)**

请用一段简洁的文字总结上述分析结果，然后以JSON格式输出最关键的洞察，以便后续导入数据库。

**JSON输出格式：**

```json
{{
    "overall_sentiment": "整体情绪百分比",
    "main_emotions": ["情感1", "情感2", "情感3"],
    "controversy_points": ["争议点1", "争议点2"],
    "main_topics": ["主题1", "主题2", "主题3"],
    "top_pain_points": ["痛点1", "痛点2", "痛点3"],
    "top_advice": ["建议1", "建议2", "建议3", "建议4", "建议5"],
    "mentioned_tools": ["工具1", "工具2"],
    "summary": "综合分析总结"
}}
```""",
            "is_default": True
        }
        
        self.save_prompt_template(**default_prompt)
    
    def get_analysis_results_with_posts(self, start_date: str = None, 
                                      end_date: str = None,
                                      subreddits: list = None):
        """
        获取分析结果及其关联的帖子数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            subreddits: 子版块列表
            
        Returns:
            分析结果列表，包含关联的帖子数据
        """
        session = self.get_session()
        try:
            from sqlalchemy import and_
            from datetime import datetime
            
            # 构建查询条件 - 使用content_id而不是post_id
            query = session.query(AnalysisResult).join(RedditPost, AnalysisResult.content_id == RedditPost.id)
            
            # 只获取帖子类型的分析结果
            query = query.filter(AnalysisResult.content_type == 'post')
            
            # 日期过滤
            if start_date:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(RedditPost.scraped_at >= start_datetime)
            
            if end_date:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                # 结束日期包含整天
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                query = query.filter(RedditPost.scraped_at <= end_datetime)
            
            # 子版块过滤
            if subreddits:
                query = query.filter(RedditPost.subreddit.in_(subreddits))
            
            # 按创建时间倒序排列
            results = query.order_by(AnalysisResult.created_at.desc()).all()
            
            # 为每个结果添加帖子对象引用
            for result in results:
                result.post = session.query(RedditPost).filter(RedditPost.id == result.content_id).first()
            
            return results
            
        except Exception as e:
            self.logger.error(f"获取分析结果失败: {str(e)}")
            return []
        finally:
            session.close()
    
    # ==================== 新增的结构化抽取和聚类相关方法 ====================
    
    def save_structured_extraction(self, extraction_data):
        """保存结构化抽取结果"""
        session = self.get_session()
        try:
            # 检查是否已存在
            existing = session.query(StructuredExtraction).filter(
                StructuredExtraction.post_id == extraction_data.post_id
            ).first()
            
            if existing:
                # 更新现有记录
                for key, value in extraction_data.__dict__.items():
                    if hasattr(existing, key) and key != 'id':
                        setattr(existing, key, value)
            else:
                # 创建新记录
                extraction = StructuredExtraction(
                    post_id=extraction_data.post_id,
                    title=extraction_data.title,
                    content=extraction_data.content,
                    author=extraction_data.author,
                    subreddit=extraction_data.subreddit,
                    created_utc=extraction_data.created_utc,
                    score=extraction_data.score,
                    upvote_ratio=extraction_data.upvote_ratio,
                    main_topic=extraction_data.main_topic,
                    pain_points=extraction_data.pain_points,
                    user_needs=extraction_data.user_needs,
                    sentiment=extraction_data.sentiment,
                    sentiment_score=extraction_data.sentiment_score,
                    key_phrases=extraction_data.key_phrases,
                    mentioned_tools=extraction_data.mentioned_tools,
                    evidence_sentences=extraction_data.evidence_sentences,
                    confidence_score=extraction_data.confidence_score,
                    extraction_timestamp=extraction_data.extraction_timestamp,
                    extraction_model=extraction_data.extraction_model
                )
                session.add(extraction)
            
            session.commit()
            self.logger.info(f"结构化抽取结果已保存: {extraction_data.post_id}")
            return True
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存结构化抽取结果失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_structured_extractions(self, limit: int = None, subreddits: List[str] = None):
        """获取结构化抽取结果"""
        session = self.get_session()
        try:
            query = session.query(StructuredExtraction)
            
            if subreddits:
                query = query.filter(StructuredExtraction.subreddit.in_(subreddits))
            
            if limit:
                query = query.limit(limit)
            
            return query.order_by(StructuredExtraction.extraction_timestamp.desc()).all()
            
        except Exception as e:
            self.logger.error(f"获取结构化抽取结果失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def save_vectorized_text(self, vectorized_text):
        """保存向量化文本"""
        from datetime import datetime
        session = self.get_session()
        try:
            # 确保时间戳是 datetime 对象
            timestamp = vectorized_text.vectorization_timestamp
            if not isinstance(timestamp, datetime):
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        timestamp = datetime.utcnow()
                else:
                    timestamp = datetime.utcnow()
            
            # 检查是否已存在
            existing = session.query(VectorizedText).filter(
                VectorizedText.text_id == vectorized_text.text_id
            ).first()
            
            if existing:
                # 更新现有记录
                existing.text = vectorized_text.text
                existing.vector = json.dumps(vectorized_text.vector.tolist())
                existing.model_name = vectorized_text.model_name
                existing.vectorization_timestamp = timestamp
            else:
                # 创建新记录
                vt = VectorizedText(
                    text_id=vectorized_text.text_id,
                    text=vectorized_text.text,
                    vector=json.dumps(vectorized_text.vector.tolist()),
                    model_name=vectorized_text.model_name,
                    vectorization_timestamp=timestamp
                )
                session.add(vt)
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存向量化文本失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_vectorized_texts(self, text_ids: List[str] = None):
        """获取向量化文本"""
        session = self.get_session()
        try:
            query = session.query(VectorizedText)
            
            if text_ids:
                query = query.filter(VectorizedText.text_id.in_(text_ids))
            
            results = query.all()
            
            # 解析向量
            for result in results:
                if result.vector:
                    result.vector = np.array(json.loads(result.vector))
            
            return results
            
        except Exception as e:
            self.logger.error(f"获取向量化文本失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def save_clustering_result(self, analysis_id: str, cluster_result):
        """保存聚类结果"""
        session = self.get_session()
        try:
            clustering = ClusteringResult(
                analysis_id=analysis_id,
                cluster_id=cluster_result.cluster_id,
                center_vector=json.dumps(cluster_result.center_vector.tolist()),
                member_indices=cluster_result.member_indices,
                member_count=cluster_result.member_count,
                avg_similarity=cluster_result.avg_similarity,
                representative_samples=cluster_result.representative_samples,
                keywords=cluster_result.keywords,
                dominant_sentiment=cluster_result.dominant_sentiment,
                avg_sentiment_score=cluster_result.avg_sentiment_score,
                clustering_timestamp=cluster_result.clustering_timestamp,
                model_name=cluster_result.model_name
            )
            session.add(clustering)
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存聚类结果失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def save_business_insight(self, analysis_id: str, business_insight):
        """保存业务洞察"""
        session = self.get_session()
        try:
            insight = BusinessInsight(
                analysis_id=analysis_id,
                total_clusters=business_insight.total_clusters,
                total_samples=business_insight.total_samples,
                overall_sentiment=business_insight.overall_sentiment,
                dominant_themes=business_insight.dominant_themes,
                top_pain_points=business_insight.top_pain_points,
                key_opportunities=business_insight.key_opportunities,
                strategic_recommendations=business_insight.strategic_recommendations,
                cluster_insights=[
                    {
                        "cluster_id": ci.cluster_id,
                        "cluster_name": ci.cluster_name,
                        "key_insights": ci.key_insights,
                        "pain_points": ci.pain_points,
                        "opportunities": ci.opportunities,
                        "recommended_actions": ci.recommended_actions,
                        "priority_score": ci.priority_score,
                        "confidence_level": ci.confidence_level
                    }
                    for ci in business_insight.cluster_insights
                ],
                action_priority_matrix=business_insight.action_priority_matrix,
                analysis_timestamp=business_insight.analysis_timestamp,
                model_name=business_insight.model_name
            )
            session.add(insight)
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存业务洞察失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_latest_business_insight(self):
        """获取最新的业务洞察"""
        session = self.get_session()
        try:
            return session.query(BusinessInsight).order_by(
                BusinessInsight.analysis_timestamp.desc()
            ).first()
        except Exception as e:
            self.logger.error(f"获取业务洞察失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_posts(self, limit: int = 100, subreddits: List[str] = None):
        """获取帖子数据，支持子版块过滤"""
        session = self.get_session()
        try:
            query = session.query(RedditPost)
            if subreddits:
                query = query.filter(RedditPost.subreddit.in_(subreddits))
            
            posts = query.limit(limit).all()
            return posts
        except Exception as e:
            self.logger.error(f"获取帖子数据失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def upsert_keyword_statistics(self, keywords: List[Tuple[str, float]], category: str = "all"):
        """
        更新或插入关键词统计（去重）
        
        Args:
            keywords: [(keyword, score), ...] 关键词和得分列表
            category: 关键词类别
        """
        session = self.get_session()
        try:
            for keyword, score in keywords:
                # 查询是否已存在
                existing = session.query(KeywordStatistic).filter(
                    KeywordStatistic.keyword == keyword,
                    KeywordStatistic.category == category
                ).first()
                
                if existing:
                    # 更新频率和得分
                    existing.frequency += 1
                    existing.tfidf_score = max(existing.tfidf_score, score)
                    existing.last_seen = datetime.utcnow()
                else:
                    # 创建新记录
                    new_stat = KeywordStatistic(
                        keyword=keyword,
                        category=category,
                        frequency=1,
                        tfidf_score=score,
                        first_seen=datetime.utcnow(),
                        last_seen=datetime.utcnow()
                    )
                    session.add(new_stat)
            
            session.commit()
            self.logger.info(f"成功更新关键词统计: {category} - {len(keywords)}个关键词")
            return True
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"更新关键词统计失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_top_keywords(self, category: str = "all", limit: int = 50, order_by: str = "frequency"):
        """
        获取高频关键词
        
        Args:
            category: 类别筛选
            limit: 返回数量
            order_by: 排序方式 (frequency 或 tfidf_score)
        """
        session = self.get_session()
        try:
            query = session.query(KeywordStatistic)
            
            if category:
                query = query.filter(KeywordStatistic.category == category)
            
            if order_by == "frequency":
                query = query.order_by(KeywordStatistic.frequency.desc())
            else:
                query = query.order_by(KeywordStatistic.tfidf_score.desc())
            
            stats = query.limit(limit).all()
            
            result = []
            for stat in stats:
                result.append({
                    'keyword': stat.keyword,
                    'category': stat.category,
                    'frequency': stat.frequency,
                    'tfidf_score': stat.tfidf_score,
                    'first_seen': stat.first_seen,
                    'last_seen': stat.last_seen
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"获取高频关键词失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def clear_keyword_statistics(self):
        """清空关键词统计"""
        session = self.get_session()
        try:
            session.query(KeywordStatistic).delete()
            session.commit()
            self.logger.info("关键词统计已清空")
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"清空关键词统计失败: {str(e)}")
            return False
        finally:
            session.close()

