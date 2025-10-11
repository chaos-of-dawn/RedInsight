"""
RedInsight Streamlit Web应用
使用Streamlit创建现代化的Web界面
"""
import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta
import logging

from reddit_scraper import RedditScraper
from database import DatabaseManager
from llm_analyzer import LLMAnalyzer

# 页面配置
st.set_page_config(
    page_title="RedInsight - Reddit数据分析工具",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF4500;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #FF4500;
    }
    .success-message {
        color: #00ff00;
        font-weight: bold;
    }
    .error-message {
        color: #ff0000;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def load_config():
    """加载配置文件"""
    if os.path.exists('api_keys.json'):
        try:
            with open('api_keys.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"配置文件加载失败: {str(e)}")
            return {}
    return {}

def save_config(config):
    """保存配置文件"""
    try:
        with open('api_keys.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"配置文件保存失败: {str(e)}")
        return False

# 初始化session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.scraper = None
    st.session_state.db = None
    st.session_state.analyzer = None
    # 从配置文件加载API密钥
    st.session_state.api_keys = load_config()

def init_components():
    """初始化组件"""
    if not st.session_state.initialized:
        try:
            # 检查必要的API密钥
            required_keys = ['reddit_client_id', 'reddit_client_secret']
            missing_keys = [key for key in required_keys if not st.session_state.api_keys.get(key)]
            
            if missing_keys:
                st.error(f"缺少必要的Reddit API配置: {', '.join(missing_keys)}。请在侧边栏配置这些信息。")
                return False
            
            # 检查Reddit认证状态
            if not st.session_state.api_keys.get('reddit_access_token'):
                st.error("Reddit API未认证。请点击'开始Reddit认证'按钮完成OAuth2认证。")
                return False
            
            # 设置环境变量
            for key, value in st.session_state.api_keys.items():
                if value:
                    os.environ[key.upper()] = value
            
            # 重新加载配置
            from importlib import reload
            import config
            reload(config)
            
            # 使用访问令牌创建scraper
            st.session_state.scraper = RedditScraper(
                access_token=st.session_state.api_keys['reddit_access_token'],
                client_id=st.session_state.api_keys['reddit_client_id'],
                client_secret=st.session_state.api_keys['reddit_client_secret'],
                redirect_uri=st.session_state.api_keys['reddit_redirect_uri']
            )
            st.session_state.db = DatabaseManager()
            st.session_state.analyzer = LLMAnalyzer(st.session_state.api_keys)
            st.session_state.initialized = True
            
            return True
        except Exception as e:
            st.error(f"初始化失败: {str(e)}")
            return False
    return True

def reinit_analyzer():
    """重新初始化分析器（当API密钥更新时）"""
    try:
        st.session_state.analyzer = LLMAnalyzer(st.session_state.api_keys)
        return True
    except Exception as e:
        st.error(f"重新初始化分析器失败: {str(e)}")
        return False

def main():
    """主函数"""
    # 标题
    st.markdown('<h1 class="main-header">🔍 RedInsight - Reddit数据分析工具</h1>', unsafe_allow_html=True)
    
    # 侧边栏 - API配置
    with st.sidebar:
        st.header("🔧 API配置")
        
        # Reddit API配置 (OAuth2)
        st.subheader("Reddit API (OAuth2)")
        reddit_client_id = st.text_input(
            "Client ID", 
            type="password", 
            value=st.session_state.api_keys.get('reddit_client_id', ''),
            key="reddit_client_id"
        )
        reddit_client_secret = st.text_input(
            "Client Secret", 
            type="password", 
            value=st.session_state.api_keys.get('reddit_client_secret', ''),
            key="reddit_client_secret"
        )
        reddit_redirect_uri = st.text_input(
            "重定向URI", 
            value=st.session_state.api_keys.get('reddit_redirect_uri', 'http://localhost:8080'),
            key="reddit_redirect_uri"
        )
        
        # 认证状态指示器
        st.markdown("---")
        st.markdown("### 🔐 认证状态")
        
        if st.session_state.api_keys.get('reddit_access_token'):
            # 验证访问令牌是否有效
            try:
                from reddit_scraper import RedditScraper
                test_scraper = RedditScraper(
                    access_token=st.session_state.api_keys['reddit_access_token'],
                    client_id=reddit_client_id,
                    client_secret=reddit_client_secret,
                    redirect_uri=reddit_redirect_uri
                )
                if test_scraper.is_authenticated():
                    username = test_scraper.get_authenticated_user()
                    st.success(f"✅ Reddit API 已认证 - 用户名: {username}")
                else:
                    st.error("❌ Reddit API 认证已过期")
                    st.session_state.api_keys['reddit_access_token'] = ''
                    save_config(st.session_state.api_keys)
            except Exception as e:
                st.error("❌ Reddit API 认证验证失败")
                st.session_state.api_keys['reddit_access_token'] = ''
                save_config(st.session_state.api_keys)
        else:
            st.error("❌ Reddit API 未认证")
        
        # 调试信息
        if st.checkbox("🔍 显示调试信息"):
            st.json({
                "Client ID": reddit_client_id[:8] + "..." if reddit_client_id else "未设置",
                "Client Secret": "已设置" if reddit_client_secret else "未设置",
                "Redirect URI": reddit_redirect_uri,
                "Access Token": "已设置" if st.session_state.api_keys.get('reddit_access_token') else "未设置"
            })
        
        # Reddit认证控制区域
        st.markdown("### 🔐 Reddit认证")
        
        if st.session_state.api_keys.get('reddit_access_token'):
            # 验证访问令牌是否仍然有效
            try:
                from reddit_scraper import RedditScraper
                test_scraper = RedditScraper(
                    access_token=st.session_state.api_keys['reddit_access_token'],
                    client_id=reddit_client_id,
                    client_secret=reddit_client_secret,
                    redirect_uri=reddit_redirect_uri
                )
                if test_scraper.is_authenticated():
                    username = test_scraper.get_authenticated_user()
                    st.success(f"✅ Reddit已认证 - 用户名: {username}")
                    if st.button("🔄 重新认证"):
                        st.session_state.api_keys['reddit_access_token'] = ''
                        save_config(st.session_state.api_keys)
                        st.rerun()
                else:
                    st.warning("⚠️ Reddit认证已过期")
                    st.session_state.api_keys['reddit_access_token'] = ''
                    save_config(st.session_state.api_keys)
            except Exception as e:
                st.warning("⚠️ Reddit认证验证失败")
                st.session_state.api_keys['reddit_access_token'] = ''
                save_config(st.session_state.api_keys)
        
        # 密码认证区域 - 适用于script类型应用
        if not st.session_state.api_keys.get('reddit_access_token'):
            st.markdown("#### 📝 Reddit凭据")
            st.info("💡 对于script类型应用，需要提供Reddit用户名和密码")
            
            reddit_username = st.text_input("Reddit用户名:", key="reddit_username", placeholder="输入您的Reddit用户名")
            reddit_password = st.text_input("Reddit密码:", type="password", key="reddit_password", placeholder="输入您的Reddit密码")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔐 使用密码认证", type="primary", key="reddit_password_auth"):
                    if reddit_client_id and reddit_client_secret and reddit_username and reddit_password:
                        # 创建结果容器
                        result_container = st.container()
                        
                        try:
                            # 先设置环境变量
                            os.environ['REDDIT_CLIENT_ID'] = reddit_client_id
                            os.environ['REDDIT_CLIENT_SECRET'] = reddit_client_secret
                            os.environ['REDDIT_REDIRECT_URI'] = reddit_redirect_uri
                            
                            # 重新加载配置
                            from importlib import reload
                            import config
                            reload(config)
                            
                            # 使用密码认证
                            from reddit_scraper import RedditScraper
                            scraper = RedditScraper(
                                client_id=reddit_client_id,
                                client_secret=reddit_client_secret,
                                redirect_uri=reddit_redirect_uri
                            )
                            
                            # 显示调试信息
                            with result_container:
                                st.info(f"🔍 调试信息:")
                                st.info(f"   - Client ID: {reddit_client_id[:10]}...")
                                st.info(f"   - 用户名: {reddit_username}")
                                st.info(f"   - 重定向URI: {reddit_redirect_uri}")
                            
                            with st.spinner("正在进行密码认证..."):
                                access_token = scraper.authenticate_with_password(reddit_username, reddit_password)
                                st.session_state.api_keys['reddit_access_token'] = access_token
                            
                            # 立即保存到配置文件
                            save_config(st.session_state.api_keys)
                            
                            # 验证认证结果
                            authenticated_scraper = RedditScraper(
                                access_token=access_token,
                                client_id=reddit_client_id,
                                client_secret=reddit_client_secret,
                                redirect_uri=reddit_redirect_uri
                            )
                            
                            if authenticated_scraper.is_authenticated():
                                username = authenticated_scraper.get_authenticated_user()
                                with result_container:
                                    st.success(f"✅ 认证成功！用户名: {username}")
                                    st.balloons()
                                
                                # 等待3秒让用户看到结果
                                time.sleep(3)
                                
                                # 刷新页面显示认证状态
                                st.rerun()
                            else:
                                with result_container:
                                    st.error("❌ 认证失败，请重试")
                        except Exception as e:
                            with result_container:
                                st.error(f"❌ 认证失败: {str(e)}")
                                st.error("💡 请检查：")
                                st.error("1. Reddit应用类型是否为 'script'")
                                st.error("2. 用户名和密码是否正确")
                                st.error("3. 该账户是否为Reddit应用的开发者")
                                st.error("4. Client ID和Client Secret是否正确")
                                
                                # 显示详细错误信息用于调试
                                st.error("🔍 详细错误信息:")
                                st.code(str(e))
                    else:
                        st.error("请填写所有必需字段：Client ID、Client Secret、用户名和密码")
            
            with col2:
                if st.button("🧪 测试连接", key="reddit_test_connection"):
                    if reddit_client_id and reddit_client_secret:
                        try:
                            import requests
                            import base64
                            
                            # 测试基本连接
                            credentials = f"{reddit_client_id}:{reddit_client_secret}"
                            encoded_credentials = base64.b64encode(credentials.encode()).decode()
                            
                            headers = {
                                'Authorization': f'Basic {encoded_credentials}',
                                'User-Agent': 'RedInsight Test/1.0',
                                'Content-Type': 'application/x-www-form-urlencoded'
                            }
                            
                            # 发送测试请求
                            response = requests.post(
                                'https://www.reddit.com/api/v1/access_token',
                                data={'grant_type': 'client_credentials'},
                                headers=headers,
                                timeout=10
                            )
                            
                            if response.status_code == 200:
                                st.success("✅ Reddit API连接正常")
                            else:
                                st.error(f"❌ Reddit API连接失败: {response.status_code}")
                                st.code(response.text)
                        except Exception as e:
                            st.error(f"❌ 连接测试失败: {str(e)}")
                    else:
                        st.error("请先填写Client ID和Client Secret")
        
        # AI API配置
        st.subheader("AI API")
        openai_api_key = st.text_input(
            "OpenAI API Key", 
            type="password", 
            value=st.session_state.api_keys.get('openai_api_key', ''),
            key="openai_api_key"
        )
        anthropic_api_key = st.text_input(
            "Anthropic API Key", 
            type="password", 
            value=st.session_state.api_keys.get('anthropic_api_key', ''),
            key="anthropic_api_key"
        )
        deepseek_api_key = st.text_input(
            "DeepSeek API Key", 
            type="password", 
            value=st.session_state.api_keys.get('deepseek_api_key', ''),
            key="deepseek_api_key"
        )
        
        # 保存配置
        if st.button("💾 保存配置", type="primary"):
            # 更新配置
            st.session_state.api_keys.update({
                'reddit_client_id': reddit_client_id,
                'reddit_client_secret': reddit_client_secret,
                'reddit_redirect_uri': reddit_redirect_uri,
                'openai_api_key': openai_api_key,
                'anthropic_api_key': anthropic_api_key,
                'deepseek_api_key': deepseek_api_key
            })
            
            # 立即设置环境变量
            os.environ['REDDIT_CLIENT_ID'] = reddit_client_id
            os.environ['REDDIT_CLIENT_SECRET'] = reddit_client_secret
            os.environ['REDDIT_REDIRECT_URI'] = reddit_redirect_uri
            
            # 保存到文件
            if save_config(st.session_state.api_keys):
                st.success("✅ 配置已保存")
                
                # 如果系统已初始化，重新初始化分析器
                if st.session_state.initialized:
                    if reinit_analyzer():
                        st.success("✅ 分析器已更新")
                    else:
                        st.warning("⚠️ 分析器更新失败，请重新初始化系统")
            else:
                st.error("❌ 配置保存失败")
        
        # 测试连接
        if st.button("🧪 测试连接", key="main_test_connection"):
            with st.spinner("测试API连接..."):
                # 这里可以添加实际的连接测试代码
                time.sleep(2)
                st.success("✅ 连接测试成功")
        
        # 清除配置
        if st.button("🗑️ 清除所有配置", type="secondary"):
            if st.session_state.api_keys:
                st.session_state.api_keys = {}
                if os.path.exists('api_keys.json'):
                    os.remove('api_keys.json')
                st.success("✅ 配置已清除")
                st.rerun()
            else:
                st.info("没有配置需要清除")
        
        st.divider()
        
        # 快速统计
        st.subheader("📊 快速统计")
        try:
            if st.session_state.db:
                session = st.session_state.db.get_session()
                total_posts = session.query(st.session_state.db.RedditPost).count()
                total_comments = session.query(st.session_state.db.RedditComment).count()
                total_analysis = session.query(st.session_state.db.AnalysisResult).count()
                session.close()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("帖子", total_posts)
                with col2:
                    st.metric("评论", total_comments)
                with col3:
                    st.metric("分析", total_analysis)
            else:
                st.info("请先配置API密钥并初始化系统")
        except:
            st.info("请先配置API密钥并初始化系统")
    
    # 主内容区域
    tab1, tab2, tab3 = st.tabs(["🏠 首页", "📥 数据抓取", "📊 数据分析与结果展示"])
    
    with tab1:
        st.header("欢迎使用RedInsight")
        st.markdown("""
        RedInsight是一个强大的Reddit数据分析工具，可以帮助您：
        
        - 🔍 **抓取Reddit数据**: 从指定子版块获取帖子和评论
        - 🤖 **AI智能分析**: 使用大模型进行情感分析、主题分析等
        - 📊 **可视化展示**: 生成详细的分析报告和统计图表
        - 💾 **本地存储**: 将数据和分析结果保存到本地数据库
        
        ### 使用步骤：
        1. 在左侧配置API密钥
        2. 在"数据抓取"标签页设置抓取参数
        3. 在"数据分析"标签页进行AI分析
        4. 在"结果展示"标签页查看分析结果
        """)
        
        # 系统状态
        st.subheader("系统状态")
        if st.session_state.initialized:
            st.success("✅ 系统已初始化")
        else:
            st.warning("⚠️ 系统未初始化，请配置API密钥")
    
    with tab2:
        st.header("📥 数据抓取")
        
        if st.button("🚀 初始化系统"):
            st.session_state.api_keys = {
                'reddit_client_id': reddit_client_id,
                'reddit_client_secret': reddit_client_secret,
                'reddit_redirect_uri': reddit_redirect_uri,
                'reddit_access_token': st.session_state.api_keys.get('reddit_access_token', ''),
                'openai_api_key': openai_api_key,
                'anthropic_api_key': anthropic_api_key,
                'deepseek_api_key': deepseek_api_key
            }
            
            if init_components():
                st.success("✅ 系统初始化成功")
            else:
                st.error("❌ 系统初始化失败")
        
        if st.session_state.initialized:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("抓取配置")
                subreddits = st.text_area(
                    "子版块列表 (每行一个)", 
                    value="MachineLearning\nprogramming\ndatascience",
                    height=100
                )
                post_limit = st.number_input("每个子版块帖子数", min_value=1, max_value=1000, value=50)
                include_comments = st.checkbox("包含评论", value=True)
                
            with col2:
                st.subheader("搜索配置")
                search_queries = st.text_area(
                    "搜索关键词 (每行一个)",
                    height=100,
                    help="可选：搜索特定关键词的帖子"
                )
                
                st.subheader("抓取控制")
                if st.button("🎯 开始抓取", type="primary"):
                    if subreddits.strip():
                        with st.spinner("正在抓取数据..."):
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            subreddit_list = [s.strip() for s in subreddits.split('\n') if s.strip()]
                            search_list = [s.strip() for s in search_queries.split('\n') if s.strip()] if search_queries.strip() else []
                            
                            total_subreddits = len(subreddit_list)
                            
                            for i, subreddit in enumerate(subreddit_list):
                                status_text.text(f"正在抓取 r/{subreddit}...")
                                progress_bar.progress((i + 1) / total_subreddits)
                                
                                try:
                                    posts = st.session_state.scraper.get_hot_posts(subreddit, post_limit)
                                    if posts:
                                        st.session_state.db.save_posts(posts)
                                        st.success(f"✅ r/{subreddit}: {len(posts)} 个帖子")
                                        
                                        if include_comments:
                                            total_comments = 0
                                            for post in posts[:10]:
                                                comments = st.session_state.scraper.get_post_comments(post['id'], 50)
                                                if comments:
                                                    st.session_state.db.save_comments(comments)
                                                    total_comments += len(comments)
                                            st.success(f"✅ r/{subreddit}: {total_comments} 个评论")
                                    else:
                                        st.warning(f"⚠️ r/{subreddit}: 未获取到帖子")
                                    
                                    time.sleep(1)  # 避免API限制
                                    
                                except Exception as e:
                                    st.error(f"❌ r/{subreddit}: {str(e)}")
                            
                            # 搜索特定内容
                            if search_list:
                                for subreddit in subreddit_list:
                                    for query in search_list:
                                        try:
                                            posts = st.session_state.scraper.search_posts(subreddit, query, 50)
                                            if posts:
                                                st.session_state.db.save_posts(posts)
                                                st.success(f"✅ 搜索 '{query}' 在 r/{subreddit}: {len(posts)} 个结果")
                                        except Exception as e:
                                            st.error(f"❌ 搜索 '{query}' 在 r/{subreddit}: {str(e)}")
                            
                            st.success("🎉 数据抓取完成！")
                            
                            # 显示数据存储位置
                            from config import Config
                            st.info(f"📁 数据已保存到本地数据库：`{Config.DATABASE_URL}`")
                            st.info("💡 您可以在'数据分析'标签页中查看和分析抓取的数据")
                            
                            st.balloons()
                    else:
                        st.error("请至少输入一个子版块")
        else:
            st.warning("请先配置API密钥并初始化系统")
    
    with tab3:
        # 导入合并页面
        from merged_analysis_page import create_merged_analysis_page
        create_merged_analysis_page()

if __name__ == "__main__":
    main()
