"""
子版块推荐模块
基于用户需求，使用向量匹配、关键词匹配和LLM分类推荐合适的Reddit子版块
"""
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from database import DatabaseManager

logger = logging.getLogger(__name__)

class SubredditRecommender:
    """子版块推荐器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.vectorizer = SentenceTransformer('all-MiniLM-L6-v2')
        
    def recommend(self, user_query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        推荐子版块
        
        Args:
            user_query: 用户需求描述
            top_k: 返回前K个推荐
            
        Returns:
            推荐结果列表，包含子版块名称、匹配度、理由
        """
        try:
            logger.info(f"开始推荐子版块，查询: {user_query}")
            
            # 1. 获取所有已索引的子版块
            all_indices = self.db_manager.get_all_subreddit_indices()
            if not all_indices:
                logger.warning("没有已索引的子版块")
                return []
            
            # 2. 向量匹配
            vector_scores = self._vector_matching(user_query, all_indices)
            
            # 3. 关键词匹配
            keyword_scores = self._keyword_matching(user_query, all_indices)
            
            # 4. 综合评分
            final_scores = self._weighted_fusion(vector_scores, keyword_scores)
            
            # 5. 排序并返回Top-K
            recommendations = sorted(final_scores, key=lambda x: x['score'], reverse=True)[:top_k]
            
            # 6. 添加推荐理由
            for rec in recommendations:
                rec['reason'] = self._generate_reason(rec, user_query, all_indices)
            
            logger.info(f"✅ 推荐完成，返回 {len(recommendations)} 个结果")
            return recommendations
            
        except Exception as e:
            logger.error(f"推荐子版块失败: {str(e)}", exc_info=True)
            return []
    
    def _vector_matching(self, query: str, indices: List[Dict]) -> List[Dict[str, float]]:
        """向量匹配"""
        try:
            # 将查询向量化
            query_vector = self.vectorizer.encode([query])[0]
            
            scores = []
            for idx in indices:
                if idx['avg_vector'] and len(idx['avg_vector']) > 0:
                    # 计算余弦相似度
                    similarity = cosine_similarity(
                        [query_vector],
                        [idx['avg_vector']]
                    )[0][0]
                    
                    scores.append({
                        'subreddit_name': idx['subreddit_name'],
                        'vector_score': float(similarity)
                    })
                else:
                    scores.append({
                        'subreddit_name': idx['subreddit_name'],
                        'vector_score': 0.0
                    })
            
            return scores
            
        except Exception as e:
            logger.error(f"向量匹配失败: {str(e)}")
            return []
    
    def _keyword_matching(self, query: str, indices: List[Dict]) -> List[Dict[str, float]]:
        """关键词匹配"""
        try:
            # 简单分词
            query_words = set(query.lower().split())
            
            scores = []
            for idx in indices:
                if idx['keywords'] and len(idx['keywords']) > 0:
                    # 计算关键词匹配度
                    keywords = set([k.lower() for k in idx['keywords']])
                    match_count = len(query_words & keywords)
                    match_score = match_count / max(len(query_words), 1)
                    
                    scores.append({
                        'subreddit_name': idx['subreddit_name'],
                        'keyword_score': float(match_score)
                    })
                else:
                    scores.append({
                        'subreddit_name': idx['subreddit_name'],
                        'keyword_score': 0.0
                    })
            
            return scores
            
        except Exception as e:
            logger.error(f"关键词匹配失败: {str(e)}")
            return []
    
    def _weighted_fusion(self, vector_scores: List[Dict], keyword_scores: List[Dict]) -> List[Dict[str, Any]]:
        """加权融合"""
        # 归一化向量分数
        if vector_scores:
            max_vector_score = max([s['vector_score'] for s in vector_scores]) or 1.0
            for s in vector_scores:
                s['normalized_vector_score'] = s['vector_score'] / max_vector_score if max_vector_score > 0 else 0
        else:
            for s in vector_scores:
                s['normalized_vector_score'] = 0
        
        # 归一化关键词分数
        if keyword_scores:
            max_keyword_score = max([s['keyword_score'] for s in keyword_scores]) or 1.0
            for s in keyword_scores:
                s['normalized_keyword_score'] = s['keyword_score'] / max_keyword_score if max_keyword_score > 0 else 0
        else:
            for s in keyword_scores:
                s['normalized_keyword_score'] = 0
        
        # 合并分数（向量70%，关键词30%）
        final_scores = []
        for i, vector_score in enumerate(vector_scores):
            keyword_score = next((s for s in keyword_scores if s['subreddit_name'] == vector_score['subreddit_name']), None)
            
            if keyword_score:
                final_score = (
                    vector_score['normalized_vector_score'] * 0.7 +
                    keyword_score['normalized_keyword_score'] * 0.3
                )
                final_scores.append({
                    'subreddit_name': vector_score['subreddit_name'],
                    'score': final_score,
                    'vector_score': vector_score['vector_score'],
                    'keyword_score': keyword_score['keyword_score']
                })
        
        return final_scores
    
    def _generate_reason(self, recommendation: Dict, query: str, indices: List[Dict]) -> str:
        """生成推荐理由"""
        subreddit_name = recommendation['subreddit_name']
        idx = next((i for i in indices if i['subreddit_name'] == subreddit_name), None)
        
        if not idx:
            return f"匹配度: {recommendation['score']:.1%}"
        
        # 找到匹配的关键词
        query_words = set(query.lower().split())
        matched_keywords = []
        if idx['keywords']:
            keywords = [k.lower() for k in idx['keywords']]
            matched_keywords = [k for k in keywords if k in query_words]
        
        # 构建理由
        reasons = []
        if matched_keywords:
            reasons.append(f"关键词匹配: {', '.join(matched_keywords[:3])}")
        
        if idx['main_topics']:
            reasons.append(f"主要话题: {', '.join(idx['main_topics'][:3])}")
        
        if idx['subscriber_count'] > 0:
            reasons.append(f"订阅者: {idx['subscriber_count']:,}")
        
        base_reason = f"匹配度: {recommendation['score']:.0%}"
        if reasons:
            return base_reason + " | " + " | ".join(reasons)
        
        return base_reason
    
    def get_subreddit_details(self, subreddit_name: str) -> Optional[Dict[str, Any]]:
        """获取子版块详细信息"""
        return self.db_manager.get_subreddit_index(subreddit_name)

