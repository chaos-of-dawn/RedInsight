"""
聚类模块
使用KMeans等算法对向量化文本进行聚类分析
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class ClusterResult:
    """聚类结果"""
    cluster_id: int
    center_vector: np.ndarray
    member_indices: List[int]
    member_count: int
    avg_similarity: float
    representative_samples: List[Dict[str, Any]]
    keywords: List[str]
    dominant_sentiment: str
    avg_sentiment_score: float
    clustering_timestamp: datetime = None
    model_name: str = "kmeans"

@dataclass
class ClusteringAnalysis:
    """聚类分析结果"""
    n_clusters: int
    cluster_results: List[ClusterResult]
    silhouette_score: float
    inertia: float
    clustering_timestamp: datetime
    model_name: str

class TextClustering:
    """文本聚类器"""
    
    def __init__(self, n_clusters: int = 5, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.kmeans = None
        self.vectorizer = None
    
    def cluster_vectors(self, vectors: List[np.ndarray], vectorized_texts: List[Any] = None) -> Optional[ClusteringAnalysis]:
        """对向量进行聚类"""
        try:
            if not vectors:
                logger.warning("向量列表为空")
                return None
            
            # 转换为numpy数组
            X = np.array(vectors)
            logger.info(f"开始聚类，数据形状: {X.shape}")
            
            # 确定聚类数量
            optimal_k = self._determine_optimal_clusters(X)
            logger.info(f"使用聚类数量: {optimal_k}")
            
            # 执行KMeans聚类
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score
            
            self.kmeans = KMeans(
                n_clusters=optimal_k,
                random_state=self.random_state,
                n_init=10,
                max_iter=300
            )
            
            cluster_labels = self.kmeans.fit_predict(X)
            
            # 计算评估指标
            silhouette_avg = silhouette_score(X, cluster_labels)
            inertia = self.kmeans.inertia_
            
            logger.info(f"聚类完成 - 轮廓系数: {silhouette_avg:.3f}, 惯性: {inertia:.3f}")
            
            # 分析每个簇
            cluster_results = self._analyze_clusters(
                X, cluster_labels, vectorized_texts
            )
            
            return ClusteringAnalysis(
                n_clusters=optimal_k,
                cluster_results=cluster_results,
                silhouette_score=silhouette_avg,
                inertia=inertia,
                clustering_timestamp=datetime.now(),
                model_name="KMeans"
            )
            
        except Exception as e:
            logger.error(f"聚类失败: {str(e)}")
            return None
    
    def _determine_optimal_clusters(self, X: np.ndarray) -> int:
        """确定最优聚类数量"""
        try:
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score
            
            # 如果数据点太少，直接返回较小的聚类数
            if len(X) < 10:
                return min(3, len(X))
            
            # 尝试不同的聚类数量
            max_k = min(self.n_clusters * 2, len(X) // 2)
            k_range = range(2, max_k + 1)
            
            silhouette_scores = []
            inertias = []
            
            for k in k_range:
                kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
                cluster_labels = kmeans.fit_predict(X)
                
                if len(set(cluster_labels)) > 1:  # 确保有多个簇
                    silhouette_avg = silhouette_score(X, cluster_labels)
                    silhouette_scores.append(silhouette_avg)
                    inertias.append(kmeans.inertia_)
                else:
                    silhouette_scores.append(0)
                    inertias.append(float('inf'))
            
            # 选择轮廓系数最高的k
            if silhouette_scores:
                best_k = k_range[np.argmax(silhouette_scores)]
                logger.info(f"最优聚类数: {best_k} (轮廓系数: {max(silhouette_scores):.3f})")
                return best_k
            else:
                return min(3, len(X))
                
        except Exception as e:
            logger.warning(f"最优聚类数确定失败: {str(e)}")
            return min(self.n_clusters, len(X))
    
    def _analyze_clusters(self, X: np.ndarray, cluster_labels: np.ndarray, 
                         vectorized_texts: List[Any] = None) -> List[ClusterResult]:
        """分析每个簇的特征"""
        cluster_results = []
        
        for cluster_id in range(self.kmeans.n_clusters):
            # 获取簇成员
            member_indices = np.where(cluster_labels == cluster_id)[0]
            member_vectors = X[member_indices]
            
            if len(member_indices) == 0:
                continue
            
            # 计算簇中心
            center_vector = self.kmeans.cluster_centers_[cluster_id]
            
            # 计算平均相似度
            avg_similarity = self._calculate_avg_similarity(member_vectors, center_vector)
            
            # 获取代表样本
            representative_samples = self._get_representative_samples(
                member_indices, member_vectors, center_vector, vectorized_texts
            )
            
            # 提取关键词
            keywords = self._extract_cluster_keywords(
                member_indices, vectorized_texts
            )
            
            # 分析情感倾向
            dominant_sentiment, avg_sentiment_score = self._analyze_cluster_sentiment(
                member_indices, vectorized_texts
            )
            
            cluster_result = ClusterResult(
                cluster_id=cluster_id,
                center_vector=center_vector,
                member_indices=member_indices.tolist(),
                member_count=len(member_indices),
                avg_similarity=avg_similarity,
                representative_samples=representative_samples,
                keywords=keywords,
                dominant_sentiment=dominant_sentiment,
                avg_sentiment_score=avg_sentiment_score,
                clustering_timestamp=datetime.utcnow(),
                model_name="kmeans"
            )
            
            cluster_results.append(cluster_result)
        
        return cluster_results
    
    def _calculate_avg_similarity(self, member_vectors: np.ndarray, center_vector: np.ndarray) -> float:
        """计算簇内平均相似度"""
        try:
            similarities = []
            for vector in member_vectors:
                # 计算余弦相似度
                dot_product = np.dot(vector, center_vector)
                norm1 = np.linalg.norm(vector)
                norm2 = np.linalg.norm(center_vector)
                
                if norm1 > 0 and norm2 > 0:
                    similarity = dot_product / (norm1 * norm2)
                    similarities.append(similarity)
            
            return np.mean(similarities) if similarities else 0.0
            
        except Exception as e:
            logger.warning(f"相似度计算失败: {str(e)}")
            return 0.0
    
    def _get_representative_samples(self, member_indices: np.ndarray, member_vectors: np.ndarray,
                                  center_vector: np.ndarray, vectorized_texts: List[Any] = None) -> List[Dict[str, Any]]:
        """获取簇的代表样本"""
        try:
            # 计算每个成员到中心的距离
            distances = []
            for i, vector in enumerate(member_vectors):
                distance = np.linalg.norm(vector - center_vector)
                distances.append((member_indices[i], distance))
            
            # 按距离排序，选择最近的几个作为代表
            distances.sort(key=lambda x: x[1])
            top_samples = distances[:min(3, len(distances))]
            
            representative_samples = []
            for idx, distance in top_samples:
                sample_info = {
                    "index": int(idx),
                    "distance_to_center": float(distance)
                }
                
                if vectorized_texts and idx < len(vectorized_texts):
                    sample_info["text_id"] = getattr(vectorized_texts[idx], 'text_id', str(idx))
                    sample_info["text_preview"] = getattr(vectorized_texts[idx], 'text', '')[:200]
                
                representative_samples.append(sample_info)
            
            return representative_samples
            
        except Exception as e:
            logger.warning(f"代表样本获取失败: {str(e)}")
            return []
    
    def _extract_cluster_keywords(self, member_indices: np.ndarray, 
                                vectorized_texts: List[Any] = None) -> List[str]:
        """提取簇的关键词"""
        try:
            if not vectorized_texts:
                return []
            
            # 收集所有文本
            texts = []
            for idx in member_indices:
                if idx < len(vectorized_texts):
                    text = getattr(vectorized_texts[idx], 'text', '')
                    if text:
                        texts.append(text)
            
            if not texts:
                return []
            
            # 简单的关键词提取（可以后续优化为更复杂的方法）
            from collections import Counter
            import re
            
            # 合并所有文本
            combined_text = ' '.join(texts).lower()
            
            # 提取单词（过滤短词和常见停用词）
            words = re.findall(r'\b[a-zA-Z]{3,}\b', combined_text)
            
            # 过滤停用词
            stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'a', 'an'}
            words = [word for word in words if word not in stop_words]
            
            # 统计词频
            word_counts = Counter(words)
            
            # 返回最常见的5个词
            return [word for word, count in word_counts.most_common(5)]
            
        except Exception as e:
            logger.warning(f"关键词提取失败: {str(e)}")
            return []
    
    def _analyze_cluster_sentiment(self, member_indices: np.ndarray, 
                                 vectorized_texts: List[Any] = None) -> Tuple[str, float]:
        """分析簇的情感倾向"""
        try:
            if not vectorized_texts:
                return "neutral", 0.0
            
            sentiment_scores = []
            for idx in member_indices:
                if idx < len(vectorized_texts):
                    # 这里需要从原始抽取结果中获取情感分数
                    # 暂时返回中性
                    sentiment_scores.append(0.0)
            
            if not sentiment_scores:
                return "neutral", 0.0
            
            avg_score = np.mean(sentiment_scores)
            
            if avg_score > 0.1:
                return "positive", avg_score
            elif avg_score < -0.1:
                return "negative", avg_score
            else:
                return "neutral", avg_score
                
        except Exception as e:
            logger.warning(f"情感分析失败: {str(e)}")
            return "neutral", 0.0
    
    def predict_cluster(self, vector: np.ndarray) -> int:
        """预测单个向量的簇标签"""
        try:
            if self.kmeans is None:
                logger.error("聚类模型未训练")
                return -1
            
            return int(self.kmeans.predict([vector])[0])
            
        except Exception as e:
            logger.error(f"簇预测失败: {str(e)}")
            return -1
    
    def get_cluster_summary(self, clustering_analysis: ClusteringAnalysis) -> Dict[str, Any]:
        """获取聚类摘要"""
        try:
            summary = {
                "total_clusters": clustering_analysis.n_clusters,
                "total_samples": sum(cluster.member_count for cluster in clustering_analysis.cluster_results),
                "silhouette_score": clustering_analysis.silhouette_score,
                "inertia": clustering_analysis.inertia,
                "clusters": []
            }
            
            for cluster in clustering_analysis.cluster_results:
                cluster_info = {
                    "cluster_id": cluster.cluster_id,
                    "member_count": cluster.member_count,
                    "avg_similarity": cluster.avg_similarity,
                    "keywords": cluster.keywords,
                    "dominant_sentiment": cluster.dominant_sentiment,
                    "avg_sentiment_score": cluster.avg_sentiment_score,
                    "representative_samples": cluster.representative_samples
                }
                summary["clusters"].append(cluster_info)
            
            return summary
            
        except Exception as e:
            logger.error(f"聚类摘要生成失败: {str(e)}")
            return {}
