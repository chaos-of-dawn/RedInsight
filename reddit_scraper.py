"""
Reddit数据抓取模块
使用PRAW (Python Reddit API Wrapper) 抓取Reddit帖子和评论
支持OAuth2认证
"""
import praw
import logging
import webbrowser
import urllib.parse
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app_config import Config

# --- Rate limit helpers ---
try:
    from praw.exceptions import RedditAPIException  # type: ignore
except Exception:  # pragma: no cover
    RedditAPIException = None  # type: ignore

try:
    from prawcore.exceptions import TooManyRequests  # type: ignore
except Exception:  # pragma: no cover
    TooManyRequests = None  # type: ignore

_RATELIMIT_RE = re.compile(
    r"take a break for\s+(?P<num>\d+)\s+(?P<unit>second|seconds|minute|minutes)",
    re.IGNORECASE,
)
_RETRY_AFTER_RE = re.compile(
    r"(?P<num>\d+)\s*(?P<unit>second|seconds|minute|minutes)",
    re.IGNORECASE,
)

def _parse_retry_after_seconds(text: str) -> Optional[int]:
    """从错误文本里提取建议等待时间（秒）。"""
    if not text:
        return None
    m = _RATELIMIT_RE.search(text) or _RETRY_AFTER_RE.search(text)
    if not m:
        return None
    try:
        num = int(m.group("num"))
        unit = m.group("unit").lower()
        if unit.startswith("minute"):
            return num * 60
        return num
    except Exception:
        return None

def _extract_ratelimit_from_exception(e: Exception) -> Optional[int]:
    """优先从 RedditAPIException.items 中提取 RATELIMIT 的等待秒数。"""
    try:
        if RedditAPIException is not None and isinstance(e, RedditAPIException):
            for item in getattr(e, "items", []) or []:
                if getattr(item, "error_type", "") == "RATELIMIT":
                    return _parse_retry_after_seconds(getattr(item, "message", "") or str(e))
    except Exception:
        pass
    return _parse_retry_after_seconds(str(e))

