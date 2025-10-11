"""
配置文件 - 存储所有API密钥和配置参数
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # Reddit API 配置 (OAuth2)
    REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
    REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
    REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'RedInsight Bot 1.0')
    REDDIT_REDIRECT_URI = os.getenv('REDDIT_REDIRECT_URI', 'http://localhost:8080')
    # 注意：用户名和密码认证已被弃用，现在使用OAuth2
    
    # 大模型API配置
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    
    # 数据库配置
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///redinsight.db')
    
    # 抓取配置
    DEFAULT_SUBREDDITS = ['MachineLearning', 'programming', 'datascience']
    MAX_POSTS_PER_SUBREDDIT = 100
    MAX_COMMENTS_PER_POST = 50
    
    # 分析配置
    ANALYSIS_MODEL = os.getenv('ANALYSIS_MODEL', 'gpt-3.5-turbo')
    BATCH_SIZE = 10
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'redinsight.log'

