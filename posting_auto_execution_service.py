"""
自动发帖后台执行服务（PostingSchedule）
用于在Streamlit启动后持续轮询执行到期的 PostingSchedule 计划。
"""

import threading
import time
import logging
from typing import Optional, Dict, Any

from database import DatabaseManager
from reddit_scraper import RedditScraper
from posting_execution_service import PostingExecutionService

logger = logging.getLogger(__name__)


class PostingAutoExecutionService:
    """PostingSchedule 自动执行后台服务"""

    def __init__(self, db_manager: DatabaseManager, scraper: RedditScraper, poll_interval_seconds: int = 20):
        self.db = db_manager
        self.scraper = scraper
        self.poll_interval_seconds = int(max(5, poll_interval_seconds))

        self.executor = PostingExecutionService(db_manager, scraper)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def set_scraper(self, scraper: RedditScraper):
        """更新scraper引用（用于认证更新后继续发布）。"""
        self.scraper = scraper
        try:
            self.executor.scraper = scraper
        except Exception:
            pass

    def start(self):
        if self.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=2)
            except Exception:
                pass

    def _run_loop(self):
        logger.info("PostingAutoExecutionService started")
        while not self._stop_event.is_set():
            try:
                # 执行一个批次（同一post_content_id的多子版块发布）
                result: Dict[str, Any] = self.executor.execute_next_batch()
                
                # 如果遇到认证错误，记录详细信息
                # 注意：后台服务使用的 scraper 会在 UI 层面通过 set_scraper() 更新
                # 当用户在左侧边栏重新认证后，UI 会自动调用 set_scraper() 更新后台服务
                if result.get('error_type') == 'authentication_required':
                    error_msg = result.get('error', '')
                    suggestion = result.get('suggestion', '')
                    logger.warning(
                        f"❌ 认证错误: {error_msg}\n"
                        f"   建议: {suggestion}\n"
                        f"   提示: 请在左侧边栏重新进行OAuth2认证，系统会自动更新后台服务的认证状态。"
                    )
                
                if result.get('executed', 0) > 0:
                    # 如果刚执行了任务，立即尝试下一批（减少延迟）
                    continue
            except Exception as e:
                logger.error(f"自动发帖后台循环异常: {str(e)}", exc_info=True)

            # 没任务/或失败：等待下一轮
            self._stop_event.wait(self.poll_interval_seconds)

        logger.info("PostingAutoExecutionService stopped")


