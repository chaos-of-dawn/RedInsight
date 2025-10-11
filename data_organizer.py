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
