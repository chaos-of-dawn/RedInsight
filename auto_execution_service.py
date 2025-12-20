"""
自动化执行后台服务
独立于Streamlit运行，基于时间设定自动执行任务
处理Reddit API速率限制
"""
import threading
import time
import logging
import json
import random
from datetime import datetime, time as dt_time
from typing import Dict, Any, Optional, List
from database import DatabaseManager
from reddit_scraper import RedditScraper
from rpta_scorer import RPTAScorer
from task_executor import TaskExecutor
from auto_config import AutoConfig
from auto_scheduler import AutoScheduler
# from post_task_executor import PostTaskExecutor  # 已删除智能发帖功能

logger = logging.getLogger(__name__)

class AutoExecutionService:
    """自动化执行后台服务"""
    
    def __init__(self, db_manager: DatabaseManager,
                 scraper: RedditScraper,
                 scorer: RPTAScorer,
                 executor: TaskExecutor,
                 config: AutoConfig,
                 scheduler: AutoScheduler,
                 post_executor=None):  # 已删除智能发帖功能，参数保留以兼容旧代码
        """
        初始化后台服务
        
        Args:
            db_manager: DatabaseManager实例
            scraper: RedditScraper实例（来自左边栏认证）
            scorer: RPTAScorer实例
            executor: TaskExecutor实例
            config: AutoConfig实例
            scheduler: AutoScheduler实例
            post_executor: 已删除智能发帖功能，此参数不再使用
        
        注意：如果传入的scraper是使用access_token创建的，且配置文件中有username/password，
        会自动使用username/password重新创建PRAW实例，以确保可以执行点赞等操作。
        """
        self.db = db_manager
        
        # 检查scraper是否使用username/password创建（通过检查PRAW实例的创建方式）
        # 如果scraper是使用access_token创建的，且配置文件中有username/password，重新创建
        import os
        import json
        
        config_file = 'api_keys.json'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    api_keys = json.load(f)
                
                username = api_keys.get('reddit_username')
                password = api_keys.get('reddit_password')
                client_id = api_keys.get('reddit_client_id')
                client_secret = api_keys.get('reddit_client_secret')
                redirect_uri = api_keys.get('reddit_redirect_uri', 'http://localhost:8080')
                
                # 如果有username/password，且scraper可能不是使用username/password创建的，重新创建
                if username and password and client_id and client_secret:
                    # 检查scraper的PRAW实例是否使用username/password创建
                    # 如果scraper.reddit是使用access_token创建的，需要重新创建
                    try:
                        # 尝试获取用户信息，如果失败，可能是使用access_token创建的
                        user = scraper.reddit.user.me() if hasattr(scraper, 'reddit') else None
                        if not user:
                            logger.info("检测到scraper可能不是使用username/password创建的，重新创建PRAW实例...")
                            # 使用username/password重新创建PRAW实例
                            import praw
                            praw_instance = praw.Reddit(
                                client_id=client_id,
                                client_secret=client_secret,
                                user_agent='RedInsight Bot 1.0',
                                username=username,
                                password=password
                            )
                            
                            # 更新scraper的PRAW实例
                            scraper.reddit = praw_instance
                            # 更新access_token（用于is_authenticated()验证）
                            if hasattr(praw_instance, 'auth') and hasattr(praw_instance.auth, 'access_token'):
                                scraper.access_token = praw_instance.auth.access_token
                            elif hasattr(praw_instance, '_authorized_core') and hasattr(praw_instance._authorized_core, 'authorizer'):
                                authorizer = praw_instance._authorized_core.authorizer
                                if hasattr(authorizer, 'access_token'):
                                    scraper.access_token = authorizer.access_token
                            
                            logger.info("已使用username/password重新创建PRAW实例")
                    except Exception as e:
                        logger.warning(f"检查scraper创建方式失败: {str(e)}，继续使用原有scraper")
            except Exception as e:
                logger.warning(f"读取配置文件失败: {str(e)}，继续使用传入的scraper")
        
        self.scraper = scraper
        self.scorer = scorer
        self.executor = executor
        self.config = config
        self.scheduler = scheduler
        self.post_executor = post_executor
        
        self.is_running = False
        self.thread = None
        self.stop_event = threading.Event()
        
        # Reddit API速率限制控制
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 最小请求间隔（秒），Reddit建议60次/分钟
        self.request_count = 0
        self.request_window_start = time.time()
        self.max_requests_per_minute = 60  # Reddit API限制：60次/分钟

        # 动作级别限速（RATELIMIT）：全局暂停到指定时间后自动恢复
        self.action_pause_until_ts = 0.0  # epoch seconds
        # 温和节流：成功发出评论后，至少等待一段时间再继续下一个任务（降低触发概率）
        self.min_pause_after_comment_seconds = 30  # 可按需要调大（更不容易触发限速）
        # 随机分配执行间隔的边界（拟人化）
        self.min_random_interval_seconds = 8
        self.max_random_interval_seconds = 15 * 60  # 15分钟上限（避免“卡死感”）
        
        # 执行间隔（会根据执行时间段和任务数量自动计算）
        self.execution_interval = 10  # 默认10秒检查一次
        self._calculated_interval = None  # 智能计算的间隔时间
        
        # 活动日志
        self.activity_log: List[Dict[str, Any]] = []
        self.last_log_save_time = time.time()
        self.log_save_interval = 5  # 每5秒保存一次日志到数据库
    
    def _wait_for_rate_limit(self):
        """等待以满足速率限制"""
        current_time = time.time()

        # 1) 先处理动作级别限速（RATELIMIT）
        if self.action_pause_until_ts and current_time < self.action_pause_until_ts:
            wait_time = self.action_pause_until_ts - current_time
            if wait_time > 0:
                logger.info(f"检测到Reddit限速，暂停 {wait_time:.1f} 秒后自动恢复执行")
                # 用 stop_event.wait() 便于随时停止
                self.stop_event.wait(wait_time)
                current_time = time.time()
        
        # 检查是否超过1分钟窗口
        if current_time - self.request_window_start >= 60:
            self.request_count = 0
            self.request_window_start = current_time
        
        # 如果接近限制，等待
        if self.request_count >= self.max_requests_per_minute - 5:  # 留5个请求的缓冲
            wait_time = 60 - (current_time - self.request_window_start)
            if wait_time > 0:
                logger.info(f"接近速率限制，等待 {wait_time:.1f} 秒")
                self.stop_event.wait(wait_time)
                self.request_count = 0
                self.request_window_start = time.time()
        
        # 确保最小请求间隔
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            self.stop_event.wait(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1

    def _set_action_pause(self, seconds: Optional[int], reason: str = ""):
        """设置动作级别暂停（RATELIMIT / 评论节流）。"""
        if not seconds:
            return
        seconds = int(max(1, seconds))
        # 轻微随机抖动，避免精准踩线再次触发
        jitter = random.randint(5, 20)
        pause_seconds = seconds + jitter
        until = time.time() + pause_seconds
        if until > self.action_pause_until_ts:
            self.action_pause_until_ts = until
            msg = f"⏸️ 检测到限速/需要冷却，暂停 {pause_seconds} 秒后自动恢复"
            if reason:
                msg += f"（原因: {reason}）"
            self._add_activity_log('warning', msg)
    
    def _add_activity_log(self, log_type: str, message: str):
        """
        添加活动日志
        
        Args:
            log_type: 日志类型 ('info', 'success', 'warning', 'error')
            message: 日志消息
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = {
                'type': log_type,
                'timestamp': timestamp,
                'message': message
            }
            
            # 添加到内存中的日志列表
            self.activity_log.append(log_entry)
            
            # 限制日志数量，只保留最近1000条
            if len(self.activity_log) > 1000:
                self.activity_log = self.activity_log[-1000:]
            
            # 定期保存到数据库（每5秒保存一次）
            current_time = time.time()
            if current_time - self.last_log_save_time >= self.log_save_interval:
                try:
                    # 保存到数据库
                    log_json = json.dumps(self.activity_log, default=str, ensure_ascii=False)
                    self.db.set_config('auto_activity_logs', log_json, '自动化运营活动日志')
                    self.last_log_save_time = current_time
                except Exception as e:
                    logger.error(f"保存活动日志到数据库失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"添加活动日志失败: {str(e)}")
    
    def _is_execution_time(self) -> bool:
        """检查当前是否在执行时间段内"""
        try:
            scheduler_config = self.config.get_scheduler_config() or self.config.get_default_scheduler_config()
            exec_time = scheduler_config.get('execution_time', {})
            
            start_str = exec_time.get('start', '08:00')
            end_str = exec_time.get('end', '20:00')
            
            # 解析时间
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
            current_time = datetime.now().time()
            
            return start_time <= current_time <= end_time
            
        except Exception as e:
            logger.error(f"检查执行时间失败: {str(e)}")
            return True  # 默认允许执行
    
    def _calculate_smart_interval(self) -> float:
        """
        智能计算执行间隔时间
        根据“执行时间段 + 每日执行次数上限（剩余配额）”，自动平均分配执行间隔
        目标：更稳、更像真人（并给出缓冲时间避免踩线）
        
        Returns:
            建议的执行间隔（秒）
        """
        try:
            scheduler_config = self.config.get_scheduler_config() or self.config.get_default_scheduler_config()
            exec_time = scheduler_config.get('execution_time', {})
            exec_limits = scheduler_config.get('execution_limits', {})
            
            start_str = exec_time.get('start', '08:00')
            end_str = exec_time.get('end', '20:00')
            
            # 计算执行时间段的起止时间
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
            
            # 转换为datetime对象以便计算差值
            today = datetime.now().date()
            start_dt = datetime.combine(today, start_time)
            end_dt = datetime.combine(today, end_time)
            
            # 如果结束时间小于开始时间，说明跨天了
            if end_dt < start_dt:
                end_dt = end_dt + timedelta(days=1)

            now_dt = datetime.now()
            # 更稳：用“剩余可执行时间”而不是整段时间（避免启动较晚时间隔仍按整段平均导致过慢）
            if now_dt < start_dt:
                remaining_seconds = (end_dt - start_dt).total_seconds()
            elif now_dt > end_dt:
                remaining_seconds = 0
            else:
                remaining_seconds = (end_dt - now_dt).total_seconds()
            
            # 计算剩余待执行任务数量
            # 获取各类型任务的剩余配额
            remaining_tasks = 0
            for interaction_type in ['deep', 'standard', 'light']:
                limit = exec_limits.get(interaction_type, 0)
                if limit > 0:  # 只计算有限制的类型
                    today_count = self.scheduler.get_today_execution_count(interaction_type)
                    remaining = limit - today_count
                    if remaining > 0:
                        remaining_tasks += remaining
            
            # 如果没有剩余任务，使用默认间隔
            if remaining_tasks == 0:
                return 10.0

            # 如果剩余时间不足（或已过执行时间段），给一个保守的默认间隔
            if remaining_seconds <= 0:
                return 60.0
            
            # 计算平均间隔时间（秒）
            # 留出20%的缓冲时间，避免时间不够 / 留出更像真人的空隙
            available_seconds = remaining_seconds * 0.8
            interval = available_seconds / remaining_tasks
            
            # 限制间隔范围：最小10秒，最大600秒（10分钟）
            # 评论动作会额外触发 comment 冷却（min_pause_after_comment_seconds），这里仍给一个较稳的下限
            interval = max(10.0, min(interval, 600.0))
            
            logger.debug(
                f"智能计算执行间隔: 执行时间段={start_str}-{end_str}, 剩余时间={remaining_seconds/60:.1f}分钟, "
                f"剩余任务={remaining_tasks}个, 建议间隔={interval:.1f}秒"
            )
            
            return interval
            
        except Exception as e:
            logger.error(f"计算智能间隔失败: {str(e)}")
            return 10.0  # 出错时返回默认值

    def _sample_random_interval(self, mean_seconds: float, *, has_pending_tasks: bool) -> float:
        """
        把“平均间隔”转成“随机间隔”（更像真人）。

        方式：以 mean_seconds 为期望，用指数分布抽样（泊松过程），并做上下限裁剪。
        - mean_seconds 来自剩余时间/剩余配额的“期望频率”
        - 指数分布会产生：多数较短间隔 + 少数较长间隔（更拟人）
        """
        try:
            mean_seconds = float(mean_seconds or 0.0)
        except Exception:
            mean_seconds = 0.0
        if mean_seconds <= 0:
            mean_seconds = 10.0

        # 没有待执行任务时：更频繁检查一下，保证新任务能尽快被拾取
        if not has_pending_tasks:
            base = min(20.0, mean_seconds)
            return max(2.0, base * random.uniform(0.8, 1.4))

        # 指数分布抽样：lambda = 1/mean
        lam = 1.0 / max(1.0, mean_seconds)
        sampled = random.expovariate(lam)

        # 轻度“拟人”抖动（避免纯指数也太“数学”）
        sampled *= random.uniform(0.9, 1.3)

        # 偶发长停顿：像在阅读/切换窗口（概率略低，避免影响吞吐）
        if random.random() < 0.04:
            sampled += random.uniform(20, 120)

        # 裁剪到合理范围
        sampled = max(float(self.min_random_interval_seconds), sampled)
        sampled = min(float(self.max_random_interval_seconds), sampled)
        return float(sampled)
    
    def _get_smart_task(self) -> List[Dict[str, Any]]:
        """
        智能获取待执行任务（支持任务升级）
        
        当深度或中度互动有配额但队列中没有对应类型的任务时，
        从队列中按评分从高到低筛选任务，临时升级为深度或中度互动
        
        Returns:
            任务列表（最多1个任务）
        """
        try:
            scheduler_config = self.config.get_scheduler_config() or self.config.get_default_scheduler_config()
            exec_limits = scheduler_config.get('execution_limits', {})

            def _try_upgrade_task_to(task: Dict[str, Any], target_type: str) -> Optional[Dict[str, Any]]:
                """
                尝试把任务升级为 target_type（deep/standard），并确保生成所需 ai_comment。
                成功：更新DB并返回更新后的task dict；失败：返回None。
                """
                if not task:
                    return None
                if target_type not in ('deep', 'standard'):
                    return None
                if task.get('interaction_type') == target_type:
                    return task

                # deep/standard 执行需要评论内容
                ai_comment = task.get('ai_comment')
                session = self.db.SessionLocal()
                try:
                    reddit_post = session.query(self.db.RedditPost).filter_by(id=task.get('post_id')).first()
                    if not reddit_post:
                        logger.warning(f"智能升级失败：数据库中找不到帖子数据 post_id={task.get('post_id')}，跳过该任务")
                        return None

                    if not ai_comment:
                        post_data = {
                            'id': task.get('post_id'),
                            'title': reddit_post.title or '',
                            'selftext': reddit_post.selftext or '',
                            'subreddit': task.get('subreddit')
                        }
                        ai_comment = self.executor.generate_ai_comment(post_data, target_type)
                        if not ai_comment:
                            logger.warning(f"智能升级失败：无法生成{target_type}评论内容，跳过任务 #{task.get('id')}")
                            return None

                    task_obj = session.query(self.db.AutoInteractionQueue).filter_by(id=task.get('id')).first()
                    if not task_obj:
                        return None
                    task_obj.interaction_type = target_type
                    task_obj.ai_comment = ai_comment
                    session.commit()

                    task['interaction_type'] = target_type
                    task['ai_comment'] = ai_comment
                    logger.info(f"✅ 智能升级成功：任务 #{task.get('id')} 已升级为 {target_type}")
                    return task
                except Exception as e:
                    session.rollback()
                    logger.error(f"智能升级异常: {str(e)}", exc_info=True)
                    return None
                finally:
                    session.close()
            
            # 1. 优先检查深度互动
            deep_limit = exec_limits.get('deep', 0)
            if deep_limit > 0:
                deep_count = self.scheduler.get_today_execution_count('deep')
                if deep_count < deep_limit:
                    # 深度互动还有配额，先尝试获取深度互动任务
                    deep_tasks = self.db.get_pending_interactions(limit=1, interaction_type='deep')
                    if deep_tasks:
                        return deep_tasks
                    
                    # 没有深度互动任务：从队列中按评分从高到低尝试升级（只有升级成功才返回）
                    all_tasks = self.db.get_pending_interactions(limit=30)
                    for cand in all_tasks or []:
                        upgraded = _try_upgrade_task_to(cand, 'deep')
                        if upgraded:
                            return [upgraded]
            
            # 2. 检查标准互动
            standard_limit = exec_limits.get('standard', 0)
            if standard_limit > 0:
                standard_count = self.scheduler.get_today_execution_count('standard')
                if standard_count < standard_limit:
                    # 标准互动还有配额，先尝试获取标准互动任务
                    standard_tasks = self.db.get_pending_interactions(limit=1, interaction_type='standard')
                    if standard_tasks:
                        return standard_tasks
                    
                    # 没有标准互动任务：从队列中按评分从高到低尝试升级（跳过deep任务）
                    all_tasks = self.db.get_pending_interactions(limit=30)
                    for cand in all_tasks or []:
                        if cand.get('interaction_type') == 'deep':
                            continue
                        upgraded = _try_upgrade_task_to(cand, 'standard')
                        if upgraded:
                            return [upgraded]
            
            # 3. 默认返回轻度互动任务（如果有配额）
            light_limit = exec_limits.get('light', 0)
            if light_limit > 0:
                light_count = self.scheduler.get_today_execution_count('light')
                if light_count < light_limit:
                    light_tasks = self.db.get_pending_interactions(limit=1, interaction_type='light')
                    if light_tasks:
                        return light_tasks
            
            # 4. 如果都没有配额或没有任务：不要返回“任意任务”，否则会反复尝试不可执行任务导致卡住
            return []
            
        except Exception as e:
            logger.error(f"智能获取任务失败: {str(e)}")
            # 出错时返回空，避免反复执行不可执行任务导致卡住
            return []
    
    def _reauthenticate_reddit(self) -> bool:
        """
        重新认证Reddit API
        
        注意：这个方法会从 api_keys.json 读取认证信息并重新认证。
        如果左边栏已经完成认证并保存了用户名和密码，后台服务会自动使用这些信息重新认证。
        如果只保存了 access_token（没有用户名密码），当 token 过期时，需要用户在左边栏重新认证。
        
        Returns:
            是否认证成功
        """
        try:
            import os
            import json
            
            logger.info("检测到认证失败，尝试从配置文件重新认证...")
            
            # 从配置文件读取API密钥
            config_file = 'api_keys.json'
            if not os.path.exists(config_file):
                logger.error("Reddit API配置文件不存在")
                self._add_activity_log('error', '❌ Reddit API配置文件不存在。请在左边栏完成Reddit认证。')
                return False
            
            with open(config_file, 'r', encoding='utf-8') as f:
                api_keys = json.load(f)
            
            access_token = api_keys.get('reddit_access_token')
            client_id = api_keys.get('reddit_client_id')
            client_secret = api_keys.get('reddit_client_secret')
            redirect_uri = api_keys.get('reddit_redirect_uri', 'http://localhost:8080')
            username = api_keys.get('reddit_username')  # 获取用户名
            password = api_keys.get('reddit_password')  # 获取密码
            
            if not (client_id and client_secret):
                logger.error("Reddit API密钥不完整（缺少Client ID或Client Secret）")
                self._add_activity_log('error', '❌ Reddit API密钥不完整。请在左边栏配置Client ID和Client Secret。')
                return False
            
            # 检查是否有用户名和密码（用于自动重新认证）
            has_credentials = username and password
            if not has_credentials:
                logger.warning("配置文件中没有保存用户名和密码，无法自动重新认证")
                self._add_activity_log('warning', '⚠️ 配置文件中没有保存用户名和密码。当token过期时，请在左边栏重新进行Reddit认证。')
            
            # 重新创建scraper
            from reddit_scraper import RedditScraper
            
            # 如果有用户名和密码，使用username/password方式（推荐，PRAW会正确处理认证）
            # 对于script类型应用，PRAW会自动使用username/password进行OAuth2认证
            if username and password:
                try:
                    # 直接使用username/password创建PRAW实例，PRAW会自动处理OAuth2认证
                    # 这样PRAW会正确设置用户认证状态，可以执行点赞等操作
                    from reddit_scraper import RedditScraper
                    import praw
                    
                    # 创建PRAW实例，使用username/password（PRAW会自动处理OAuth2）
                    praw_instance = praw.Reddit(
                        client_id=client_id,
                        client_secret=client_secret,
                        user_agent='RedInsight Bot 1.0',  # 使用默认user_agent
                        username=username,
                        password=password
                    )
                    
                    # 验证PRAW实例是否可以执行操作（尝试获取用户信息）
                    try:
                        user = praw_instance.user.me()
                        if user:
                            logger.info(f"PRAW实例创建成功，用户: {user}")
                        else:
                            logger.warning("PRAW user.me()返回None，但继续使用")
                    except Exception as e:
                        logger.warning(f"PRAW user.me()验证失败: {str(e)}，但继续使用")
                    
                    # 创建RedditScraper实例，但使用已创建的PRAW实例
                    # 注意：RedditScraper的__init__会创建新的PRAW实例，我们需要绕过它
                    new_scraper = RedditScraper(
                        client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=redirect_uri
                    )
                    # 替换PRAW实例为我们创建的实例
                    new_scraper.reddit = praw_instance
                    
                    # 获取access_token（用于is_authenticated()验证）
                    # 注意：不要调用 authenticate_with_password，因为这会重新创建PRAW实例，覆盖我们正确创建的实例
                    # PRAW的auth对象可能在不同版本中结构不同，尝试多种方式获取
                    access_token_found = None
                    try:
                        # 方式1：直接从auth对象获取
                        if hasattr(praw_instance, 'auth') and hasattr(praw_instance.auth, 'access_token'):
                            access_token_found = praw_instance.auth.access_token
                        # 方式2：从authorized_core获取
                        elif hasattr(praw_instance, '_authorized_core') and hasattr(praw_instance._authorized_core, 'authorizer'):
                            authorizer = praw_instance._authorized_core.authorizer
                            if hasattr(authorizer, 'access_token'):
                                access_token_found = authorizer.access_token
                        # 方式3：从core获取
                        elif hasattr(praw_instance, '_core') and hasattr(praw_instance._core, 'authorizer'):
                            authorizer = praw_instance._core.authorizer
                            if hasattr(authorizer, 'access_token'):
                                access_token_found = authorizer.access_token
                    except Exception as e:
                        logger.warning(f"从PRAW实例获取access_token失败: {str(e)}")
                    
                    # 如果无法从PRAW实例获取access_token，手动进行OAuth2认证获取token
                    # 但不要重新创建PRAW实例，保持使用username/password创建的实例
                    if not access_token_found:
                        logger.warning("无法从PRAW实例获取access_token，手动获取token（但不重新创建PRAW实例）")
                        try:
                            import requests
                            import base64
                            
                            data = {
                                'grant_type': 'password',
                                'username': username,
                                'password': password,
                                'scope': 'vote read identity submit edit save'
                            }
                            
                            credentials = f"{client_id}:{client_secret}"
                            encoded_credentials = base64.b64encode(credentials.encode()).decode()
                            
                            headers = {
                                'Authorization': f'Basic {encoded_credentials}',
                                'User-Agent': 'RedInsight Bot 1.0',
                                'Content-Type': 'application/x-www-form-urlencoded'
                            }
                            
                            response = requests.post(
                                'https://www.reddit.com/api/v1/access_token',
                                data=data,
                                headers=headers,
                                timeout=30
                            )
                            
                            if response.status_code == 200:
                                token_data = response.json()
                                access_token_found = token_data['access_token']
                                logger.info("手动获取access_token成功")
                            else:
                                logger.error(f"手动获取access_token失败: {response.status_code} - {response.text}")
                        except Exception as e:
                            logger.error(f"手动获取access_token异常: {str(e)}")
                    
                    new_scraper.access_token = access_token_found
                    
                    # 更新配置文件中的access_token（如果有）
                    if new_scraper.access_token:
                        try:
                            api_keys['reddit_access_token'] = new_scraper.access_token
                            with open(config_file, 'w', encoding='utf-8') as f:
                                json.dump(api_keys, f, ensure_ascii=False, indent=2)
                            logger.info("已更新配置文件中的access_token")
                        except Exception as e:
                            logger.warning(f"更新配置文件失败: {str(e)}")
                    
                    logger.info("使用用户名/密码创建PRAW实例成功")
                except Exception as e:
                    logger.error(f"使用用户名/密码创建PRAW实例失败: {str(e)}")
                    # 如果失败，尝试使用旧的access_token（但可能仍然失败）
                    if access_token:
                        logger.warning("密码认证失败，尝试使用旧的access_token（可能仍然失败）")
                        new_scraper = RedditScraper(
                            access_token=access_token,
                            client_id=client_id,
                            client_secret=client_secret,
                            redirect_uri=redirect_uri
                        )
                    else:
                        logger.error("无法重新认证：缺少access_token和用户名/密码")
                        return False
            elif access_token:
                # 如果没有用户名/密码，使用access_token方式
                new_scraper = RedditScraper(
                    access_token=access_token,
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=redirect_uri
                )
            else:
                logger.error("无法重新认证：缺少access_token和用户名/密码")
                return False
            
            # 验证认证状态
            # 注意：即使is_authenticated()返回True，PRAW实例可能仍然没有正确设置用户认证状态
            # 所以我们需要额外验证PRAW实例的用户认证状态
            auth_check_passed = False
            try:
                # 检查access_token是否有效
                if new_scraper.is_authenticated():
                    # 尝试获取用户信息，验证PRAW实例的用户认证状态
                    try:
                        user = new_scraper.reddit.user.me()
                        if user:
                            auth_check_passed = True
                            logger.info(f"PRAW用户认证验证成功，用户: {user}")
                        else:
                            logger.warning("PRAW user.me()返回None，但is_authenticated()返回True")
                            # 即使无法获取用户信息，如果is_authenticated()返回True，我们也继续使用
                            auth_check_passed = True
                    except Exception as e:
                        logger.warning(f"PRAW用户认证验证失败: {str(e)}，但is_authenticated()返回True，继续使用")
                        # 即使无法获取用户信息，如果is_authenticated()返回True，我们也继续使用
                        auth_check_passed = True
                else:
                    # 即使is_authenticated()返回False，如果PRAW实例是使用username/password创建的，
                    # 它仍然可能可以执行操作
                    if username and password:
                        logger.warning("is_authenticated()返回False，但使用username/password创建，继续使用")
                        # 尝试获取用户信息验证
                        try:
                            user = new_scraper.reddit.user.me()
                            if user:
                                logger.info(f"PRAW实例可以获取用户信息，用户: {user}，认证成功")
                                auth_check_passed = True
                            else:
                                logger.warning("PRAW user.me()返回None，但继续使用（可能仍然可以执行操作）")
                                # 对于script类型应用，即使user.me()返回None，PRAW实例仍然可能可以执行操作
                                auth_check_passed = True
                        except Exception as e:
                            logger.warning(f"PRAW user.me()验证失败: {str(e)}，但继续使用（可能仍然可以执行操作）")
                            # 对于script类型应用，即使user.me()失败，PRAW实例仍然可能可以执行操作
                            auth_check_passed = True
                    else:
                        logger.warning("is_authenticated()返回False，且没有username/password")
            except Exception as e:
                logger.error(f"认证状态验证异常: {str(e)}")
            
            if auth_check_passed:
                # 更新scraper和相关组件
                self.scraper = new_scraper
                # 更新scheduler和executor中的scraper引用
                if hasattr(self.scheduler, 'scraper'):
                    self.scheduler.scraper = new_scraper
                if hasattr(self.executor, 'scraper'):
                    self.executor.scraper = new_scraper
                if hasattr(self.executor, 'interaction_manager') and hasattr(self.executor.interaction_manager, 'reddit_scraper'):
                    self.executor.interaction_manager.reddit_scraper = new_scraper
                # 已删除智能发帖功能，不再更新post_executor
                # if self.post_executor and hasattr(self.post_executor, 'scraper'):
                #     self.post_executor.scraper = new_scraper
                
                logger.info("Reddit API认证已从配置文件重新获取")
                return True
            else:
                logger.error("重新创建的scraper认证验证失败")
                # 如果认证失败，记录详细错误信息
                self._add_activity_log('error', '❌ Reddit API重新认证失败：access_token可能已过期或缺少必要的scope。请在左边栏或"自动点赞回帖控制台"中重新进行Reddit认证。')
                return False
                
        except Exception as e:
            logger.error(f"重新获取Reddit API认证失败: {str(e)}")
            self._add_activity_log('error', f'❌ Reddit API重新认证异常: {str(e)}。请在左边栏或"自动点赞回帖控制台"中重新进行Reddit认证。')
            return False
    
    def _execute_single_task(self) -> Dict[str, Any]:
        """执行单个任务（带速率限制控制）"""
        try:
            # 等待以满足速率限制
            self._wait_for_rate_limit()
            
            # 执行任务
            result = self.scheduler.execute_next_task()
            # 如果触发RATELIMIT：设置暂停时间，任务已在executor里回滚为pending
            if result and result.get('error_type') == 'ratelimit':
                retry_after = result.get('retry_after')
                self._set_action_pause(retry_after, reason=result.get('error', 'RATELIMIT'))
            # 成功执行后，如果包含评论动作，做温和节流降低触发概率
            if result and result.get('success') and 'comment' in (result.get('actions') or []):
                self._set_action_pause(self.min_pause_after_comment_seconds, reason="评论后冷却")
            return result
            
        except Exception as e:
            logger.error(f"执行任务失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _execution_loop(self):
        """执行循环（后台线程）"""
        logger.info("自动化执行服务线程已启动")
        self._add_activity_log('info', '🚀 后台执行服务已启动')
        
        last_status_log_time = 0
        # 启动后立即检查一次状态，避免等待
        initial_check_done = False
        # 启动后立即执行一次，不等待
        first_run = True
        
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                
                # 检查运行状态
                status = self.db.get_status()
                if not status or not status.get('is_running', False):
                    # 如果不在运行状态，等待一段时间后继续检查
                    if not initial_check_done:
                        logger.info("系统未运行，等待中...")
                        initial_check_done = True
                    else:
                        logger.debug("系统未运行，等待中...")
                    # 首次检查时，只等待1秒，然后立即重试（避免数据库状态更新延迟）
                    wait_time = 1 if first_run else 30
                    self.stop_event.wait(wait_time)
                    first_run = False
                    continue
                
                # 首次进入运行状态时记录日志
                if not initial_check_done:
                    logger.info("系统已进入运行状态，开始执行任务")
                    self._add_activity_log('info', '✅ 系统已进入运行状态，开始执行任务')
                    initial_check_done = True
                    first_run = False
                
                # 检查是否在执行时间段内
                if not self._is_execution_time():
                    # 不在执行时间段内，等待一段时间后继续检查
                    current_time_only = datetime.now().time()
                    # 每5分钟记录一次状态
                    if current_time - last_status_log_time > 300:
                        scheduler_config = self.config.get_scheduler_config() or self.config.get_default_scheduler_config()
                        exec_time = scheduler_config.get('execution_time', {})
                        start_str = exec_time.get('start', '08:00')
                        end_str = exec_time.get('end', '20:00')
                        self._add_activity_log('info', f"⏸️ 不在执行时间段内 (当前: {current_time_only.strftime('%H:%M')}, 执行时间段: {start_str}-{end_str})")
                        last_status_log_time = current_time
                    # 首次运行时，只等待5秒后重试（避免启动时刚好不在执行时间段）
                    wait_time = 5 if first_run else 60
                    self.stop_event.wait(wait_time)
                    first_run = False
                    continue
                
                # 每30秒记录一次状态（在执行时间段内时）
                if current_time - last_status_log_time > 30:
                    pending_tasks = self.db.get_pending_interactions(limit=1000)
                    pending_count = len(pending_tasks) if pending_tasks else 0
                    
                    # 重新计算智能间隔
                    self._calculated_interval = self._calculate_smart_interval()
                    self.execution_interval = self._calculated_interval
                    
                    self._add_activity_log('info', f"系统运行中 | 待执行任务: {pending_count} 个 | 执行间隔: {self.execution_interval:.1f}秒")
                    last_status_log_time = current_time
                
                # 检查Reddit API认证状态
                # 重要说明：由于左边栏认证是必须的（否则无法打开"自动运营"界面），
                # 所以初始化时scraper肯定是已认证的。这里只检查token是否过期，
                # 如果过期则自动重新认证（使用保存的username/password，无需用户再次操作）
                if not self.scraper:
                    logger.error("Scraper实例不存在，无法执行任务")
                    self.stop_event.wait(60)
                    continue
                
                # 检查认证状态
                # 注意：如果scraper是使用username/password创建的（标记为_using_username_password），
                # 即使is_authenticated()返回False，PRAW实例仍然可能可以执行操作
                # 所以这里只在明确检测到认证失败时才重新认证
                needs_reauth = False
                if hasattr(self.scraper, '_using_username_password') and self.scraper._using_username_password:
                    # 使用username/password创建的，即使is_authenticated()返回False，也可能可以执行操作
                    # 只有在实际执行操作失败时才重新认证
                    pass  # 先尝试执行，如果失败再重新认证
                elif not self.scraper.is_authenticated():
                    # 不是使用username/password创建的，且is_authenticated()返回False，需要重新认证
                    needs_reauth = True
                
                if needs_reauth:
                    logger.info("检测到认证已过期，尝试自动重新认证（使用左边栏保存的认证信息）...")
                    self._add_activity_log('info', '🔄 检测到认证已过期，正在自动重新认证（使用左边栏保存的认证信息）...')
                    auth_success = self._reauthenticate_reddit()
                    if not auth_success:
                        # 每5分钟记录一次认证失败
                        if current_time - last_status_log_time > 300:
                            self._add_activity_log('error', '❌ Reddit API认证已过期，自动重新认证失败。如果左边栏已保存用户名和密码，系统会自动重新认证；否则请在左边栏重新进行Reddit认证。')
                            last_status_log_time = current_time
                        self.stop_event.wait(60)  # 每分钟检查一次
                        continue
                    else:
                        self._add_activity_log('success', '✅ Reddit API认证已自动更新（使用了左边栏保存的认证信息），继续执行任务')
                
                # 智能获取待执行任务（支持任务升级）
                pending_tasks = self._get_smart_task()
                
                # 已删除发帖任务执行代码
                # if pending_posts:
                #     ... (发帖任务执行代码已删除)
                
                # 执行互动任务
                if pending_tasks:
                    # 再次检查认证状态（确保在执行前认证有效）
                    if not self.scraper or not self.scraper.is_authenticated():
                        self._add_activity_log('warning', '⚠️ 互动任务执行前认证检查失败，跳过本次执行')
                        self.stop_event.wait(10)
                        continue
                    
                    # 有任务，执行
                    task = pending_tasks[0]
                    task_msg = f"准备执行任务 #{task['id']} ({task['interaction_type']}) - r/{task['subreddit']} (评分: {task['post_score']:.2f})"
                    logger.info(task_msg)
                    self._add_activity_log('info', task_msg)
                    
                    result = self._execute_single_task()
                    
                    if result.get('success'):
                        actions = result.get('actions', [])
                        actions_str = ', '.join(actions) if actions else '无'
                        success_msg = f"✅ 任务 #{task['id']} 执行成功！执行动作: {actions_str}"
                        logger.info(success_msg)
                        self._add_activity_log('success', success_msg)
                    else:
                        error = result.get('error', '未知错误')
                        
                        # 如果是因为认证失败，立即尝试重新认证
                        if 'USER_REQUIRED' in error or 'Please log in' in error or '认证失败' in error or 'not authenticated' in error.lower():
                            logger.warning(f"检测到认证失败，尝试重新认证...")
                            self._add_activity_log('warning', f'⚠️ 任务 #{task["id"]} 因认证失败，正在尝试重新认证...')
                            
                            # 尝试重新认证
                            auth_success = self._reauthenticate_reddit()
                            if auth_success:
                                # 重新认证成功，将任务重置为pending以便重试
                                try:
                                    session = self.db.SessionLocal()
                                    try:
                                        task_obj = session.query(self.db.AutoInteractionQueue).filter_by(id=task['id']).first()
                                        if task_obj:
                                            task_obj.status = 'pending'
                                            task_obj.error_message = None
                                            session.commit()
                                            logger.info(f"任务 #{task['id']} 已重置为pending，将在下次循环重试")
                                            self._add_activity_log('info', f'✅ 重新认证成功，任务 #{task["id"]} 已重置为pending，将在下次重试')
                                    finally:
                                        session.close()
                                except Exception as e:
                                    logger.error(f"重置任务状态失败: {str(e)}")
                                
                                # 等待一下再继续，避免立即重试
                                self.stop_event.wait(5)
                                continue
                            else:
                                # 重新认证失败
                                error_msg = f"❌ 任务 #{task['id']} 执行失败: {error}（重新认证也失败）"
                                logger.error(error_msg)
                                self._add_activity_log('error', error_msg)
                                # 继续处理其他错误逻辑
                        
                        if '不满足执行条件' in error:
                            # 详细说明原因
                            scheduler_config = self.config.get_scheduler_config() or self.config.get_default_scheduler_config()
                            exec_time = scheduler_config.get('execution_time', {})
                            exec_limits = scheduler_config.get('execution_limits', {})
                            
                            reason = []
                            current_time_only = datetime.now().time()
                            start_str = exec_time.get('start', '08:00')
                            end_str = exec_time.get('end', '20:00')
                            start_time = datetime.strptime(start_str, '%H:%M').time()
                            end_time = datetime.strptime(end_str, '%H:%M').time()
                            
                            if not (start_time <= current_time_only <= end_time):
                                reason.append(f"当前时间 {current_time_only.strftime('%H:%M')} 不在执行时间段 {start_str}-{end_str} 内")
                            
                            limit = exec_limits.get(task['interaction_type'], 0)
                            if limit == 0:
                                reason.append(f"{task['interaction_type']}类型任务每日上限为0（已禁用）")
                            elif limit > 0:
                                today_count = self.scheduler.get_today_execution_count(task['interaction_type'])
                                if today_count >= limit:
                                    reason.append(f"{task['interaction_type']}类型任务今日已达上限 ({today_count}/{limit})")
                            
                            reason_str = '; '.join(reason) if reason else error
                            warning_msg = f"⚠️ 任务 #{task['id']} 暂不执行: {reason_str}"
                            logger.debug(warning_msg)
                            self._add_activity_log('warning', warning_msg)
                        else:
                            error_msg = f"❌ 任务 #{task['id']} 执行失败: {error}"
                            logger.warning(error_msg)
                            self._add_activity_log('error', error_msg)
                else:
                    # 没有任务，等待
                    logger.debug("没有待执行任务，等待中...")
                
                # 使用智能计算的间隔时间（如果已计算），否则使用默认间隔
                interval_to_use = self._calculated_interval if self._calculated_interval else self.execution_interval
                
                # 首次运行时，如果没有任务，只等待2秒后立即重试（确保新加入的任务能快速执行）
                if first_run:
                    interval_to_use = 2
                    first_run = False
                # 等待执行间隔（但至少等待2秒，避免过于频繁）
                elif interval_to_use < 2:
                    interval_to_use = 2

                # 拟人：把“平均间隔”转成“随机间隔”
                # pending_tasks 变量在本轮循环内会被赋值（list或None），这里统一转 bool
                has_pending = bool(pending_tasks) if 'pending_tasks' in locals() else False
                if not first_run:
                    interval_to_use = self._sample_random_interval(interval_to_use, has_pending_tasks=has_pending)
                
                self.stop_event.wait(interval_to_use)
                
            except Exception as e:
                error_msg = f"❌ 执行循环异常: {str(e)}"
                logger.error(error_msg)
                self._add_activity_log('error', error_msg)
                import traceback
                logger.error(traceback.format_exc())
                # 出错后等待更长时间
                self.stop_event.wait(60)
        
        logger.info("自动化执行服务已停止")
        self._add_activity_log('info', '⏹️ 后台执行服务已停止')
    
    def start(self):
        """启动后台服务"""
        if self.is_running:
            logger.warning("服务已在运行")
            return
        
        self.is_running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._execution_loop, daemon=True)
        self.thread.start()
        logger.info("自动化执行服务已启动")
    
    def stop(self):
        """停止后台服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=5)
        
        # 保存最后的日志
        try:
            if self.activity_log:
                log_json = json.dumps(self.activity_log, default=str, ensure_ascii=False)
                self.db.set_config('auto_activity_logs', log_json, '自动化运营活动日志')
        except Exception as e:
            logger.error(f"保存活动日志失败: {str(e)}")
        
        logger.info("自动化执行服务已停止")
    
    def is_alive(self) -> bool:
        """检查服务是否运行中"""
        return self.is_running and self.thread and self.thread.is_alive()

