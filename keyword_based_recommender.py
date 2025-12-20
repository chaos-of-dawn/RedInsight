"""
基于关键词抓取数据的子版块推荐器
分析本地已抓取的关键词数据，推荐讨论热度最高的子版块
"""
import logging
from typing import List, Dict, Any, Optional
from database import DatabaseManager

logger = logging.getLogger(__name__)

class KeywordBasedRecommender:
    """基于关键词数据的子版块推荐器"""
    
    def __init__(self, db_manager: DatabaseManager, llm_analyzer=None):
        """
        初始化推荐器
        
        Args:
            db_manager: 数据库管理器
            llm_analyzer: LLM分析器（可选，用于生成AI推荐理由）
        """
        self.db_manager = db_manager
        self.llm_analyzer = llm_analyzer
    
    def get_available_keywords(self) -> List[str]:
        """
        获取所有可用的搜索关键词
        
        Returns:
            搜索关键词列表
        """
        try:
            keywords = self.db_manager.get_all_search_queries()
            logger.info(f"找到 {len(keywords)} 个可用的搜索关键词")
            return keywords
        except Exception as e:
            logger.error(f"获取搜索关键词失败: {str(e)}")
            return []
    
    def analyze_and_recommend(self, search_query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        分析指定关键词的热度并推荐子版块
        
        Args:
            search_query: 搜索关键词
            top_k: 返回前K个推荐
            
        Returns:
            推荐结果列表，包含子版块名称、热度评分、统计信息、推荐理由等
        """
        try:
            logger.info(f"开始分析关键词 '{search_query}' 的子版块热度")
            
            # 1. 获取热度分析结果
            heat_analysis = self.db_manager.analyze_subreddit_heat_by_keyword(search_query)
            
            if not heat_analysis:
                logger.warning(f"关键词 '{search_query}' 没有找到相关数据")
                return []
            
            # 2. 获取前K个最热门的子版块
            top_subreddits = heat_analysis[:top_k]
            
            # 3. 生成推荐结果（包含AI分析）
            recommendations = []
            for i, subreddit_data in enumerate(top_subreddits):
                recommendation = {
                    'rank': i + 1,
                    'subreddit': subreddit_data['subreddit'],
                    'heat_score': subreddit_data['heat_score'],
                    'post_count': subreddit_data['post_count'],
                    'avg_score': subreddit_data['avg_score'],
                    'total_score': subreddit_data['total_score'],
                    'avg_comments': subreddit_data['avg_comments'],
                    'total_comments': subreddit_data['total_comments'],
                    'match_score': min(100, int(subreddit_data['heat_score'])),  # 转换为匹配度
                    'reason': self._generate_reason(subreddit_data, search_query),
                    'category': self._infer_category(subreddit_data['subreddit']),
                    'description': f"关于 '{search_query}' 的讨论热度: {subreddit_data['heat_score']:.1f}分"
                }
                recommendations.append(recommendation)
            
            logger.info(f"✅ 关键词 '{search_query}' 推荐完成，返回 {len(recommendations)} 个结果")
            return recommendations
            
        except Exception as e:
            logger.error(f"分析并推荐失败: {str(e)}", exc_info=True)
            return []
    
    def _generate_reason(self, subreddit_data: Dict[str, Any], search_query: str) -> str:
        """
        生成推荐理由
        
        Args:
            subreddit_data: 子版块统计数据
            search_query: 搜索关键词
            
        Returns:
            推荐理由文本
        """
        reasons = []
        
        # 基于统计数据的理由
        if subreddit_data['post_count'] > 0:
            reasons.append(f"找到 {subreddit_data['post_count']} 个相关帖子")
        
        if subreddit_data['avg_score'] > 10:
            reasons.append(f"平均分数 {subreddit_data['avg_score']:.0f} 分")
        
        if subreddit_data['avg_comments'] > 5:
            reasons.append(f"平均评论数 {subreddit_data['avg_comments']:.0f} 条")
        
        if subreddit_data['heat_score'] > 50:
            reasons.append("讨论热度高")
        elif subreddit_data['heat_score'] > 30:
            reasons.append("讨论热度中等")
        else:
            reasons.append("有一定讨论")
        
        base_reason = f"r/{subreddit_data['subreddit']} 在关键词 '{search_query}' 下的讨论"
        if reasons:
            return base_reason + " | " + " | ".join(reasons)
        
        return base_reason
    
    def _infer_category(self, subreddit_name: str) -> str:
        """
        推断子版块分类
        
        Args:
            subreddit_name: 子版块名称
            
        Returns:
            分类名称
        """
        subreddit_lower = subreddit_name.lower()
        
        # 技术类
        tech_keywords = ['tech', 'programming', 'coding', 'dev', 'software', 'code', 'computer', 'ai', 'ml', 'data']
        if any(kw in subreddit_lower for kw in tech_keywords):
            return "技术/编程"
        
        # 商业类
        business_keywords = ['business', 'entrepreneur', 'startup', 'finance', 'invest', 'money', 'market']
        if any(kw in subreddit_lower for kw in business_keywords):
            return "商业/金融"
        
        # 生活类
        life_keywords = ['life', 'lifestyle', 'food', 'travel', 'health', 'fitness', 'home']
        if any(kw in subreddit_lower for kw in life_keywords):
            return "生活/娱乐"
        
        # 游戏类
        gaming_keywords = ['game', 'gaming', 'play', 'gamer']
        if any(kw in subreddit_lower for kw in gaming_keywords):
            return "游戏"
        
        # 科学类
        science_keywords = ['science', 'research', 'study', 'learn', 'education']
        if any(kw in subreddit_lower for kw in science_keywords):
            return "科学/教育"
        
        return "其他"
    
    def generate_ai_recommendation(self, search_query: str, recommendations: List[Dict[str, Any]]) -> Optional[str]:
        """
        使用AI生成更详细的推荐分析
        
        Args:
            search_query: 搜索关键词
            recommendations: 推荐结果列表
            
        Returns:
            AI生成的推荐分析文本
        """
        if not self.llm_analyzer or not recommendations:
            return None
        
        try:
            # 构建提示词
            top_3 = recommendations[:3]
            subreddit_summary = "\n".join([
                f"- r/{r['subreddit']}: {r['post_count']}个帖子, 平均分数{r['avg_score']:.0f}, 热度{r['heat_score']:.1f}分"
                for r in top_3
            ])
            
            prompt = f"""
基于以下关键词抓取的本地数据，分析并推荐最适合讨论该关键词的子版块：

关键词：{search_query}

热度分析结果（前3名）：
{subreddit_summary}

请提供：
1. 简要分析为什么这些子版块讨论该关键词的热度较高
2. 推荐策略：应该优先选择哪些子版块，为什么
3. 注意事项：在选择这些子版块时需要注意什么

请用中文回答，简洁明了。
"""
            
            # 调用LLM分析
            response = self.llm_analyzer._call_llm(prompt, "deepseek", "keyword_recommendation")
            
            if isinstance(response, dict) and 'content' in response:
                return response['content']
            elif isinstance(response, str):
                return response
            else:
                return None
                
        except Exception as e:
            logger.error(f"生成AI推荐分析失败: {str(e)}")
            return None































