"""
洞察生成模块
基于聚类结果生成业务洞察和行动建议
"""

import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ClusterInsight:
    """单个簇的洞察"""
    cluster_id: int
    cluster_name: str
    key_insights: List[str]
    pain_points: List[str]
    opportunities: List[str]
    recommended_actions: List[str]
    priority_score: float
    confidence_level: str

@dataclass
class BusinessInsight:
    """业务洞察报告"""
    analysis_timestamp: datetime
    total_clusters: int
    total_samples: int
    overall_sentiment: str
    dominant_themes: List[str]
    top_pain_points: List[str]
    key_opportunities: List[str]
    strategic_recommendations: List[str]
    cluster_insights: List[ClusterInsight]
    action_priority_matrix: List[Dict[str, Any]]
    model_name: str = "insights_generator"

class InsightsGenerator:
    """洞察生成器"""
    
    def __init__(self, llm_analyzer, provider: str = "openai"):
        self.llm_analyzer = llm_analyzer
        self.provider = provider
    
    def generate_insights(self, clustering_analysis: Any, extractions: List[Any] = None) -> Optional[BusinessInsight]:
        """生成业务洞察"""
        try:
            logger.info("开始生成业务洞察...")
            
            # 生成整体洞察
            overall_insights = self._generate_overall_insights(clustering_analysis, extractions)
            
            # 生成簇级洞察
            cluster_insights = self._generate_cluster_insights(clustering_analysis, extractions)
            
            # 生成行动优先级矩阵
            action_matrix = self._generate_action_priority_matrix(cluster_insights)
            
            # 创建业务洞察报告
            business_insight = BusinessInsight(
                analysis_timestamp=datetime.now(),
                total_clusters=clustering_analysis.n_clusters,
                total_samples=sum(cluster.member_count for cluster in clustering_analysis.cluster_results),
                overall_sentiment=overall_insights.get('overall_sentiment', 'neutral'),
                dominant_themes=overall_insights.get('dominant_themes', []),
                top_pain_points=overall_insights.get('top_pain_points', []),
                key_opportunities=overall_insights.get('key_opportunities', []),
                strategic_recommendations=overall_insights.get('strategic_recommendations', []),
                cluster_insights=cluster_insights,
                action_priority_matrix=action_matrix
            )
            
            logger.info("业务洞察生成完成")
            return business_insight
            
        except Exception as e:
            logger.error(f"洞察生成失败: {str(e)}")
            return None
    
    def _generate_overall_insights(self, clustering_analysis: Any, extractions: List[Any] = None) -> Dict[str, Any]:
        """生成整体洞察"""
        try:
            # 准备整体分析数据
            analysis_data = self._prepare_overall_analysis_data(clustering_analysis, extractions)
            
            # 构建提示词
            prompt = self._build_overall_insights_prompt(analysis_data)
            
            # 调用LLM生成洞察
            result = self.llm_analyzer._call_llm(
                prompt=prompt,
                provider=self.provider,
                analysis_type="business_insights"
            )
            
            if "error" in result:
                logger.error(f"整体洞察生成失败: {result['error']}")
                return self._get_default_overall_insights()
            
            # 解析结果
            insights = self._parse_insights_result(result.get('content', ''))
            return insights
            
        except Exception as e:
            logger.error(f"整体洞察生成异常: {str(e)}")
            return self._get_default_overall_insights()
    
    def _generate_cluster_insights(self, clustering_analysis: Any, extractions: List[Any] = None) -> List[ClusterInsight]:
        """生成簇级洞察"""
        cluster_insights = []
        
        for cluster in clustering_analysis.cluster_results:
            try:
                # 准备簇分析数据
                cluster_data = self._prepare_cluster_analysis_data(cluster, extractions)
                
                # 构建提示词
                prompt = self._build_cluster_insights_prompt(cluster_data)
                
                # 调用LLM生成洞察
                result = self.llm_analyzer._call_llm(
                    prompt=prompt,
                    provider=self.provider,
                    analysis_type="cluster_insights"
                )
                
                if "error" in result:
                    logger.warning(f"簇 {cluster.cluster_id} 洞察生成失败: {result['error']}")
                    cluster_insight = self._get_default_cluster_insight(cluster)
                else:
                    # 解析结果
                    insights_data = self._parse_cluster_insights_result(result.get('content', ''))
                    cluster_insight = self._create_cluster_insight(cluster, insights_data)
                
                cluster_insights.append(cluster_insight)
                
            except Exception as e:
                logger.error(f"簇 {cluster.cluster_id} 洞察生成异常: {str(e)}")
                cluster_insights.append(self._get_default_cluster_insight(cluster))
        
        return cluster_insights
    
    def _prepare_overall_analysis_data(self, clustering_analysis: Any, extractions: List[Any] = None) -> Dict[str, Any]:
        """准备整体分析数据"""
        data = {
            "total_clusters": clustering_analysis.n_clusters,
            "total_samples": sum(cluster.member_count for cluster in clustering_analysis.cluster_results),
            "silhouette_score": clustering_analysis.silhouette_score,
            "clusters": []
        }
        
        for cluster in clustering_analysis.cluster_results:
            cluster_info = {
                "cluster_id": cluster.cluster_id,
                "member_count": cluster.member_count,
                "keywords": cluster.keywords,
                "dominant_sentiment": cluster.dominant_sentiment,
                "avg_sentiment_score": cluster.avg_sentiment_score,
                "representative_samples": cluster.representative_samples
            }
            data["clusters"].append(cluster_info)
        
        return data
    
    def _prepare_cluster_analysis_data(self, cluster: Any, extractions: List[Any] = None) -> Dict[str, Any]:
        """准备簇分析数据"""
        return {
            "cluster_id": cluster.cluster_id,
            "member_count": cluster.member_count,
            "keywords": cluster.keywords,
            "dominant_sentiment": cluster.dominant_sentiment,
            "avg_sentiment_score": cluster.avg_sentiment_score,
            "representative_samples": cluster.representative_samples,
            "avg_similarity": cluster.avg_similarity
        }
    
    def _build_overall_insights_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """构建整体洞察提示词"""
        return f"""你是一位专业的商业分析师，需要基于Reddit社区讨论的聚类分析结果生成业务洞察。

## 分析数据
- 总簇数: {analysis_data['total_clusters']}
- 总样本数: {analysis_data['total_samples']}
- 聚类质量(轮廓系数): {analysis_data['silhouette_score']:.3f}

## 各簇特征
{self._format_clusters_for_prompt(analysis_data['clusters'])}

请基于以上数据生成以下洞察，并以JSON格式输出：

1. overall_sentiment: 整体情感倾向 (positive/negative/neutral/mixed)
2. dominant_themes: 主导主题列表 (最多5个)
3. top_pain_points: 主要痛点列表 (最多5个)
4. key_opportunities: 关键机会列表 (最多5个)
5. strategic_recommendations: 战略建议列表 (最多5个)

JSON格式：
{{
    "overall_sentiment": "整体情感",
    "dominant_themes": ["主题1", "主题2"],
    "top_pain_points": ["痛点1", "痛点2"],
    "key_opportunities": ["机会1", "机会2"],
    "strategic_recommendations": ["建议1", "建议2"]
}}"""
    
    def _build_cluster_insights_prompt(self, cluster_data: Dict[str, Any]) -> str:
        """构建簇洞察提示词"""
        return f"""你是一位专业的商业分析师，需要为以下Reddit讨论簇生成深度洞察。

## 簇信息
- 簇ID: {cluster_data['cluster_id']}
- 样本数量: {cluster_data['member_count']}
- 关键词: {', '.join(cluster_data['keywords'])}
- 主导情感: {cluster_data['dominant_sentiment']}
- 情感强度: {cluster_data['avg_sentiment_score']:.2f}

## 代表样本
{self._format_samples_for_prompt(cluster_data['representative_samples'])}

请基于以上信息生成以下洞察，并以JSON格式输出：

1. cluster_name: 簇的简洁名称
2. key_insights: 关键洞察列表 (最多3个)
3. pain_points: 痛点列表 (最多3个)
4. opportunities: 机会列表 (最多3个)
5. recommended_actions: 建议行动列表 (最多3个)
6. priority_score: 优先级分数 (0-10)
7. confidence_level: 置信度 (high/medium/low)

JSON格式：
{{
    "cluster_name": "簇名称",
    "key_insights": ["洞察1", "洞察2"],
    "pain_points": ["痛点1", "痛点2"],
    "opportunities": ["机会1", "机会2"],
    "recommended_actions": ["行动1", "行动2"],
    "priority_score": 8.5,
    "confidence_level": "high"
}}"""
    
    def _format_clusters_for_prompt(self, clusters: List[Dict[str, Any]]) -> str:
        """格式化簇信息用于提示词"""
        formatted = []
        for cluster in clusters:
            formatted.append(f"""
簇 {cluster['cluster_id']}:
- 样本数: {cluster['member_count']}
- 关键词: {', '.join(cluster['keywords'])}
- 情感: {cluster['dominant_sentiment']} ({cluster['avg_sentiment_score']:.2f})
""")
        return '\n'.join(formatted)
    
    def _format_samples_for_prompt(self, samples: List[Dict[str, Any]]) -> str:
        """格式化样本信息用于提示词"""
        formatted = []
        for i, sample in enumerate(samples[:3]):  # 最多显示3个样本
            text_preview = sample.get('text_preview', '')[:100]
            formatted.append(f"样本 {i+1}: {text_preview}...")
        return '\n'.join(formatted)
    
    def _parse_insights_result(self, content: str) -> Dict[str, Any]:
        """解析整体洞察结果"""
        try:
            # 尝试解析JSON
            if content.strip().startswith('{'):
                return json.loads(content.strip())
            
            # 尝试从代码块中提取JSON
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # 尝试查找JSON对象
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            logger.warning(f"无法解析整体洞察JSON: {content[:200]}...")
            return self._get_default_overall_insights()
            
        except json.JSONDecodeError as e:
            logger.error(f"整体洞察JSON解析失败: {str(e)}")
            return self._get_default_overall_insights()
    
    def _parse_cluster_insights_result(self, content: str) -> Dict[str, Any]:
        """解析簇洞察结果"""
        try:
            # 尝试解析JSON
            if content.strip().startswith('{'):
                return json.loads(content.strip())
            
            # 尝试从代码块中提取JSON
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # 尝试查找JSON对象
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            logger.warning(f"无法解析簇洞察JSON: {content[:200]}...")
            return self._get_default_cluster_insights_data()
            
        except json.JSONDecodeError as e:
            logger.error(f"簇洞察JSON解析失败: {str(e)}")
            return self._get_default_cluster_insights_data()
    
    def _create_cluster_insight(self, cluster: Any, insights_data: Dict[str, Any]) -> ClusterInsight:
        """创建簇洞察对象"""
        return ClusterInsight(
            cluster_id=cluster.cluster_id,
            cluster_name=insights_data.get('cluster_name', f'簇 {cluster.cluster_id}'),
            key_insights=insights_data.get('key_insights', []),
            pain_points=insights_data.get('pain_points', []),
            opportunities=insights_data.get('opportunities', []),
            recommended_actions=insights_data.get('recommended_actions', []),
            priority_score=float(insights_data.get('priority_score', 5.0)),
            confidence_level=insights_data.get('confidence_level', 'medium')
        )
    
    def _generate_action_priority_matrix(self, cluster_insights: List[ClusterInsight]) -> List[Dict[str, Any]]:
        """生成行动优先级矩阵"""
        matrix = []
        
        for insight in cluster_insights:
            for action in insight.recommended_actions:
                matrix.append({
                    "action": action,
                    "cluster_id": insight.cluster_id,
                    "cluster_name": insight.cluster_name,
                    "priority_score": insight.priority_score,
                    "confidence_level": insight.confidence_level,
                    "related_insights": insight.key_insights
                })
        
        # 按优先级排序
        matrix.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return matrix
    
    def _get_default_overall_insights(self) -> Dict[str, Any]:
        """获取默认整体洞察"""
        return {
            "overall_sentiment": "neutral",
            "dominant_themes": ["主题分析中"],
            "top_pain_points": ["痛点分析中"],
            "key_opportunities": ["机会分析中"],
            "strategic_recommendations": ["建议分析中"]
        }
    
    def _get_default_cluster_insights_data(self) -> Dict[str, Any]:
        """获取默认簇洞察数据"""
        return {
            "cluster_name": "分析中",
            "key_insights": ["洞察分析中"],
            "pain_points": ["痛点分析中"],
            "opportunities": ["机会分析中"],
            "recommended_actions": ["行动分析中"],
            "priority_score": 5.0,
            "confidence_level": "medium"
        }
    
    def _get_default_cluster_insight(self, cluster: Any) -> ClusterInsight:
        """获取默认簇洞察"""
        return ClusterInsight(
            cluster_id=cluster.cluster_id,
            cluster_name=f'簇 {cluster.cluster_id}',
            key_insights=[f"基于关键词 {', '.join(cluster.keywords[:3])} 的讨论"],
            pain_points=["需要进一步分析"],
            opportunities=["需要进一步分析"],
            recommended_actions=["需要进一步分析"],
            priority_score=5.0,
            confidence_level="low"
        )
    
    def export_insights_to_json(self, business_insight: BusinessInsight, file_path: str) -> bool:
        """导出洞察为JSON文件"""
        try:
            # 转换为可序列化的字典
            insights_dict = {
                "analysis_timestamp": business_insight.analysis_timestamp.isoformat(),
                "total_clusters": business_insight.total_clusters,
                "total_samples": business_insight.total_samples,
                "overall_sentiment": business_insight.overall_sentiment,
                "dominant_themes": business_insight.dominant_themes,
                "top_pain_points": business_insight.top_pain_points,
                "key_opportunities": business_insight.key_opportunities,
                "strategic_recommendations": business_insight.strategic_recommendations,
                "cluster_insights": [
                    {
                        "cluster_id": insight.cluster_id,
                        "cluster_name": insight.cluster_name,
                        "key_insights": insight.key_insights,
                        "pain_points": insight.pain_points,
                        "opportunities": insight.opportunities,
                        "recommended_actions": insight.recommended_actions,
                        "priority_score": insight.priority_score,
                        "confidence_level": insight.confidence_level
                    }
                    for insight in business_insight.cluster_insights
                ],
                "action_priority_matrix": business_insight.action_priority_matrix
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(insights_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"洞察报告已导出到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"洞察导出失败: {str(e)}")
            return False
    
    def generate_readable_report(self, business_insight: BusinessInsight) -> str:
        """生成可读的洞察报告文本"""
        try:
            report = []
            
            # 报告标题
            report.append("=" * 80)
            report.append("🔍 RedInsight 高级分析洞察报告")
            report.append("=" * 80)
            report.append("")
            
            # 分析概览
            report.append("📊 分析概览")
            report.append("-" * 40)
            report.append(f"分析时间: {business_insight.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"总簇数: {business_insight.total_clusters}")
            report.append(f"总样本数: {business_insight.total_samples}")
            report.append(f"整体情感倾向: {business_insight.overall_sentiment}")
            report.append("")
            
            # 主导主题
            if business_insight.dominant_themes:
                report.append("🎯 主导主题")
                report.append("-" * 40)
                for i, theme in enumerate(business_insight.dominant_themes, 1):
                    report.append(f"{i}. {theme}")
                report.append("")
            
            # 主要痛点
            if business_insight.top_pain_points:
                report.append("⚠️ 主要痛点")
                report.append("-" * 40)
                for i, pain in enumerate(business_insight.top_pain_points, 1):
                    report.append(f"{i}. {pain}")
                report.append("")
            
            # 关键机会
            if business_insight.key_opportunities:
                report.append("💡 关键机会")
                report.append("-" * 40)
                for i, opportunity in enumerate(business_insight.key_opportunities, 1):
                    report.append(f"{i}. {opportunity}")
                report.append("")
            
            # 战略建议
            if business_insight.strategic_recommendations:
                report.append("🚀 战略建议")
                report.append("-" * 40)
                for i, recommendation in enumerate(business_insight.strategic_recommendations, 1):
                    report.append(f"{i}. {recommendation}")
                report.append("")
            
            # 各簇详细洞察
            if business_insight.cluster_insights:
                report.append("🔬 各簇详细洞察")
                report.append("=" * 80)
                
                for insight in business_insight.cluster_insights:
                    report.append(f"\n📋 簇 {insight.cluster_id}: {insight.cluster_name}")
                    report.append("-" * 60)
                    report.append(f"优先级: {insight.priority_score:.1f}/10")
                    report.append(f"置信度: {insight.confidence_level}")
                    report.append("")
                    
                    # 关键洞察
                    if insight.key_insights:
                        report.append("🔍 关键洞察:")
                        for i, insight_text in enumerate(insight.key_insights, 1):
                            report.append(f"  {i}. {insight_text}")
                        report.append("")
                    
                    # 痛点分析
                    if insight.pain_points:
                        report.append("⚠️ 痛点分析:")
                        for i, pain in enumerate(insight.pain_points, 1):
                            report.append(f"  {i}. {pain}")
                        report.append("")
                    
                    # 机会识别
                    if insight.opportunities:
                        report.append("💡 机会识别:")
                        for i, opportunity in enumerate(insight.opportunities, 1):
                            report.append(f"  {i}. {opportunity}")
                        report.append("")
                    
                    # 建议行动
                    if insight.recommended_actions:
                        report.append("🎯 建议行动:")
                        for i, action in enumerate(insight.recommended_actions, 1):
                            report.append(f"  {i}. {action}")
                        report.append("")
            
            # 行动优先级矩阵
            if business_insight.action_priority_matrix:
                report.append("📈 行动优先级矩阵")
                report.append("=" * 80)
                report.append("按优先级排序的行动建议:")
                report.append("")
                
                for i, action_item in enumerate(business_insight.action_priority_matrix[:10], 1):  # 显示前10个
                    report.append(f"{i}. {action_item['action']}")
                    report.append(f"   来源: {action_item['cluster_name']} (簇 {action_item['cluster_id']})")
                    report.append(f"   优先级: {action_item['priority_score']:.1f}/10")
                    report.append(f"   置信度: {action_item['confidence_level']}")
                    report.append("")
            
            # 报告结尾
            report.append("=" * 80)
            report.append("📝 报告生成完成")
            report.append(f"生成时间: {business_insight.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("=" * 80)
            
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"生成可读报告失败: {str(e)}")
            return f"报告生成失败: {str(e)}"
    
    def export_insights_to_text(self, business_insight: BusinessInsight, file_path: str) -> bool:
        """导出洞察为可读文本文件"""
        try:
            # 生成可读报告
            readable_report = self.generate_readable_report(business_insight)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(readable_report)
            
            logger.info(f"可读洞察报告已导出到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"可读报告导出失败: {str(e)}")
            return False
