"""
配置文件 - 存储所有API密钥和配置参数
"""
import os
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def load_api_keys():
    """从 api_keys.json 文件加载 API 密钥"""
    try:
        with open('api_keys.json', 'r', encoding='utf-8') as f:
            keys = json.load(f)
        return keys
    except FileNotFoundError:
        print("警告: api_keys.json 文件未找到，使用环境变量")
        return {}
    except Exception as e:
        print(f"警告: 加载 api_keys.json 失败: {e}，使用环境变量")
        return {}

# 加载 API 密钥
api_keys = load_api_keys()

class Config:
    # Reddit API 配置 (OAuth2)
    REDDIT_CLIENT_ID = api_keys.get('reddit_client_id') or os.getenv('REDDIT_CLIENT_ID')
    REDDIT_CLIENT_SECRET = api_keys.get('reddit_client_secret') or os.getenv('REDDIT_CLIENT_SECRET')
    REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'RedInsight Bot 1.0')
    REDDIT_REDIRECT_URI = api_keys.get('reddit_redirect_uri') or os.getenv('REDDIT_REDIRECT_URI', 'http://localhost:8080')
    # 注意：用户名和密码认证已被弃用，现在使用OAuth2
    
    # 大模型API配置
    OPENAI_API_KEY = api_keys.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = api_keys.get('anthropic_api_key') or os.getenv('ANTHROPIC_API_KEY')
    DEEPSEEK_API_KEY = api_keys.get('deepseek_api_key') or os.getenv('DEEPSEEK_API_KEY')
    
    # 数据库配置
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///redinsight.db')
    
    # 抓取配置
    DEFAULT_SUBREDDITS = ['MachineLearning', 'programming', 'datascience']
    MAX_POSTS_PER_SUBREDDIT = 100
    MAX_COMMENTS_PER_POST = 50
    
    # 分析配置
    ANALYSIS_MODEL = os.getenv('ANALYSIS_MODEL', 'gpt-3.5-turbo')
    BATCH_SIZE = 25  # 根据输出限制4K tokens优化，安全边际20-30个帖子/批
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'redinsight.log'

