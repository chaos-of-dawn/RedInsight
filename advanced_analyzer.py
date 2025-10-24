"""
高级分析器
整合结构化抽取、向量化、聚类和洞察生成功能
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from structured_extractor import StructuredExtractor, StructuredExtraction
from vectorizer import TextVectorizer, VectorizedText
from clustering import TextClustering, ClusteringAnalysis
from insights_generator import InsightsGenerator, BusinessInsight
from database import DatabaseManager
from llm_analyzer import LLMAnalyzer

logger = logging.getLogger(__name__)

class AdvancedAnalyzer:
    """高级分析器 - 整合所有分析功能"""
    
    def __init__(self, db_manager: DatabaseManager, llm_analyzer: LLMAnalyzer, provider: str = "openai"):
        self.db_manager = db_manager
        self.llm_analyzer = llm_analyzer
        self.provider = provider
        
        # 初始化各个组件
        self.structured_extractor = StructuredExtractor(llm_analyzer)
        self.vectorizer = TextVectorizer()
        self.clustering = TextClustering()
        self.insights_generator = InsightsGenerator(llm_analyzer, provider)
    
    def run_full_analysis(self, subreddits: List[str] = None, limit: int = None) -> Dict[str, Any]:
        """运行完整的分析流程"""
        try:
            analysis_id = str(uuid.uuid4())
            logger.info(f"开始高级分析流程，分析ID: {analysis_id}")
            
            # 1. 获取帖子数据
            posts = self.db_manager.get_posts(limit=limit, subreddits=subreddits)
            if not posts:
                return {"error": "没有找到可分析的帖子数据"}
            
            logger.info(f"找到 {len(posts)} 个帖子，开始结构化抽取...")
            
            # 2. 结构化抽取
            logger.info("开始结构化抽取，这可能需要较长时间...")
            extractions = self._run_structured_extraction(posts, self.provider)
            if not extractions:
                return {"error": "结构化抽取失败"}
            
            logger.info(f"结构化抽取完成，成功 {len(extractions)} 条")
            
            # 3. 向量化
            logger.info("开始向量化...")
            vectorized_texts = self._run_vectorization(extractions)
            if not vectorized_texts:
                return {"error": "向量化失败"}
            
            logger.info(f"向量化完成，成功 {len(vectorized_texts)} 条")
            
            # 4. 聚类
            logger.info("开始聚类分析...")
            clustering_analysis = self._run_clustering(vectorized_texts, extractions)
            if not clustering_analysis:
                return {"error": "聚类分析失败"}
            
            logger.info(f"聚类完成，生成 {clustering_analysis.n_clusters} 个簇")
            
            # 5. 洞察生成
            logger.info("开始生成业务洞察...")
            business_insight = self._run_insights_generation(clustering_analysis, extractions)
            if not business_insight:
                return {"error": "洞察生成失败"}
            
            logger.info("业务洞察生成完成")
            
            # 6. 保存结果到数据库
            self._save_analysis_results(analysis_id, extractions, vectorized_texts, 
                                      clustering_analysis, business_insight)
            
            # 7. 导出结果
            export_path = self._export_results(analysis_id, business_insight)
            
            return {
                "success": True,
                "analysis_id": analysis_id,
                "total_posts": len(posts),
                "extractions_count": len(extractions),
                "clusters_count": clustering_analysis.n_clusters,
                "silhouette_score": clustering_analysis.silhouette_score,
                "export_path": export_path,
                "insights_summary": {
                    "overall_sentiment": business_insight.overall_sentiment,
                    "dominant_themes": business_insight.dominant_themes,
                    "top_pain_points": business_insight.top_pain_points,
                    "key_opportunities": business_insight.key_opportunities
                }
            }
            
        except Exception as e:
            logger.error(f"高级分析流程失败: {str(e)}")
            return {"error": f"分析流程失败: {str(e)}"}
    
    def _run_structured_extraction(self, posts: List[Any], provider: str) -> List[StructuredExtraction]:
        """运行结构化抽取"""
        try:
            # 转换帖子数据为字典格式
            posts_data = []
            for post in posts:
                post_dict = {
                    'id': post.id,
                    'title': post.title,
                    'selftext': post.selftext,
                    'author': post.author,
                    'subreddit': post.subreddit,
                    'created_utc': post.created_utc,
                    'score': post.score,
                    'upvote_ratio': post.upvote_ratio
                }
                posts_data.append(post_dict)
            
            # 批量抽取
            extractions = self.structured_extractor.extract_batch(posts_data, provider)
            
            # 保存到数据库
            for extraction in extractions:
                self.db_manager.save_structured_extraction(extraction)
            
            return extractions
            
        except Exception as e:
            logger.error(f"结构化抽取失败: {str(e)}")
            return []
    
    def _run_vectorization(self, extractions: List[StructuredExtraction]) -> List[VectorizedText]:
        """运行向量化"""
        try:
            # 向量化抽取结果
            vectorized_texts = self.vectorizer.vectorize_extractions(extractions)
            
            # 保存到数据库
            save_success_count = 0
            for vt in vectorized_texts:
                if self.db_manager.save_vectorized_text(vt):
                    save_success_count += 1
                else:
                    logger.warning(f"向量化文本保存失败: {vt.text_id}")
            
            logger.info(f"向量化完成: {len(vectorized_texts)} 条，成功保存 {save_success_count} 条到数据库")
            return vectorized_texts
            
        except Exception as e:
            logger.error(f"向量化失败: {str(e)}")
            return []
    
    def _run_clustering(self, vectorized_texts: List[VectorizedText], 
                       extractions: List[StructuredExtraction]) -> Optional[ClusteringAnalysis]:
        """运行聚类分析"""
        try:
            # 提取向量
            vectors = [vt.vector for vt in vectorized_texts]
            
            # 执行聚类
            clustering_analysis = self.clustering.cluster_vectors(vectors, vectorized_texts)
            
            if clustering_analysis:
                # 保存聚类结果到数据库
                for cluster_result in clustering_analysis.cluster_results:
                    self.db_manager.save_clustering_result(
                        f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
                        cluster_result
                    )
            
            return clustering_analysis
            
        except Exception as e:
            logger.error(f"聚类分析失败: {str(e)}")
            return None
    
    def _run_insights_generation(self, clustering_analysis: ClusteringAnalysis, 
                                extractions: List[StructuredExtraction]) -> Optional[BusinessInsight]:
        """运行洞察生成"""
        try:
            # 生成业务洞察
            business_insight = self.insights_generator.generate_insights(
                clustering_analysis, extractions
            )
            
            if business_insight:
                # 保存到数据库
                analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.db_manager.save_business_insight(analysis_id, business_insight)
            
            return business_insight
            
        except Exception as e:
            logger.error(f"洞察生成失败: {str(e)}")
            return None
    
    def _save_analysis_results(self, analysis_id: str, extractions: List[StructuredExtraction],
                              vectorized_texts: List[VectorizedText], 
                              clustering_analysis: ClusteringAnalysis,
                              business_insight: BusinessInsight):
        """保存分析结果到数据库"""
        try:
            # 保存聚类结果
            for cluster_result in clustering_analysis.cluster_results:
                self.db_manager.save_clustering_result(analysis_id, cluster_result)
            
            # 保存业务洞察
            self.db_manager.save_business_insight(analysis_id, business_insight)
            
            logger.info(f"分析结果已保存到数据库，分析ID: {analysis_id}")
            
        except Exception as e:
            logger.error(f"保存分析结果失败: {str(e)}")
    
    def _export_results(self, analysis_id: str, business_insight: BusinessInsight) -> str:
        """导出分析结果"""
        try:
            # 生成导出文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 导出JSON格式
            json_filename = f"business_insights_{analysis_id}_{timestamp}.json"
            json_file_path = f"./output/{json_filename}"
            json_success = self.insights_generator.export_insights_to_json(business_insight, json_file_path)
            
            # 导出可读文本格式
            text_filename = f"business_insights_{analysis_id}_{timestamp}.txt"
            text_file_path = f"./output/{text_filename}"
            text_success = self.insights_generator.export_insights_to_text(business_insight, text_file_path)
            
            if json_success and text_success:
                logger.info(f"洞察报告已导出到: {json_file_path} 和 {text_file_path}")
                return f"{json_file_path}, {text_file_path}"
            elif json_success:
                logger.info(f"JSON洞察报告已导出到: {json_file_path}")
                return json_file_path
            elif text_success:
                logger.info(f"可读洞察报告已导出到: {text_file_path}")
                return text_file_path
            else:
                logger.warning("洞察报告导出失败")
                return ""
                
        except Exception as e:
            logger.error(f"导出结果失败: {str(e)}")
            return ""
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        try:
            # 获取最新的业务洞察
            latest_insight = self.db_manager.get_latest_business_insight()
            
            if not latest_insight:
                return {"error": "没有找到分析结果"}
            
            return {
                "analysis_timestamp": latest_insight.analysis_timestamp.isoformat(),
                "total_clusters": latest_insight.total_clusters,
                "total_samples": latest_insight.total_samples,
                "overall_sentiment": latest_insight.overall_sentiment,
                "dominant_themes": latest_insight.dominant_themes,
                "top_pain_points": latest_insight.top_pain_points,
                "key_opportunities": latest_insight.key_opportunities,
                "strategic_recommendations": latest_insight.strategic_recommendations
            }
            
        except Exception as e:
            logger.error(f"获取分析摘要失败: {str(e)}")
            return {"error": f"获取分析摘要失败: {str(e)}"}
    
    def run_quick_analysis(self, subreddits: List[str] = None, limit: int = 50) -> Dict[str, Any]:
        """运行快速分析（使用较少数据）"""
        return self.run_full_analysis(subreddits=subreddits, limit=limit)
    
    def run_comprehensive_analysis(self, subreddits: List[str] = None, limit: int = 500) -> Dict[str, Any]:
        """运行全面分析（使用更多数据）"""
        return self.run_full_analysis(subreddits=subreddits, limit=limit)
