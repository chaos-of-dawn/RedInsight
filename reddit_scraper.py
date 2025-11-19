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
            import urllib3
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # 禁用SSL警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            headers = {
                'Authorization': f'bearer {self.access_token}',
                'User-Agent': Config.REDDIT_USER_AGENT
            }
            
            # 创建会话并配置重试策略
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            response = session.get(
                'https://oauth.reddit.com/api/v1/me',
                headers=headers,
                timeout=30,
                verify=True  # 保持SSL验证
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"认证验证失败: {str(e)}")
            # 如果是SSL错误，尝试不验证SSL证书
            try:
                response = requests.get(
                    'https://oauth.reddit.com/api/v1/me',
                    headers=headers,
                    timeout=30,
                    verify=False  # 临时禁用SSL验证
                )
                return response.status_code == 200
            except:
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
            import urllib3
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # 禁用SSL警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            headers = {
                'Authorization': f'bearer {self.access_token}',
                'User-Agent': Config.REDDIT_USER_AGENT
            }
            
            # 创建会话并配置重试策略
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            response = session.get(
                'https://oauth.reddit.com/api/v1/me',
                headers=headers,
                timeout=30,
                verify=True
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return user_data.get('name', 'Unknown')
            return None
        except Exception as e:
            print(f"获取用户名失败: {str(e)}")
            # 如果是SSL错误，尝试不验证SSL证书
            try:
                response = requests.get(
                    'https://oauth.reddit.com/api/v1/me',
                    headers=headers,
                    timeout=30,
                    verify=False
                )
                if response.status_code == 200:
                    user_data = response.json()
                    return user_data.get('name', 'Unknown')
            except:
                pass
            return None
        
    def get_hot_posts(self, subreddit_name: str, limit: int = 100, time_filter: str = "week",
                     start_date = None, end_date = None, min_score: int = 0, max_score: int = 0) -> List[Dict[str, Any]]:
        """
        获取指定子版块的热门帖子
        
        Args:
            subreddit_name: 子版块名称
            limit: 获取帖子数量限制
            time_filter: 时间筛选 (hour, day, week, month, year, all)
            start_date: 开始日期 (datetime.date对象)
            end_date: 结束日期 (datetime.date对象)
            min_score: 最低分数筛选
            max_score: 最高分数筛选 (0表示无限制)
            
        Note:
            - 当需要分数筛选时，使用Reddit API的top()方法按分数排序
            - 当不需要分数筛选时，根据time_filter选择top()或hot()方法
            - 分数筛选在本地进行，但利用了Reddit API的原生排序
            
        Returns:
            帖子数据列表
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            
            # 根据分数筛选需求选择合适的方法
            if min_score > 0 or max_score > 0:
                # 需要分数筛选时，使用top方法按分数排序
                if time_filter and time_filter != "all":
                    posts_generator = subreddit.top(time_filter=time_filter, limit=limit*2)  # 获取更多数据用于筛选
                else:
                    posts_generator = subreddit.top(time_filter="week", limit=limit*2)  # 默认获取一周的高分帖子
            else:
                # 不需要分数筛选时，根据时间筛选选择方法
                if time_filter and time_filter != "all":
                    posts_generator = subreddit.top(time_filter=time_filter, limit=limit)
                else:
                    posts_generator = subreddit.hot(limit=limit)
            
            for post in posts_generator:
                post_created = datetime.fromtimestamp(post.created_utc)
                
                # 日期筛选
                if start_date:
                    if post_created.date() < start_date:
                        continue
                if end_date:
                    if post_created.date() > end_date:
                        continue
                
                # 分数筛选
                if min_score > 0 and post.score < min_score:
                    continue
                if max_score > 0 and post.score > max_score:
                    continue
                
                post_data = {
                    'id': post.id,
                    'title': post.title,
                    'author': str(post.author) if post.author else '[deleted]',
                    'score': post.score,
                    'upvote_ratio': post.upvote_ratio,
                    'num_comments': post.num_comments,
                    'created_utc': post_created,
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
    
    def submit_post(self, subreddit_name: str, title: str, content: str = None, 
                   url: str = None, flair_text: str = None, kind: str = 'self') -> Dict[str, Any]:
        """
        发布帖子到指定子版块
        
        Args:
            subreddit_name: 子版块名称
            title: 帖子标题
            content: 帖子内容（文本帖子）
            url: 链接URL（链接帖子）
            flair_text: 标签文本
            kind: 帖子类型 ('self' 或 'link')
            
        Returns:
            发布结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # 根据类型发布帖子
            if kind == 'self' and content:
                submission = subreddit.submit(
                    title=title,
                    selftext=content,
                    flair_text=flair_text
                )
            elif kind == 'link' and url:
                submission = subreddit.submit(
                    title=title,
                    url=url,
                    flair_text=flair_text
                )
            else:
                raise ValueError("无效的帖子类型或缺少必要参数")
            
            result = {
                'success': True,
                'post_id': submission.id,
                'title': submission.title,
                'url': f"https://www.reddit.com{submission.permalink}",
                'subreddit': subreddit_name,
                'created_utc': datetime.fromtimestamp(submission.created_utc)
            }
            
            self.logger.info(f"成功发布帖子到 r/{subreddit_name}: {submission.id}")
            return result
            
        except Exception as e:
            self.logger.error(f"发布帖子到 r/{subreddit_name} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def reply_to_comment(self, comment_id: str, text: str) -> Dict[str, Any]:
        """
        回复评论
        
        Args:
            comment_id: 评论ID
            text: 回复内容
            
        Returns:
            回复结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            comment = self.reddit.comment(id=comment_id)
            reply = comment.reply(text)
            
            result = {
                'success': True,
                'reply_id': reply.id,
                'parent_id': comment_id,
                'text': text,
                'created_utc': datetime.fromtimestamp(reply.created_utc)
            }
            
            self.logger.info(f"成功回复评论 {comment_id}: {reply.id}")
            return result
            
        except Exception as e:
            self.logger.error(f"回复评论 {comment_id} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def reply_to_post(self, post_id: str, text: str) -> Dict[str, Any]:
        """
        回复帖子（顶级评论）
        
        Args:
            post_id: 帖子ID
            text: 回复内容
            
        Returns:
            回复结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            submission = self.reddit.submission(id=post_id)
            comment = submission.reply(text)
            
            result = {
                'success': True,
                'comment_id': comment.id,
                'post_id': post_id,
                'text': text,
                'created_utc': datetime.fromtimestamp(comment.created_utc)
            }
            
            self.logger.info(f"成功回复帖子 {post_id}: {comment.id}")
            return result
            
        except Exception as e:
            self.logger.error(f"回复帖子 {post_id} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_subreddit_rules(self, subreddit_name: str) -> List[Dict[str, Any]]:
        """
        获取子版块规则
        
        Args:
            subreddit_name: 子版块名称
            
        Returns:
            规则列表
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            rules = []
            
            for rule in subreddit.rules:
                rules.append({
                    'short_name': rule.short_name,
                    'description': rule.description,
                    'kind': rule.kind,
                    'created_utc': rule.created_utc,
                    'priority': rule.priority
                })
            
            self.logger.info(f"成功获取 r/{subreddit_name} 的 {len(rules)} 条规则")
            return rules
            
        except Exception as e:
            self.logger.error(f"获取 r/{subreddit_name} 规则失败: {str(e)}")
            return []

    def get_subreddit_rules_text(self, subreddit_name: str) -> str:
        """获取子版块规则的合并文本（便于启发式解析）。"""
        try:
            rules = self.get_subreddit_rules(subreddit_name)
            if not rules:
                return ""
            parts = []
            for r in rules:
                title = r.get('short_name') or r.get('name') or ''
                desc = r.get('description') or ''
                parts.append(f"{title}: {desc}")
            return "\n".join(parts)
        except Exception as e:
            self.logger.error(f"组合 r/{subreddit_name} 规则文本失败: {str(e)}")
            return ""

    def get_subreddit_sidebar_text(self, subreddit_name: str) -> str:
        """获取子版块侧栏/简介文本。"""
        try:
            if not self.is_authenticated():
                # 读取公开信息不一定需要认证，但保持一致性
                pass
            subreddit = self.reddit.subreddit(subreddit_name)
            desc = subreddit.description or ''
            public_desc = subreddit.public_description or ''
            return f"{desc}\n{public_desc}"
        except Exception as e:
            self.logger.error(f"获取 r/{subreddit_name} 侧栏文本失败: {str(e)}")
            return ""

    def get_me(self):
        """获取当前认证用户对象。"""
        try:
            if not self.is_authenticated():
                raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
            # 优先通过PRAW获取
            try:
                if hasattr(self, 'reddit') and self.reddit is not None:
                    user_obj = self.reddit.user.me()
                    if user_obj is not None:
                        return user_obj
            except Exception:
                pass

            # 退回到HTTP接口获取，构造轻量用户对象以兼容属性访问
            import requests
            headers = {
                'Authorization': f'bearer {self.access_token}',
                'User-Agent': Config.REDDIT_USER_AGENT
            }
            resp = requests.get('https://oauth.reddit.com/api/v1/me', headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                # 构造具备属性访问的对象
                try:
                    return type('RedditUser', (), {
                        'name': data.get('name'),
                        'link_karma': data.get('link_karma', 0),
                        'comment_karma': data.get('comment_karma', 0),
                        'created_utc': data.get('created_utc', None)
                    })()
                except Exception:
                    return data
            return None
        except Exception as e:
            self.logger.error(f"获取当前用户失败: {str(e)}")
            return None
    
    def track_subreddit(self, subreddit_name: str, keywords: List[str] = None, 
                       limit: int = 50) -> List[Dict[str, Any]]:
        """
        跟踪子版块的新帖子（用于热帖监控）
        
        Args:
            subreddit_name: 子版块名称
            keywords: 关键词列表（可选）
            limit: 获取帖子数量
            
        Returns:
            新帖子列表
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            
            # 获取最新帖子
            for post in subreddit.new(limit=limit):
                post_data = {
                    'id': post.id,
                    'title': post.title,
                    'author': str(post.author) if post.author else '[deleted]',
                    'score': post.score,
                    'num_comments': post.num_comments,
                    'created_utc': datetime.fromtimestamp(post.created_utc),
                    'url': post.url,
                    'selftext': post.selftext,
                    'subreddit': subreddit_name,
                    'flair': post.link_flair_text
                }
                
                # 如果有关键词筛选
                if keywords:
                    title_text = f"{post.title} {post.selftext}".lower()
                    if any(keyword.lower() in title_text for keyword in keywords):
                        posts.append(post_data)
                else:
                    posts.append(post_data)
            
            self.logger.info(f"跟踪 r/{subreddit_name} 获取到 {len(posts)} 个新帖子")
            return posts
            
        except Exception as e:
            self.logger.error(f"跟踪 r/{subreddit_name} 失败: {str(e)}")
            return []
    
    def get_user_posts(self, username: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户的帖子
        
        Args:
            username: 用户名
            limit: 获取数量
            
        Returns:
            用户帖子列表
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            user = self.reddit.redditor(username)
            posts = []
            
            for submission in user.submissions.new(limit=limit):
                post_data = {
                    'id': submission.id,
                    'title': submission.title,
                    'author': username,
                    'score': submission.score,
                    'num_comments': submission.num_comments,
                    'created_utc': datetime.fromtimestamp(submission.created_utc),
                    'url': submission.url,
                    'selftext': submission.selftext,
                    'subreddit': str(submission.subreddit),
                    'flair': submission.link_flair_text
                }
                posts.append(post_data)
            
            self.logger.info(f"获取用户 {username} 的 {len(posts)} 个帖子")
            return posts
            
        except Exception as e:
            self.logger.error(f"获取用户 {username} 帖子失败: {str(e)}")
            return []
    
    def get_user_comments(self, username: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户的评论
        
        Args:
            username: 用户名
            limit: 获取数量
            
        Returns:
            用户评论列表
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            user = self.reddit.redditor(username)
            comments = []
            
            for comment in user.comments.new(limit=limit):
                comment_data = {
                    'id': comment.id,
                    'post_id': str(comment.submission.id),
                    'author': username,
                    'body': comment.body,
                    'score': comment.score,
                    'created_utc': datetime.fromtimestamp(comment.created_utc),
                    'subreddit': str(comment.subreddit),
                    'parent_id': comment.parent_id
                }
                comments.append(comment_data)
            
            self.logger.info(f"获取用户 {username} 的 {len(comments)} 个评论")
            return comments
            
        except Exception as e:
            self.logger.error(f"获取用户 {username} 评论失败: {str(e)}")
            return []

    # ==================== 互动功能方法 ====================
    
    def upvote_post(self, post_id: str) -> Dict[str, Any]:
        """
        点赞帖子
        
        Args:
            post_id: 帖子ID
            
        Returns:
            操作结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            submission = self.reddit.submission(id=post_id)
            submission.upvote()
            
            result = {
                'success': True,
                'post_id': post_id,
                'action': 'upvote',
                'new_score': submission.score,
                'upvote_ratio': submission.upvote_ratio
            }
            
            self.logger.info(f"成功点赞帖子 {post_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"点赞帖子 {post_id} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def downvote_post(self, post_id: str) -> Dict[str, Any]:
        """
        点踩帖子
        
        Args:
            post_id: 帖子ID
            
        Returns:
            操作结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            submission = self.reddit.submission(id=post_id)
            submission.downvote()
            
            result = {
                'success': True,
                'post_id': post_id,
                'action': 'downvote',
                'new_score': submission.score,
                'upvote_ratio': submission.upvote_ratio
            }
            
            self.logger.info(f"成功点踩帖子 {post_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"点踩帖子 {post_id} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def upvote_comment(self, comment_id: str) -> Dict[str, Any]:
        """
        点赞评论
        
        Args:
            comment_id: 评论ID
            
        Returns:
            操作结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            comment = self.reddit.comment(id=comment_id)
            comment.upvote()
            
            result = {
                'success': True,
                'comment_id': comment_id,
                'action': 'upvote',
                'new_score': comment.score
            }
            
            self.logger.info(f"成功点赞评论 {comment_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"点赞评论 {comment_id} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def downvote_comment(self, comment_id: str) -> Dict[str, Any]:
        """
        点踩评论
        
        Args:
            comment_id: 评论ID
            
        Returns:
            操作结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            comment = self.reddit.comment(id=comment_id)
            comment.downvote()
            
            result = {
                'success': True,
                'comment_id': comment_id,
                'action': 'downvote',
                'new_score': comment.score
            }
            
            self.logger.info(f"成功点踩评论 {comment_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"点踩评论 {comment_id} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_post(self, post_id: str) -> Dict[str, Any]:
        """
        保存帖子
        
        Args:
            post_id: 帖子ID
            
        Returns:
            操作结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            submission = self.reddit.submission(id=post_id)
            submission.save()
            
            result = {
                'success': True,
                'post_id': post_id,
                'action': 'save',
                'title': submission.title,
                'subreddit': str(submission.subreddit)
            }
            
            self.logger.info(f"成功保存帖子 {post_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"保存帖子 {post_id} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def unsave_post(self, post_id: str) -> Dict[str, Any]:
        """
        取消保存帖子
        
        Args:
            post_id: 帖子ID
            
        Returns:
            操作结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            submission = self.reddit.submission(id=post_id)
            submission.unsave()
            
            result = {
                'success': True,
                'post_id': post_id,
                'action': 'unsave',
                'title': submission.title,
                'subreddit': str(submission.subreddit)
            }
            
            self.logger.info(f"成功取消保存帖子 {post_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"取消保存帖子 {post_id} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def follow_user(self, username: str) -> Dict[str, Any]:
        """
        关注用户
        
        Args:
            username: 用户名
            
        Returns:
            操作结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            user = self.reddit.redditor(username)
            user.friend()  # Reddit API中关注用户的方法是friend()
            
            result = {
                'success': True,
                'username': username,
                'action': 'follow',
                'user_id': user.id if hasattr(user, 'id') else None
            }
            
            self.logger.info(f"成功关注用户 {username}")
            return result
            
        except Exception as e:
            self.logger.error(f"关注用户 {username} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def unfollow_user(self, username: str) -> Dict[str, Any]:
        """
        取消关注用户
        
        Args:
            username: 用户名
            
        Returns:
            操作结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            user = self.reddit.redditor(username)
            user.unfriend()  # Reddit API中取消关注用户的方法是unfriend()
            
            result = {
                'success': True,
                'username': username,
                'action': 'unfollow'
            }
            
            self.logger.info(f"成功取消关注用户 {username}")
            return result
            
        except Exception as e:
            self.logger.error(f"取消关注用户 {username} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def subscribe_subreddit(self, subreddit_name: str) -> Dict[str, Any]:
        """
        订阅子版块
        
        Args:
            subreddit_name: 子版块名称
            
        Returns:
            操作结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            subreddit.subscribe()
            
            result = {
                'success': True,
                'subreddit_name': subreddit_name,
                'action': 'subscribe',
                'subscriber_count': subreddit.subscribers
            }
            
            self.logger.info(f"成功订阅子版块 r/{subreddit_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"订阅子版块 r/{subreddit_name} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def unsubscribe_subreddit(self, subreddit_name: str) -> Dict[str, Any]:
        """
        取消订阅子版块
        
        Args:
            subreddit_name: 子版块名称
            
        Returns:
            操作结果字典
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            subreddit.unsubscribe()
            
            result = {
                'success': True,
                'subreddit_name': subreddit_name,
                'action': 'unsubscribe',
                'subscriber_count': subreddit.subscribers
            }
            
            self.logger.info(f"成功取消订阅子版块 r/{subreddit_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"取消订阅子版块 r/{subreddit_name} 失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_saved_posts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取保存的帖子
        
        Args:
            limit: 返回数量限制
            
        Returns:
            保存的帖子列表
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            saved_posts = []
            for submission in self.reddit.user.me().saved(limit=limit):
                saved_posts.append({
                    'id': submission.id,
                    'title': submission.title,
                    'subreddit': str(submission.subreddit),
                    'score': submission.score,
                    'num_comments': submission.num_comments,
                    'url': submission.url,
                    'permalink': submission.permalink,
                    'created_utc': datetime.fromtimestamp(submission.created_utc),
                    'saved_at': datetime.utcnow()  # 本地记录保存时间
                })
            
            self.logger.info(f"获取到 {len(saved_posts)} 个保存的帖子")
            return saved_posts
            
        except Exception as e:
            self.logger.error(f"获取保存的帖子失败: {str(e)}")
            return []
    
    def get_followed_users(self) -> List[Dict[str, Any]]:
        """
        获取关注的用户列表
        
        Returns:
            关注的用户列表
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            followed_users = []
            for friend in self.reddit.user.me().friends():
                followed_users.append({
                    'username': str(friend),
                    'user_id': friend.id if hasattr(friend, 'id') else None,
                    'followed_at': datetime.utcnow()  # 本地记录关注时间
                })
            
            self.logger.info(f"获取到 {len(followed_users)} 个关注的用户")
            return followed_users
            
        except Exception as e:
            self.logger.error(f"获取关注的用户失败: {str(e)}")
            return []
    
    def get_subscribed_subreddits(self) -> List[Dict[str, Any]]:
        """
        获取订阅的子版块列表
        
        Returns:
            订阅的子版块列表
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subscribed_subreddits = []
            for subreddit in self.reddit.user.me().subreddits():
                subscribed_subreddits.append({
                    'name': str(subreddit),
                    'title': subreddit.title,
                    'subscribers': subreddit.subscribers,
                    'description': subreddit.description,
                    'subscribed_at': datetime.utcnow()  # 本地记录订阅时间
                })
            
            self.logger.info(f"获取到 {len(subscribed_subreddits)} 个订阅的子版块")
            return subscribed_subreddits
            
        except Exception as e:
            self.logger.error(f"获取订阅的子版块失败: {str(e)}")
            return []


