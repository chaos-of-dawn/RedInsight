"""
子版块规则分析模块
分析Reddit子版块规则，提供合规建议和内容策略
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from database import DatabaseManager
from llm_analyzer import LLMAnalyzer
from reddit_scraper import RedditScraper

logger = logging.getLogger(__name__)

class SubredditRulesAnalyzer:
    """子版块规则分析器"""
    
    def __init__(self, db_manager: DatabaseManager, llm_analyzer: LLMAnalyzer, reddit_scraper: RedditScraper):
        self.db_manager = db_manager
        self.llm_analyzer = llm_analyzer
        self.reddit_scraper = reddit_scraper
    
    def analyze_subreddit_rules(self, subreddit_name: str) -> Dict[str, Any]:
        """
        分析子版块规则
        
        Args:
            subreddit_name: 子版块名称
            
        Returns:
            规则分析结果
        """
        try:
            logger.info(f"开始分析子版块规则: r/{subreddit_name}")
            
            # 1. 获取规则
            rules = self._fetch_subreddit_rules(subreddit_name)
            if not rules:
                return {"error": f"无法获取 r/{subreddit_name} 的规则"}
            
            # 2. 分析规则内容
            analysis = self._analyze_rules_content(rules, subreddit_name)
            
            # 3. 生成合规建议
            compliance_tips = self._generate_compliance_tips(analysis)
            
            # 4. 生成内容策略
            content_strategy = self._generate_content_strategy(analysis, subreddit_name)
            
            result = {
                'subreddit_name': subreddit_name,
                'rules': rules,
                'analysis': analysis,
                'compliance_tips': compliance_tips,
                'content_strategy': content_strategy,
                'analyzed_at': datetime.now().isoformat()
            }
            
            # 5. 缓存结果
            self._cache_rules_analysis(subreddit_name, result)
            
            logger.info(f"✅ 规则分析完成: r/{subreddit_name}")
            return result
            
        except Exception as e:
            logger.error(f"分析子版块规则失败: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def _fetch_subreddit_rules(self, subreddit_name: str) -> List[Dict[str, Any]]:
        """获取子版块规则"""
        try:
            # 使用RedditScraper的get_subreddit_rules方法
            return self.reddit_scraper.get_subreddit_rules(subreddit_name)
            
        except Exception as e:
            logger.error(f"获取子版块规则失败: {str(e)}")
            return []
    
    def _analyze_rules_content(self, rules: List[Dict[str, Any]], subreddit_name: str) -> Dict[str, Any]:
        """分析规则内容"""
        try:
            # 构建分析提示词
            rules_text = "\n".join([
                f"规则 {i+1}: {rule['short_name']}\n描述: {rule['description']}\n类型: {rule['kind']}\n"
                for i, rule in enumerate(rules)
            ])
            
            prompt = f"""
请分析以下Reddit子版块 r/{subreddit_name} 的规则，并提供结构化分析：

## 子版块规则
{rules_text}

## 分析要求
请从以下角度分析规则：
1. 内容要求：什么类型的内容被允许/禁止
2. 行为规范：用户行为要求
3. 格式要求：发帖格式、标签要求等
4. 常见违规：容易违反的规则
5. 社区文化：从规则推断的社区特色

