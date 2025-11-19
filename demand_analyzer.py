"""
需求分析模块
使用大模型分析用户需求，翻译并推荐相关子版块
"""
import logging
from typing import Dict, List, Any, Tuple
import json

logger = logging.getLogger(__name__)

class DemandAnalyzer:
    """需求分析器"""
    
    def __init__(self, llm_analyzer):
        """
        初始化需求分析器
        
        Args:
            llm_analyzer: LLM分析器实例
        """
        self.llm_analyzer = llm_analyzer
        
    def analyze_demand(self, user_input: str) -> Dict[str, Any]:
        """
        分析用户需求
        
        Args:
            user_input: 用户输入的需求描述
            
        Returns:
            分析结果字典，包含翻译、关键词、推荐子版块等
        """
        try:
            # 构建分析提示
            prompt = self._build_analysis_prompt(user_input)
            
            # 调用大模型分析
            response = self.llm_analyzer._call_llm(prompt, "deepseek", "demand_analysis")
            
            # 解析响应
            if isinstance(response, dict) and 'content' in response:
                result = self._parse_analysis_response(response['content'])
            elif isinstance(response, dict) and 'error' in response:
                logger.error(f"LLM调用失败: {response['error']}")
                return self._get_default_result(user_input)
            else:
                result = self._parse_analysis_response(str(response))
            
            return result
            
        except Exception as e:
            logger.error(f"需求分析失败: {str(e)}")
            return self._get_default_result(user_input)
    
    def _build_analysis_prompt(self, user_input: str) -> str:
        """构建分析提示"""
        prompt = f"""
请分析以下用户需求，并提供漏斗式筛选的子版块推荐：

用户需求：{user_input}

请按以下JSON格式返回分析结果：
{{
    "translation": "英文翻译",
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "intent": "用户意图分析",
    "funnel_candidates": {{
        "high_match": [
            {{
                "name": "子版块名称",
                "match_score": 95,
                "reason": "高度匹配理由",
                "description": "子版块描述",
                "category": "技术/商业/生活等"
            }}
        ],
        "medium_match": [
            {{
                "name": "子版块名称",
                "match_score": 80,
                "reason": "中度匹配理由",
                "description": "子版块描述",
                "category": "技术/商业/生活等"
            }}
        ],
        "low_match": [
            {{
                "name": "子版块名称",
                "match_score": 65,
                "reason": "相关匹配理由",
                "description": "子版块描述",
                "category": "技术/商业/生活等"
            }}
        ]
    }},
    "index_params": {{
        "post_limit": 30,
        "time_filter": "month",
        "reason": "参数选择理由"
    }},
    "recommended_selection": {{
        "suggested_count": 5,
        "reason": "建议选择理由",
        "strategy": "选择策略说明"
    }}
}}

要求：
1. 翻译要准确，保持原意
2. 关键词要精准，3-5个核心词汇
3. 按匹配度分为三个等级：high_match(5-8个), medium_match(8-12个), low_match(10-15个)
4. 匹配度要合理：high(85-100), medium(70-84), low(60-69)
5. 推荐理由要具体，包含分类信息
6. 参数要根据子版块类型优化
7. 提供选择建议和策略
8. **重要：子版块名称必须是英文名称，如MachineLearning、programming、selfhosted等，不要使用中文**
"""
        return prompt
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """解析大模型响应"""
        try:
            # 尝试提取JSON部分
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                # 如果没有找到JSON，使用默认结果
                return self._get_default_result("")
            
            result = json.loads(json_str)
            
            # 验证必要字段
            required_fields = ["translation", "keywords", "suggested_subreddits"]
            for field in required_fields:
                if field not in result:
                    result[field] = self._get_default_field(field)
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return self._get_default_result("")
        except Exception as e:
            logger.error(f"响应解析失败: {str(e)}")
            return self._get_default_result("")
    
    def _get_default_result(self, user_input: str) -> Dict[str, Any]:
        """获取默认结果"""
        return {
            "translation": user_input if user_input else "No translation available",
            "keywords": ["general", "discussion"],
            "intent": "General discussion request",
            "funnel_candidates": {
                "high_match": [
                    {
                        "name": "AskReddit",
                        "match_score": 85,
                        "reason": "General discussion subreddit",
                        "description": "Ask questions and discuss various topics",
                        "category": "general"
                    }
                ],
                "medium_match": [
                    {
                        "name": "discussion",
                        "match_score": 75,
                        "reason": "Open discussion platform",
                        "description": "General discussion subreddit",
                        "category": "general"
                    }
                ],
                "low_match": [
                    {
                        "name": "CasualConversation",
                        "match_score": 65,
                        "reason": "Casual discussion platform",
                        "description": "Casual conversation subreddit",
                        "category": "general"
                    }
                ]
            },
            "index_params": {
                "post_limit": 20,
                "time_filter": "week",
                "reason": "Default parameters for general subreddits"
            },
            "recommended_selection": {
                "suggested_count": 3,
                "reason": "Start with general discussion subreddits",
                "strategy": "Choose 3-5 subreddits for initial indexing"
            }
        }
    
    def _get_default_field(self, field: str) -> Any:
        """获取默认字段值"""
        defaults = {
            "translation": "Translation not available",
            "keywords": ["general"],
            "intent": "General request",
            "funnel_candidates": {
                "high_match": [],
                "medium_match": [],
                "low_match": []
            },
            "index_params": {"post_limit": 20, "time_filter": "week"},
            "recommended_selection": {"suggested_count": 3, "reason": "Default selection", "strategy": "General strategy"}
        }
        return defaults.get(field, "")

