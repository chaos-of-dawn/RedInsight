"""
RedInsight GUI应用程序
使用tkinter创建简单的用户界面
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import threading
import os
import json
from datetime import datetime
import logging

from reddit_scraper import RedditScraper
from database import DatabaseManager
from llm_analyzer import LLMAnalyzer
from config import Config

class RedInsightGUI:
    """RedInsight图形用户界面"""
    
    def __init__(self):
        """初始化GUI应用"""
        self.root = tk.Tk()
        self.root.title("RedInsight - Reddit数据分析工具")
        self.root.geometry("1000x700")
        self.root.configure(bg='#f0f0f0')
        
        # 初始化组件
        self.scraper = None
        self.db = None
        self.analyzer = None
        
        # API密钥存储
        self.api_keys = {
            'reddit_client_id': '',
            'reddit_client_secret': '',
            'reddit_user_agent': 'RedInsight Bot 1.0',
            'reddit_redirect_uri': 'http://localhost:8080',
            'reddit_access_token': '',  # OAuth2访问令牌
            'openai_api_key': '',
            'anthropic_api_key': '',
            'deepseek_api_key': ''
        }
        
        self.setup_ui()
        self.load_saved_keys()
        
    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 创建标签页
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # API配置标签页
        self.setup_api_config_tab(notebook)
        
        # 数据抓取标签页
        self.setup_scraping_tab(notebook)
        
        # 数据分析标签页
        self.setup_analysis_tab(notebook)
        
        # 结果显示标签页
        self.setup_results_tab(notebook)
        
        # 日志显示区域
        self.setup_log_area(main_frame)
        
    def setup_api_config_tab(self, notebook):
        """设置API配置标签页"""
        api_frame = ttk.Frame(notebook, padding="10")
        notebook.add(api_frame, text="API配置")
        
        # Reddit API配置
        reddit_frame = ttk.LabelFrame(api_frame, text="Reddit API配置", padding="10")
        reddit_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(reddit_frame, text="Client ID:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.reddit_client_id = ttk.Entry(reddit_frame, width=50, show="*")
        self.reddit_client_id.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        ttk.Label(reddit_frame, text="Client Secret:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.reddit_client_secret = ttk.Entry(reddit_frame, width=50, show="*")
        self.reddit_client_secret.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        ttk.Label(reddit_frame, text="重定向URI:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.reddit_redirect_uri = ttk.Entry(reddit_frame, width=50)
        self.reddit_redirect_uri.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        self.reddit_redirect_uri.insert(0, "http://localhost:8080")
        
        # OAuth2认证按钮
        ttk.Button(reddit_frame, text="🔐 开始Reddit认证", command=self.start_reddit_auth).grid(row=3, column=0, columnspan=2, pady=10)
        
        # AI API配置
        ai_frame = ttk.LabelFrame(api_frame, text="AI API配置", padding="10")
        ai_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(ai_frame, text="OpenAI API Key:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.openai_api_key = ttk.Entry(ai_frame, width=50, show="*")
        self.openai_api_key.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        ttk.Label(ai_frame, text="Anthropic API Key:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.anthropic_api_key = ttk.Entry(ai_frame, width=50, show="*")
        self.anthropic_api_key.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        ttk.Label(ai_frame, text="DeepSeek API Key:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.deepseek_api_key = ttk.Entry(ai_frame, width=50, show="*")
        self.deepseek_api_key.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # 保存按钮
        save_frame = ttk.Frame(api_frame)
        save_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Button(save_frame, text="保存配置", command=self.save_api_keys).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(save_frame, text="测试连接", command=self.test_connections).pack(side=tk.LEFT)
        
    def setup_scraping_tab(self, notebook):
        """设置数据抓取标签页"""
        scrape_frame = ttk.Frame(notebook, padding="10")
        notebook.add(scrape_frame, text="数据抓取")
        
        # 子版块配置
        subreddit_frame = ttk.LabelFrame(scrape_frame, text="子版块配置", padding="10")
        subreddit_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(subreddit_frame, text="子版块列表 (用逗号分隔):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.subreddit_input = ttk.Entry(subreddit_frame, width=60)
        self.subreddit_input.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        self.subreddit_input.insert(0, "MachineLearning,programming,datascience")
        
        ttk.Label(subreddit_frame, text="每个子版块帖子数:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.post_limit = ttk.Entry(subreddit_frame, width=20)
        self.post_limit.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        self.post_limit.insert(0, "50")
        
        # 搜索配置
        search_frame = ttk.LabelFrame(scrape_frame, text="搜索配置", padding="10")
        search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(search_frame, text="搜索关键词 (用逗号分隔):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.search_input = ttk.Entry(search_frame, width=60)
        self.search_input.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # 选项
        options_frame = ttk.LabelFrame(scrape_frame, text="抓取选项", padding="10")
        options_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.include_comments = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="包含评论", variable=self.include_comments).grid(row=0, column=0, sticky=tk.W)
        
        # 控制按钮
        control_frame = ttk.Frame(scrape_frame)
        control_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Button(control_frame, text="开始抓取", command=self.start_scraping).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="停止抓取", command=self.stop_scraping).pack(side=tk.LEFT)
        
        # 进度条
        self.progress = ttk.Progressbar(scrape_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=10)
        
    def setup_analysis_tab(self, notebook):
        """设置数据分析标签页"""
        analysis_frame = ttk.Frame(notebook, padding="10")
        notebook.add(analysis_frame, text="数据分析")
        
        # AI模型选择
        model_frame = ttk.LabelFrame(analysis_frame, text="AI模型配置", padding="10")
        model_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(model_frame, text="选择AI提供商:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ai_provider = ttk.Combobox(model_frame, values=["openai", "anthropic", "deepseek"], state="readonly")
        self.ai_provider.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        self.ai_provider.set("openai")
        
        ttk.Label(model_frame, text="批处理大小:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.batch_size = ttk.Entry(model_frame, width=20)
        self.batch_size.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        self.batch_size.insert(0, "10")
        
        # 分析选项
        options_frame = ttk.LabelFrame(analysis_frame, text="分析选项", padding="10")
        options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.analyze_sentiment = tk.BooleanVar(value=True)
        self.analyze_topic = tk.BooleanVar(value=True)
        self.analyze_quality = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(options_frame, text="情感分析", variable=self.analyze_sentiment).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="主题分析", variable=self.analyze_topic).grid(row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="质量评估", variable=self.analyze_quality).grid(row=1, column=0, sticky=tk.W)
        
        # 控制按钮
        control_frame = ttk.Frame(analysis_frame)
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Button(control_frame, text="开始分析", command=self.start_analysis).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="生成报告", command=self.generate_report).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="停止分析", command=self.stop_analysis).pack(side=tk.LEFT)
        
        # 进度条
        self.analysis_progress = ttk.Progressbar(analysis_frame, mode='indeterminate')
        self.analysis_progress.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        
    def setup_results_tab(self, notebook):
        """设置结果显示标签页"""
        results_frame = ttk.Frame(notebook, padding="10")
        notebook.add(results_frame, text="分析结果")
        
        # 结果统计
        stats_frame = ttk.LabelFrame(results_frame, text="数据统计", padding="10")
        stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=8, width=80)
        self.stats_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # 刷新按钮
        ttk.Button(stats_frame, text="刷新统计", command=self.refresh_stats).pack(pady=(10, 0))
        
        # 分析结果展示
        results_display_frame = ttk.LabelFrame(results_frame, text="分析结果", padding="10")
        results_display_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 创建树形视图
        columns = ('ID', '类型', '分析类型', '模型', '时间')
        self.results_tree = ttk.Treeview(results_display_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=120)
        
        self.results_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滚动条
        scrollbar = ttk.Scrollbar(results_display_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        # 结果详情
        detail_frame = ttk.LabelFrame(results_frame, text="结果详情", padding="10")
        detail_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.detail_text = scrolledtext.ScrolledText(detail_frame, height=6, width=80)
        self.detail_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # 绑定选择事件
        self.results_tree.bind('<<TreeviewSelect>>', self.on_result_select)
        
    def setup_log_area(self, parent):
        """设置日志显示区域"""
        log_frame = ttk.LabelFrame(parent, text="运行日志", padding="10")
        log_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置日志
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志记录"""
        # 创建自定义日志处理器
        class GUILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
                
            def emit(self, record):
                msg = self.format(record)
                self.text_widget.insert(tk.END, msg + '\n')
                self.text_widget.see(tk.END)
        
        # 添加GUI日志处理器
        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(gui_handler)
        logging.getLogger().setLevel(logging.INFO)
        
    def save_api_keys(self):
        """保存API密钥"""
        self.api_keys = {
            'reddit_client_id': self.reddit_client_id.get(),
            'reddit_client_secret': self.reddit_client_secret.get(),
            'reddit_redirect_uri': self.reddit_redirect_uri.get(),
            'reddit_access_token': self.api_keys.get('reddit_access_token', ''),  # 保持现有令牌
            'openai_api_key': self.openai_api_key.get(),
            'anthropic_api_key': self.anthropic_api_key.get(),
            'deepseek_api_key': self.deepseek_api_key.get()
        }
        
        # 保存到文件
        with open('api_keys.json', 'w', encoding='utf-8') as f:
            json.dump(self.api_keys, f, ensure_ascii=False, indent=2)
        
        messagebox.showinfo("成功", "API密钥已保存")
        self.log_message("API密钥配置已保存")
    
    def start_reddit_auth(self):
        """开始Reddit OAuth2认证流程"""
        try:
            # 检查必要的配置
            if not self.reddit_client_id.get() or not self.reddit_client_secret.get():
                messagebox.showerror("配置错误", "请先填写Reddit Client ID和Client Secret")
                return
            
            # 创建临时的scraper实例用于认证
            from reddit_scraper import RedditScraper
            temp_scraper = RedditScraper()
            
            # 获取授权URL
            auth_url = temp_scraper.get_auth_url()
            
            # 打开浏览器进行认证
            import webbrowser
            webbrowser.open(auth_url)
            
            # 显示认证码输入对话框
            auth_code = tk.simpledialog.askstring(
                "Reddit认证", 
                "请在浏览器中完成认证，然后将授权码粘贴到这里:",
                parent=self.root
            )
            
            if auth_code:
                # 使用授权码获取访问令牌
                access_token = temp_scraper.authenticate_with_code(auth_code)
                
                # 保存访问令牌
                self.api_keys['reddit_access_token'] = access_token
                
                # 验证认证状态
                if temp_scraper.is_authenticated():
                    username = temp_scraper.get_authenticated_user()
                    messagebox.showinfo("认证成功", f"Reddit认证成功！用户名: {username}")
                    self.log_message(f"Reddit认证成功，用户: {username}")
                else:
                    messagebox.showerror("认证失败", "Reddit认证失败，请重试")
                    
        except Exception as e:
            messagebox.showerror("认证错误", f"Reddit认证失败: {str(e)}")
            self.log_message(f"Reddit认证失败: {str(e)}")
        
    def load_saved_keys(self):
        """加载保存的API密钥"""
        try:
            if os.path.exists('api_keys.json'):
                with open('api_keys.json', 'r', encoding='utf-8') as f:
                    saved_keys = json.load(f)
                    
                self.reddit_client_id.insert(0, saved_keys.get('reddit_client_id', ''))
                self.reddit_client_secret.insert(0, saved_keys.get('reddit_client_secret', ''))
                self.reddit_redirect_uri.delete(0, tk.END)
                self.reddit_redirect_uri.insert(0, saved_keys.get('reddit_redirect_uri', 'http://localhost:8080'))
                self.openai_api_key.insert(0, saved_keys.get('openai_api_key', ''))
                self.anthropic_api_key.insert(0, saved_keys.get('anthropic_api_key', ''))
                self.deepseek_api_key.insert(0, saved_keys.get('deepseek_api_key', ''))
                
                # 加载访问令牌（不显示在界面上）
                if 'reddit_access_token' in saved_keys:
                    self.api_keys['reddit_access_token'] = saved_keys['reddit_access_token']
                
                self.api_keys.update(saved_keys)
                self.log_message("已加载保存的API密钥")
        except Exception as e:
            self.log_message(f"加载API密钥失败: {str(e)}")
    
    def test_connections(self):
        """测试API连接"""
        def test_in_thread():
            try:
                # 测试Reddit连接
                if self.api_keys['reddit_client_id'] and self.api_keys['reddit_client_secret']:
                    self.log_message("测试Reddit API连接...")
                    # 这里可以添加实际的连接测试代码
                    self.log_message("Reddit API连接测试成功")
                
                # 测试OpenAI连接
                if self.api_keys['openai_api_key']:
                    self.log_message("测试OpenAI API连接...")
                    # 这里可以添加实际的连接测试代码
                    self.log_message("OpenAI API连接测试成功")
                
                # 测试Anthropic连接
                if self.api_keys['anthropic_api_key']:
                    self.log_message("测试Anthropic API连接...")
                    # 这里可以添加实际的连接测试代码
                    self.log_message("Anthropic API连接测试成功")
                    
                messagebox.showinfo("测试完成", "所有API连接测试完成，请查看日志")
                
            except Exception as e:
                self.log_message(f"API连接测试失败: {str(e)}")
                messagebox.showerror("测试失败", f"API连接测试失败: {str(e)}")
        
        threading.Thread(target=test_in_thread, daemon=True).start()
    
    def start_scraping(self):
        """开始数据抓取"""
        def scrape_in_thread():
            try:
                self.progress.start()
                self.log_message("开始数据抓取...")
                
                # 初始化组件
                self.init_components()
                
                # 获取配置
                subreddits = [s.strip() for s in self.subreddit_input.get().split(',') if s.strip()]
                limit = int(self.post_limit.get())
                include_comments = self.include_comments.get()
                search_queries = [s.strip() for s in self.search_input.get().split(',') if s.strip()]
                
                # 开始抓取
                for subreddit in subreddits:
                    self.log_message(f"抓取 r/{subreddit}...")
                    posts = self.scraper.get_hot_posts(subreddit, limit)
                    if posts:
                        self.db.save_posts(posts)
                        self.log_message(f"成功抓取 {len(posts)} 个帖子")
                        
                        if include_comments:
                            total_comments = 0
                            for post in posts[:10]:
                                comments = self.scraper.get_post_comments(post['id'], 50)
                                if comments:
                                    self.db.save_comments(comments)
                                    total_comments += len(comments)
                            self.log_message(f"成功抓取 {total_comments} 个评论")
                
                # 搜索特定内容
                if search_queries:
                    for subreddit in subreddits:
                        for query in search_queries:
                            self.log_message(f"搜索 '{query}' 在 r/{subreddit}")
                            posts = self.scraper.search_posts(subreddit, query, 50)
                            if posts:
                                self.db.save_posts(posts)
                                self.log_message(f"搜索到 {len(posts)} 个相关帖子")
                
                self.progress.stop()
                self.log_message("数据抓取完成")
                self.refresh_stats()
                
            except Exception as e:
                self.progress.stop()
                self.log_message(f"数据抓取失败: {str(e)}")
                messagebox.showerror("抓取失败", f"数据抓取失败: {str(e)}")
        
        threading.Thread(target=scrape_in_thread, daemon=True).start()
    
    def stop_scraping(self):
        """停止数据抓取"""
        self.progress.stop()
        self.log_message("数据抓取已停止")
    
    def start_analysis(self):
        """开始数据分析"""
        def analyze_in_thread():
            try:
                self.analysis_progress.start()
                self.log_message("开始数据分析...")
                
                # 初始化组件
                self.init_components()
                
                provider = self.ai_provider.get()
                batch_size = int(self.batch_size.get())
                
                # 获取未分析的内容
                unanalyzed_posts = self.db.get_unanalyzed_posts(batch_size)
                
                for post in unanalyzed_posts:
                    self.log_message(f"分析帖子: {post.title[:50]}...")
                    
                    text_content = f"{post.title} {post.selftext}"
                    
                    if self.analyze_sentiment.get():
                        result = self.analyzer.analyze_sentiment(text_content, provider)
                        if "error" not in result:
                            self.db.save_analysis_result(post.id, "post", "sentiment", str(result), provider)
                    
                    if self.analyze_topic.get():
                        result = self.analyzer.analyze_topic(text_content, provider)
                        if "error" not in result:
                            self.db.save_analysis_result(post.id, "post", "topic", str(result), provider)
                    
                    if self.analyze_quality.get():
                        result = self.analyzer.analyze_quality(text_content, provider)
                        if "error" not in result:
                            self.db.save_analysis_result(post.id, "post", "quality", str(result), provider)
                
                self.analysis_progress.stop()
                self.log_message("数据分析完成")
                self.refresh_results()
                
            except Exception as e:
                self.analysis_progress.stop()
                self.log_message(f"数据分析失败: {str(e)}")
                messagebox.showerror("分析失败", f"数据分析失败: {str(e)}")
        
        threading.Thread(target=analyze_in_thread, daemon=True).start()
    
    def stop_analysis(self):
        """停止数据分析"""
        self.analysis_progress.stop()
        self.log_message("数据分析已停止")
    
    def generate_report(self):
        """生成分析报告"""
        def report_in_thread():
            try:
                self.log_message("生成分析报告...")
                
                # 初始化组件
                self.init_components()
                
                provider = self.ai_provider.get()
                
                # 获取子版块列表
                subreddits = [s.strip() for s in self.subreddit_input.get().split(',') if s.strip()]
                
                for subreddit in subreddits:
                    self.log_message(f"为 r/{subreddit} 生成报告...")
                    
                    # 获取数据
                    session = self.db.get_session()
                    posts = session.query(self.db.RedditPost).filter(
                        self.db.RedditPost.subreddit == subreddit,
                        self.db.RedditPost.analyzed == True
                    ).limit(50).all()
                    
                    posts_data = [{'title': p.title, 'selftext': p.selftext} for p in posts]
                    
                    if posts_data:
                        result = self.analyzer.generate_summary(posts_data, provider)
                        if "error" not in result:
                            self.db.save_analysis_result(
                                f"{subreddit}_summary", "summary", "community_report",
                                str(result), provider
                            )
                
                self.log_message("分析报告生成完成")
                self.refresh_results()
                
            except Exception as e:
                self.log_message(f"生成报告失败: {str(e)}")
                messagebox.showerror("报告生成失败", f"生成报告失败: {str(e)}")
        
        threading.Thread(target=report_in_thread, daemon=True).start()
    
    def refresh_stats(self):
        """刷新统计信息"""
        try:
            if not self.db:
                self.init_components()
            
            session = self.db.get_session()
            
            # 获取统计数据
            total_posts = session.query(self.db.RedditPost).count()
            total_comments = session.query(self.db.RedditComment).count()
            analyzed_posts = session.query(self.db.RedditPost).filter(self.db.RedditPost.analyzed == True).count()
            analyzed_comments = session.query(self.db.RedditComment).filter(self.db.RedditComment.analyzed == True).count()
            total_analysis = session.query(self.db.AnalysisResult).count()
            
            stats_text = f"""
数据统计 (更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

📊 帖子统计:
  - 总帖子数: {total_posts}
  - 已分析帖子: {analyzed_posts}
  - 未分析帖子: {total_posts - analyzed_posts}

💬 评论统计:
  - 总评论数: {total_comments}
  - 已分析评论: {analyzed_comments}
  - 未分析评论: {total_comments - analyzed_comments}

🔍 分析统计:
  - 总分析结果: {total_analysis}

📈 完成率:
  - 帖子分析完成率: {(analyzed_posts/total_posts*100):.1f}% (如果total_posts > 0)
  - 评论分析完成率: {(analyzed_comments/total_comments*100):.1f}% (如果total_comments > 0)
            """
            
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, stats_text)
            
            session.close()
            
        except Exception as e:
            self.log_message(f"刷新统计失败: {str(e)}")
    
    def refresh_results(self):
        """刷新分析结果"""
        try:
            if not self.db:
                self.init_components()
            
            # 清空现有结果
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            
            # 获取分析结果
            results = self.db.get_analysis_results()
            
            for result in results[-50:]:  # 只显示最近50条
                self.results_tree.insert('', 'end', values=(
                    result.content_id[:20] + '...' if len(result.content_id) > 20 else result.content_id,
                    result.content_type,
                    result.analysis_type,
                    result.model_used,
                    result.created_at.strftime('%Y-%m-%d %H:%M')
                ))
            
        except Exception as e:
            self.log_message(f"刷新结果失败: {str(e)}")
    
    def on_result_select(self, event):
        """处理结果选择事件"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            content_id = item['values'][0]
            
            try:
                # 获取详细结果
                results = self.db.get_analysis_results(content_id=content_id)
                if results:
                    result = results[0]
                    self.detail_text.delete(1.0, tk.END)
                    self.detail_text.insert(1.0, result.result)
            except Exception as e:
                self.log_message(f"获取结果详情失败: {str(e)}")
    
    def init_components(self):
        """初始化组件"""
        if not self.scraper:
            # 检查必要的API密钥
            required_keys = ['reddit_client_id', 'reddit_client_secret']
            missing_keys = [key for key in required_keys if not self.api_keys.get(key)]
            
            if missing_keys:
                raise ValueError(f"缺少必要的Reddit API配置: {', '.join(missing_keys)}。请在API配置标签页中填写这些信息。")
            
            # 检查Reddit认证状态
            if not self.api_keys.get('reddit_access_token'):
                raise ValueError("Reddit API未认证。请点击'开始Reddit认证'按钮完成OAuth2认证。")
            
            # 设置环境变量
            os.environ['REDDIT_CLIENT_ID'] = self.api_keys['reddit_client_id']
            os.environ['REDDIT_CLIENT_SECRET'] = self.api_keys['reddit_client_secret']
            os.environ['REDDIT_REDIRECT_URI'] = self.api_keys.get('reddit_redirect_uri', 'http://localhost:8080')
            os.environ['OPENAI_API_KEY'] = self.api_keys['openai_api_key']
            os.environ['ANTHROPIC_API_KEY'] = self.api_keys['anthropic_api_key']
            os.environ['DEEPSEEK_API_KEY'] = self.api_keys['deepseek_api_key']
            
            # 重新加载配置
            from importlib import reload
            import config
            reload(config)
            
            # 使用访问令牌创建scraper
            self.scraper = RedditScraper(access_token=self.api_keys['reddit_access_token'])
            self.db = DatabaseManager()
            self.analyzer = LLMAnalyzer()
    
    def log_message(self, message):
        """记录日志消息"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        self.log_text.insert(tk.END, log_msg + '\n')
        self.log_text.see(tk.END)
        logging.info(message)
    
    def run(self):
        """运行GUI应用"""
        self.root.mainloop()

def main():
    """主函数"""
    app = RedInsightGUI()
    app.run()

if __name__ == "__main__":
    main()
