"""
子版块规则检查器
"""
import streamlit as st
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SubredditRuleChecker:
    """子版块规则检查器"""
    
    def __init__(self, db_manager, llm_analyzer, reddit_scraper=None):
        """
        初始化规则检查器
        
        Args:
            db_manager: 数据库管理器
            llm_analyzer: LLM分析器
            reddit_scraper: RedditScraper实例（可选）
        """
        self.db = db_manager
        self.analyzer = llm_analyzer
        self.reddit_scraper = reddit_scraper
    
    def get_subreddit_rules(self, subreddit: str, force_refresh: bool = False) -> Optional[str]:
        """
        获取子版块规则
        
        Args:
            subreddit: 子版块名称
            force_refresh: 是否强制刷新
        
        Returns:
            规则文本，如果获取失败返回None
        """
        session = self.db.get_session()
        try:
            # 检查缓存
            if not force_refresh:
                rule = session.query(self.db.SubredditRule).filter(
                    self.db.SubredditRule.subreddit == subreddit
                ).first()
                
                if rule:
                    # 检查是否过期（24小时）
                    if (datetime.utcnow() - rule.last_updated).total_seconds() < 86400:
                        return rule.rules_text
            
            # 从Reddit API获取规则（这里需要实现）
            # 暂时返回None，后续可以通过reddit_scraper获取
            rules_text = self._fetch_rules_from_reddit(subreddit)
            
            if rules_text:
                # 保存到数据库
                rule = session.query(self.db.SubredditRule).filter(
                    self.db.SubredditRule.subreddit == subreddit
                ).first()
                
                if rule:
                    rule.rules_text = rules_text
                    rule.last_updated = datetime.utcnow()
                    rule.rule_version += 1
                else:
                    rule = self.db.SubredditRule(
                        subreddit=subreddit,
                        rules_text=rules_text,
                        last_updated=datetime.utcnow()
                    )
                    session.add(rule)
                
                session.commit()
                return rules_text
            
            return None
            
        except Exception as e:
            logger.error(f"获取子版块规则失败: {str(e)}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def _fetch_rules_from_reddit(self, subreddit: str) -> Optional[str]:
        """
        从Reddit API获取规则
        
        Args:
            subreddit: 子版块名称
        
        Returns:
            规则文本
        """
        try:
            # 优先使用传入的 scraper
            scraper = self.reddit_scraper
            
            # 如果没有传入，尝试从 session_state 获取
            if not scraper:
                try:
                    # 检查 streamlit 是否已初始化
                    if hasattr(st, 'session_state') and st.session_state is not None:
                        scraper = st.session_state.get('scraper')
                except (AttributeError, RuntimeError, KeyError):
                    # Streamlit 可能尚未初始化，忽略错误
                    pass
            
            # 如果仍然没有，返回 None
            if not scraper:
                logger.warning(f"无法获取RedditScraper实例，无法获取 r/{subreddit} 的规则")
                return None
            
            # 检查认证状态
            if not scraper.is_authenticated():
                logger.warning(f"Reddit API未认证，无法获取 r/{subreddit} 的规则")
                return None
            
            # 使用 RedditScraper 获取规则文本
            rules_text = scraper.get_subreddit_rules_text(subreddit)
            
            if rules_text:
                logger.info(f"成功获取 r/{subreddit} 的规则（{len(rules_text)} 字符）")
                return rules_text
            else:
                logger.warning(f"获取 r/{subreddit} 的规则为空")
                return None
                
        except Exception as e:
            logger.error(f"从Reddit API获取 r/{subreddit} 规则失败: {str(e)}")
            return None
    
    def check_post_compliance(self, 
                             subreddit: str, 
                             title: str, 
                             content: str,
                             provider: str = "deepseek") -> Dict[str, Any]:
        """
        检查帖子是否符合子版块规则
        
        Args:
            subreddit: 子版块名称
            title: 帖子标题
            content: 帖子内容
            provider: LLM提供商
        
        Returns:
            检查结果字典
        """
        try:
            # 获取规则
            rules_text = self.get_subreddit_rules(subreddit)
            
            if not rules_text:
                # 如果没有规则，返回默认结果
                return {
                    'is_compliant': True,
                    'compliance_score': 100,
                    'suggestions': [],
                    'message': '无法获取子版块规则，跳过检查'
                }
            
            # 构建AI检查提示词
            prompt = f"""请检查以下帖子内容是否符合 r/{subreddit} 的规则：

子版块规则：
{rules_text}

帖子内容：
标题：{title}
内容：{content}

请分析：
1. 是否符合所有规则（是/否）
2. 符合度评分（0-100分）
3. 如果不符合，请指出违反的规则
4. 提供具体的修改建议

请返回JSON格式：
{{
    "is_compliant": true/false,
    "compliance_score": 85,
    "violated_rules": ["规则1", "规则2"],
    "suggestions": ["建议1", "建议2"],
    "reasoning": "分析原因"
}}"""
            
            # 调用AI分析
            result = self.analyzer._call_llm(prompt, provider, "rule_check")
            
            # 解析结果
            if isinstance(result, dict):
                return {
                    'is_compliant': result.get('is_compliant', True),
                    'compliance_score': result.get('compliance_score', 100),
                    'violated_rules': result.get('violated_rules', []),
                    'suggestions': result.get('suggestions', []),
                    'reasoning': result.get('reasoning', '')
                }
            elif isinstance(result, str):
                # 尝试从字符串中提取JSON
                import json
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        return {
                            'is_compliant': parsed.get('is_compliant', True),
                            'compliance_score': parsed.get('compliance_score', 100),
                            'violated_rules': parsed.get('violated_rules', []),
                            'suggestions': parsed.get('suggestions', []),
                            'reasoning': parsed.get('reasoning', '')
                        }
                    except:
                        pass
            
            # 默认返回
            return {
                'is_compliant': True,
                'compliance_score': 100,
                'suggestions': [],
                'message': '规则检查完成，但无法解析结果'
            }
            
        except Exception as e:
            logger.error(f"规则检查失败: {str(e)}")
            return {
                'is_compliant': True,
                'compliance_score': 100,
                'suggestions': [],
                'error': str(e)
            }


