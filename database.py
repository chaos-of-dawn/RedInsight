"""
数据库模块 - 使用SQLAlchemy管理本地数据库
存储Reddit帖子和评论数据
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, JSON, Index, distinct, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging
import json
import numpy as np
from typing import List, Tuple, Dict, Any
from app_config import Config

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

class SubredditIndex(Base):
    """子版块索引表"""
    __tablename__ = 'subreddit_index'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subreddit_name = Column(String, unique=True, nullable=False)  # 子版块名称
    title = Column(String)  # 子版块标题
    description = Column(Text)  # 子版块描述
    public_description = Column(Text)  # 公开描述
    subscriber_count = Column(Integer)  # 订阅者数量
    
    # 向量化内容
    avg_vector = Column(JSON)  # 平均向量
    keywords = Column(JSON)  # 关键词列表
    main_topics = Column(JSON)  # 主要主题
    
    # 关联的帖子数据（用于展示）
    posts_data = Column(JSON)  # 帖子数据列表
    
    # 元数据
    indexed_at = Column(DateTime, default=datetime.utcnow)  # 索引时间
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 最后更新时间

class UserInteractions(Base):
    """用户互动记录表"""
    __tablename__ = 'user_interactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String, nullable=False)  # 帖子ID
    comment_id = Column(String)  # 评论ID（可选）
    interaction_type = Column(String, nullable=False)  # 互动类型：upvote, downvote, save, follow, subscribe
    target_user = Column(String)  # 目标用户
    target_subreddit = Column(String)  # 目标子版块
    created_at = Column(DateTime, default=datetime.utcnow)  # 互动时间
    status = Column(String, default='success')  # 状态：success, failed, pending
    error_message = Column(Text)  # 错误信息（如果失败）
    
    # 索引
    __table_args__ = (
        Index('idx_post_interaction', 'post_id', 'interaction_type'),
        Index('idx_user_interaction', 'target_user', 'interaction_type'),
        Index('idx_subreddit_interaction', 'target_subreddit', 'interaction_type'),
    )

class PostMonitoring(Base):
    """帖子监控表"""
    __tablename__ = 'post_monitoring'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String, unique=True, nullable=False)  # 帖子ID
    subreddit_name = Column(String, nullable=False)  # 子版块名称
    monitor_type = Column(String, nullable=False)  # 监控类型：comments, votes, saves, follows
    last_check_time = Column(DateTime, default=datetime.utcnow)  # 最后检查时间
    is_active = Column(Boolean, default=True)  # 是否激活
    notification_settings = Column(JSON)  # 通知设置
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    
    # 索引
    __table_args__ = (
        Index('idx_post_monitor', 'post_id', 'is_active'),
        Index('idx_subreddit_monitor', 'subreddit_name', 'is_active'),
    )

class InteractionStats(Base):
    """互动统计表"""
    __tablename__ = 'interaction_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String, unique=True, nullable=False)  # 帖子ID
    subreddit_name = Column(String, nullable=False)  # 子版块名称
    total_upvotes = Column(Integer, default=0)  # 总点赞数
    total_downvotes = Column(Integer, default=0)  # 总点踩数
    total_comments = Column(Integer, default=0)  # 总评论数
    total_saves = Column(Integer, default=0)  # 总保存数
    engagement_score = Column(Float, default=0.0)  # 互动评分
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 最后更新时间
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    
    # 索引
    __table_args__ = (
        Index('idx_post_stats', 'post_id'),
        Index('idx_subreddit_stats', 'subreddit_name'),
        Index('idx_engagement_score', 'engagement_score'),
    )

class UserFollows(Base):
    """用户关注表"""
    __tablename__ = 'user_follows'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_username = Column(String, nullable=False)  # 关注用户名
    follow_type = Column(String, nullable=False)  # 关注类型：follow, unfollow
    followed_at = Column(DateTime, default=datetime.utcnow)  # 关注时间
    user_activity_score = Column(Float, default=0.0)  # 用户活跃度评分
    last_interaction = Column(DateTime)  # 最后互动时间
    interaction_count = Column(Integer, default=0)  # 互动次数
    is_active = Column(Boolean, default=True)  # 是否激活关注
    
    # 索引
    __table_args__ = (
        Index('idx_user_follow', 'target_username', 'is_active'),
        Index('idx_follow_type', 'follow_type', 'is_active'),
    )

class AccountSnapshots(Base):
    """账号快照表（每日记录业力与活跃数据）"""
    __tablename__ = 'account_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_time = Column(DateTime, default=datetime.utcnow)
    link_karma = Column(Integer, default=0)
    comment_karma = Column(Integer, default=0)
    total_karma = Column(Integer, default=0)
    account_age_days = Column(Integer, default=0)
    subs_joined = Column(Integer, default=0)
    upvotes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    posts = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_snapshot_time', 'snapshot_time'),
    )

class SubredditReadiness(Base):
    """子版块发帖资格判定表"""
    __tablename__ = 'subreddit_readiness'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subreddit = Column(String, nullable=False)
    can_post = Column(Boolean, default=False)
    confidence = Column(String, default='Low')
    reasons = Column(JSON)  # 列表
    recommendations = Column(JSON)  # 列表
    checked_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_readiness_subreddit', 'subreddit', 'checked_at'),
    )

class KeywordHistory(Base):
    """关键词历史记录表"""
    __tablename__ = 'keyword_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String, nullable=False)  # 关键词
    source = Column(String)  # 来源（ai_generator, data_scraping, smart_filter, subreddit_recommendation, auto_scheduler等）
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    usage_count = Column(Integer, default=1)  # 使用次数
    last_used_at = Column(DateTime, default=datetime.utcnow)  # 最后使用时间
    
    __table_args__ = (
        Index('idx_keyword_history_keyword', 'keyword'),
        Index('idx_keyword_history_source', 'source'),
        Index('idx_keyword_history_created_at', 'created_at'),
    )

class SubredditHistory(Base):
    """子版块历史记录表（自动去重收录）"""
    __tablename__ = 'subreddit_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subreddit_name = Column(String, nullable=False)  # 子版块名称（不含r/前缀）
    source = Column(String)  # 来源（subreddit_recommendation: 智能推荐, ai_generator: AI生成）
    match_score = Column(Float)  # 匹配度分数
    heat_score = Column(Float)  # 热度分数（仅AI生成）
    combined_score = Column(Float)  # 综合分数（仅AI生成）
    rank = Column(Integer)  # 排名（1-5 for 智能推荐, 1-3 for AI生成）
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    usage_count = Column(Integer, default=1)  # 使用次数（被推荐的次数）
    last_used_at = Column(DateTime, default=datetime.utcnow)  # 最后使用时间
    
    __table_args__ = (
        Index('idx_subreddit_history_name', 'subreddit_name'),
        Index('idx_subreddit_history_source', 'source'),
        Index('idx_subreddit_history_created_at', 'created_at'),
    )

class UploadedFile(Base):
    """上传文件表（与Reddit数据隔离）"""
    __tablename__ = 'uploaded_files'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # 'text' 或 'image'
    file_path = Column(String, nullable=False)  # 文件存储路径
    file_size = Column(Integer)  # 文件大小（字节）
    description = Column(Text)  # 文件描述
    content_preview = Column(Text)  # 文本内容预览（仅文本文件）
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_uploaded_file_type', 'file_type'),
        Index('idx_uploaded_at', 'uploaded_at'),
    )

class PostScoring(Base):
    """帖子评分表"""
    __tablename__ = 'post_scoring'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String, nullable=False)  # Reddit帖子ID
    subreddit = Column(String, nullable=False)  # 子版块名称
    title = Column(Text)  # 帖子标题
    relevance_score = Column(Float, default=0.0)  # 相关性评分 (0-1)
    pain_emotion_score = Column(Float, default=0.0)  # 痛点/情感评分 (0-1)
    timeliness_score = Column(Float, default=0.0)  # 时效性评分 (0-1)
    activity_score = Column(Float, default=0.0)  # 活跃度评分 (0-1)
    final_score = Column(Float, default=0.0)  # 最终综合评分 S
    scored_at = Column(DateTime, default=datetime.utcnow)  # 评分时间
    
    __table_args__ = (
        Index('idx_post_scoring_post_id', 'post_id'),
        Index('idx_post_scoring_subreddit', 'subreddit'),
        Index('idx_post_scoring_final_score', 'final_score'),
        Index('idx_post_scoring_scored_at', 'scored_at'),
    )

class AutoInteractionQueue(Base):
    """自动互动队列表"""
    __tablename__ = 'auto_interaction_queue'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String, nullable=False)  # Reddit帖子ID
    subreddit = Column(String, nullable=False)  # 子版块名称
    interaction_type = Column(String, nullable=False)  # 'deep', 'standard', 'light'
    post_score = Column(Float, default=0.0)  # 帖子评分（用于排序）
    status = Column(String, default='pending')  # 'pending', 'executing', 'completed', 'failed'
    ai_comment = Column(Text)  # AI生成的评论内容（如果是评论互动）
    requires_review = Column(Boolean, default=False)  # 是否需要人工审核
    review_status = Column(String)  # 'pending', 'approved', 'rejected'
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    executed_at = Column(DateTime)  # 执行时间
    error_message = Column(Text)  # 错误信息（如果失败）
    
    __table_args__ = (
        Index('idx_queue_status', 'status'),
        Index('idx_queue_post_score', 'post_score'),
        Index('idx_queue_created_at', 'created_at'),
        Index('idx_queue_review_status', 'review_status'),
    )

class DailyQuota(Base):
    """每日配额表"""
    __tablename__ = 'daily_quota'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    quota_date = Column(DateTime, nullable=False)  # 配额日期
    deep_interactions = Column(Integer, default=0)  # 深度互动配额
    standard_interactions = Column(Integer, default=0)  # 标准互动配额
    light_interactions = Column(Integer, default=0)  # 轻量互动配额
    deep_used = Column(Integer, default=0)  # 已使用深度互动
    standard_used = Column(Integer, default=0)  # 已使用标准互动
    light_used = Column(Integer, default=0)  # 已使用轻量互动
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_quota_date', 'quota_date'),
    )

class AutoInteractionConfig(Base):
    """自动化配置表"""
    __tablename__ = 'auto_interaction_config'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String, nullable=False, unique=True)  # 配置键
    config_value = Column(Text)  # 配置值（JSON字符串）
    description = Column(Text)  # 配置描述
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_config_key', 'config_key'),
    )

class AutoInteractionStatus(Base):
    """自动化运行状态表"""
    __tablename__ = 'auto_interaction_status'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    is_running = Column(Boolean, default=False)  # 是否正在运行
    is_paused = Column(Boolean, default=False)  # 是否暂停
    current_subreddit = Column(String)  # 当前扫描的子版块
    last_scan_time = Column(DateTime)  # 最后扫描时间
    last_execution_time = Column(DateTime)  # 最后执行时间
    total_scanned = Column(Integer, default=0)  # 累计扫描帖子数
    total_scored = Column(Integer, default=0)  # 累计评分帖子数
    total_executed = Column(Integer, default=0)  # 累计执行互动数
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_status_is_running', 'is_running'),
    )

class AutoPostQueue(Base):
    """自动发帖队列表"""
    __tablename__ = 'auto_post_queue'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)  # 帖子标题
    content = Column(Text, nullable=False)  # 帖子内容
    subreddit = Column(String, nullable=False)  # 子版块名称（单个）
    flair = Column(String)  # 标签（可选）
    post_type = Column(String, default='ai_generated')  # 'ai_generated', 'uploaded_text', 'uploaded_image'
    uploaded_file_id = Column(Integer)  # 关联的上传文件ID（如果是本地上传）
    image_path = Column(String)  # 图片路径（如果是图片帖子）
    status = Column(String, default='pending')  # 'pending', 'executing', 'completed', 'failed'
    requires_review = Column(Boolean, default=False)  # 是否需要人工审核
    review_status = Column(String)  # 'pending', 'approved', 'rejected'
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    scheduled_at = Column(DateTime)  # 计划发布时间（可选）
    executed_at = Column(DateTime)  # 执行时间
    error_message = Column(Text)  # 错误信息（如果失败）
    reddit_post_id = Column(String)  # Reddit帖子ID（发布成功后）
    reddit_post_url = Column(String)  # Reddit帖子URL（发布成功后）
    
    __table_args__ = (
        Index('idx_post_queue_status', 'status'),
        Index('idx_post_queue_subreddit', 'subreddit'),
        Index('idx_post_queue_created_at', 'created_at'),
        Index('idx_post_queue_scheduled_at', 'scheduled_at'),
        Index('idx_post_queue_review_status', 'review_status'),
    )

class PostContent(Base):
    """帖子内容表 - 存储准备发布的帖子内容"""
    __tablename__ = 'post_contents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String, default='text')  # 'text', 'markdown', 'html'
    media_files = Column(JSON)  # JSON数组，存储媒体文件信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default='draft')  # 'draft', 'ready', 'scheduled', 'published', 'archived'
    source = Column(String, default='manual')  # 'manual', 'ai_generated'
    keywords = Column(Text)  # 关联的关键词（如果是AI生成）
    is_ai_generated = Column(Boolean, default=False)
    original_ai_prompt = Column(Text)
    generation_batch_id = Column(String)  # 同一批生成的帖子
    edit_history = Column(JSON)  # 编辑历史
    copy_count = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_post_content_status', 'status'),
        Index('idx_post_content_source', 'source'),
        Index('idx_post_content_created_at', 'created_at'),
    )

class PostingSchedule(Base):
    """发布计划表 - 一个帖子可以发布到多个子版块"""
    __tablename__ = 'posting_schedules'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_content_id = Column(Integer, nullable=False)  # 关联的帖子内容ID
    subreddit = Column(String, nullable=False)  # 目标子版块
    scheduled_time = Column(DateTime, nullable=False)  # 计划发布时间
    posting_order = Column(Integer, default=0)  # 发布顺序（同一时间的多个子版块）
    status = Column(String, default='pending')  # 'pending', 'checking', 'approved', 'rejected', 'posting', 'posted', 'failed'
    rule_check_result = Column(JSON)  # AI规则检查结果
    posting_result = Column(JSON)  # 发布结果
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_schedule_status', 'status'),
        Index('idx_schedule_subreddit', 'subreddit'),
        Index('idx_schedule_time', 'scheduled_time'),
        Index('idx_schedule_content', 'post_content_id'),
    )

class SubredditRule(Base):
    """子版块规则缓存表"""
    __tablename__ = 'subreddit_rules'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subreddit = Column(String, nullable=False, unique=True)
    rules_text = Column(Text)
    rules_summary = Column(Text)  # AI生成的规则摘要
    last_updated = Column(DateTime, default=datetime.utcnow)
    rule_version = Column(Integer, default=1)
    
    __table_args__ = (
        Index('idx_subreddit_rule_name', 'subreddit'),
    )

class PostInteraction(Base):
    """互动监控表"""
    __tablename__ = 'post_interactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    posting_schedule_id = Column(Integer, nullable=False)
    post_id = Column(String, nullable=False)  # Reddit帖子ID
    subreddit = Column(String, nullable=False)
    check_time = Column(DateTime, default=datetime.utcnow)
    has_interaction = Column(Boolean, default=False)
    interaction_count = Column(Integer, default=0)  # 评论数+点赞数
    comment_count = Column(Integer, default=0)
    upvote_count = Column(Integer, default=0)
    last_check_at = Column(DateTime, default=datetime.utcnow)
    next_check_at = Column(DateTime)
    auto_reply_triggered = Column(Boolean, default=False)
    auto_reply_count = Column(Integer, default=0)
    check_count = Column(Integer, default=0)  # 检查次数
    
    __table_args__ = (
        Index('idx_interaction_schedule', 'posting_schedule_id'),
        Index('idx_interaction_post', 'post_id'),
        Index('idx_interaction_next_check', 'next_check_at'),
    )

class AutoReply(Base):
    """自动回复记录表"""
    __tablename__ = 'auto_replies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_interaction_id = Column(Integer, nullable=False)
    parent_id = Column(String)  # 父评论ID（如果是回复评论）
    reply_content = Column(Text, nullable=False)
    reply_type = Column(String, default='top_level')  # 'top_level', 'reply_to_comment'
    posted_at = Column(DateTime)
    status = Column(String, default='pending')  # 'pending', 'posted', 'failed'
    reddit_comment_id = Column(String)  # Reddit评论ID（回复成功后）
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_reply_interaction', 'post_interaction_id'),
        Index('idx_reply_status', 'status'),
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
        self.StructuredExtraction = StructuredExtraction
        self.VectorizedText = VectorizedText
        self.ClusteringResult = ClusteringResult
        self.BusinessInsight = BusinessInsight
        self.SubredditIndex = SubredditIndex
        # 智能发帖相关表
        self.PostContent = PostContent
        self.PostingSchedule = PostingSchedule
        self.SubredditRule = SubredditRule
        self.PostInteraction = PostInteraction
        self.AutoReply = AutoReply
        self.UserInteractions = UserInteractions
        self.PostMonitoring = PostMonitoring
        self.InteractionStats = InteractionStats
        self.UserFollows = UserFollows
        self.AccountSnapshots = AccountSnapshots
        self.SubredditReadiness = SubredditReadiness
        self.UploadedFile = UploadedFile
        self.PostScoring = PostScoring
        self.AutoInteractionQueue = AutoInteractionQueue
        self.DailyQuota = DailyQuota
        self.AutoInteractionConfig = AutoInteractionConfig
        self.AutoInteractionStatus = AutoInteractionStatus
        self.AutoPostQueue = AutoPostQueue
        self.KeywordHistory = KeywordHistory
        self.SubredditHistory = SubredditHistory
        
        self.create_tables()
    
    def create_tables(self):
        """创建数据库表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("数据库表创建成功")
        except Exception as e:
            self.logger.error(f"创建数据库表失败: {str(e)}")

    # ==================== 账号与子版块发帖资格相关 ====================
    def save_account_snapshot(self, snapshot: dict) -> bool:
        session = self.get_session()
        try:
            rec = AccountSnapshots(
                snapshot_time=snapshot.get('snapshot_time', datetime.utcnow()),
                link_karma=snapshot.get('link_karma', 0),
                comment_karma=snapshot.get('comment_karma', 0),
                total_karma=snapshot.get('total_karma', 0),
                account_age_days=snapshot.get('account_age_days', 0),
                subs_joined=snapshot.get('subs_joined', 0),
                upvotes=snapshot.get('upvotes', 0),
                comments=snapshot.get('comments', 0),
                posts=snapshot.get('posts', 0),
            )
            session.add(rec)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存账号快照失败: {str(e)}")
            return False
        finally:
            session.close()

    def get_latest_account_snapshot(self):
        session = self.get_session()
        try:
            return session.query(AccountSnapshots).order_by(AccountSnapshots.snapshot_time.desc()).first()
        except Exception as e:
            self.logger.error(f"获取最新账号快照失败: {str(e)}")
            return None
        finally:
            session.close()

    def save_subreddit_readiness(self, subreddit: str, can_post: bool, confidence: str, reasons: list, recommendations: list) -> bool:
        session = self.get_session()
        try:
            rec = SubredditReadiness(
                subreddit=subreddit,
                can_post=can_post,
                confidence=confidence,
                reasons=reasons or [],
                recommendations=recommendations or [],
                checked_at=datetime.utcnow()
            )
            session.add(rec)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存子版块发帖资格失败: {str(e)}")
            return False
        finally:
            session.close()

    def get_latest_subreddit_readiness(self, subreddit: str):
        session = self.get_session()
        try:
            return session.query(SubredditReadiness).filter(SubredditReadiness.subreddit == subreddit).order_by(SubredditReadiness.checked_at.desc()).first()
        except Exception as e:
            self.logger.error(f"获取子版块发帖资格失败: {str(e)}")
            return None
        finally:
            session.close()
    
    # ==================== 上传文件管理（与Reddit数据隔离） ====================
    
    def save_uploaded_file(self, filename: str, file_type: str, file_path: str, file_size: int, 
                          description: str = None, content_preview: str = None) -> int:
        """
        保存上传文件记录
        
        Args:
            filename: 文件名
            file_type: 文件类型 ('text' 或 'image')
            file_path: 文件存储路径
            file_size: 文件大小（字节）
            description: 文件描述
            content_preview: 文本内容预览（仅文本文件）
            
        Returns:
            文件记录ID
        """
        session = self.get_session()
        try:
            uploaded_file = UploadedFile(
                filename=filename,
                file_type=file_type,
                file_path=file_path,
                file_size=file_size,
                description=description,
                content_preview=content_preview,
                uploaded_at=datetime.utcnow()
            )
            session.add(uploaded_file)
            session.commit()
            file_id = uploaded_file.id
            self.logger.info(f"文件上传记录保存成功: {filename} (ID: {file_id})")
            return file_id
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存上传文件记录失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_uploaded_file(self, file_id: int):
        """获取上传文件记录"""
        session = self.get_session()
        try:
            file_record = session.query(UploadedFile).filter(UploadedFile.id == file_id).first()
            if file_record:
                return {
                    'id': file_record.id,
                    'filename': file_record.filename,
                    'file_type': file_record.file_type,
                    'file_path': file_record.file_path,
                    'file_size': file_record.file_size,
                    'description': file_record.description,
                    'content_preview': file_record.content_preview,
                    'uploaded_at': file_record.uploaded_at
                }
            return None
        except Exception as e:
            self.logger.error(f"获取上传文件记录失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_all_uploaded_files(self, file_type: str = None):
        """
        获取所有上传文件记录
        
        Args:
            file_type: 文件类型过滤 ('text' 或 'image')，None表示获取所有类型
            
        Returns:
            文件记录列表
        """
        session = self.get_session()
        try:
            query = session.query(UploadedFile)
            if file_type:
                query = query.filter(UploadedFile.file_type == file_type)
            
            files = query.order_by(UploadedFile.uploaded_at.desc()).all()
            return [
                {
                    'id': f.id,
                    'filename': f.filename,
                    'file_type': f.file_type,
                    'file_path': f.file_path,
                    'file_size': f.file_size,
                    'description': f.description,
                    'content_preview': f.content_preview,
                    'uploaded_at': f.uploaded_at
                }
                for f in files
            ]
        except Exception as e:
            self.logger.error(f"获取上传文件列表失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def delete_uploaded_file(self, file_id: int) -> bool:
        """
        删除上传文件记录（不删除实际文件，需要手动删除文件）
        
        Args:
            file_id: 文件记录ID
            
        Returns:
            是否删除成功
        """
        session = self.get_session()
        try:
            file_record = session.query(UploadedFile).filter(UploadedFile.id == file_id).first()
            if file_record:
                session.delete(file_record)
                session.commit()
                self.logger.info(f"文件记录删除成功: ID {file_id}")
                return True
            return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"删除文件记录失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def save_keyword_to_history(self, keyword: str, source: str = "unknown"):
        """
        保存关键词到历史记录（自动去重，不考虑来源）
        
        Args:
            keyword: 关键词（单个关键词，不是逗号分隔的字符串）
            source: 来源（ai_generator, data_scraping, smart_filter, subreddit_recommendation, auto_scheduler等）
        """
        if not keyword or not keyword.strip():
            return
        
        keyword = keyword.strip()
        session = self.get_session()
        try:
            # 查找是否已存在相同关键词（不考虑来源，实现自动去重）
            existing = session.query(KeywordHistory).filter(
                KeywordHistory.keyword == keyword
            ).first()
            
            if existing:
                # 更新使用次数和最后使用时间
                existing.usage_count += 1
                existing.last_used_at = datetime.utcnow()
                
                # 如果来源不同，合并来源信息（用逗号分隔多个来源）
                if source and source != "unknown" and source not in (existing.source or ""):
                    if existing.source:
                        # 检查来源是否已包含当前来源
                        existing_sources = [s.strip() for s in existing.source.split(',')]
                        if source not in existing_sources:
                            existing.source = existing.source + f", {source}"
                    else:
                        existing.source = source
            else:
                # 创建新记录
                new_record = KeywordHistory(
                    keyword=keyword,
                    source=source,
                    usage_count=1,
                    last_used_at=datetime.utcnow()
                )
                session.add(new_record)
            
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存关键词到历史记录失败: {str(e)}")
        finally:
            session.close()
    
    def save_keywords_to_history(self, keywords: str, source: str = "unknown"):
        """
        保存多个关键词到历史记录（支持逗号分隔、换行分隔等）
        
        Args:
            keywords: 关键词字符串（可以是逗号分隔、换行分隔等）
            source: 来源
        """
        if not keywords or not keywords.strip():
            return
        
        # 解析关键词（支持逗号、换行、空格分隔）
        import re
        # 先按换行分割
        lines = keywords.split('\n')
        keyword_list = []
        for line in lines:
            # 再按逗号分割
            parts = line.split(',')
            for part in parts:
                # 再按空格分割（处理多个空格分隔的关键词）
                words = re.split(r'\s+', part.strip())
                for word in words:
                    if word.strip():
                        keyword_list.append(word.strip())
        
        # 去重并保存
        unique_keywords = list(set(keyword_list))
        for keyword in unique_keywords:
            self.save_keyword_to_history(keyword, source)
    
    def save_subreddit_to_history(self, subreddit_name: str, source: str = "unknown", 
                                   match_score: float = None, heat_score: float = None, 
                                   combined_score: float = None, rank: int = None):
        """
        保存子版块到历史记录（自动去重，不考虑来源）
        
        Args:
            subreddit_name: 子版块名称（不含r/前缀）
            source: 来源（subreddit_recommendation: 智能推荐, ai_generator: AI生成）
            match_score: 匹配度分数
            heat_score: 热度分数（仅AI生成）
            combined_score: 综合分数（仅AI生成）
            rank: 排名（1-5 for 智能推荐, 1-3 for AI生成）
        """
        if not subreddit_name or not subreddit_name.strip():
            return
        
        # 清理子版块名称（移除r/前缀和空格）
        subreddit_name = subreddit_name.strip().lstrip('r/').strip()
        if not subreddit_name:
            return
        
        session = self.get_session()
        try:
            # 查找是否已存在相同子版块（不考虑来源，实现自动去重）
            existing = session.query(SubredditHistory).filter(
                SubredditHistory.subreddit_name == subreddit_name
            ).first()
            
            if existing:
                # 更新使用次数和最后使用时间
                existing.usage_count += 1
                existing.last_used_at = datetime.utcnow()
                
                # 如果来源不同，合并来源信息（用逗号分隔多个来源）
                if source and source != "unknown" and source not in (existing.source or ""):
                    if existing.source:
                        existing_sources = [s.strip() for s in existing.source.split(',')]
                        if source not in existing_sources:
                            existing.source = existing.source + f", {source}"
                    else:
                        existing.source = source
                
                # 更新分数信息（保留最高的分数）
                if match_score is not None and (existing.match_score is None or match_score > existing.match_score):
                    existing.match_score = match_score
                if heat_score is not None and (existing.heat_score is None or heat_score > existing.heat_score):
                    existing.heat_score = heat_score
                if combined_score is not None and (existing.combined_score is None or combined_score > existing.combined_score):
                    existing.combined_score = combined_score
                if rank is not None and (existing.rank is None or rank < existing.rank):
                    existing.rank = rank  # 保留更小的排名（更靠前）
            else:
                # 创建新记录
                new_record = SubredditHistory(
                    subreddit_name=subreddit_name,
                    source=source,
                    match_score=match_score,
                    heat_score=heat_score,
                    combined_score=combined_score,
                    rank=rank,
                    usage_count=1,
                    last_used_at=datetime.utcnow()
                )
                session.add(new_record)
            
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存子版块到历史记录失败: {str(e)}")
        finally:
            session.close()
    
    def save_subreddits_to_history(self, subreddits: List[Dict[str, Any]], source: str, top_n: int = None):
        """
        批量保存子版块到历史记录
        
        Args:
            subreddits: 子版块列表，每个元素包含子版块信息
            source: 来源（subreddit_recommendation: 智能推荐, ai_generator: AI生成）
            top_n: 只保存前N个（如果指定）
        """
        if not subreddits:
            return
        
        # 如果指定了top_n，只保存前N个
        if top_n:
            subreddits = subreddits[:top_n]
        
        for idx, subreddit_info in enumerate(subreddits, 1):
            # 提取子版块名称（支持多种格式）
            subreddit_name = subreddit_info.get('subreddit') or subreddit_info.get('subreddit_name') or subreddit_info.get('name', '')
            if not subreddit_name:
                continue
            
            # 提取分数信息
            match_score = subreddit_info.get('match_score') or subreddit_info.get('score')
            heat_score = subreddit_info.get('heat_score')
            combined_score = subreddit_info.get('combined_score')
            rank = idx  # 使用索引作为排名
            
            # 如果match_score是百分比，转换为0-100的分数
            if match_score is not None and isinstance(match_score, float) and match_score <= 1.0:
                match_score = match_score * 100
            
            self.save_subreddit_to_history(
                subreddit_name=subreddit_name,
                source=source,
                match_score=match_score,
                heat_score=heat_score,
                combined_score=combined_score,
                rank=rank
            )
    
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
            insight = session.query(BusinessInsight).order_by(
                BusinessInsight.analysis_timestamp.desc()
            ).first()
            if insight:
                self.logger.info(f"找到最新业务洞察: analysis_id={insight.analysis_id}, timestamp={insight.analysis_timestamp}")
            else:
                # 使用DEBUG级别，避免在没有深度分析时频繁警告
                self.logger.debug("数据库中未找到任何业务洞察记录（这是正常的，如果还没有运行过深度分析）")
            return insight
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
    
    def get_posts_with_filters(self, 
                               subreddits: List[str] = None,
                               min_score: int = None,
                               max_score: int = None,
                               keywords: List[str] = None,
                               limit: int = 1000):
        """
        获取帖子数据（支持多条件筛选）
        
        Args:
            subreddits: 子版块列表（多选）
            min_score: 最低分数
            max_score: 最高分数（0表示不限制）
            keywords: 关键词列表（在标题和内容中搜索）
            limit: 结果数量限制
            
        Returns:
            符合条件的帖子列表
        """
        session = self.get_session()
        try:
            from sqlalchemy import or_, text
            
            query = session.query(RedditPost)
            
            # 子版块筛选
            if subreddits:
                query = query.filter(RedditPost.subreddit.in_(subreddits))
            
            # 分数范围筛选
            if min_score is not None and min_score > 0:
                query = query.filter(RedditPost.score >= min_score)
            if max_score is not None and max_score > 0:
                query = query.filter(RedditPost.score <= max_score)
            
            # 关键词筛选（在标题或内容中搜索）
            if keywords:
                valid_keywords = []
                
                # 清理和验证关键词
                for keyword in keywords:
                    if keyword:
                        keyword_clean = keyword.strip()
                        if keyword_clean:
                            valid_keywords.append(keyword_clean)
                
                if valid_keywords:
                    # 构建OR条件：多个关键词之间是OR关系
                    if len(valid_keywords) == 1:
                        keyword_clean = valid_keywords[0]
                        keyword_condition = (
                            RedditPost.title.contains(keyword_clean) |
                            RedditPost.selftext.contains(keyword_clean)
                        )
                        query = query.filter(keyword_condition)
                    else:
                        # 多个关键词，使用OR组合
                        keyword_conditions = []
                        for keyword_clean in valid_keywords:
                            keyword_condition = (
                                RedditPost.title.contains(keyword_clean) |
                                RedditPost.selftext.contains(keyword_clean)
                            )
                            keyword_conditions.append(keyword_condition)
                        
                        combined_condition = or_(*keyword_conditions)
                        query = query.filter(combined_condition)
            
            # 按分数降序排列
            posts = query.order_by(RedditPost.score.desc()).limit(limit).all()
            
            self.logger.info(f"筛选查询完成，找到 {len(posts)} 条符合条件的帖子")
            return posts
            
        except Exception as e:
            self.logger.error(f"筛选查询失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_posts_by_search_query(self, search_query: str) -> List:
        """
        根据搜索关键词获取帖子数据
        
        Args:
            search_query: 搜索关键词
            
        Returns:
            符合条件的帖子列表
        """
        session = self.get_session()
        try:
            query = session.query(RedditPost).filter(RedditPost.search_query == search_query)
            posts = query.all()
            self.logger.info(f"查询关键词 '{search_query}' 找到 {len(posts)} 个帖子")
            return posts
        except Exception as e:
            self.logger.error(f"查询关键词帖子失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_all_search_queries(self) -> List[str]:
        """
        获取所有已使用的搜索关键词
        
        Returns:
            搜索关键词列表（去重）
        """
        session = self.get_session()
        try:
            queries = session.query(distinct(RedditPost.search_query)).filter(
                RedditPost.search_query.isnot(None),
                RedditPost.search_query != ''
            ).all()
            search_queries = [q[0] for q in queries if q[0]]
            self.logger.info(f"找到 {len(search_queries)} 个不同的搜索关键词")
            return search_queries
        except Exception as e:
            self.logger.error(f"获取搜索关键词列表失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def analyze_subreddit_heat_by_keyword(self, search_query: str) -> List[Dict[str, Any]]:
        """
        分析指定关键词下各子版块的热度
        
        Args:
            search_query: 搜索关键词
            
        Returns:
            子版块热度统计列表，包含：
            - subreddit: 子版块名称
            - post_count: 帖子数量
            - total_score: 总分数
            - avg_score: 平均分数
            - total_comments: 总评论数
            - avg_comments: 平均评论数
            - heat_score: 热度评分（综合指标）
        """
        session = self.get_session()
        try:
            # 查询该关键词下的所有帖子
            posts = session.query(RedditPost).filter(
                RedditPost.search_query == search_query
            ).all()
            
            if not posts:
                return []
            
            # 按子版块分组统计
            subreddit_stats = {}
            for post in posts:
                subreddit = post.subreddit
                if subreddit not in subreddit_stats:
                    subreddit_stats[subreddit] = {
                        'subreddit': subreddit,
                        'post_count': 0,
                        'total_score': 0,
                        'total_comments': 0,
                        'scores': [],
                        'comments': []
                    }
                
                stats = subreddit_stats[subreddit]
                stats['post_count'] += 1
                stats['total_score'] += (post.score or 0)
                stats['total_comments'] += (post.num_comments or 0)
                stats['scores'].append(post.score or 0)
                stats['comments'].append(post.num_comments or 0)
            
            # 计算统计指标
            results = []
            for subreddit, stats in subreddit_stats.items():
                post_count = stats['post_count']
                avg_score = stats['total_score'] / post_count if post_count > 0 else 0
                avg_comments = stats['total_comments'] / post_count if post_count > 0 else 0
                
                # 计算热度评分（综合多个指标）
                # 热度 = (帖子数量权重 * 0.3 + 平均分数权重 * 0.4 + 平均评论数权重 * 0.3)
                max_posts = max([s['post_count'] for s in subreddit_stats.values()]) or 1
                max_avg_score = max([s['total_score'] / s['post_count'] for s in subreddit_stats.values() if s['post_count'] > 0]) or 1
                max_avg_comments = max([s['total_comments'] / s['post_count'] for s in subreddit_stats.values() if s['post_count'] > 0]) or 1
                
                post_count_weight = (post_count / max_posts) if max_posts > 0 else 0
                avg_score_weight = (avg_score / max_avg_score) if max_avg_score > 0 else 0
                avg_comments_weight = (avg_comments / max_avg_comments) if max_avg_comments > 0 else 0
                
                heat_score = (
                    post_count_weight * 0.3 +
                    avg_score_weight * 0.4 +
                    avg_comments_weight * 0.3
                ) * 100  # 转换为0-100分
                
                results.append({
                    'subreddit': subreddit,
                    'post_count': post_count,
                    'total_score': stats['total_score'],
                    'avg_score': round(avg_score, 2),
                    'total_comments': stats['total_comments'],
                    'avg_comments': round(avg_comments, 2),
                    'heat_score': round(heat_score, 2)
                })
            
            # 按热度评分排序
            results.sort(key=lambda x: x['heat_score'], reverse=True)
            
            self.logger.info(f"关键词 '{search_query}' 热度分析完成，找到 {len(results)} 个子版块")
            return results
            
        except Exception as e:
            self.logger.error(f"分析子版块热度失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_comments_by_post_id(self, post_id: str):
        """从本地数据库获取指定帖子的评论"""
        session = self.get_session()
        try:
            comments = session.query(RedditComment).filter(
                RedditComment.post_id == post_id
            ).order_by(RedditComment.score.desc()).all()
            
            self.logger.info(f"从数据库获取帖子 {post_id} 的 {len(comments)} 条评论")
            return comments
            
        except Exception as e:
            self.logger.error(f"获取评论失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_post_by_id(self, post_id: str):
        """根据ID获取单个帖子的完整信息"""
        session = self.get_session()
        try:
            post = session.query(RedditPost).filter(RedditPost.id == post_id).first()
            return post
        except Exception as e:
            self.logger.error(f"获取帖子失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def save_subreddit_index(self, subreddit_name: str, description: str = None, 
                             subscriber_count: int = 0, public_description: str = None,
                             avg_vector: List[float] = None, keywords: List[str] = None,
                             main_topics: List[str] = None, posts_data: List[Dict] = None,
                             indexed_at: datetime = None):
        """保存或更新子版块索引"""
        session = self.get_session()
        try:
            # 检查是否已存在
            existing = session.query(SubredditIndex).filter(
                SubredditIndex.subreddit_name == subreddit_name
            ).first()
            
            if existing:
                # 更新现有记录
                if description is not None:
                    existing.description = description
                if public_description is not None:
                    existing.public_description = public_description
                if subscriber_count > 0:
                    existing.subscriber_count = subscriber_count
                if avg_vector:
                    existing.avg_vector = avg_vector
                if keywords:
                    existing.keywords = keywords
                if main_topics:
                    existing.main_topics = main_topics
                if posts_data:
                    existing.posts_data = posts_data
                if indexed_at:
                    existing.indexed_at = indexed_at
                existing.last_updated = datetime.utcnow()
            else:
                # 创建新记录
                new_index = SubredditIndex(
                    subreddit_name=subreddit_name,
                    description=description or '',
                    public_description=public_description or '',
                    subscriber_count=subscriber_count,
                    avg_vector=avg_vector or [],
                    keywords=keywords or [],
                    main_topics=main_topics or [],
                    posts_data=posts_data or [],
                    indexed_at=indexed_at or datetime.utcnow()
                )
                session.add(new_index)
            
            session.commit()
            self.logger.info(f"子版块索引保存成功: r/{subreddit_name}")
            return True
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存子版块索引失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_subreddit_index(self, subreddit_name: str):
        """获取子版块索引"""
        session = self.get_session()
        try:
            index = session.query(SubredditIndex).filter(
                SubredditIndex.subreddit_name == subreddit_name
            ).first()
            
            if index:
                return {
                    'subreddit_name': index.subreddit_name,
                    'title': index.title,
                    'description': index.description,
                    'public_description': index.public_description,
                    'subscriber_count': index.subscriber_count,
                    'avg_vector': index.avg_vector,
                    'keywords': index.keywords,
                    'main_topics': index.main_topics,
                    'posts_data': index.posts_data,
                    'indexed_at': index.indexed_at,
                    'last_updated': index.last_updated
                }
            return None
            
        except Exception as e:
            self.logger.error(f"获取子版块索引失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_all_subreddit_indices(self):
        """获取所有子版块索引"""
        session = self.get_session()
        try:
            indices = session.query(SubredditIndex).all()
            return [self.get_subreddit_index(idx.subreddit_name) for idx in indices]
        except Exception as e:
            self.logger.error(f"获取所有子版块索引失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def delete_subreddit_index(self, subreddit_name: str):
        """删除子版块索引"""
        session = self.get_session()
        try:
            index = session.query(SubredditIndex).filter(
                SubredditIndex.subreddit_name == subreddit_name
            ).first()
            
            if index:
                session.delete(index)
                session.commit()
                self.logger.info(f"子版块索引删除成功: r/{subreddit_name}")
                return True
            return False
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"删除子版块索引失败: {str(e)}")
            return False
        finally:
            session.close()
    
    # ==================== 自动化运营相关 ====================
    
    def save_post_scoring(self, post_id: str, subreddit: str, title: str, 
                         relevance_score: float, pain_emotion_score: float,
                         timeliness_score: float, activity_score: float,
                         final_score: float) -> int:
        """保存帖子评分"""
        session = self.get_session()
        try:
            # 检查是否已存在
            existing = session.query(PostScoring).filter(PostScoring.post_id == post_id).first()
            if existing:
                # 更新现有记录
                existing.subreddit = subreddit
                existing.title = title
                existing.relevance_score = relevance_score
                existing.pain_emotion_score = pain_emotion_score
                existing.timeliness_score = timeliness_score
                existing.activity_score = activity_score
                existing.final_score = final_score
                existing.scored_at = datetime.utcnow()
                session.commit()
                return existing.id
            else:
                # 创建新记录
                scoring = PostScoring(
                    post_id=post_id,
                    subreddit=subreddit,
                    title=title,
                    relevance_score=relevance_score,
                    pain_emotion_score=pain_emotion_score,
                    timeliness_score=timeliness_score,
                    activity_score=activity_score,
                    final_score=final_score,
                    scored_at=datetime.utcnow()
                )
                session.add(scoring)
                session.commit()
                return scoring.id
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存帖子评分失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_post_scorings(self, subreddit: str = None, min_score: float = None, limit: int = 100):
        """获取帖子评分列表（返回字典列表，避免session依赖）"""
        session = self.get_session()
        try:
            query = session.query(PostScoring)
            if subreddit:
                query = query.filter(PostScoring.subreddit == subreddit)
            if min_score is not None:
                query = query.filter(PostScoring.final_score >= min_score)
            scorings = query.order_by(PostScoring.final_score.desc()).limit(limit).all()
            # 转换为字典列表
            result = []
            for scoring in scorings:
                result.append({
                    'id': scoring.id,
                    'post_id': scoring.post_id,
                    'subreddit': scoring.subreddit,
                    'title': scoring.title,
                    'relevance_score': scoring.relevance_score,
                    'pain_emotion_score': scoring.pain_emotion_score,
                    'timeliness_score': scoring.timeliness_score,
                    'activity_score': scoring.activity_score,
                    'final_score': scoring.final_score,
                    'scored_at': scoring.scored_at
                })
            return result
        except Exception as e:
            self.logger.error(f"获取帖子评分失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def add_to_interaction_queue(self, post_id: str, subreddit: str, interaction_type: str,
                                 post_score: float, ai_comment: str = None,
                                 requires_review: bool = False) -> int:
        """添加到互动队列"""
        session = self.get_session()
        try:
            # 检查是否已存在待执行的相同任务
            existing = session.query(AutoInteractionQueue).filter(
                AutoInteractionQueue.post_id == post_id,
                AutoInteractionQueue.status == 'pending'
            ).first()
            if existing:
                return existing.id
            
            queue_item = AutoInteractionQueue(
                post_id=post_id,
                subreddit=subreddit,
                interaction_type=interaction_type,
                post_score=post_score,
                ai_comment=ai_comment,
                status='pending',  # 显式设置状态为pending
                requires_review=requires_review,
                review_status='pending' if requires_review else None,
                created_at=datetime.utcnow()
            )
            session.add(queue_item)
            session.commit()
            return queue_item.id
        except Exception as e:
            session.rollback()
            self.logger.error(f"添加到互动队列失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_pending_interactions(self, limit: int = 50, interaction_type: str = None):
        """
        获取待执行的互动任务（按评分排序，返回字典列表，避免session依赖）
        
        Args:
            limit: 返回数量限制
            interaction_type: 可选，按互动类型筛选（'deep', 'standard', 'light'）
        """
        from sqlalchemy import or_
        session = self.get_session()
        try:
            query = session.query(AutoInteractionQueue).filter(
                AutoInteractionQueue.status == 'pending',
                # 自动执行：允许 pending/approved/None，只排除明确被拒绝(rejected)的任务
                or_(
                    AutoInteractionQueue.review_status.is_(None),
                    AutoInteractionQueue.review_status != 'rejected'
                )
            )
            
            # 如果指定了互动类型，添加筛选条件
            if interaction_type:
                query = query.filter(AutoInteractionQueue.interaction_type == interaction_type)
            
            tasks = query.order_by(AutoInteractionQueue.post_score.desc()).limit(limit).all()
            # 转换为字典列表
            result = []
            for task in tasks:
                result.append({
                    'id': task.id,
                    'post_id': task.post_id,
                    'subreddit': task.subreddit,
                    'interaction_type': task.interaction_type,
                    'post_score': task.post_score,
                    'status': task.status,
                    'ai_comment': task.ai_comment,
                    'requires_review': task.requires_review,
                    'review_status': task.review_status,
                    'created_at': task.created_at,
                    'executed_at': task.executed_at,
                    'error_message': task.error_message
                })
            return result
        except Exception as e:
            self.logger.error(f"获取待执行互动失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def update_interaction_status(self, queue_id: int, status: str, error_message: str = None):
        """更新互动任务状态"""
        session = self.get_session()
        try:
            queue_item = session.query(AutoInteractionQueue).filter(AutoInteractionQueue.id == queue_id).first()
            if queue_item:
                queue_item.status = status
                if status == 'completed':
                    queue_item.executed_at = datetime.utcnow()
                if error_message:
                    queue_item.error_message = error_message
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"更新互动状态失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def reset_failed_tasks(self, reset_executing: bool = True) -> int:
        """
        重置失败和卡住的任务为pending状态
        
        Args:
            reset_executing: 是否也重置executing状态的任务（卡住的任务）
            
        Returns:
            重置的任务数量
        """
        session = self.get_session()
        try:
            # 重置failed状态的任务
            failed_tasks = session.query(AutoInteractionQueue).filter(
                AutoInteractionQueue.status == 'failed'
            ).all()
            
            # 重置executing状态的任务（如果启用）
            executing_tasks = []
            if reset_executing:
                executing_tasks = session.query(AutoInteractionQueue).filter(
                    AutoInteractionQueue.status == 'executing'
                ).all()
            
            reset_count = 0
            for task in failed_tasks + executing_tasks:
                task.status = 'pending'
                task.error_message = None  # 清除错误信息
                task.executed_at = None  # 清除执行时间
                reset_count += 1
            
            session.commit()
            return reset_count
        except Exception as e:
            session.rollback()
            self.logger.error(f"重置失败任务失败: {str(e)}")
            return 0
        finally:
            session.close()
    
    def reset_auto_operation(self, clear_all_tasks: bool = True, reset_statistics: bool = True, clear_activity_logs: bool = True) -> Dict[str, Any]:
        """
        完全重置自动运营功能
        
        Args:
            clear_all_tasks: 是否清理所有任务（包括pending、executing、failed，但保留completed用于历史记录）
            reset_statistics: 是否重置运行状态统计
            clear_activity_logs: 是否清理活动日志
            
        Returns:
            重置结果统计
        """
        session = self.get_session()
        result = {
            'tasks_deleted': 0,
            'tasks_reset': 0,
            'statistics_reset': False,
            'logs_cleared': False
        }
        
        try:
            # 1. 停止运行状态
            status = session.query(AutoInteractionStatus).order_by(AutoInteractionStatus.id.desc()).first()
            if status:
                status.is_running = False
                status.is_paused = False
                status.current_subreddit = None
                status.last_scan_time = None
                status.last_execution_time = None
            
            # 2. 清理任务
            if clear_all_tasks:
                # 删除所有非completed状态的任务（保留已完成的任务作为历史记录）
                deleted = session.query(AutoInteractionQueue).filter(
                    AutoInteractionQueue.status.in_(['pending', 'executing', 'failed'])
                ).delete()
                result['tasks_deleted'] = deleted
                
                # 重置executing状态的任务为pending（如果还有的话）
                executing_tasks = session.query(AutoInteractionQueue).filter(
                    AutoInteractionQueue.status == 'executing'
                ).all()
                for task in executing_tasks:
                    task.status = 'pending'
                    task.error_message = None
                    task.executed_at = None
                result['tasks_reset'] = len(executing_tasks)
            
            # 3. 重置统计信息
            if reset_statistics and status:
                status.total_scanned = 0
                status.total_scored = 0
                status.total_executed = 0
                result['statistics_reset'] = True
            
            # 4. 清理活动日志
            if clear_activity_logs:
                # 清理存储在配置中的活动日志
                config = session.query(AutoInteractionConfig).filter(
                    AutoInteractionConfig.config_key == 'auto_activity_logs'
                ).first()
                if config:
                    config.config_value = '[]'
                    result['logs_cleared'] = True
            
            session.commit()
            return result
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"重置自动运营功能失败: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_pending_reviews(self):
        """获取待审核的评论（返回字典列表，避免session依赖）"""
        session = self.get_session()
        try:
            reviews = session.query(AutoInteractionQueue).filter(
                AutoInteractionQueue.requires_review == True,
                AutoInteractionQueue.review_status == 'pending'
            ).order_by(AutoInteractionQueue.created_at.desc()).all()
            # 转换为字典列表
            result = []
            for review in reviews:
                result.append({
                    'id': review.id,
                    'post_id': review.post_id,
                    'subreddit': review.subreddit,
                    'interaction_type': review.interaction_type,
                    'post_score': review.post_score,
                    'status': review.status,
                    'ai_comment': review.ai_comment,
                    'requires_review': review.requires_review,
                    'review_status': review.review_status,
                    'created_at': review.created_at,
                    'executed_at': review.executed_at,
                    'error_message': review.error_message
                })
            return result
        except Exception as e:
            self.logger.error(f"获取待审核评论失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def update_review_status(self, queue_id: int, review_status: str):
        """更新审核状态"""
        session = self.get_session()
        try:
            queue_item = session.query(AutoInteractionQueue).filter(AutoInteractionQueue.id == queue_id).first()
            if queue_item:
                queue_item.review_status = review_status
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"更新审核状态失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_daily_quota(self, quota_date: datetime = None):
        """获取每日配额（如果不存在则创建，返回字典，避免session依赖）"""
        if quota_date is None:
            quota_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            quota_date = quota_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        session = self.get_session()
        try:
            quota = session.query(DailyQuota).filter(
                func.date(DailyQuota.quota_date) == quota_date.date()
            ).first()
            
            if not quota:
                # 创建默认配额
                quota = DailyQuota(
                    quota_date=quota_date,
                    deep_interactions=0,
                    standard_interactions=0,
                    light_interactions=0,
                    deep_used=0,
                    standard_used=0,
                    light_used=0
                )
                session.add(quota)
                session.commit()
            
            # 在session关闭前访问所有属性，转换为字典
            result = {
                'id': quota.id,
                'quota_date': quota.quota_date,
                'deep_interactions': quota.deep_interactions,
                'standard_interactions': quota.standard_interactions,
                'light_interactions': quota.light_interactions,
                'deep_used': quota.deep_used,
                'standard_used': quota.standard_used,
                'light_used': quota.light_used,
                'updated_at': quota.updated_at
            }
            return result
        except Exception as e:
            session.rollback()
            self.logger.error(f"获取每日配额失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def update_daily_quota(self, quota_date: datetime, deep: int = None, standard: int = None, light: int = None):
        """更新每日配额"""
        quota_date = quota_date.replace(hour=0, minute=0, second=0, microsecond=0)
        session = self.get_session()
        try:
            quota = session.query(DailyQuota).filter(
                func.date(DailyQuota.quota_date) == quota_date.date()
            ).first()
            
            if not quota:
                quota = DailyQuota(quota_date=quota_date)
                session.add(quota)
            
            if deep is not None:
                quota.deep_interactions = deep
            if standard is not None:
                quota.standard_interactions = standard
            if light is not None:
                quota.light_interactions = light
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"更新每日配额失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def increment_quota_used(self, quota_date: datetime, interaction_type: str):
        """增加配额使用量"""
        quota_date = quota_date.replace(hour=0, minute=0, second=0, microsecond=0)
        session = self.get_session()
        try:
            quota = session.query(DailyQuota).filter(
                func.date(DailyQuota.quota_date) == quota_date.date()
            ).first()
            
            if quota:
                if interaction_type == 'deep':
                    quota.deep_used += 1
                elif interaction_type == 'standard':
                    quota.standard_used += 1
                elif interaction_type == 'light':
                    quota.light_used += 1
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"增加配额使用量失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_config(self, config_key: str, default_value: str = None):
        """获取配置值"""
        session = self.get_session()
        try:
            config = session.query(AutoInteractionConfig).filter(
                AutoInteractionConfig.config_key == config_key
            ).first()
            if config:
                return config.config_value
            return default_value
        except Exception as e:
            self.logger.error(f"获取配置失败: {str(e)}")
            return default_value
        finally:
            session.close()
    
    def set_config(self, config_key: str, config_value: str, description: str = None):
        """设置配置值"""
        session = self.get_session()
        try:
            config = session.query(AutoInteractionConfig).filter(
                AutoInteractionConfig.config_key == config_key
            ).first()
            
            if config:
                config.config_value = config_value
                if description:
                    config.description = description
                config.updated_at = datetime.utcnow()
            else:
                config = AutoInteractionConfig(
                    config_key=config_key,
                    config_value=config_value,
                    description=description,
                    updated_at=datetime.utcnow()
                )
                session.add(config)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"设置配置失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_status(self):
        """获取运行状态（返回字典，避免session依赖）"""
        session = self.get_session()
        try:
            status = session.query(AutoInteractionStatus).order_by(AutoInteractionStatus.id.desc()).first()
            if not status:
                # 创建默认状态
                status = AutoInteractionStatus(
                    is_running=False,
                    is_paused=False,
                    total_scanned=0,
                    total_scored=0,
                    total_executed=0
                )
                session.add(status)
                session.commit()
            
            # 在session关闭前访问所有属性，转换为字典
            result = {
                'id': status.id,
                'is_running': status.is_running,
                'is_paused': status.is_paused,
                'current_subreddit': status.current_subreddit,
                'last_scan_time': status.last_scan_time,
                'last_execution_time': status.last_execution_time,
                'total_scanned': status.total_scanned,
                'total_scored': status.total_scored,
                'total_executed': status.total_executed,
                'updated_at': status.updated_at
            }
            return result
        except Exception as e:
            session.rollback()
            self.logger.error(f"获取运行状态失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def update_status(self, is_running: bool = None, is_paused: bool = None,
                     current_subreddit: str = None, last_scan_time: datetime = None,
                     last_execution_time: datetime = None, total_scanned: int = None,
                     total_scored: int = None, total_executed: int = None):
        """更新运行状态"""
        session = self.get_session()
        try:
            status = session.query(AutoInteractionStatus).order_by(AutoInteractionStatus.id.desc()).first()
            if not status:
                status = AutoInteractionStatus()
                session.add(status)
            
            if is_running is not None:
                status.is_running = is_running
            if is_paused is not None:
                status.is_paused = is_paused
            if current_subreddit is not None:
                status.current_subreddit = current_subreddit
            if last_scan_time is not None:
                status.last_scan_time = last_scan_time
            if last_execution_time is not None:
                status.last_execution_time = last_execution_time
            if total_scanned is not None:
                status.total_scanned = total_scanned
            if total_scored is not None:
                status.total_scored = total_scored
            if total_executed is not None:
                status.total_executed = total_executed
            
            status.updated_at = datetime.utcnow()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"更新运行状态失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def add_to_post_queue(self, title: str, content: str, subreddit: str, 
                         flair: str = None, post_type: str = 'ai_generated',
                         uploaded_file_id: int = None, image_path: str = None,
                         scheduled_at: datetime = None, requires_review: bool = False) -> int:
        """
        添加发帖任务到队列
        
        Args:
            title: 帖子标题
            content: 帖子内容
            subreddit: 子版块名称
            flair: 标签（可选）
            post_type: 帖子类型 ('ai_generated', 'uploaded_text', 'uploaded_image')
            uploaded_file_id: 关联的上传文件ID
            image_path: 图片路径
            scheduled_at: 计划发布时间
            requires_review: 是否需要审核
            
        Returns:
            任务ID
        """
        session = self.get_session()
        try:
            post_task = AutoPostQueue(
                title=title,
                content=content,
                subreddit=subreddit,
                flair=flair,
                post_type=post_type,
                uploaded_file_id=uploaded_file_id,
                image_path=image_path,
                scheduled_at=scheduled_at,
                requires_review=requires_review,
                status='pending',
                review_status='pending' if requires_review else None
            )
            session.add(post_task)
            session.commit()
            task_id = post_task.id
            self.logger.info(f"发帖任务已加入队列: {task_id} (r/{subreddit})")
            return task_id
        except Exception as e:
            session.rollback()
            self.logger.error(f"添加发帖任务到队列失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_pending_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取待执行的发帖任务
        
        Args:
            limit: 返回数量限制
            
        Returns:
            待执行任务列表
        """
        session = self.get_session()
        try:
            from sqlalchemy import or_
            # 获取待执行的任务（pending状态，且审核通过或无需审核）
            query = session.query(AutoPostQueue).filter(
                AutoPostQueue.status == 'pending'
            ).filter(
                or_(
                    AutoPostQueue.review_status == 'approved',
                    AutoPostQueue.review_status.is_(None),
                    AutoPostQueue.requires_review == False
                )
            )
            
            # 如果有计划发布时间，只获取到期的任务
            from datetime import datetime
            now = datetime.utcnow()
            query = query.filter(
                or_(
                    AutoPostQueue.scheduled_at.is_(None),
                    AutoPostQueue.scheduled_at <= now
                )
            )
            
            tasks = query.order_by(AutoPostQueue.created_at.asc()).limit(limit).all()
            
            result = []
            for task in tasks:
                result.append({
                    'id': task.id,
                    'title': task.title,
                    'content': task.content,
                    'subreddit': task.subreddit,
                    'flair': task.flair,
                    'post_type': task.post_type,
                    'uploaded_file_id': task.uploaded_file_id,
                    'image_path': task.image_path,
                    'status': task.status,
                    'scheduled_at': task.scheduled_at,
                    'created_at': task.created_at
                })
            return result
        except Exception as e:
            self.logger.error(f"获取待执行发帖任务失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def update_post_task_status(self, task_id: int, status: str, 
                               reddit_post_id: str = None, reddit_post_url: str = None,
                               error_message: str = None):
        """
        更新发帖任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态 ('executing', 'completed', 'failed')
            reddit_post_id: Reddit帖子ID（成功时）
            reddit_post_url: Reddit帖子URL（成功时）
            error_message: 错误信息（失败时）
        """
        session = self.get_session()
        try:
            task = session.query(AutoPostQueue).filter_by(id=task_id).first()
            if task:
                task.status = status
                if status == 'completed':
                    task.executed_at = datetime.utcnow()
                    if reddit_post_id:
                        task.reddit_post_id = reddit_post_id
                    if reddit_post_url:
                        task.reddit_post_url = reddit_post_url
                elif status == 'failed':
                    task.executed_at = datetime.utcnow()
                    if error_message:
                        task.error_message = error_message
                session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"更新发帖任务状态失败: {str(e)}")
        finally:
            session.close()
    
    def get_post_history(self, limit: int = 50, status: str = None):
        """获取发帖历史记录（返回字典列表，避免session依赖）"""
        session = self.get_session()
        try:
            query = session.query(AutoPostQueue)
            if status:
                query = query.filter(AutoPostQueue.status == status)
            history = query.order_by(AutoPostQueue.executed_at.desc()).limit(limit).all()
            # 转换为字典列表
            result = []
            for h in history:
                result.append({
                    'id': h.id,
                    'title': h.title,
                    'subreddit': h.subreddit,
                    'post_type': h.post_type,
                    'status': h.status,
                    'flair': h.flair,
                    'reddit_post_id': h.reddit_post_id,
                    'reddit_post_url': h.reddit_post_url,
                    'created_at': h.created_at,
                    'executed_at': h.executed_at,
                    'error_message': h.error_message
                })
            return result
        except Exception as e:
            self.logger.error(f"获取发帖历史失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_interaction_history(self, limit: int = 50, status: str = None):
        """获取互动历史记录（返回字典列表，避免session依赖）"""
        session = self.get_session()
        try:
            query = session.query(AutoInteractionQueue)
            if status:
                query = query.filter(AutoInteractionQueue.status == status)
            history = query.order_by(AutoInteractionQueue.executed_at.desc()).limit(limit).all()
            # 转换为字典列表
            result = []
            for h in history:
                result.append({
                    'id': h.id,
                    'post_id': h.post_id,
                    'subreddit': h.subreddit,
                    'interaction_type': h.interaction_type,
                    'post_score': h.post_score,
                    'status': h.status,
                    'ai_comment': h.ai_comment,
                    'requires_review': h.requires_review,
                    'review_status': h.review_status,
                    'created_at': h.created_at,
                    'executed_at': h.executed_at,
                    'error_message': h.error_message
                })
            return result
        except Exception as e:
            self.logger.error(f"获取互动历史失败: {str(e)}")
            return []
        finally:
            session.close()