class SubredditSuggester:
    """子版块推荐器"""
    
    def __init__(self, llm_analyzer):
        """
        初始化子版块推荐器
        
        Args:
            llm_analyzer: LLM分析器实例
        """
        self.llm_analyzer = llm_analyzer
        self.popular_subreddits = self._load_popular_subreddits()
    
    def suggest_subreddits(self, demand_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        基于需求分析推荐子版块
        
        Args:
            demand_analysis: 需求分析结果
            
        Returns:
            推荐子版块列表
        """
        try:
            # 如果分析结果中已有推荐，直接返回
            if "suggested_subreddits" in demand_analysis and demand_analysis["suggested_subreddits"]:
                return demand_analysis["suggested_subreddits"]
            
            # 否则基于关键词推荐
            keywords = demand_analysis.get("keywords", [])
            return self._suggest_by_keywords(keywords)
            
        except Exception as e:
            logger.error(f"子版块推荐失败: {str(e)}")
            return self._get_default_suggestions()
    
    def _suggest_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """基于关键词推荐子版块"""
        suggestions = []
        
        # 关键词到子版块的映射
        keyword_mapping = {
            "programming": ["programming", "webdev", "learnprogramming", "coding"],
            "machine learning": ["MachineLearning", "datascience", "artificial", "deeplearning"],
            "self-hosted": ["selfhosted", "homelab", "nextcloud", "privacy"],
            "entrepreneur": ["entrepreneur", "startups", "smallbusiness", "business"],
            "technology": ["technology", "gadgets", "tech", "computers"],
            "design": ["design", "graphic_design", "web_design", "UI_Design"],
            "marketing": ["marketing", "advertising", "socialmedia", "digitalmarketing"],
            "finance": ["personalfinance", "investing", "stocks", "cryptocurrency"],
            "gaming": ["gaming", "pcgaming", "games", "gamedev"],
            "science": ["science", "askscience", "physics", "chemistry"],
            "health": ["health", "fitness", "nutrition", "mentalhealth"],
            "education": ["education", "teachers", "college", "studytips"],
            "travel": ["travel", "solotravel", "backpacking", "digitalnomad"],
            "food": ["food", "cooking", "recipes", "baking"],
            "photography": ["photography", "itookapicture", "photocritique", "analog"]
        }
        
        # 基于关键词匹配
        matched_subreddits = set()
        for keyword in keywords:
            keyword_lower = keyword.lower()
            for category, subreddits in keyword_mapping.items():
                if keyword_lower in category or category in keyword_lower:
                    matched_subreddits.update(subreddits)
        
        # 转换为推荐格式
        for subreddit in list(matched_subreddits)[:5]:
            suggestions.append({
                "name": subreddit,
                "match_score": 80,
                "reason": f"Related to keywords: {', '.join(keywords)}",
                "description": f"Discussion about {subreddit}"
            })
        
        return suggestions if suggestions else self._get_default_suggestions()
    
    def _load_popular_subreddits(self) -> List[str]:
        """加载热门子版块列表"""
        return [
            "AskReddit", "funny", "gaming", "worldnews", "todayilearned",
            "mildlyinteresting", "Showerthoughts", "explainlikeimfive",
            "programming", "webdev", "MachineLearning", "selfhosted",
            "homelab", "entrepreneur", "startups", "personalfinance",
            "technology", "science", "askscience", "photography"
        ]
    
    def _get_default_suggestions(self) -> List[Dict[str, Any]]:
        """获取默认推荐"""
        return [
            {
                "name": "AskReddit",
                "match_score": 70,
                "reason": "General discussion subreddit",
                "description": "Ask questions and discuss various topics"
            },
            {
                "name": "discussion",
                "match_score": 65,
                "reason": "Open discussion platform",
                "description": "General discussion subreddit"
            }
        ]

class IndexOptimizer:
    """索引参数优化器"""
    
    def __init__(self):
        """初始化索引优化器"""
        self.subreddit_profiles = self._load_subreddit_profiles()
    
    def optimize_params(self, subreddits: List[str]) -> Dict[str, Any]:
        """
        根据子版块类型优化索引参数
        
        Args:
            subreddits: 子版块名称列表
            
        Returns:
            优化后的参数配置
        """
        try:
            # 分析子版块特征
            total_subscribers = 0
            avg_activity = 0
            tech_subreddits = 0
            
            for subreddit in subreddits:
                profile = self.subreddit_profiles.get(subreddit.lower(), {})
                total_subscribers += profile.get("subscribers", 1000000)
                avg_activity += profile.get("activity", "medium")
                if profile.get("category") == "technology":
                    tech_subreddits += 1
            
            # 计算平均订阅者数量
            avg_subscribers = total_subscribers / len(subreddits) if subreddits else 1000000
            
            # 根据特征优化参数
            if avg_subscribers > 5000000:  # 大型子版块
                post_limit = 25
                time_filter = "week"
                reason = "Large subreddit, moderate post limit to avoid overwhelming"
            elif avg_subscribers > 1000000:  # 中型子版块
                post_limit = 35
                time_filter = "month"
                reason = "Medium-sized subreddit, good post limit for comprehensive data"
            else:  # 小型子版块
                post_limit = 50
                time_filter = "month"
                reason = "Smaller subreddit, higher post limit for better coverage"
            
            # 技术子版块特殊处理
            if tech_subreddits > len(subreddits) / 2:
                post_limit = min(post_limit + 10, 50)
                reason += " (increased for tech subreddits)"
            
            return {
                "post_limit": post_limit,
                "time_filter": time_filter,
                "reason": reason,
                "estimated_time": self._estimate_time(len(subreddits), post_limit)
            }
            
        except Exception as e:
            logger.error(f"参数优化失败: {str(e)}")
            return self._get_default_params()
    
    def _load_subreddit_profiles(self) -> Dict[str, Dict[str, Any]]:
        """加载子版块特征配置"""
        return {
            "askreddit": {"subscribers": 40000000, "activity": "high", "category": "general"},
            "funny": {"subscribers": 40000000, "activity": "high", "category": "entertainment"},
            "gaming": {"subscribers": 30000000, "activity": "high", "category": "gaming"},
            "programming": {"subscribers": 4000000, "activity": "medium", "category": "technology"},
            "webdev": {"subscribers": 1000000, "activity": "medium", "category": "technology"},
            "machinelearning": {"subscribers": 2000000, "activity": "medium", "category": "technology"},
            "selfhosted": {"subscribers": 200000, "activity": "low", "category": "technology"},
            "homelab": {"subscribers": 500000, "activity": "medium", "category": "technology"},
            "entrepreneur": {"subscribers": 1000000, "activity": "medium", "category": "business"},
            "startups": {"subscribers": 800000, "activity": "medium", "category": "business"},
            "personalfinance": {"subscribers": 15000000, "activity": "high", "category": "finance"},
            "technology": {"subscribers": 10000000, "activity": "high", "category": "technology"},
            "science": {"subscribers": 20000000, "activity": "high", "category": "science"},
            "askscience": {"subscribers": 20000000, "activity": "high", "category": "science"},
            "photography": {"subscribers": 20000000, "activity": "high", "category": "art"}
        }
    
    def _estimate_time(self, subreddit_count: int, post_limit: int) -> str:
        """估算索引时间"""
        # 每个子版块大约需要 2-5 秒
        total_seconds = subreddit_count * (post_limit * 0.1 + 2)
        
        if total_seconds < 60:
            return f"约 {int(total_seconds)} 秒"
        elif total_seconds < 3600:
            return f"约 {int(total_seconds / 60)} 分钟"
        else:
            return f"约 {int(total_seconds / 3600)} 小时"
    
    def _get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            "post_limit": 30,
            "time_filter": "month",
            "reason": "Default parameters",
            "estimated_time": "约 2-5 分钟"
        }
