"""
Reddit数据抓取模块
使用PRAW (Python Reddit API Wrapper) 抓取Reddit帖子和评论
支持OAuth2认证
"""
import praw
import logging
import webbrowser
import urllib.parse
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import Config

class RedditScraper:
    def __init__(self, access_token: Optional[str] = None, client_id: Optional[str] = None, 
                 client_secret: Optional[str] = None, redirect_uri: Optional[str] = None):
        """初始化Reddit API连接"""
        # 优先使用传入的参数，否则使用配置文件
        self.client_id = client_id or Config.REDDIT_CLIENT_ID
        self.client_secret = client_secret or Config.REDDIT_CLIENT_SECRET
        self.redirect_uri = redirect_uri or Config.REDDIT_REDIRECT_URI
        
        # 检查必要的配置项
        required_configs = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri
        }
        
        missing_configs = [key for key, value in required_configs.items() if not value]
        if missing_configs:
            raise ValueError(f"缺少Reddit API配置: {', '.join(missing_configs)}。请在UI界面配置API密钥。")
        
        # 使用OAuth2认证
        if access_token:
            # 如果提供了访问令牌，直接使用
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=Config.REDDIT_USER_AGENT,
                access_token=access_token
            )
        else:
            # 创建未认证的实例，稍后需要OAuth2流程
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=Config.REDDIT_USER_AGENT,
                redirect_uri=self.redirect_uri
            )
        
        self.logger = logging.getLogger(__name__)
        self.access_token = access_token
    
    def get_auth_url(self) -> str:
        """
        对于script类型应用，不需要授权URL，直接使用密码授权
        这个方法保留用于兼容性，但实际应该使用authenticate_with_password
        
        Returns:
            说明信息
        """
        return "script类型应用使用密码授权，无需授权URL"
    
    def authenticate_with_password(self, username: str, password: str) -> str:
        """
        使用用户名和密码获取访问令牌（适用于script类型应用）
        
        Args:
            username: Reddit用户名
            password: Reddit密码
            
        Returns:
            访问令牌字符串
        """
        try:
            import requests
            import base64
            
            # 准备OAuth2密码授权请求
            data = {
                'grant_type': 'password',
                'username': username,
                'password': password
            }
            
            # 准备认证头
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'User-Agent': Config.REDDIT_USER_AGENT,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # 调试信息
            print(f"发送密码授权请求到: https://www.reddit.com/api/v1/access_token")
            print(f"Client ID: {self.client_id}")
            print(f"Username: {username}")
            print(f"Data: {data}")
            
            # 发送令牌请求
            response = requests.post(
                'https://www.reddit.com/api/v1/access_token',
                data=data,
                headers=headers,
                timeout=30
            )
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data['access_token']
                self.access_token = access_token
                
                # 更新PRAW实例
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=Config.REDDIT_USER_AGENT,
                    access_token=access_token
                )
                
                return access_token
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.logger.error(f"获取访问令牌失败: {error_msg}")
                
                # 提供更详细的错误信息
                if response.status_code == 401:
                    if "invalid_client" in response.text:
                        raise Exception("Client ID或Client Secret错误，请检查Reddit应用配置")
                    else:
                        raise Exception("用户名或密码错误，请检查Reddit凭据")
                elif response.status_code == 400:
                    if "invalid_grant" in response.text:
                        raise Exception("用户名或密码无效，或该账户不是Reddit应用的开发者")
                    elif "unsupported_grant_type" in response.text:
                        raise Exception("不支持的授权类型，请确保使用script类型应用")
                    else:
                        raise Exception(f"请求参数错误: {response.text}")
                elif response.status_code == 403:
                    raise Exception("访问被拒绝，请确保该账户是Reddit应用的开发者")
                else:
                    raise Exception(f"认证失败: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"获取访问令牌失败: {str(e)}")
            raise

    def authenticate_with_code(self, auth_code: str) -> str:
        """
        使用授权码获取访问令牌
        
        Args:
            auth_code: 从授权URL回调中获取的授权码
            
        Returns:
            访问令牌字符串
        """
        try:
            import requests
            import base64
            
            # 清理授权码（移除可能的空白字符）
            auth_code = auth_code.strip()
            
            # 准备OAuth2令牌请求
            data = {
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': self.redirect_uri
            }
            
            # 准备认证头
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'User-Agent': Config.REDDIT_USER_AGENT,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # 调试信息
            self.logger.info(f"发送令牌请求到: https://www.reddit.com/api/v1/access_token")
            self.logger.info(f"Client ID: {self.client_id}")
            self.logger.info(f"Redirect URI: {self.redirect_uri}")
            self.logger.info(f"Auth Code: {auth_code[:10]}...")
            self.logger.info(f"Data: {data}")
            
            # 发送令牌请求
            response = requests.post(
                'https://www.reddit.com/api/v1/access_token',
                data=data,
                headers=headers,
                timeout=30
            )
            
            self.logger.info(f"响应状态码: {response.status_code}")
            self.logger.info(f"响应内容: {response.text}")
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data['access_token']
                self.access_token = access_token
                
                # 更新PRAW实例
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=Config.REDDIT_USER_AGENT,
                    access_token=access_token
                )
                
                return access_token
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.logger.error(f"获取访问令牌失败: {error_msg}")
                
                # 提供更详细的错误信息
                if response.status_code == 400:
                    if "invalid_grant" in response.text:
                        raise Exception("授权码无效或已过期。请重新获取授权码。")
                    elif "redirect_uri_mismatch" in response.text:
                        raise Exception(f"重定向URI不匹配。请确保Reddit应用中的重定向URI设置为: {self.redirect_uri}")
                    else:
                        raise Exception(f"请求参数错误: {response.text}")
                else:
                    raise Exception(error_msg)
                
        except Exception as e:
            self.logger.error(f"获取访问令牌失败: {str(e)}")
            raise
    
    def is_authenticated(self) -> bool:
        """
        检查是否已认证
        
        Returns:
            是否已认证
        """
        try:
            if not self.access_token:
                return False
            
            # 使用API直接验证访问令牌
            import requests
            headers = {
                'Authorization': f'bearer {self.access_token}',
                'User-Agent': Config.REDDIT_USER_AGENT
            }
            
            response = requests.get(
                'https://oauth.reddit.com/api/v1/me',
                headers=headers,
                timeout=10
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"认证验证失败: {str(e)}")
            return False
    
    def get_authenticated_user(self) -> Optional[str]:
        """
        获取已认证的用户名
        
        Returns:
            用户名或None
        """
        try:
            if not self.access_token:
                return None
                
            # 使用API直接获取用户信息
            import requests
            headers = {
                'Authorization': f'bearer {self.access_token}',
                'User-Agent': Config.REDDIT_USER_AGENT
            }
            
            response = requests.get(
                'https://oauth.reddit.com/api/v1/me',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return user_data.get('name', 'Unknown')
            return None
        except Exception as e:
            print(f"获取用户名失败: {str(e)}")
            return None
        
    def get_hot_posts(self, subreddit_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取指定子版块的热门帖子
        
        Args:
            subreddit_name: 子版块名称
            limit: 获取帖子数量限制
            
        Returns:
            帖子数据列表
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            
            for post in subreddit.hot(limit=limit):
                post_data = {
                    'id': post.id,
                    'title': post.title,
                    'author': str(post.author) if post.author else '[deleted]',
                    'score': post.score,
                    'upvote_ratio': post.upvote_ratio,
                    'num_comments': post.num_comments,
                    'created_utc': datetime.fromtimestamp(post.created_utc),
                    'url': post.url,
                    'selftext': post.selftext,
                    'subreddit': subreddit_name,
                    'flair': post.link_flair_text,
                    'is_self': post.is_self,
                    'over_18': post.over_18
                }
                posts.append(post_data)
                
            self.logger.info(f"成功获取 {len(posts)} 个帖子来自 r/{subreddit_name}")
            return posts
            
        except Exception as e:
            self.logger.error(f"获取 r/{subreddit_name} 帖子失败: {str(e)}")
            return []
    
    def get_post_comments(self, post_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取指定帖子的评论
        
        Args:
            post_id: 帖子ID
            limit: 评论数量限制
            
        Returns:
            评论数据列表
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)  # 展开所有评论
            
            comments = []
            for comment in submission.comments.list()[:limit]:
                if hasattr(comment, 'body') and comment.body != '[deleted]':
                    comment_data = {
                        'id': comment.id,
                        'post_id': post_id,
                        'author': str(comment.author) if comment.author else '[deleted]',
                        'body': comment.body,
                        'score': comment.score,
                        'created_utc': datetime.fromtimestamp(comment.created_utc),
                        'parent_id': comment.parent_id,
                        'is_submitter': comment.is_submitter,
                        'stickied': comment.stickied
                    }
                    comments.append(comment_data)
                    
            self.logger.info(f"成功获取 {len(comments)} 个评论来自帖子 {post_id}")
            return comments
            
        except Exception as e:
            self.logger.error(f"获取帖子 {post_id} 评论失败: {str(e)}")
            return []
    
    def search_posts(self, subreddit_name: str, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        在指定子版块搜索帖子
        
        Args:
            subreddit_name: 子版块名称
            query: 搜索关键词
            limit: 结果数量限制
            
        Returns:
            搜索结果列表
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            
            for post in subreddit.search(query, limit=limit, sort='relevance'):
                post_data = {
                    'id': post.id,
                    'title': post.title,
                    'author': str(post.author) if post.author else '[deleted]',
                    'score': post.score,
                    'upvote_ratio': post.upvote_ratio,
                    'num_comments': post.num_comments,
                    'created_utc': datetime.fromtimestamp(post.created_utc),
                    'url': post.url,
                    'selftext': post.selftext,
                    'subreddit': subreddit_name,
                    'flair': post.link_flair_text,
                    'search_query': query
                }
                posts.append(post_data)
                
            self.logger.info(f"搜索 '{query}' 在 r/{subreddit_name} 中找到 {len(posts)} 个结果")
            return posts
            
        except Exception as e:
            self.logger.error(f"搜索 r/{subreddit_name} 失败: {str(e)}")
            return []
    
    def get_subreddit_info(self, subreddit_name: str) -> Dict[str, Any]:
        """
        获取子版块信息
        
        Args:
            subreddit_name: 子版块名称
            
        Returns:
            子版块信息字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            return {
                'name': subreddit.display_name,
                'title': subreddit.title,
                'description': subreddit.description,
                'subscribers': subreddit.subscribers,
                'created_utc': datetime.fromtimestamp(subreddit.created_utc),
                'over18': subreddit.over18,
                'public_description': subreddit.public_description
            }
        except Exception as e:
            self.logger.error(f"获取 r/{subreddit_name} 信息失败: {str(e)}")
            return {}

