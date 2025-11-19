"""
子版块索引模块
用于抓取、分析和索引Reddit子版块信息，支持子版块推荐功能
"""
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from database import DatabaseManager, Base
from reddit_scraper import RedditScraper
import json

logger = logging.getLogger(__name__)

class SubredditIndexer:
    """子版块索引器"""
    
    def __init__(self, db_manager: DatabaseManager, reddit_scraper: RedditScraper):
        self.db_manager = db_manager
        self.reddit_scraper = reddit_scraper
        self.vectorizer = SentenceTransformer('all-MiniLM-L6-v2')
        self.tfidf_vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        
    def index_subreddit(self, subreddit_name: str, num_posts: int = 50) -> Dict[str, Any]:
        """
        索引一个子版块
        
        Args:
            subreddit_name: 子版块名称
            num_posts: 抓取的帖子数量
            
        Returns:
            索引结果
        """
        try:
            logger.info(f"开始索引子版块: r/{subreddit_name}")
            
            # 1. 获取子版块基本信息
            subreddit_info = self._get_subreddit_info(subreddit_name)
            if not subreddit_info:
                return {"error": f"无法获取子版块信息: r/{subreddit_name}"}
            
            # 2. 抓取热门帖子
            posts_data = self._fetch_popular_posts(subreddit_name, num_posts)
            if not posts_data:
                return {"error": f"无法抓取帖子: r/{subreddit_name}"}
            
            # 3. 提取文本内容
            texts = [f"{post['title']} {post.get('selftext', '')}" for post in posts_data]
            
            # 4. 向量化
            vectors = self.vectorizer.encode(texts)
            avg_vector = np.mean(vectors, axis=0).tolist()
            
            # 5. 提取关键词
            keywords = self._extract_keywords(texts)
            
            # 6. 提取主题
            main_topics = self._extract_main_topics(posts_data)
            
            # 7. 保存到数据库
            # 处理 posts_data 中的 datetime 对象
            posts_data_serializable = []
            for post in posts_data:
                post_copy = post.copy()
                # 将 datetime 对象转换为字符串
                if 'created_utc' in post_copy and isinstance(post_copy['created_utc'], datetime):
                    post_copy['created_utc'] = post_copy['created_utc'].isoformat()
                posts_data_serializable.append(post_copy)
            
            result = self.db_manager.save_subreddit_index(
                subreddit_name=subreddit_name,
                description=subreddit_info.get('description', ''),
                subscriber_count=subreddit_info.get('subscribers', 0),
                public_description=subreddit_info.get('public_description', ''),
                avg_vector=avg_vector,
                keywords=keywords,
                main_topics=main_topics,
                posts_data=posts_data_serializable,
                indexed_at=None  # 让数据库自动设置时间
            )
            
            logger.info(f"✅ 子版块 r/{subreddit_name} 索引完成，抓取了 {len(posts_data)} 个帖子")
            return {"success": True, "subreddit": subreddit_name, "posts_count": len(posts_data)}
            
        except Exception as e:
            logger.error(f"索引子版块失败: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def _get_subreddit_info(self, subreddit_name: str) -> Optional[Dict[str, Any]]:
        """获取子版块基本信息"""
        try:
            # 使用 RedditScraper 的方法获取信息
            info = self.reddit_scraper.get_subreddit_info(subreddit_name)
            if info:
                return info
            
            # 如果获取失败，使用备用方法
            subreddit = self.reddit_scraper.reddit.subreddit(subreddit_name)
            return {
                'title': subreddit.title,
                'description': subreddit.public_description or subreddit.description,
                'public_description': subreddit.public_description,
                'subscribers': subreddit.subscribers,
                'created_utc': datetime.fromtimestamp(subreddit.created_utc),
                'over18': subreddit.over18
            }
        except Exception as e:
            logger.error(f"获取子版块信息失败: {str(e)}")
            return None
    
    def _fetch_popular_posts(self, subreddit_name: str, num_posts: int) -> List[Dict[str, Any]]:
        """抓取热门帖子"""
        try:
            subreddit = self.reddit_scraper.reddit.subreddit(subreddit_name)
            posts_data = []
            
            for post in subreddit.hot(limit=min(num_posts, 100)):
                posts_data.append({
                    'id': post.id,
                    'title': post.title,
                    'selftext': post.selftext,
                    'score': post.score,
                    'num_comments': post.num_comments,
                    'url': post.url,
                    'created_utc': datetime.fromtimestamp(post.created_utc),
                    'author': str(post.author) if post.author else '[deleted]'
                })
                
                # 避免触发速率限制
                time.sleep(0.5)
            
            return posts_data
            
        except Exception as e:
            logger.error(f"抓取帖子失败: {str(e)}")
            return []
    
    def _extract_keywords(self, texts: List[str]) -> List[str]:
        """使用TF-IDF提取关键词"""
        try:
            # 过滤空文本
            texts = [t for t in texts if t.strip()]
            if not texts:
                return []
            
            # 训练TF-IDF模型
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # 获取特征词
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
            
            # 计算每个词的平均TF-IDF分数
            mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
            
            # 获取前20个关键词
            top_indices = np.argsort(mean_scores)[-20:][::-1]
            keywords = [feature_names[i] for i in top_indices]
            
            return keywords
            
        except Exception as e:
            logger.error(f"提取关键词失败: {str(e)}")
            return []
    
    def _extract_main_topics(self, posts_data: List[Dict[str, Any]]) -> List[str]:
        """从帖子标题中提取主要主题"""
        try:
            # 简单的主题提取：基于高频词
            all_words = []
            for post in posts_data:
                title_words = post.get('title', '').lower().split()
                all_words.extend(title_words)
            
            # 统计词频
            word_freq = {}
            for word in all_words:
                if len(word) > 3:  # 过滤短词
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 获取前10个高频词作为主题
            topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            return [topic[0] for topic in topics]
            
        except Exception as e:
            logger.error(f"提取主题失败: {str(e)}")
            return []
    
    def index_multiple_subreddits(self, subreddit_names: List[str], num_posts: int = 50) -> Dict[str, Any]:
        """批量索引多个子版块"""
        results = []
        for subreddit_name in subreddit_names:
            result = self.index_subreddit(subreddit_name, num_posts)
            results.append(result)
            
            # 避免触发速率限制
            time.sleep(2)
        
        return {
            "total": len(subreddit_names),
            "success": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if r.get("error")),
            "results": results
        }