## 输出格式
请以JSON格式输出分析结果：
{{
    "content_requirements": ["允许的内容类型1", "禁止的内容类型2"],
    "behavior_standards": ["行为要求1", "行为要求2"],
    "format_requirements": ["格式要求1", "格式要求2"],
    "common_violations": ["常见违规1", "常见违规2"],
    "community_culture": "社区文化特征描述",
    "strictness_level": "strict/moderate/lenient",
    "key_restrictions": ["关键限制1", "关键限制2"]
}}
"""
            
            response = self.llm_analyzer.analyze_text(prompt)
            
            # 解析响应
            analysis = self._parse_analysis_response(response)
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析规则内容失败: {str(e)}")
            return {
                "content_requirements": [],
                "behavior_standards": [],
                "format_requirements": [],
                "common_violations": [],
                "community_culture": "无法分析",
                "strictness_level": "unknown",
                "key_restrictions": []
            }
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """解析分析响应"""
        try:
            import json
            
            # 尝试解析JSON
            if response.strip().startswith('{'):
                return json.loads(response)
            
            # 如果不是JSON，返回默认结构
            return {
                "content_requirements": ["需要进一步分析"],
                "behavior_standards": ["需要进一步分析"],
                "format_requirements": ["需要进一步分析"],
                "common_violations": ["需要进一步分析"],
                "community_culture": response[:200] if response else "无法分析",
                "strictness_level": "unknown",
                "key_restrictions": ["需要进一步分析"]
            }
            
        except Exception as e:
            logger.error(f"解析分析响应失败: {str(e)}")
            return {
                "content_requirements": ["解析失败"],
                "behavior_standards": ["解析失败"],
                "format_requirements": ["解析失败"],
                "common_violations": ["解析失败"],
                "community_culture": "解析失败",
                "strictness_level": "unknown",
                "key_restrictions": ["解析失败"]
            }
    
    def _generate_compliance_tips(self, analysis: Dict[str, Any]) -> List[str]:
        """生成合规建议"""
        tips = []
        
        # 基于分析结果生成建议
        if analysis.get("strictness_level") == "strict":
            tips.append("该子版块规则较严格，建议仔细阅读所有规则后再发帖")
        
        if analysis.get("key_restrictions"):
            tips.append(f"特别注意以下限制: {', '.join(analysis['key_restrictions'][:3])}")
        
        if analysis.get("common_violations"):
            tips.append(f"避免以下常见违规: {', '.join(analysis['common_violations'][:3])}")
        
        if analysis.get("format_requirements"):
            tips.append(f"注意格式要求: {', '.join(analysis['format_requirements'][:2])}")
        
        # 通用建议
        tips.extend([
            "发帖前仔细检查标题和内容是否符合规则",
            "使用合适的标签（flair）",
            "保持友好和建设性的语调",
            "避免重复发帖或垃圾信息"
        ])
        
        return tips
    
    def _generate_content_strategy(self, analysis: Dict[str, Any], subreddit_name: str) -> Dict[str, Any]:
        """生成内容策略"""
        try:
            # 获取子版块洞察（如果存在）
            insights = self.db_manager.get_latest_business_insight()
            
            prompt = f"""
基于以下信息，为Reddit子版块 r/{subreddit_name} 生成内容策略建议：

## 规则分析
社区文化: {analysis.get('community_culture', '未知')}
严格程度: {analysis.get('strictness_level', '未知')}
内容要求: {', '.join(analysis.get('content_requirements', [])[:5])}
关键限制: {', '.join(analysis.get('key_restrictions', [])[:3])}

## 社区洞察（如果有）
{'主导主题: ' + ', '.join(insights.dominant_themes[:5]) if insights and insights.dominant_themes else '无洞察数据'}
{'主要痛点: ' + ', '.join(insights.top_pain_points[:5]) if insights and insights.top_pain_points else '无洞察数据'}

## 策略要求
请生成内容策略，包括：
1. 标题策略
2. 内容类型建议
3. 互动策略
4. 发布时间建议
5. 避免的内容类型

