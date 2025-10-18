"""
数据整理模块 - 将抓取的Reddit数据整理成大模型可理解的格式
按抓取时间、板块名称分组，并生成内容梗概
"""
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import re
from database import DatabaseManager
from llm_analyzer import LLMAnalyzer

class DataOrganizer:
    """数据整理器"""
    
    def __init__(self, db_manager: DatabaseManager, llm_analyzer: LLMAnalyzer = None):
        """
        初始化数据整理器
        
        Args:
            db_manager: 数据库管理器
            llm_analyzer: 大模型分析器（可选，用于生成内容梗概）
        """
        self.db = db_manager
        self.llm_analyzer = llm_analyzer
        self.logger = logging.getLogger(__name__)
    
    def organize_data_by_scraping_session(self, 
                                        start_date: Optional[str] = None, 
                                        end_date: Optional[str] = None,
                                        subreddits: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        按抓取会话整理数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            subreddits: 子版块列表
            
        Returns:
            整理后的数据结构
        """
        try:
            # 获取分组数据
            grouped_data = self.db.get_posts_grouped_by_date_subreddit()
            
            # 过滤数据
            filtered_data = self._filter_data_by_criteria(
                grouped_data, start_date, end_date, subreddits
            )
            
            # 整理数据结构
            organized_data = self._organize_data_structure(filtered_data)
            
            return organized_data
            
        except Exception as e:
            self.logger.error(f"数据整理失败: {str(e)}")
            return {"error": str(e)}
    
    def _filter_data_by_criteria(self, 
                                grouped_data: Dict, 
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None,
                                subreddits: Optional[List[str]] = None) -> Dict:
        """根据条件过滤数据"""
        filtered_data = {}
        
        for group_key, group_info in grouped_data.items():
            # 检查日期范围
            if start_date and group_info['date'] < start_date:
                continue
            if end_date and group_info['date'] > end_date:
                continue
            
            # 检查子版块
            if subreddits and group_info['subreddit'] not in subreddits:
                continue
            
            filtered_data[group_key] = group_info
        
        return filtered_data
    
    def _organize_data_structure(self, grouped_data: Dict) -> Dict[str, Any]:
        """整理数据结构"""
        organized_data = {
            "metadata": {
                "total_groups": len(grouped_data),
                "total_posts": sum(group['total_posts'] for group in grouped_data.values()),
                "total_comments": sum(group['total_comments'] for group in grouped_data.values()),
                "date_range": self._get_date_range(grouped_data),
                "subreddits": list(set(group['subreddit'] for group in grouped_data.values())),
                "organized_at": datetime.now().isoformat()
            },
            "scraping_sessions": []
        }
        
        # 按日期排序
        sorted_groups = sorted(grouped_data.items(), key=lambda x: x[1]['date'], reverse=True)
        
        for group_key, group_info in sorted_groups:
            session_data = self._create_session_data(group_key, group_info)
            organized_data["scraping_sessions"].append(session_data)
        
        return organized_data
    
    def _create_session_data(self, group_key: str, group_info: Dict) -> Dict[str, Any]:
        """创建单个抓取会话的数据"""
        date = group_info['date']
        subreddit = group_info['subreddit']
        posts = group_info['posts']
        
        # 生成内容梗概
        content_summary = self._generate_content_summary(posts)
        
        # 提取关键信息
        key_topics = self._extract_key_topics(posts)
        sentiment_overview = self._analyze_sentiment_overview(posts)
        
        session_data = {
            "session_id": group_key,
            "scraping_date": date,
            "subreddit": subreddit,
            "statistics": {
                "total_posts": group_info['total_posts'],
                "total_comments": group_info['total_comments'],
                "avg_score": sum(post.score or 0 for post in posts) / len(posts) if posts else 0,
                "top_author": self._get_top_author(posts)
            },
            "content_summary": content_summary,
            "key_topics": key_topics,
            "sentiment_overview": sentiment_overview,
            "posts": self._format_posts_for_llm(posts)
        }
        
        return session_data
    
    def _generate_content_summary(self, posts: List) -> str:
        """生成内容梗概"""
        if not posts:
            return "无内容"
        
        # 提取所有文本内容
        all_text = []
        for post in posts:
            if post.title:
                all_text.append(f"标题: {post.title}")
            if post.selftext:
                all_text.append(f"内容: {post.selftext}")
        
        combined_text = "\n".join(all_text)
        
        # 如果内容太长，先进行简单摘要
        if len(combined_text) > 2000:
            combined_text = self._simple_summary(combined_text)
        
        # 使用LLM生成精准梗概（如果可用）
        if self.llm_analyzer and len(combined_text) > 100:
            try:
                summary_prompt = f"""
                请为以下Reddit数据生成一个精准的内容梗概，要求：
                1. 总结主要讨论话题和主题
                2. 识别用户最关心的问题和痛点
                3. 提取关键观点和态度
                4. 控制在200字以内
                
                数据内容：
                {combined_text[:1500]}
                """
                
                result = self.llm_analyzer._call_llm(summary_prompt, "openai", "content_summary")
                if "error" not in result:
                    return result.get("summary", combined_text[:200] + "...")
            except Exception as e:
                self.logger.warning(f"LLM生成梗概失败: {str(e)}")
        
        # 回退到简单摘要
        return self._simple_summary(combined_text)
    
    def _simple_summary(self, text: str, max_length: int = 200) -> str:
        """简单文本摘要"""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 如果文本长度在限制内，直接返回
        if len(text) <= max_length:
            return text
        
        # 尝试在句号处截断
        sentences = text.split('。')
        summary = ""
        for sentence in sentences:
            if len(summary + sentence) <= max_length - 3:
                summary += sentence + "。"
            else:
                break
        
        if summary:
            return summary + "..."
        
        # 如果句子太长，直接截断
        return text[:max_length-3] + "..."
    
    def _extract_key_topics(self, posts: List) -> List[str]:
        """提取关键话题"""
        # 简单的关键词提取
        all_text = []
        for post in posts:
            if post.title:
                all_text.append(post.title)
            if post.selftext:
                all_text.append(post.selftext)
        
        combined_text = " ".join(all_text).lower()
        
        # 提取常见词汇（简单实现）
        words = re.findall(r'\b\w{4,}\b', combined_text)
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 返回最常见的5个词
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return [word for word, freq in top_words]
    
    def _analyze_sentiment_overview(self, posts: List) -> Dict[str, Any]:
        """分析情感概览"""
        if not posts:
            return {"positive": 0, "negative": 0, "neutral": 0}
        
        # 简单的关键词情感分析
        positive_words = ['good', 'great', 'excellent', 'amazing', 'love', 'happy', 'satisfied', 'recommend']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'angry', 'disappointed', 'frustrated', 'problem']
        
        positive_count = 0
        negative_count = 0
        total_posts = len(posts)
        
        for post in posts:
            text = f"{post.title or ''} {post.selftext or ''}".lower()
            
            pos_score = sum(1 for word in positive_words if word in text)
            neg_score = sum(1 for word in negative_words if word in text)
            
            if pos_score > neg_score:
                positive_count += 1
            elif neg_score > pos_score:
                negative_count += 1
        
        return {
            "positive": round((positive_count / total_posts) * 100, 1),
            "negative": round((negative_count / total_posts) * 100, 1),
            "neutral": round(((total_posts - positive_count - negative_count) / total_posts) * 100, 1)
        }
    
    def _get_top_author(self, posts: List) -> str:
        """获取最活跃作者"""
        if not posts:
            return "无"
        
        author_count = {}
        for post in posts:
            if post.author:
                author_count[post.author] = author_count.get(post.author, 0) + 1
        
        if author_count:
            return max(author_count.items(), key=lambda x: x[1])[0]
        return "无"
    
    def _format_posts_for_llm(self, posts: List) -> List[Dict[str, Any]]:
        """格式化帖子数据供大模型处理"""
        formatted_posts = []
        
        for post in posts:
            formatted_post = {
                "id": post.id,
                "title": post.title,
                "author": post.author,
                "score": post.score,
                "num_comments": post.num_comments,
                "created_utc": post.created_utc.isoformat() if post.created_utc else None,
                "content": post.selftext,
                "url": post.url,
                "flair": post.flair,
                "is_self": post.is_self,
                "over_18": post.over_18
            }
            formatted_posts.append(formatted_post)
        
        return formatted_posts
    
    def _get_date_range(self, grouped_data: Dict) -> Dict[str, str]:
        """获取日期范围"""
        if not grouped_data:
            return {"start": None, "end": None}
        
        dates = [group['date'] for group in grouped_data.values()]
        return {
            "start": min(dates),
            "end": max(dates)
        }
    
    def create_llm_ready_package(self, 
                               organized_data: Dict[str, Any], 
                               output_format: str = "json",
                               include_metadata: bool = True) -> str:
        """
        创建大模型就绪的数据包
        
        Args:
            organized_data: 整理后的数据
            output_format: 输出格式 (json, txt, markdown)
            include_metadata: 是否包含元数据
            
        Returns:
            数据包内容
        """
        try:
            if output_format == "json":
                return self._create_json_package(organized_data, include_metadata)
            elif output_format == "txt":
                return self._create_txt_package(organized_data, include_metadata)
            elif output_format == "markdown":
                return self._create_markdown_package(organized_data, include_metadata)
            else:
                raise ValueError(f"不支持的输出格式: {output_format}")
                
        except Exception as e:
            self.logger.error(f"创建数据包失败: {str(e)}")
            return f"创建数据包失败: {str(e)}"
    
    def _create_json_package(self, data: Dict[str, Any], include_metadata: bool) -> str:
        """创建JSON格式数据包"""
        package_data = data.copy()
        
        if not include_metadata:
            package_data.pop("metadata", None)
        
        return json.dumps(package_data, ensure_ascii=False, indent=2)
    
    def _create_txt_package(self, data: Dict[str, Any], include_metadata: bool) -> str:
        """创建TXT格式数据包"""
        lines = []
        
        if include_metadata and "metadata" in data:
            meta = data["metadata"]
            lines.append("=" * 60)
            lines.append("Reddit数据抓取报告")
            lines.append("=" * 60)
            lines.append(f"抓取时间范围: {meta.get('date_range', {}).get('start', 'N/A')} - {meta.get('date_range', {}).get('end', 'N/A')}")
            lines.append(f"总分组数: {meta.get('total_groups', 0)}")
            lines.append(f"总帖子数: {meta.get('total_posts', 0)}")
            lines.append(f"总评论数: {meta.get('total_comments', 0)}")
            lines.append(f"涉及子版块: {', '.join(meta.get('subreddits', []))}")
            lines.append(f"整理时间: {meta.get('organized_at', 'N/A')}")
            lines.append("")
        
        for session in data.get("scraping_sessions", []):
            lines.append("-" * 50)
            lines.append(f"抓取会话: {session['session_id']}")
            lines.append(f"日期: {session['scraping_date']} | 子版块: r/{session['subreddit']}")
            lines.append(f"帖子数: {session['statistics']['total_posts']} | 评论数: {session['statistics']['total_comments']}")
            lines.append(f"平均分数: {session['statistics']['avg_score']:.1f}")
            lines.append(f"最活跃作者: u/{session['statistics']['top_author']}")
            lines.append("")
            
            lines.append("内容梗概:")
            lines.append(session['content_summary'])
            lines.append("")
            
            lines.append("关键话题:")
            lines.append(", ".join(session['key_topics']))
            lines.append("")
            
            lines.append("情感分析:")
            sentiment = session['sentiment_overview']
            lines.append(f"积极: {sentiment['positive']}% | 消极: {sentiment['negative']}% | 中性: {sentiment['neutral']}%")
            lines.append("")
            
            lines.append("帖子详情:")
            for i, post in enumerate(session['posts'][:5], 1):  # 只显示前5个帖子
                lines.append(f"{i}. {post['title']}")
                lines.append(f"   作者: u/{post['author']} | 分数: {post['score']} | 评论: {post['num_comments']}")
                if post['content']:
                    content_preview = post['content'][:100] + "..." if len(post['content']) > 100 else post['content']
                    lines.append(f"   内容: {content_preview}")
                lines.append("")
            
            if len(session['posts']) > 5:
                lines.append(f"... 还有 {len(session['posts']) - 5} 个帖子")
                lines.append("")
        
        return "\n".join(lines)
    
    def _create_markdown_package(self, data: Dict[str, Any], include_metadata: bool) -> str:
        """创建Markdown格式数据包"""
        lines = []
        
        if include_metadata and "metadata" in data:
            meta = data["metadata"]
            lines.append("# Reddit数据抓取报告")
            lines.append("")
            lines.append("## 概览信息")
            lines.append("")
            lines.append(f"- **抓取时间范围**: {meta.get('date_range', {}).get('start', 'N/A')} - {meta.get('date_range', {}).get('end', 'N/A')}")
            lines.append(f"- **总分组数**: {meta.get('total_groups', 0)}")
            lines.append(f"- **总帖子数**: {meta.get('total_posts', 0)}")
            lines.append(f"- **总评论数**: {meta.get('total_comments', 0)}")
            lines.append(f"- **涉及子版块**: {', '.join([f'r/{s}' for s in meta.get('subreddits', [])])}")
            lines.append(f"- **整理时间**: {meta.get('organized_at', 'N/A')}")
            lines.append("")
        
        for session in data.get("scraping_sessions", []):
            lines.append(f"## 抓取会话: {session['session_id']}")
            lines.append("")
            lines.append(f"**日期**: {session['scraping_date']} | **子版块**: r/{session['subreddit']}")
            lines.append("")
            lines.append(f"- 帖子数: {session['statistics']['total_posts']}")
            lines.append(f"- 评论数: {session['statistics']['total_comments']}")
            lines.append(f"- 平均分数: {session['statistics']['avg_score']:.1f}")
            lines.append(f"- 最活跃作者: u/{session['statistics']['top_author']}")
            lines.append("")
            
            lines.append("### 内容梗概")
            lines.append("")
            lines.append(session['content_summary'])
            lines.append("")
            
            lines.append("### 关键话题")
            lines.append("")
            lines.append(", ".join([f"`{topic}`" for topic in session['key_topics']]))
            lines.append("")
            
            lines.append("### 情感分析")
            lines.append("")
            sentiment = session['sentiment_overview']
            lines.append(f"- 积极: {sentiment['positive']}%")
            lines.append(f"- 消极: {sentiment['negative']}%")
            lines.append(f"- 中性: {sentiment['neutral']}%")
            lines.append("")
            
            lines.append("### 帖子详情")
            lines.append("")
            for i, post in enumerate(session['posts'][:10], 1):  # 显示前10个帖子
                lines.append(f"#### {i}. {post['title']}")
                lines.append("")
                lines.append(f"- **作者**: u/{post['author']}")
                lines.append(f"- **分数**: {post['score']}")
                lines.append(f"- **评论数**: {post['num_comments']}")
                lines.append(f"- **创建时间**: {post['created_utc']}")
                if post['content']:
                    lines.append("")
                    lines.append("**内容**:")
                    lines.append("")
                    lines.append(post['content'])
                    lines.append("")
                lines.append("---")
                lines.append("")
            
            if len(session['posts']) > 10:
                lines.append(f"*还有 {len(session['posts']) - 10} 个帖子...*")
                lines.append("")
        
        return "\n".join(lines)
    
    def save_package_to_file(self, 
                           package_content: str, 
                           filename: str, 
                           output_dir: str = "output") -> str:
        """
        保存数据包到文件
        
        Args:
            package_content: 数据包内容
            filename: 文件名
            output_dir: 输出目录
            
        Returns:
            文件路径
        """
        try:
            # 创建输出目录
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # 生成完整文件路径
            file_path = output_path / filename
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(package_content)
            
            self.logger.info(f"数据包已保存到: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"保存文件失败: {str(e)}")
            raise e
    
    def generate_excel_report(self, start_date: Optional[str] = None, 
                            end_date: Optional[str] = None,
                            subreddits: Optional[List[str]] = None,
                            output_dir: str = "output") -> str:
        """
        生成Excel格式的分析报告
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            subreddits: 子版块列表
            output_dir: 输出目录
            
        Returns:
            生成的Excel文件路径
        """
        try:
            # 获取分析结果数据
            analysis_results = self.db.get_analysis_results_with_posts(
                start_date=start_date,
                end_date=end_date,
                subreddits=subreddits
            )
            
            if not analysis_results:
                raise ValueError("没有找到符合条件的分析结果数据")
            
            # 创建输出目录
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reddit_analysis_report_{timestamp}.xlsx"
            file_path = output_path / filename
            
            # 创建Excel工作簿
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 1. 主数据表 - 综合分析结果
                main_data = self._prepare_main_dataframe(analysis_results)
                main_data.to_excel(writer, sheet_name='综合分析结果', index=False)
                
                # 2. 统计概览表
                stats_data = self._prepare_statistics_dataframe(analysis_results)
                stats_data.to_excel(writer, sheet_name='统计概览', index=False)
                
                # 3. 按子版块分组统计
                subreddit_data = self._prepare_subreddit_dataframe(analysis_results)
                subreddit_data.to_excel(writer, sheet_name='子版块分析', index=False)
                
                # 4. 情感分析结果统计
                sentiment_data = self._prepare_sentiment_dataframe(analysis_results)
                sentiment_data.to_excel(writer, sheet_name='情感分析', index=False)
                
                # 5. 主题分析结果统计
                topic_data = self._prepare_topic_dataframe(analysis_results)
                topic_data.to_excel(writer, sheet_name='主题分析', index=False)
            
            self.logger.info(f"Excel报告已生成: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"生成Excel报告失败: {str(e)}")
            raise e
    
    def _prepare_main_dataframe(self, analysis_results: List) -> pd.DataFrame:
        """准备主数据表"""
        data = []
        for result in analysis_results:
            post = result.post
            data.append({
                '帖子ID': post.id,
                '标题': post.title,
                '作者': post.author,
                '子版块': post.subreddit,
                '分数': post.score,
                '评论数': post.num_comments,
                '创建时间': post.created_utc.strftime('%Y-%m-%d %H:%M:%S') if post.created_utc else '',
                '抓取时间': post.scraped_at.strftime('%Y-%m-%d %H:%M:%S') if post.scraped_at else '',
                '情感分析结果': result.result if result.analysis_type == 'sentiment' else '',
                '主题分析结果': result.result if result.analysis_type == 'topic' else '',
                '质量评估结果': result.result if result.analysis_type == 'quality' else '',
                '综合分析结果': result.result if result.analysis_type == 'comprehensive' else '',
                'AI提供商': result.model_used or 'unknown',
                '分析时间': result.created_at.strftime('%Y-%m-%d %H:%M:%S') if result.created_at else ''
            })
        
        return pd.DataFrame(data)
    
    def _prepare_statistics_dataframe(self, analysis_results: List) -> pd.DataFrame:
        """准备统计概览表"""
        total_posts = len(set(result.content_id for result in analysis_results))
        total_analyses = len(analysis_results)
        
        # 按分析类型统计
        analysis_types = {}
        for result in analysis_results:
            analysis_types[result.analysis_type] = analysis_types.get(result.analysis_type, 0) + 1
        
        # 按AI提供商统计
        providers = {}
        for result in analysis_results:
            provider = result.model_used or 'unknown'
            providers[provider] = providers.get(provider, 0) + 1
        
        # 按子版块统计
        subreddits = {}
        for result in analysis_results:
            subreddit = result.post.subreddit
            subreddits[subreddit] = subreddits.get(subreddit, 0) + 1
        
        stats_data = [
            {'统计项目': '总帖子数', '数量': total_posts},
            {'统计项目': '总分析次数', '数量': total_analyses},
            {'统计项目': '平均每帖分析次数', '数量': round(total_analyses / total_posts, 2) if total_posts > 0 else 0}
        ]
        
        # 添加分析类型统计
        for analysis_type, count in analysis_types.items():
            stats_data.append({'统计项目': f'{analysis_type}分析次数', '数量': count})
        
        # 添加AI提供商统计
        for provider, count in providers.items():
            stats_data.append({'统计项目': f'{provider}分析次数', '数量': count})
        
        # 添加子版块统计
        for subreddit, count in subreddits.items():
            stats_data.append({'统计项目': f'r/{subreddit}帖子数', '数量': count})
        
        return pd.DataFrame(stats_data)
    
    def _prepare_subreddit_dataframe(self, analysis_results: List) -> pd.DataFrame:
        """准备子版块分析表"""
        subreddit_stats = {}
        
        for result in analysis_results:
            subreddit = result.post.subreddit
            if subreddit not in subreddit_stats:
                subreddit_stats[subreddit] = {
                    '子版块': subreddit,
                    '帖子数': 0,
                    '总分数': 0,
                    '总评论数': 0,
                    '平均分数': 0,
                    '平均评论数': 0,
                    '分析次数': 0
                }
            
            stats = subreddit_stats[subreddit]
            stats['帖子数'] += 1
            stats['总分数'] += result.post.score or 0
            stats['总评论数'] += result.post.num_comments or 0
            stats['分析次数'] += 1
        
        # 计算平均值
        for stats in subreddit_stats.values():
            if stats['帖子数'] > 0:
                stats['平均分数'] = round(stats['总分数'] / stats['帖子数'], 2)
                stats['平均评论数'] = round(stats['总评论数'] / stats['帖子数'], 2)
        
        return pd.DataFrame(list(subreddit_stats.values()))
    
    def _prepare_sentiment_dataframe(self, analysis_results: List) -> pd.DataFrame:
        """准备情感分析表"""
        sentiment_results = [r for r in analysis_results if r.analysis_type == 'sentiment']
        
        if not sentiment_results:
            return pd.DataFrame({'情感类型': [], '数量': [], '百分比': []})
        
        # 简单的情感分类统计
        sentiment_counts = {}
        for result in sentiment_results:
            result_text = result.result.lower()
            if 'positive' in result_text or '积极' in result_text or '正面' in result_text:
                sentiment_counts['积极'] = sentiment_counts.get('积极', 0) + 1
            elif 'negative' in result_text or '消极' in result_text or '负面' in result_text:
                sentiment_counts['消极'] = sentiment_counts.get('消极', 0) + 1
            else:
                sentiment_counts['中性'] = sentiment_counts.get('中性', 0) + 1
        
        total = sum(sentiment_counts.values())
        data = []
        for sentiment, count in sentiment_counts.items():
            data.append({
                '情感类型': sentiment,
                '数量': count,
                '百分比': round((count / total) * 100, 2) if total > 0 else 0
            })
        
        return pd.DataFrame(data)
    
    def _prepare_topic_dataframe(self, analysis_results: List) -> pd.DataFrame:
        """准备主题分析表"""
        topic_results = [r for r in analysis_results if r.analysis_type == 'topic']
        
        if not topic_results:
            return pd.DataFrame({'主题': [], '出现次数': [], '百分比': []})
        
        # 提取主题关键词
        topic_keywords = {}
        for result in topic_results:
            # 简单的关键词提取
            result_text = result.result.lower()
            words = re.findall(r'\b\w{3,}\b', result_text)
            for word in words:
                if len(word) > 3:  # 过滤短词
                    topic_keywords[word] = topic_keywords.get(word, 0) + 1
        
        # 取前20个最常见的主题
        top_topics = sorted(topic_keywords.items(), key=lambda x: x[1], reverse=True)[:20]
        
        total = sum(topic_keywords.values())
        data = []
        for topic, count in top_topics:
            data.append({
                '主题': topic,
                '出现次数': count,
                '百分比': round((count / total) * 100, 2) if total > 0 else 0
            })
        
        return pd.DataFrame(data)