def _is_ratelimit_exception(e: Exception) -> bool:
    s = str(e)
    if "RATELIMIT" in s or "too many requests" in s.lower():
        return True
    try:
        if RedditAPIException is not None and isinstance(e, RedditAPIException):
            for item in getattr(e, "items", []) or []:
                if getattr(item, "error_type", "") == "RATELIMIT":
                    return True
    except Exception:
        pass
    try:
        if TooManyRequests is not None and isinstance(e, TooManyRequests):
            return True
    except Exception:
        pass
    return False

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
        # 注意：如果只提供 access_token，PRAW 会创建只读实例（ReadOnlyAuthorizer）
        # 为了支持写操作（发帖、点赞等），应该使用 username/password 方式创建 PRAW 实例
        # 或者使用 OAuth2 code 流程获取完整的授权
        if access_token:
            # 如果提供了访问令牌，直接使用（但注意：这可能是只读的）
            # 建议：如果需要进行写操作，应该使用 username/password 或 OAuth2 code 流程
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=Config.REDDIT_USER_AGENT,
                access_token=access_token
            )
            # 检查是否是只读模式
            if hasattr(self.reddit, 'read_only') and self.reddit.read_only:
                self.logger.warning("使用 access_token 创建的 PRAW 实例是只读的，无法执行写操作（发帖、点赞等）")
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
        self.refresh_token = None  # refresh_token用于刷新access_token
        self._using_username_password = False  # 标记是否使用 username/password 方式
    
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
            # 添加必要的scope：vote（点赞）、read（读取）、identity（身份）、submit（发帖）、edit（编辑）
            data = {
                'grant_type': 'password',
                'username': username,
                'password': password,
                'scope': 'vote read identity submit edit save'  # 添加必要的权限范围
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
                refresh_token = token_data.get('refresh_token')  # 获取refresh_token（如果有）
                self.access_token = access_token
                self.refresh_token = refresh_token  # 保存refresh_token
                
                # 更新PRAW实例 - 使用username和password方式（推荐）
                # PRAW在使用username/password时会自动处理OAuth2认证，并正确设置用户认证状态
                # 这比直接使用access_token更可靠，因为PRAW会正确处理认证状态
                # 注意：PRAW会自动使用这些凭据获取access_token，不需要我们手动传递
                try:
                    self.reddit = praw.Reddit(
                        client_id=self.client_id,
                        client_secret=self.client_secret,
                        user_agent=Config.REDDIT_USER_AGENT,
                        username=username,
                        password=password
                    )
                    
                    # 标记使用 username/password 方式
                    self._using_username_password = True
                    
                    # 验证认证状态 - 尝试获取用户信息
                    try:
                        user = self.reddit.user.me()
                        if user:
                            self.logger.info(f"PRAW认证成功，用户: {user}")
                            # 检查是否是只读模式
                            if hasattr(self.reddit, 'read_only') and self.reddit.read_only:
                                self.logger.warning("PRAW实例处于只读模式，但已使用username/password认证，这不应该发生")
                            else:
                                self.logger.info("PRAW实例已正确设置为可写模式（使用username/password）")
                        else:
                            self.logger.warning("PRAW user.me()返回None，但继续使用")
                    except Exception as e:
                        # 如果user.me()失败，可能是read_only模式或其他问题
                        # 但PRAW实例仍然可能可以执行操作，所以继续使用
                        self.logger.warning(f"PRAW user.me()验证失败: {str(e)}，但继续使用username/password方式")
                        
                except Exception as e:
                    self.logger.error(f"使用username/password创建PRAW实例失败: {str(e)}")
                    # 如果username/password方式失败，回退到access_token方式
                    self.logger.warning("回退到access_token方式创建PRAW实例")
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
            # 添加必要的scope：vote（点赞）、read（读取）、identity（身份）、submit（发帖）、edit（编辑）
            data = {
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': self.redirect_uri,
                'scope': 'vote read identity submit edit save'  # 添加必要的权限范围
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
                refresh_token = token_data.get('refresh_token')  # 获取refresh_token（如果有）
                self.access_token = access_token
                self.refresh_token = refresh_token  # 保存refresh_token
                
                # 更新PRAW实例 - 使用access_token方式
                # 注意：对于authorization_code流程，通常需要保存refresh_token以便后续刷新
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
    
    def get_subreddit_posts(self, subreddit_name: str, limit: int = 100, sort: str = 'hot') -> List[Dict[str, Any]]:
        """
        获取指定子版块的帖子（支持多种排序方式）
        
        Args:
            subreddit_name: 子版块名称
            limit: 获取帖子数量限制
            sort: 排序方式 ('hot', 'new', 'top', 'rising')
            
        Returns:
            帖子数据列表
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            
            # 根据sort参数选择不同的排序方式
            if sort == 'hot':
                posts_generator = subreddit.hot(limit=limit)
            elif sort == 'new':
                posts_generator = subreddit.new(limit=limit)
            elif sort == 'top':
                posts_generator = subreddit.top(time_filter='week', limit=limit)
            elif sort == 'rising':
                posts_generator = subreddit.rising(limit=limit)
            else:
                # 默认使用hot
                posts_generator = subreddit.hot(limit=limit)
            
            for post in posts_generator:
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
            
            self.logger.info(f"成功获取 {len(posts)} 个帖子来自 r/{subreddit_name} (排序: {sort})")
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
    
    def search_all_posts(self, query: str, limit: int = 300, sort: str = 'relevance', 
                        months_back: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        在全站搜索帖子（所有公开子版块）
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制（建议200-500）
            sort: 排序方式 ('relevance', 'hot', 'top', 'new')
            months_back: 时间限制，只返回最近N个月的帖子（例如：3表示最近3个月）
            
        Returns:
            搜索结果列表（按子版块分组）
        """
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            # 使用 'all' 子版块进行全站搜索
            all_subreddit = self.reddit.subreddit('all')
            posts = []
            
            # 限制搜索数量，避免过多结果
            search_limit = min(limit, 500)  # 最多500条
            
            # 计算时间阈值（如果指定了月份限制）
            time_threshold = None
            if months_back is not None and months_back > 0:
                time_threshold = datetime.utcnow() - timedelta(days=months_back * 30)
                self.logger.info(f"开始全站搜索 '{query}'，限制 {search_limit} 条结果，时间范围：最近 {months_back} 个月")
            else:
                self.logger.info(f"开始全站搜索 '{query}'，限制 {search_limit} 条结果")
            
            for post in all_subreddit.search(query, limit=search_limit, sort=sort):
                post_created = datetime.fromtimestamp(post.created_utc)
                
                # 如果设置了时间限制，过滤掉超过时间范围的帖子
                if time_threshold is not None and post_created < time_threshold:
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
                    'subreddit': str(post.subreddit),
                    'flair': post.link_flair_text,
                    'search_query': query
                }
                posts.append(post_data)
                
            self.logger.info(f"全站搜索 '{query}' 找到 {len(posts)} 个结果（已应用时间过滤），来自 {len(set(p['subreddit'] for p in posts))} 个子版块")
            return posts
            
        except Exception as e:
            self.logger.error(f"全站搜索 '{query}' 失败: {str(e)}")
            return []
    
    def get_subreddit_info(self, subreddit_name: str) -> Dict[str, Any]:
        """
        获取子版块信息
        
        Args:
            subreddit_name: 子版块名称
            
        Returns:
            子版块信息字典
        """
        # 清理子版块名称：去除空格、去除r/前缀、去除特殊字符
        import re
        cleaned_subreddit = subreddit_name.strip().lstrip('r/').strip()
        cleaned_subreddit = re.sub(r'[^a-zA-Z0-9_]', '', cleaned_subreddit)
        
        if not cleaned_subreddit:
            self.logger.warning(f"无效的子版块名称: {subreddit_name}")
            return {}
        
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subreddit = self.reddit.subreddit(cleaned_subreddit)
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
            error_str = str(e)
            # 处理403错误（权限不足或子版块受限）
            if '403' in error_str or 'Forbidden' in error_str:
                self.logger.warning(f"获取 r/{cleaned_subreddit} 信息失败: 403 Forbidden - 可能是子版块私有/受限或API权限不足")
            else:
                self.logger.error(f"获取 r/{cleaned_subreddit} 信息失败: {error_str}")
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
        
        # 清理子版块名称：去除空格、去除r/前缀、去除特殊字符
        # Reddit子版块名称只能包含字母、数字、下划线，不能有空格
        cleaned_subreddit = subreddit_name.strip().lstrip('r/').strip()
        # 去除所有空格和特殊字符，只保留字母、数字、下划线
        import re
        cleaned_subreddit = re.sub(r'[^a-zA-Z0-9_]', '', cleaned_subreddit)
        
        if not cleaned_subreddit:
            return {
                'success': False,
                'error': f'无效的子版块名称: {subreddit_name}',
                'error_type': 'invalid_subreddit',
                'suggestion': '子版块名称只能包含字母、数字和下划线，不能有空格或特殊字符。'
            }
        
        # 如果清理后的名称与原始名称不同，记录警告
        if cleaned_subreddit != subreddit_name.strip().lstrip('r/').strip():
            self.logger.warning(f"子版块名称已清理: '{subreddit_name}' -> '{cleaned_subreddit}'")
        
        # 注意：不再检查 user.me()，因为：
        # 1. 使用 access_token 方式认证时，user.me() 可能返回 None，但不影响发布功能
        # 2. is_authenticated() 已经验证了 access_token 的有效性
        # 3. 如果认证有问题，Reddit API 会返回具体错误信息（如 USER_REQUIRED）
        # 4. 这样可以复用左侧边栏已有的认证状态，避免不必要的重新认证
        
        # 检查 PRAW 实例的 read_only 状态
        # 如果使用 access_token 创建的实例，可能是只读的，无法修改
        # 如果使用 username/password 创建的实例，应该是可写的
        if hasattr(self.reddit, 'read_only') and self.reddit.read_only:
            if not getattr(self, '_using_username_password', False):
                self.logger.error("PRAW实例处于只读模式，且不是使用username/password创建的，无法执行写操作")
                return {
                    'success': False,
                    'error': 'PRAW实例处于只读模式，无法发布帖子',
                    'error_type': 'read_only_mode',
                    'suggestion': '请使用username/password方式重新认证，或者使用OAuth2 code流程获取完整的写权限。当前实例是使用access_token创建的，只能进行只读操作。'
                }
            else:
                self.logger.warning("PRAW实例处于只读模式，但已使用username/password认证，这不应该发生")
        
        # 验证 PRAW 实例是否有写权限（通过检查授权状态）
        try:
            if hasattr(self.reddit, 'auth') and hasattr(self.reddit.auth, 'scopes'):
                scopes = list(self.reddit.auth.scopes())
                self.logger.info(f"PRAW实例当前权限: {scopes}")
                if 'submit' not in scopes and '*' not in scopes:
                    self.logger.warning(f"PRAW实例缺少submit权限，当前权限: {scopes}")
                    return {
                        'success': False,
                        'error': 'PRAW实例缺少submit权限',
                        'error_type': 'missing_scope',
                        'suggestion': '请重新进行OAuth2认证，确保选择了submit权限。如果使用username/password方式，请检查Reddit应用类型是否为"script"类型。'
                    }
            else:
                # 如果无法获取权限信息，尝试检查用户信息
                try:
                    user = self.reddit.user.me()
                    if not user:
                        self.logger.warning("PRAW实例无法获取用户信息，可能认证状态不正确")
                except Exception as e:
                    self.logger.warning(f"PRAW实例无法获取用户信息: {str(e)}")
        except Exception as e:
            # 如果无法检查权限，记录警告但继续尝试发布
            self.logger.warning(f"无法检查PRAW实例权限: {str(e)}")
        
        try:
            subreddit = self.reddit.subreddit(cleaned_subreddit)
            
            # 如果子版块要求 flair 但没有提供，尝试获取可用的 flair
            # 注意：在发布前获取 flair 模板可能失败（需要特定权限），所以先尝试发布
            # 如果发布失败并提示需要 flair，再尝试获取并重新发布
            final_flair_text = flair_text
            
            # 根据类型发布帖子
            # 注意：如果提供了 flair_text，需要同时提供 flair_id
            # 如果只提供 flair_text 而没有 flair_id，Reddit API 会返回错误
            submit_kwargs = {}
            if final_flair_text:
                # 如果只提供了 flair_text，需要先获取对应的 flair_id
                # 但为了简化，这里先尝试不使用 flair，如果失败再处理
                # 实际上，如果子版块要求 flair，会在后续的错误处理中自动获取并设置
                pass
            
            if kind == 'self' and content:
                submission = subreddit.submit(
                    title=title,
                    selftext=content,
                    **submit_kwargs
                )
            elif kind == 'link' and url:
                submission = subreddit.submit(
                    title=title,
                    url=url,
                    **submit_kwargs
                )
            else:
                raise ValueError("无效的帖子类型或缺少必要参数")
            
            # 如果发布成功但子版块要求 flair，可能需要通过 flair API 设置
            # 某些子版块要求在发布后设置 flair
            if submission and not final_flair_text:
                try:
                    # 检查是否需要设置 flair（通过检查 submission 的 flair 属性）
                    if hasattr(submission, 'link_flair_text') and not submission.link_flair_text:
                        # 尝试获取可用的 flair 并设置
                        try:
                            flair_choices = submission.flair.choices()
                            if flair_choices:
                                # 选择第一个可用的 flair
                                first_choice = flair_choices[0]
                                template_id = first_choice.get('flair_template_id')
                                if template_id:
                                    submission.flair.select(template_id)
                                    self.logger.info(f"已为帖子设置 flair: {first_choice.get('text', '')}")
                        except Exception as flair_e:
                            self.logger.warning(f"无法设置 flair: {str(flair_e)}")
                except Exception as e:
                    self.logger.warning(f"检查/设置 flair 时出错: {str(e)}")
            
            result = {
                'success': True,
                'post_id': submission.id,
                'title': submission.title,
                'url': f"https://www.reddit.com{submission.permalink}",
                'subreddit': cleaned_subreddit,
                'created_utc': datetime.fromtimestamp(submission.created_utc)
            }
            
            self.logger.info(f"成功发布帖子到 r/{cleaned_subreddit}: {submission.id}")
            return result
            
        except Exception as e:
            error_str = str(e)
            self.logger.error(f"发布帖子到 r/{cleaned_subreddit} 失败: {error_str}")
            
            # 处理 FLAIR_REQUIRED 错误（需要 flair）
            if 'FLAIR_REQUIRED' in error_str or 'flair' in error_str.lower() and 'required' in error_str.lower():
                # 尝试获取可用的 flair 并重新发布
                try:
                    subreddit = self.reddit.subreddit(cleaned_subreddit)
                    
                    # 方法1：尝试通过 flair.link_templates.user_selectable() 获取（推荐方法）
                    try:
                        # 优先使用 user_selectable() 方法，这通常返回字典格式的模板列表
                        flair_templates = list(subreddit.flair.link_templates.user_selectable())
                        if not flair_templates:
                            # 如果 user_selectable() 返回空，尝试直接获取所有模板
                            flair_templates = list(subreddit.flair.link_templates)
                        
                        if flair_templates:
                            # 选择第一个可用的 flair
                            selected_template = flair_templates[0]
                            
                            # PRAW 的 flair 模板可能是对象或字典，需要兼容处理
                            # 关键：需要使用 flair_id（模板ID），而不是 flair_text
                            flair_template_id = None
                            flair_text_value = None
                            
                            # 如果是字典类型
                            if isinstance(selected_template, dict):
                                # 获取模板ID（这是必需的）
                                # 注意：user_selectable() 返回的字典可能使用 'flair_template_id' 而不是 'id'
                                flair_template_id = selected_template.get('flair_template_id') or selected_template.get('id')
                                # 获取文本（用于日志显示）
                                flair_text_value = selected_template.get('flair_text') or selected_template.get('text', '')
                            # 如果是对象类型
                            else:
                                if hasattr(selected_template, 'flair_template_id'):
                                    flair_template_id = selected_template.flair_template_id
                                elif hasattr(selected_template, 'id'):
                                    flair_template_id = selected_template.id
                                
                                if hasattr(selected_template, 'flair_text'):
                                    flair_text_value = selected_template.flair_text
                                elif hasattr(selected_template, 'text'):
                                    flair_text_value = selected_template.text
                            
                            if flair_template_id:
                                self.logger.info(f"检测到需要 flair，自动选择模板ID: {flair_template_id} (文本: {flair_text_value})")
                                
                                # 重新尝试发布，使用 flair_id（模板ID）
                                if kind == 'self' and content:
                                    submission = subreddit.submit(
                                        title=title,
                                        selftext=content,
                                        flair_id=flair_template_id
                                    )
                                elif kind == 'link' and url:
                                    submission = subreddit.submit(
                                        title=title,
                                        url=url,
                                        flair_id=flair_template_id
                                    )
                                else:
                                    raise ValueError("无效的帖子类型或缺少必要参数")
                                
                                # 发布成功
                                result = {
                                    'success': True,
                                    'post_id': submission.id,
                                    'title': submission.title,
                                    'url': f"https://www.reddit.com{submission.permalink}",
                                    'subreddit': cleaned_subreddit,
                                    'created_utc': datetime.fromtimestamp(submission.created_utc),
                                    'flair_auto_selected': True,
                                    'flair_id': flair_template_id,
                                    'flair_text': flair_text_value
                                }
                                self.logger.info(f"成功发布帖子到 r/{cleaned_subreddit} (自动选择 flair: {flair_text_value or flair_template_id}): {submission.id}")
                                return result
                            else:
                                self.logger.warning(f"获取到 flair 模板但无法提取ID: {selected_template}")
                    except Exception as template_e:
                        self.logger.warning(f"无法通过 link_templates 获取 flair: {str(template_e)}")
                        # 尝试备用方法：直接访问 flair.link_templates（不使用 user_selectable）
                        try:
                            all_templates = list(subreddit.flair.link_templates)
                            if all_templates:
                                selected_template = all_templates[0]
                                # 使用相同的提取逻辑
                                if isinstance(selected_template, dict):
                                    flair_template_id = selected_template.get('id') or selected_template.get('flair_template_id')
                                    flair_text_value = selected_template.get('text', '')
                                else:
                                    flair_template_id = getattr(selected_template, 'id', None) or getattr(selected_template, 'flair_template_id', None)
                                    flair_text_value = getattr(selected_template, 'text', '')
                                
                                if flair_template_id:
                                    self.logger.info(f"通过备用方法获取到 flair 模板ID: {flair_template_id}")
                                    # 重新发布（使用相同的逻辑）
                                    if kind == 'self' and content:
                                        submission = subreddit.submit(title=title, selftext=content, flair_id=flair_template_id)
                                    elif kind == 'link' and url:
                                        submission = subreddit.submit(title=title, url=url, flair_id=flair_template_id)
                                    else:
                                        raise ValueError("无效的帖子类型或缺少必要参数")
                                    
                                    result = {
                                        'success': True,
                                        'post_id': submission.id,
                                        'title': submission.title,
                                        'url': f"https://www.reddit.com{submission.permalink}",
                                        'subreddit': cleaned_subreddit,
                                        'created_utc': datetime.fromtimestamp(submission.created_utc),
                                        'flair_auto_selected': True,
                                        'flair_id': flair_template_id,
                                        'flair_text': flair_text_value
                                    }
                                    self.logger.info(f"成功发布帖子到 r/{cleaned_subreddit} (备用方法，自动选择 flair): {submission.id}")
                                    return result
                        except Exception as backup_e:
                            self.logger.warning(f"备用方法也失败: {str(backup_e)}")
                    
                    # 方法2：如果方法1失败，尝试先发布一个临时帖子，然后获取 flair choices
                    # 注意：这种方法可能会创建一个需要删除的临时帖子，所以暂时不使用
                    
                    # 如果所有方法都失败，返回错误
                    return {
                        "success": False,
                        "error": error_str,
                        "error_type": "flair_required",
                        "suggestion": f"子版块 r/{cleaned_subreddit} 要求帖子必须包含 flair，但无法自动获取可用的 flair 列表。请手动在 Reddit 上查看该子版块的可用 flair，然后在发布时指定 flair_text 参数。"
                    }
                except Exception as retry_e:
                    # 重试失败，返回原始错误
                    return {
                        'success': False,
                        'error': error_str,
                        'error_type': 'flair_required',
                        'suggestion': f'子版块 r/{cleaned_subreddit} 要求帖子必须包含 flair。错误: {str(retry_e)}。请手动在 Reddit 上查看该子版块的可用 flair，然后在发布时指定 flair_text 参数。'
                    }
            
            # 处理 USER_REQUIRED 错误（认证问题）
            if 'USER_REQUIRED' in error_str or 'Please log in' in error_str:
                # 检查认证方式，提供更具体的建议
                auth_method = "未知"
                has_username = False
                try:
                    if hasattr(self.reddit, 'config') and hasattr(self.reddit.config, 'username'):
                        auth_method = "username/password"
                        has_username = True
                    elif self.access_token:
                        auth_method = "access_token"
                except:
                    pass
                
                # 检查 Reddit 应用类型（如果是 username/password 方式）
                app_type_hint = ""
                if has_username:
                    app_type_hint = (
                        '\n⚠️ 重要提示：使用username/password方式时，Reddit应用类型必须是"script"类型。\n'
                        '如果您的应用是"web app"类型，请：\n'
                        '1. 在 https://www.reddit.com/prefs/apps 创建一个新的"script"类型应用\n'
                        '2. 使用新的应用ID和密钥重新认证\n'
                        '或者使用OAuth2 code流程进行认证（适用于web app类型）'
                    )
                
                suggestion = (
                    'Reddit API认证已过期或权限不足。\n'
                    f'当前认证方式: {auth_method}\n'
                    f'子版块: r/{cleaned_subreddit}\n'
                    '建议操作：\n'
                    '1. 在左侧边栏重新进行OAuth2认证\n'
                    '2. 确保认证时选择了所有必要权限（包括submit权限）\n'
                    '3. 如果使用username/password方式，请确保凭据正确\n'
                    '4. 检查Reddit应用类型是否正确（script类型支持username/password）\n'
                    '5. 如果问题持续，请尝试清除浏览器缓存后重新认证'
                    + app_type_hint
                )
                
                return {
                    'success': False,
                    'error': error_str,
                    'error_type': 'authentication_required',
                    'suggestion': suggestion
                }
            
            return {
                'success': False,
                'error': error_str,
                'error_type': 'reddit_api_error',
                'suggestion': '请检查子版块名称、帖子内容是否符合规则，或稍后重试。'
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
            error_str = str(e)
            self.logger.error(f"回复评论 {comment_id} 失败: {error_str}")
            if _is_ratelimit_exception(e):
                retry_after = _extract_ratelimit_from_exception(e)
                return {
                    'success': False,
                    'error': error_str,
                    'error_type': 'ratelimit',
                    'retry_after': retry_after
                }
            return {'success': False, 'error': error_str}
    
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
            error_str = str(e)
            self.logger.error(f"回复帖子 {post_id} 失败: {error_str}")
            if _is_ratelimit_exception(e):
                retry_after = _extract_ratelimit_from_exception(e)
                return {
                    'success': False,
                    'error': error_str,
                    'error_type': 'ratelimit',
                    'retry_after': retry_after
                }
            return {'success': False, 'error': error_str}
    
    def get_subreddit_rules(self, subreddit_name: str) -> List[Dict[str, Any]]:
        """
        获取子版块规则
        
        Args:
            subreddit_name: 子版块名称
            
        Returns:
            规则列表
        """
        # 清理子版块名称：去除空格、去除r/前缀、去除特殊字符
        import re
        cleaned_subreddit = subreddit_name.strip().lstrip('r/').strip()
        cleaned_subreddit = re.sub(r'[^a-zA-Z0-9_]', '', cleaned_subreddit)
        
        if not cleaned_subreddit:
            self.logger.warning(f"无效的子版块名称: {subreddit_name}")
            return []
        
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        try:
            subreddit = self.reddit.subreddit(cleaned_subreddit)
            rules = []
            
            for rule in subreddit.rules:
                rules.append({
                    'short_name': rule.short_name,
                    'description': rule.description,
                    'kind': rule.kind,
                    'created_utc': rule.created_utc,
                    'priority': rule.priority
                })
            
            self.logger.info(f"成功获取 r/{cleaned_subreddit} 的 {len(rules)} 条规则")
            return rules
            
        except Exception as e:
            self.logger.error(f"获取 r/{cleaned_subreddit} 规则失败: {str(e)}")
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
        # 检查认证状态
        if not self.is_authenticated():
            raise ValueError("Reddit API未认证。请先完成OAuth2认证流程。")
        
        # 验证PRAW实例是否有有效的用户认证
        # 注意：即使user.me()失败，PRAW实例仍然可能可以执行操作
        # 所以这里只记录警告，不阻止继续执行
        try:
            # 尝试获取当前用户信息，验证认证状态
            user = self.reddit.user.me()
            if user:
                self.logger.debug(f"PRAW用户认证验证成功，用户: {user}")
            else:
                self.logger.warning("PRAW user.me()返回None，但继续尝试点赞")
        except Exception as e:
            self.logger.warning(f"PRAW用户认证验证失败: {str(e)}，但继续尝试点赞")
            # 如果无法获取用户信息，可能是认证方式问题，但不一定意味着无法点赞
            # 对于script类型应用，PRAW可能无法正确获取user.me()，但仍然可以执行操作
        
        try:
            submission = self.reddit.submission(id=post_id)
            
            # 检查submission对象是否有效
            if not submission:
                raise ValueError(f"无法获取帖子 {post_id}")
            
            # 执行点赞操作
            submission.upvote()
            
            # 验证点赞是否成功（通过检查likes属性）
            # likes = 1 表示已点赞，likes = -1 表示已点踩，likes = None 表示未操作
            likes = submission.likes
            
            result = {
                'success': True,
                'post_id': post_id,
                'action': 'upvote',
                'new_score': submission.score,
                'upvote_ratio': submission.upvote_ratio,
                'likes': likes
            }
            
            self.logger.info(f"成功点赞帖子 {post_id} (likes={likes})")
            return result
            
        except Exception as e:
            error_str = str(e)
            self.logger.error(f"点赞帖子 {post_id} 失败: {error_str}")
            
            # 如果是认证错误，提供更详细的错误信息
            if 'USER_REQUIRED' in error_str or 'Please log in' in error_str:
                self.logger.error("认证错误：PRAW实例可能未正确设置用户认证状态。建议使用username/password方式创建PRAW实例。")
            
            if _is_ratelimit_exception(e):
                retry_after = _extract_ratelimit_from_exception(e)
                return {
                    'success': False,
                    'error': error_str,
                    'error_type': 'ratelimit',
                    'retry_after': retry_after
                }
            return {'success': False, 'error': error_str}
    
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
            error_str = str(e)
            self.logger.error(f"点踩帖子 {post_id} 失败: {error_str}")
            if _is_ratelimit_exception(e):
                retry_after = _extract_ratelimit_from_exception(e)
                return {
                    'success': False,
                    'error': error_str,
                    'error_type': 'ratelimit',
                    'retry_after': retry_after
                }
            return {'success': False, 'error': error_str}
    
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
            error_str = str(e)
            self.logger.error(f"点赞评论 {comment_id} 失败: {error_str}")
            if _is_ratelimit_exception(e):
                retry_after = _extract_ratelimit_from_exception(e)
                return {
                    'success': False,
                    'error': error_str,
                    'error_type': 'ratelimit',
                    'retry_after': retry_after
                }
            return {'success': False, 'error': error_str}
    
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
            error_str = str(e)
            self.logger.error(f"点踩评论 {comment_id} 失败: {error_str}")
            if _is_ratelimit_exception(e):
                retry_after = _extract_ratelimit_from_exception(e)
                return {
                    'success': False,
                    'error': error_str,
                    'error_type': 'ratelimit',
                    'retry_after': retry_after
                }
            return {'success': False, 'error': error_str}
    
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


