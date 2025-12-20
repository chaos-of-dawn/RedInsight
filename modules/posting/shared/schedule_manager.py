"""
发布计划管理逻辑
"""
import streamlit as st
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import bisect

logger = logging.getLogger(__name__)

class ScheduleManager:
    """发布计划管理器"""
    
    def __init__(self, db_manager):
        """
        初始化计划管理器
        
        Args:
            db_manager: 数据库管理器
        """
        self.db = db_manager
    
    def create_schedule(self,
                       post_content_id: int,
                       subreddit: str,
                       scheduled_time: datetime,
                       posting_order: int = 0,
                       rule_check_result: Dict[str, Any] = None) -> Optional[int]:
        """
        创建发布计划
        
        Args:
            post_content_id: 帖子内容ID
            subreddit: 子版块名称
            scheduled_time: 计划发布时间
            posting_order: 发布顺序
            rule_check_result: 规则检查结果
        
        Returns:
            计划ID，如果创建失败返回None
        """
        session = self.db.get_session()
        try:
            schedule = self.db.PostingSchedule(
                post_content_id=post_content_id,
                subreddit=subreddit,
                scheduled_time=scheduled_time,
                posting_order=posting_order,
                status='pending',
                rule_check_result=json.dumps(rule_check_result) if rule_check_result else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(schedule)
            session.commit()
            return schedule.id
        except Exception as e:
            logger.error(f"创建发布计划失败: {str(e)}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def create_schedules_for_posts(self,
                                  post_ids: List[int],
                                  subreddits: List[str],
                                  scheduled_time: datetime,
                                  rule_checker=None,
                                  provider: str = "deepseek",
                                  # 批次级节流（每篇帖子=一个批次，发到多个子版块）
                                  batch_min_interval: timedelta = timedelta(hours=2),
                                  rolling_window: timedelta = timedelta(hours=8),
                                  rolling_window_max_batches: int = 4,
                                  auto_shift: bool = True,
                                  subreddit_spacing_seconds: int = 30) -> List[int]:
        """
        为多个帖子创建发布计划（每个帖子发布到多个子版块）
        
        Args:
            post_ids: 帖子ID列表
            subreddits: 子版块列表
            scheduled_time: 计划发布时间
            rule_checker: 规则检查器
            provider: LLM提供商
        
        Returns:
            创建的计划ID列表
        """
        created_ids: List[int] = []
        if not post_ids or not subreddits:
            return created_ids
        
        # 最多取3个子版块（同一篇帖子可以发到1-3个子版块）
        # 清理子版块名称：去除空格、去除r/前缀、去除特殊字符
        # Reddit子版块名称只能包含字母、数字、下划线，不能有空格
        import re
        target_subreddits = []
        for s in subreddits:
            if s and s.strip():
                cleaned = s.strip().lstrip('r/').strip()
                # 去除所有空格和特殊字符，只保留字母、数字、下划线
                cleaned = re.sub(r'[^a-zA-Z0-9_]', '', cleaned)
                if cleaned:  # 只添加非空的清理后的名称
                    target_subreddits.append(cleaned)
        
        # 去重
        target_subreddits = list(dict.fromkeys(target_subreddits))  # 保持顺序的去重
        if len(target_subreddits) > 3:
            target_subreddits = target_subreddits[:3]
        
        # 读取已有批次时间（使用 post_content_id 作为批次标识，取该批次最早的 scheduled_time）
        existing_batch_times = self._get_existing_batch_times(
            start_time=scheduled_time - rolling_window,
            end_time=scheduled_time + timedelta(days=30)
        )
        
        for post_id in post_ids:
            # 计算该帖（批次）的基准发布时间：满足2小时间隔 + 任意8小时最多4批
            batch_time = self._find_next_available_batch_time(
                desired_time=scheduled_time,
                existing_times=existing_batch_times,
                batch_min_interval=batch_min_interval,
                rolling_window=rolling_window,
                rolling_window_max_batches=rolling_window_max_batches,
                auto_shift=auto_shift
            )
            # “占位”该批次时间，后续批次会基于它继续排
            self._insert_sorted(existing_batch_times, batch_time)

            # 获取帖子内容
            post = self._get_post_content(post_id)
            if not post:
                continue
            
            # 为每个子版块创建计划
            for order, subreddit in enumerate(target_subreddits):
                # 规则检查
                rule_result = None
                if rule_checker:
                    rule_result = rule_checker.check_post_compliance(
                        subreddit=subreddit,
                        title=post['title'],
                        content=post['content'],
                        provider=provider
                    )
                
                # 同一批次的多个子版块：按顺序做轻微错峰（默认30秒）
                schedule_time = batch_time + timedelta(seconds=order * int(subreddit_spacing_seconds))
                
                # 创建计划
                schedule_id = self.create_schedule(
                    post_content_id=post_id,
                    subreddit=subreddit,
                    scheduled_time=schedule_time,
                    posting_order=order,
                    rule_check_result=rule_result
                )
                
                if schedule_id:
                    created_ids.append(schedule_id)
            
            # 更新帖子状态为 scheduled（如果存在）
            try:
                from modules.posting.shared.post_manager import PostManager
                PostManager(self.db).update_post(post_id, status='scheduled')
            except Exception:
                pass
        
        return created_ids

    def _get_existing_batch_times(self, start_time: datetime, end_time: datetime) -> List[datetime]:
        """
        获取已有批次时间（每个 post_content_id 视为一个批次，取最早 scheduled_time）。
        """
        session = self.db.get_session()
        try:
            from sqlalchemy import func
            active_statuses = ['pending', 'approved', 'posting', 'posted']
            rows = session.query(
                self.db.PostingSchedule.post_content_id,
                func.min(self.db.PostingSchedule.scheduled_time).label('batch_time')
            ).filter(
                self.db.PostingSchedule.status.in_(active_statuses),
                self.db.PostingSchedule.scheduled_time >= start_time,
                self.db.PostingSchedule.scheduled_time <= end_time
            ).group_by(
                self.db.PostingSchedule.post_content_id
            ).all()
            times = [r.batch_time for r in rows if getattr(r, 'batch_time', None)]
            times.sort()
            return times
        except Exception as e:
            logger.error(f"获取已有批次时间失败: {str(e)}")
            return []
        finally:
            session.close()

    @staticmethod
    def _insert_sorted(arr: List[datetime], value: datetime):
        """将value按排序插入arr（arr需已排序）。"""
        bisect.insort(arr, value)

    def _find_next_available_batch_time(
        self,
        desired_time: datetime,
        existing_times: List[datetime],
        batch_min_interval: timedelta,
        rolling_window: timedelta,
        rolling_window_max_batches: int,
        auto_shift: bool
    ) -> datetime:
        """
        找到 >= desired_time 的最早可用批次时间，满足：
        - 与任意相邻批次间隔 >= batch_min_interval
        - 任意 rolling_window 内批次数 <= rolling_window_max_batches
        
        若 auto_shift=False，则不自动顺延，发现冲突时直接返回 desired_time（由上层决定报错/提示）。
        """
        candidate = desired_time
        if not existing_times:
            return candidate
        
        # 安全阈值：避免死循环（极端情况下最多推进365天）
        max_candidate = desired_time + timedelta(days=365)
        eps = timedelta(seconds=1)

        while True:
            if candidate > max_candidate:
                return candidate

            idx = bisect.bisect_left(existing_times, candidate)

            # 1) 2小时间隔：与前后相邻批次都要满足
            prev_t = existing_times[idx - 1] if idx - 1 >= 0 else None
            next_t = existing_times[idx] if idx < len(existing_times) else None

            if prev_t and candidate - prev_t < batch_min_interval:
                if not auto_shift:
                    return desired_time
                candidate = prev_t + batch_min_interval
                continue

            if next_t and next_t - candidate < batch_min_interval:
                if not auto_shift:
                    return desired_time
                candidate = next_t + batch_min_interval
                continue

            # 2) 8小时滚动窗口：等价于任意连续(rolling_window)内最多rolling_window_max_batches
            #    检查插入后是否出现“rolling_window_max_batches+1 个批次落在 rolling_window 内”
            times_with = existing_times.copy()
            bisect.insort(times_with, candidate)
            idx2 = bisect.bisect_left(times_with, candidate)

            window_violation = False
            # 需要检查所有长度为(rolling_window_max_batches+1)的连续片段
            span = rolling_window_max_batches  # e.g. 4 -> check i and i+4 (5 items)
            start_k = max(0, idx2 - span)
            end_k = min(idx2, len(times_with) - (span + 1))
            for k in range(start_k, end_k + 1):
                if times_with[k + span] - times_with[k] <= rolling_window:
                    window_violation = True
                    if not auto_shift:
                        return desired_time
                    # 将candidate推到该窗口起点 + rolling_window + eps
                    candidate = times_with[k] + rolling_window + eps
                    break
            if window_violation:
                continue

            return candidate
    
    def _get_post_content(self, post_id: int) -> Optional[Dict[str, Any]]:
        """获取帖子内容"""
        from modules.posting.shared.post_manager import PostManager
        post_manager = PostManager(self.db)
        return post_manager.get_post(post_id)
    
    def get_pending_schedules(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取待发布的计划
        
        Args:
            limit: 限制数量
        
        Returns:
            计划列表
        """
        session = self.db.get_session()
        try:
            schedules = session.query(self.db.PostingSchedule).filter(
                self.db.PostingSchedule.status.in_(['pending', 'approved'])
            ).filter(
                self.db.PostingSchedule.scheduled_time <= datetime.utcnow()
            ).order_by(
                self.db.PostingSchedule.scheduled_time.asc(),
                self.db.PostingSchedule.posting_order.asc()
            ).limit(limit).all()
            
            result = []
            for schedule in schedules:
                result.append({
                    'id': schedule.id,
                    'post_content_id': schedule.post_content_id,
                    'subreddit': schedule.subreddit,
                    'scheduled_time': schedule.scheduled_time,
                    'posting_order': schedule.posting_order,
                    'status': schedule.status,
                    'rule_check_result': json.loads(schedule.rule_check_result) if schedule.rule_check_result else None,
                    'posting_result': json.loads(schedule.posting_result) if schedule.posting_result else None
                })
            
            return result
        except Exception as e:
            logger.error(f"获取待发布计划失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def list_schedules(self,
                      status: str = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """
        列出发布计划
        
        Args:
            status: 状态筛选
            limit: 限制数量
        
        Returns:
            计划列表
        """
        session = self.db.get_session()
        try:
            query = session.query(self.db.PostingSchedule)
            
            if status:
                query = query.filter(self.db.PostingSchedule.status == status)
            
            schedules = query.order_by(
                self.db.PostingSchedule.scheduled_time.desc()
            ).limit(limit).all()
            
            result = []
            for schedule in schedules:
                # 获取帖子内容
                post = session.query(self.db.PostContent).filter(
                    self.db.PostContent.id == schedule.post_content_id
                ).first()
                
                result.append({
                    'id': schedule.id,
                    'post_content_id': schedule.post_content_id,
                    'post_title': post.title if post else '未知',
                    'subreddit': schedule.subreddit,
                    'scheduled_time': schedule.scheduled_time,
                    'posting_order': schedule.posting_order,
                    'status': schedule.status,
                    'rule_check_result': json.loads(schedule.rule_check_result) if schedule.rule_check_result else None,
                    'posting_result': json.loads(schedule.posting_result) if schedule.posting_result else None,
                    'created_at': schedule.created_at
                })
            
            return result
        except Exception as e:
            logger.error(f"列出发布计划失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def update_schedule_status(self,
                              schedule_id: int,
                              status: str,
                              posting_result: Dict[str, Any] = None) -> bool:
        """
        更新计划状态
        
        Args:
            schedule_id: 计划ID
            status: 新状态
            posting_result: 发布结果
        
        Returns:
            是否成功
        """
        session = self.db.get_session()
        try:
            schedule = session.query(self.db.PostingSchedule).filter(
                self.db.PostingSchedule.id == schedule_id
            ).first()
            
            if not schedule:
                return False
            
            schedule.status = status
            if posting_result:
                schedule.posting_result = json.dumps(posting_result)
            schedule.updated_at = datetime.utcnow()
            
            session.commit()
            return True
        except Exception as e:
            logger.error(f"更新计划状态失败: {str(e)}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def update_schedule(self,
                       schedule_id: int,
                       subreddit: str = None,
                       scheduled_time: datetime = None,
                       posting_order: int = None) -> bool:
        """
        更新发布计划
        
        Args:
            schedule_id: 计划ID
            subreddit: 子版块名称
            scheduled_time: 计划发布时间
            posting_order: 发布顺序
        
        Returns:
            是否成功
        """
        session = self.db.get_session()
        try:
            schedule = session.query(self.db.PostingSchedule).filter(
                self.db.PostingSchedule.id == schedule_id
            ).first()
            
            if not schedule:
                return False
            
            if subreddit is not None:
                schedule.subreddit = subreddit
            if scheduled_time is not None:
                schedule.scheduled_time = scheduled_time
            if posting_order is not None:
                schedule.posting_order = posting_order
            
            schedule.updated_at = datetime.utcnow()
            session.commit()
            return True
        except Exception as e:
            logger.error(f"更新发布计划失败: {str(e)}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def delete_schedule(self, schedule_id: int) -> bool:
        """
        删除发布计划
        
        Args:
            schedule_id: 计划ID
        
        Returns:
            是否成功
        """
        session = self.db.get_session()
        try:
            schedule = session.query(self.db.PostingSchedule).filter(
                self.db.PostingSchedule.id == schedule_id
            ).first()
            
            if not schedule:
                return False
            
            session.delete(schedule)
            session.commit()
            return True
        except Exception as e:
            logger.error(f"删除发布计划失败: {str(e)}")
            session.rollback()
            return False
        finally:
            session.close()

