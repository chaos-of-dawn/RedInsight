import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any


class AccountReadinessService:
    def __init__(self, db_manager, reddit_scraper):
        self.db = db_manager
        self.scraper = reddit_scraper
        self.logger = logging.getLogger(__name__)

    def snapshot_account(self) -> Dict[str, Any]:
        try:
            me = self.scraper.get_me()
            if not me:
                # 尝试检测认证状态并返回清晰的失败信息
                try:
                    authed = self.scraper.is_authenticated()
                except Exception:
                    authed = False
                msg = "未获取到用户信息，请先完成Reddit认证" if not authed else "未能读取到用户信息，请稍后重试"
                return {'success': False, 'error': msg}

            created_utc = getattr(me, 'created_utc', None)
            age_days = 0
            if created_utc:
                # PRAW的created_utc通常为timestamp
                try:
                    created_dt = datetime.utcfromtimestamp(created_utc)
                    age_days = max(0, (datetime.utcnow() - created_dt).days)
                except Exception:
                    age_days = 0

            snapshot = {
                'snapshot_time': datetime.utcnow(),
                'link_karma': getattr(me, 'link_karma', 0),
                'comment_karma': getattr(me, 'comment_karma', 0),
                'total_karma': getattr(me, 'link_karma', 0) + getattr(me, 'comment_karma', 0),
                'account_age_days': age_days,
                # 以下统计可由互动模块填充或按需更新
                'subs_joined': 0,
                'upvotes': 0,
                'comments': 0,
                'posts': 0,
            }

            self.db.save_account_snapshot(snapshot)
            return {'success': True, 'snapshot': snapshot}
        except Exception as e:
            self.logger.warning(f"账号快照失败: {str(e)}")
            return {'success': False, 'error': f"账号快照失败: {str(e)}"}

    def assess_readiness_for_subreddit(self, subreddit: str) -> Dict[str, Any]:
        try:
            me = self.scraper.get_me()
            if not me:
                # 尝试直接从 PRAW 获取
                try:
                    reddit = getattr(self.scraper, 'reddit', None)
                    if reddit is not None:
                        me = reddit.user.me()
                except Exception:
                    me = None
            if not me:
                try:
                    authed = self.scraper.is_authenticated()
                except Exception:
                    authed = False
                msg = "未获取到用户信息，请先完成Reddit认证" if not authed else "未能读取到用户信息，可能缺少identity权限或会话过期，请刷新认证后重试"
                return {'success': False, 'error': msg}
            me = self.scraper.get_me()
            if not me:
                # 尝试直接从 PRAW 获取
                try:
                    reddit = getattr(self.scraper, 'reddit', None)
                    if reddit is not None:
                        me = reddit.user.me()
                except Exception:
                    me = None
            if not me:
                try:
                    authed = self.scraper.is_authenticated()
                except Exception:
                    authed = False
                msg = "未获取到用户信息，请先完成Reddit认证" if not authed else "未能读取到用户信息，可能缺少identity权限或会话过期，请刷新认证后重试"
                return {'success': False, 'error': msg}

            link_karma = getattr(me, 'link_karma', 0)
            comment_karma = getattr(me, 'comment_karma', 0)
            total_karma = link_karma + comment_karma

            created_utc = getattr(me, 'created_utc', None)
            age_days = 0
            if created_utc:
                try:
                    created_dt = datetime.utcfromtimestamp(created_utc)
                    age_days = max(0, (datetime.utcnow() - created_dt).days)
                except Exception:
                    age_days = 0

            # 获取规则文本
            rules_text = self.scraper.get_subreddit_rules_text(subreddit) or ''
            sidebar_text = self.scraper.get_subreddit_sidebar_text(subreddit) or ''
            combined_text = f"{rules_text}\n{sidebar_text}".lower()

            reasons = []
            recommendations = []

            # 启发式阈值（可后续配置化）
            min_age_days = 14
            min_total_karma = 100
            min_recent_comments = 10  # 可结合历史统计

            # 从文本中检索明显限制关键词
            keywords = ["karma", "account age", "new account", "minimum", "post limit"]
            has_explicit_rules = any(k in combined_text for k in keywords)

            can_post = True
            confidence = 'Medium'

            if age_days < min_age_days:
                can_post = False
                reasons.append(f"账号年龄较新（{age_days} 天 < {min_age_days} 天）")
            if total_karma < min_total_karma:
                can_post = False
                reasons.append(f"总Karma较低（{total_karma} < {min_total_karma}）")

            if has_explicit_rules:
                confidence = 'High'
                if 'new account' in combined_text:
                    recommendations.append('优先参与社区讨论，提升可信度后再发帖')
                if 'karma' in combined_text:
                    recommendations.append('通过高质量评论提升 comment_karma')

            if can_post:
                recommendations.append('可尝试先在固定主题帖中发首贴，避免外链')
            else:
                recommendations.append('执行7天养号计划：订阅相关子版块、分布式点赞与高质量评论')

            result = {
                'subreddit': subreddit,
                'can_post': can_post,
                'confidence': confidence,
                'reasons': reasons,
                'recommendations': recommendations,
                'age_days': age_days,
                'total_karma': total_karma,
            }

            self.db.save_subreddit_readiness(
                subreddit=subreddit,
                can_post=can_post,
                confidence=confidence,
                reasons=reasons,
                recommendations=recommendations,
            )

            return {'success': True, 'readiness': result}
        except Exception as e:
            self.logger.warning(f"发帖资格评估失败: {str(e)}")
            return {'success': False, 'error': f"发帖资格评估失败: {str(e)}"}

    def generate_warming_plan(self, days: int = 7) -> Dict[str, Any]:
        try:
            # 基础配额，可后续根据账号画像动态调整
            daily_plan = []
            for d in range(days):
                # 渐进式递增
                upvotes = min(20, 10 + d)
                comments = min(5, 2 + (d // 2))
                posts = 1 if d >= 3 else 0

                daily_plan.append({
                    'day': d + 1,
                    'upvotes': upvotes,
                    'comments': comments,
                    'posts': posts,
                    'notes': '分布在全天，随机化时间间隔，优先中等热度的高相关帖子'
                })

            return {'success': True, 'plan_days': days, 'plan': daily_plan}
        except Exception as e:
            self.logger.error(f"生成养号计划失败: {str(e)}")
            return {'success': False, 'error': str(e)}