## 输出格式
请以JSON格式输出：
{{
    "title_strategy": ["策略1", "策略2"],
    "content_types": ["内容类型1", "内容类型2"],
    "engagement_strategy": ["互动策略1", "互动策略2"],
    "timing_suggestions": ["时间建议1", "时间建议2"],
    "avoid_content": ["避免内容1", "避免内容2"],
    "success_factors": ["成功因素1", "成功因素2"]
}}
"""
            
            response = self.llm_analyzer.analyze_text(prompt)
            
            # 解析响应
            strategy = self._parse_strategy_response(response)
            
            return strategy
            
        except Exception as e:
            logger.error(f"生成内容策略失败: {str(e)}")
            return {
                "title_strategy": ["使用清晰、描述性的标题"],
                "content_types": ["提供有价值的内容"],
                "engagement_strategy": ["积极回复评论"],
                "timing_suggestions": ["在活跃时间发帖"],
                "avoid_content": ["避免垃圾信息"],
                "success_factors": ["遵循社区规则"]
            }
    
    def _parse_strategy_response(self, response: str) -> Dict[str, Any]:
        """解析策略响应"""
        try:
            import json
            
            if response.strip().startswith('{'):
                return json.loads(response)
            
            # 如果不是JSON，返回默认策略
            return {
                "title_strategy": ["使用清晰、描述性的标题"],
                "content_types": ["提供有价值的内容"],
                "engagement_strategy": ["积极回复评论"],
                "timing_suggestions": ["在活跃时间发帖"],
                "avoid_content": ["避免垃圾信息"],
                "success_factors": ["遵循社区规则"]
            }
            
        except Exception as e:
            logger.error(f"解析策略响应失败: {str(e)}")
            return {
                "title_strategy": ["解析失败"],
                "content_types": ["解析失败"],
                "engagement_strategy": ["解析失败"],
                "timing_suggestions": ["解析失败"],
                "avoid_content": ["解析失败"],
                "success_factors": ["解析失败"]
            }
    
    def _cache_rules_analysis(self, subreddit_name: str, analysis: Dict[str, Any]) -> bool:
        """缓存规则分析结果"""
        try:
            # 这里可以保存到数据库
            # 暂时保存到文件
            import json
            import os
            
            os.makedirs('rules_cache', exist_ok=True)
            filename = f"rules_cache/{subreddit_name}_rules_analysis.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)
            
            logger.info(f"规则分析结果已缓存: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"缓存规则分析失败: {str(e)}")
            return False
    
    def get_cached_analysis(self, subreddit_name: str) -> Optional[Dict[str, Any]]:
        """获取缓存的规则分析"""
        try:
            import json
            filename = f"rules_cache/{subreddit_name}_rules_analysis.json"
            
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"获取缓存分析失败: {str(e)}")
            return None
    
    def validate_content_against_rules(self, content: Dict[str, str], subreddit_name: str) -> Dict[str, Any]:
        """
        验证内容是否符合规则
        
        Args:
            content: {'title': str, 'content': str}
            subreddit_name: 子版块名称
            
        Returns:
            验证结果
        """
        try:
            # 获取规则分析
            analysis = self.get_cached_analysis(subreddit_name)
            if not analysis:
                analysis = self.analyze_subreddit_rules(subreddit_name)
            
            validation_result = {
                'pass': True,
                'warnings': [],
                'errors': [],
                'suggestions': []
            }
            
            # 检查标题
            title = content.get('title', '')
            if len(title) > 300:
                validation_result['pass'] = False
                validation_result['errors'].append("标题过长（超过300字符）")
            
            # 检查内容
            text_content = content.get('content', '')
            if len(text_content) < 50:
                validation_result['warnings'].append("内容可能过短")
            elif len(text_content) > 40000:
                validation_result['pass'] = False
                validation_result['errors'].append("内容过长（超过40000字符）")
            
            # 基于规则分析进行更深入的检查
            if analysis.get('key_restrictions'):
                for restriction in analysis['key_restrictions']:
                    if restriction.lower() in text_content.lower():
                        validation_result['warnings'].append(f"内容可能涉及限制: {restriction}")
            
            # 添加建议
            if analysis.get('content_strategy'):
                strategy = analysis['content_strategy']
                if strategy.get('success_factors'):
                    validation_result['suggestions'].extend(strategy['success_factors'][:3])
            
            return validation_result
            
        except Exception as e:
            logger.error(f"验证内容失败: {str(e)}")
            return {
                'pass': False,
                'warnings': [],
                'errors': [f"验证失败: {str(e)}"],
                'suggestions': []
            }

