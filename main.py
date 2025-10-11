"""
RedInsight 主程序入口
整合Reddit数据抓取、数据库存储和大模型分析功能
"""
import logging
import argparse
import time
from datetime import datetime
from typing import List, Dict, Any

from reddit_scraper import RedditScraper
from database import DatabaseManager
from llm_analyzer import LLMAnalyzer
from config import Config

class RedInsight:
    """RedInsight主类"""
    
    def __init__(self):
        """初始化RedInsight系统"""
        self.setup_logging()
        self.scraper = RedditScraper()
        self.db = DatabaseManager()
        self.analyzer = LLMAnalyzer()
        self.logger = logging.getLogger(__name__)
        
    def setup_logging(self):
        """设置日志系统"""
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def scrape_subreddit(self, subreddit_name: str, limit: int = 100, include_comments: bool = True):
        """
        抓取指定子版块的数据
        
        Args:
            subreddit_name: 子版块名称
            limit: 帖子数量限制
            include_comments: 是否包含评论
        """
        self.logger.info(f"开始抓取 r/{subreddit_name}")
        
        # 获取子版块信息
        subreddit_info = self.scraper.get_subreddit_info(subreddit_name)
        if subreddit_info:
            self.db.save_subreddit_info(subreddit_info)
        
        # 获取热门帖子
        posts = self.scraper.get_hot_posts(subreddit_name, limit)
        if posts:
            self.db.save_posts(posts)
            self.logger.info(f"成功抓取 {len(posts)} 个帖子")
            
            # 获取评论
            if include_comments:
                total_comments = 0
                for post in posts[:10]:  # 限制前10个帖子的评论
                    comments = self.scraper.get_post_comments(post['id'], 50)
                    if comments:
                        self.db.save_comments(comments)
                        total_comments += len(comments)
                        time.sleep(1)  # 避免API限制
                
                self.logger.info(f"成功抓取 {total_comments} 个评论")
        else:
            self.logger.warning(f"未能获取 r/{subreddit_name} 的帖子")
    
    def search_and_scrape(self, subreddit_name: str, query: str, limit: int = 100):
        """
        搜索并抓取指定关键词的帖子
        
        Args:
            subreddit_name: 子版块名称
            query: 搜索关键词
            limit: 结果数量限制
        """
        self.logger.info(f"搜索 '{query}' 在 r/{subreddit_name}")
        
        posts = self.scraper.search_posts(subreddit_name, query, limit)
        if posts:
            self.db.save_posts(posts)
            self.logger.info(f"成功搜索并保存 {len(posts)} 个帖子")
        else:
            self.logger.warning(f"未找到包含 '{query}' 的帖子")
    
    def analyze_unanalyzed_content(self, provider: str = "openai"):
        """
        分析未分析的内容
        
        Args:
            provider: 大模型提供商
        """
        self.logger.info("开始分析未分析的内容")
        
        # 分析未分析的帖子
        unanalyzed_posts = self.db.get_unanalyzed_posts(Config.BATCH_SIZE)
        for post in unanalyzed_posts:
            self.logger.info(f"分析帖子: {post.title[:50]}...")
            
            # 情感分析
            sentiment_result = self.analyzer.analyze_sentiment(
                f"{post.title} {post.selftext}", provider
            )
            if "error" not in sentiment_result:
                self.db.save_analysis_result(
                    post.id, "post", "sentiment", 
                    str(sentiment_result), provider
                )
            
            # 主题分析
            topic_result = self.analyzer.analyze_topic(
                f"{post.title} {post.selftext}", provider
            )
            if "error" not in topic_result:
                self.db.save_analysis_result(
                    post.id, "post", "topic", 
                    str(topic_result), provider
                )
            
            # 质量分析
            quality_result = self.analyzer.analyze_quality(
                f"{post.title} {post.selftext}", provider
            )
            if "error" not in quality_result:
                self.db.save_analysis_result(
                    post.id, "post", "quality", 
                    str(quality_result), provider
                )
            
            time.sleep(2)  # 避免API限制
        
        # 分析未分析的评论
        unanalyzed_comments = self.db.get_unanalyzed_comments(Config.BATCH_SIZE)
        for comment in unanalyzed_comments:
            self.logger.info(f"分析评论: {comment.body[:50]}...")
            
            # 情感分析
            sentiment_result = self.analyzer.analyze_sentiment(comment.body, provider)
            if "error" not in sentiment_result:
                self.db.save_analysis_result(
                    comment.id, "comment", "sentiment", 
                    str(sentiment_result), provider
                )
            
            time.sleep(2)  # 避免API限制
        
        self.logger.info("内容分析完成")
    
    def generate_community_report(self, subreddit_name: str, provider: str = "openai"):
        """
        生成社区报告
        
        Args:
            subreddit_name: 子版块名称
            provider: 大模型提供商
        """
        self.logger.info(f"生成 r/{subreddit_name} 社区报告")
        
        # 获取最近的分析结果
        session = self.db.get_session()
        try:
            posts = session.query(self.db.RedditPost).filter(
                self.db.RedditPost.subreddit == subreddit_name,
                self.db.RedditPost.analyzed == True
            ).limit(50).all()
            
            comments = session.query(self.db.RedditComment).join(
                self.db.RedditPost
            ).filter(
                self.db.RedditPost.subreddit == subreddit_name,
                self.db.RedditComment.analyzed == True
            ).limit(100).all()
            
        finally:
            session.close()
        
        # 转换为字典格式
        posts_data = [{
            'title': post.title,
            'selftext': post.selftext,
            'score': post.score,
            'num_comments': post.num_comments
        } for post in posts]
        
        comments_data = [{
            'body': comment.body,
            'score': comment.score
        } for comment in comments]
        
        # 生成汇总分析
        summary_result = self.analyzer.generate_summary(posts_data, provider)
        if "error" not in summary_result:
            self.db.save_analysis_result(
                f"{subreddit_name}_summary", "summary", "community_report",
                str(summary_result), provider
            )
        
        # 生成参与度分析
        engagement_result = self.analyzer.analyze_community_engagement(
            posts_data, comments_data, provider
        )
        if "error" not in engagement_result:
            self.db.save_analysis_result(
                f"{subreddit_name}_engagement", "summary", "engagement_analysis",
                str(engagement_result), provider
            )
        
        self.logger.info("社区报告生成完成")
    
    def run_full_workflow(self, subreddit_names: List[str], search_queries: List[str] = None):
        """
        运行完整的工作流程
        
        Args:
            subreddit_names: 要分析的子版块列表
            search_queries: 可选的搜索关键词列表
        """
        self.logger.info("开始运行完整工作流程")
        
        # 1. 抓取数据
        for subreddit in subreddit_names:
            self.scrape_subreddit(subreddit, Config.MAX_POSTS_PER_SUBREDDIT)
            time.sleep(5)  # 避免API限制
        
        # 2. 搜索特定内容（如果提供）
        if search_queries:
            for subreddit in subreddit_names:
                for query in search_queries:
                    self.search_and_scrape(subreddit, query, 50)
                    time.sleep(5)
        
        # 3. 分析内容
        self.analyze_unanalyzed_content()
        
        # 4. 生成报告
        for subreddit in subreddit_names:
            self.generate_community_report(subreddit)
        
        self.logger.info("完整工作流程执行完成")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='RedInsight - Reddit数据分析工具')
    parser.add_argument('--action', choices=['scrape', 'analyze', 'report', 'full'], 
                       default='full', help='执行的操作')
    parser.add_argument('--subreddits', nargs='+', default=Config.DEFAULT_SUBREDDITS,
                       help='要分析的子版块列表')
    parser.add_argument('--search', nargs='+', help='搜索关键词列表')
    parser.add_argument('--limit', type=int, default=100, help='帖子数量限制')
    parser.add_argument('--provider', choices=['openai', 'anthropic', 'deepseek'], 
                       default='openai', help='大模型提供商')
    parser.add_argument('--no-comments', action='store_true', help='不抓取评论')
    
    args = parser.parse_args()
    
    # 初始化RedInsight
    redinsight = RedInsight()
    
    try:
        if args.action == 'scrape':
            for subreddit in args.subreddits:
                redinsight.scrape_subreddit(subreddit, args.limit, not args.no_comments)
        
        elif args.action == 'analyze':
            redinsight.analyze_unanalyzed_content(args.provider)
        
        elif args.action == 'report':
            for subreddit in args.subreddits:
                redinsight.generate_community_report(subreddit, args.provider)
        
        elif args.action == 'full':
            redinsight.run_full_workflow(args.subreddits, args.search)
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        logging.error(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    main()

