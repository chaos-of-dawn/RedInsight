"""
需求分析模块
使用大模型分析用户需求，翻译并推荐相关子版块
"""
import logging
from typing import Dict, List, Any, Tuple
import json
import re

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
            json_str = None
            
            # 方法1: 尝试提取代码块中的JSON
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                if json_end == -1:
                    # 如果没有找到结束标记，尝试找到最后一个}
                    json_end = response.rfind("}")
                    if json_end != -1:
                        json_end += 1
                if json_end > json_start:
                    json_str = response[json_start:json_end].strip()
            
            # 方法2: 尝试提取普通JSON（没有代码块）
            if not json_str and "{" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_end > json_start:
                    json_str = response[json_start:json_end]
            
            if not json_str:
                logger.warning("响应中没有找到JSON结构")
                return self._get_default_result("")
            
            # 尝试修复常见的JSON错误
            json_str = self._fix_json_string(json_str)
            
            # 尝试解析JSON
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"直接解析失败，尝试修复: {str(e)}")
                # 尝试提取部分可用的JSON
                result = self._extract_partial_json(json_str)
                if not result:
                    logger.error(f"JSON解析失败: {str(e)}")
                    logger.error(f"错误位置: 行 {e.lineno}, 列 {e.colno}")
                    logger.error(f"尝试解析的JSON文本（前500字符）: {json_str[:500]}")
                    logger.error(f"原始响应（前1000字符）: {response[:1000]}")
                    return self._get_default_result("")
            
            # 验证和补充必要字段
            if not isinstance(result, dict):
                logger.warning("解析结果不是字典类型")
                return self._get_default_result("")
            
            # 确保有基本字段
            if "translation" not in result:
                result["translation"] = "Translation not available"
            if "keywords" not in result:
                result["keywords"] = ["general"]
            if "intent" not in result:
                result["intent"] = "General request"
            
            # 确保funnel_candidates结构完整
            if "funnel_candidates" not in result:
                result["funnel_candidates"] = {
                    "high_match": [],
                    "medium_match": [],
                    "low_match": []
                }
            else:
                for match_type in ["high_match", "medium_match", "low_match"]:
                    if match_type not in result["funnel_candidates"]:
                        result["funnel_candidates"][match_type] = []
            
            return result
            
        except Exception as e:
            logger.error(f"响应解析失败: {str(e)}")
            return self._get_default_result("")
    
    def _fix_json_string(self, json_str: str) -> str:
        """尝试修复常见的JSON格式问题"""
        import re
        
        # 移除可能的BOM标记
        if json_str.startswith('\ufeff'):
            json_str = json_str[1:]
        
        # 修复缺少引号的字符串值（与llm_analyzer.py中的逻辑一致）
        # 检测 ": " 后面跟着的不是引号、数字、布尔值、null、数组或对象的情况
        i = 0
        result_chars = []
        while i < len(json_str):
            # 检查是否是 ": " 模式（键值分隔符）
            if i < len(json_str) - 2 and json_str[i:i+2] == '":':
                result_chars.append('":')
                i += 2
                # 跳过空白字符
                while i < len(json_str) and json_str[i] in [' ', '\t']:
                    result_chars.append(json_str[i])
                    i += 1
                
                if i >= len(json_str):
                    break
                
                # 检查值是否已经有引号、是数字、布尔值、null、数组或对象
                next_char = json_str[i]
                if next_char in ['"', '[', '{']:
                    # 已经有引号、数组或对象，不需要修复
                    result_chars.append(next_char)
                    i += 1
                    continue
                elif next_char.isdigit() or next_char == '-':
                    # 是数字，不需要修复
                    result_chars.append(next_char)
                    i += 1
                    continue
                elif json_str[i:i+4] == 'true' or json_str[i:i+5] == 'false' or json_str[i:i+4] == 'null':
                    # 是布尔值或null，不需要修复
                    while i < len(json_str) and json_str[i] not in [',', '}', '\n']:
                        result_chars.append(json_str[i])
                        i += 1
                    continue
                
                # 值没有引号，需要添加
                # 找到值的结束位置（下一个逗号、}，但需要处理嵌套）
                value_start = i
                value_end = i
                brace_count = 0
                bracket_count = 0
                
                while value_end < len(json_str):
                    c = json_str[value_end]
                    
                    # 不在字符串内（因为值本身没有引号）
                    if c == '{':
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count < 0:
                            # 找到了对象的结束
                            break
                    elif c == '[':
                        bracket_count += 1
                    elif c == ']':
                        bracket_count -= 1
                    elif c == ',' and brace_count == 0 and bracket_count == 0:
                        # 找到了下一个键值对的开始
                        break
                    elif c == '\n' and brace_count == 0 and bracket_count == 0:
                        # 检查下一行是否开始新的键（以"开头）
                        next_line_start = value_end + 1
                        while next_line_start < len(json_str) and json_str[next_line_start] in [' ', '\t']:
                            next_line_start += 1
                        if next_line_start < len(json_str) and json_str[next_line_start] == '"':
                            # 下一行开始新的键，当前值结束
                            break
                    
                    value_end += 1
                
                # 提取值
                value = json_str[value_start:value_end].rstrip()
                # 移除末尾可能的逗号
                trailing_comma = ''
                if value.endswith(','):
                    trailing_comma = ','
                    value = value[:-1].rstrip()
                
                # 转义值中的特殊字符
                escaped_value = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                
                # 添加引号
                result_chars.append('"')
                result_chars.append(escaped_value)
                result_chars.append('"')
                result_chars.append(trailing_comma)
                
                i = value_end
            else:
                result_chars.append(json_str[i])
                i += 1
        
        json_str = ''.join(result_chars)
        
        # 移除尾部的逗号（在最后一个对象/数组元素后）
        json_str = json_str.rstrip()
        while json_str.endswith(',') or json_str.endswith(',}'):
            json_str = json_str.rstrip(',').rstrip()
        
        return json_str
    
    def _extract_partial_json(self, json_str: str) -> Dict[str, Any]:
        """尝试从不完整的JSON中提取可用部分"""
        result = {}
        
        # 方法1: 尝试找到最后一个完整的对象
        try:
            bracket_count = 0
            last_valid_pos = -1
            in_string = False
            escape_next = False
            
            for i in range(len(json_str) - 1, -1, -1):
                char = json_str[i]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '}':
                        bracket_count += 1
                    elif char == '{':
                        bracket_count -= 1
                        if bracket_count == 0:
                            last_valid_pos = i
                            break
            
            if last_valid_pos >= 0:
                # 提取到最后一个完整对象
                partial_json = json_str[:last_valid_pos + 1]
                # 尝试修复未闭合的字符串和数组
                partial_json = self._fix_incomplete_json(partial_json)
                try:
                    parsed = json.loads(partial_json)
                    if isinstance(parsed, dict):
                        return parsed
                except:
                    pass
        except:
            pass
        
        # 方法2: 使用正则表达式提取基本字段（即使JSON不完整）
        try:
            # 提取translation（支持多行和转义字符）
            translation_pattern = r'"translation"\s*:\s*"((?:[^"\\]|\\.)*)"'
            match = re.search(translation_pattern, json_str, re.DOTALL)
            if match:
                result["translation"] = match.group(1).replace('\\"', '"').replace('\\n', '\n')
        except:
            pass
        
        try:
            # 提取keywords（支持不完整的数组）
            keywords_pattern = r'"keywords"\s*:\s*\[(.*?)\]'
            match = re.search(keywords_pattern, json_str, re.DOTALL)
            if match:
                keywords_str = match.group(1)
                # 提取所有引号内的内容
                keyword_matches = re.findall(r'"([^"]*)"', keywords_str)
                if keyword_matches:
                    result["keywords"] = keyword_matches
                else:
                    # 如果没有找到，尝试简单的分割
                    keywords = [k.strip('"\' ,') for k in keywords_str.split(',')]
                    result["keywords"] = [k.strip() for k in keywords if k.strip() and k.strip() != '']
        except:
            pass
        
        try:
            # 提取intent（支持多行）
            intent_pattern = r'"intent"\s*:\s*"((?:[^"\\]|\\.)*)"'
            match = re.search(intent_pattern, json_str, re.DOTALL)
            if match:
                result["intent"] = match.group(1).replace('\\"', '"').replace('\\n', '\n')
        except:
            pass
        
        # 如果提取到了基本字段，返回结果
        if result:
            # 确保有必要的字段
            if "translation" not in result:
                result["translation"] = "Translation not available"
            if "keywords" not in result:
                result["keywords"] = ["general"]
            if "intent" not in result:
                result["intent"] = "General request"
            
            # 添加默认的funnel_candidates结构
            result["funnel_candidates"] = {
                "high_match": [],
                "medium_match": [],
                "low_match": []
            }
            
            return result
        
        return None
    
    def _fix_incomplete_json(self, json_str: str) -> str:
        """修复不完整的JSON字符串"""
        # 移除尾部的逗号
        json_str = json_str.rstrip()
        while json_str.endswith(',') or json_str.endswith(',}') or json_str.endswith(',]'):
            json_str = json_str.rstrip(',').rstrip()
        
        # 检查未闭合的字符串
        in_string = False
        escape_next = False
        quote_count = 0
        
        for char in json_str:
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                if not in_string:
                    quote_count += 1
        
        # 如果字符串未闭合，尝试闭合它
        if in_string:
            json_str += '"'
        
        # 检查未闭合的数组
        bracket_count = json_str.count('[') - json_str.count(']')
        if bracket_count > 0:
            json_str += ']' * bracket_count
        
        # 检查未闭合的对象
        brace_count = json_str.count('{') - json_str.count('}')
        if brace_count > 0:
            json_str += '}' * brace_count
        
        return json_str
    
    
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
