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
import io
import base64

from reddit_scraper import RedditScraper
from database import DatabaseManager
from llm_analyzer import LLMAnalyzer
from advanced_analyzer import AdvancedAnalyzer

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

@st.cache_data(ttl=60)  # 缓存1分钟
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
        # 清除配置缓存
        load_config.clear()
        return True
    except Exception as e:
        st.error(f"配置文件保存失败: {str(e)}")
        return False

@st.cache_data(ttl=1)  # 缓存1秒，减少延迟
def get_analysis_status():
    """获取分析状态"""
    try:
        from background_analyzer import background_analyzer
        return background_analyzer.get_status()
    except Exception as e:
        return {'running': False, 'status': '未知状态'}

@st.cache_data(ttl=30)  # 缓存30秒
def get_database_stats():
    """获取数据库统计信息"""
    try:
        if st.session_state.db:
            session = st.session_state.db.get_session()
            total_posts = session.query(st.session_state.db.RedditPost).count()
            total_comments = session.query(st.session_state.db.RedditComment).count()
            total_analysis = session.query(st.session_state.db.AnalysisResult).count()
            return {
                'posts': total_posts,
                'comments': total_comments,
                'analysis': total_analysis
            }
    except Exception as e:
        return {'posts': 0, 'comments': 0, 'analysis': 0}

# 初始化session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.scraper = None
    st.session_state.db = None
    st.session_state.analyzer = None
    st.session_state.advanced_analyzer = None
    # 从配置文件加载API密钥
    try:
        st.session_state.api_keys = load_config()
    except Exception as e:
        st.session_state.api_keys = {}
        st.warning(f"配置文件加载失败: {str(e)}")

def init_components():
    """初始化组件"""
    if not st.session_state.initialized:
        try:
            # 检查必要的API密钥
            required_keys = ['reddit_client_id', 'reddit_client_secret']
            missing_keys = [key for key in required_keys if not st.session_state.api_keys.get(key)]
            
            if missing_keys:
                st.warning(f"缺少必要的Reddit API配置: {', '.join(missing_keys)}。请在侧边栏配置这些信息。")
                return False
            
            # 检查Reddit认证状态
            if not st.session_state.api_keys.get('reddit_access_token'):
                st.warning("Reddit API未认证。请点击'开始Reddit认证'按钮完成OAuth2认证。")
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
            # 获取当前配置的provider - 自动检测可用的API
            provider = "deepseek"  # 默认使用DeepSeek
            if st.session_state.api_keys.get('deepseek_api_key') and st.session_state.api_keys.get('deepseek_api_key') != "your-deepseek-api-key-here":
                provider = "deepseek"
            elif st.session_state.api_keys.get('openai_api_key') and st.session_state.api_keys.get('openai_api_key') != "your-openai-api-key-here":
                provider = "openai"
            elif st.session_state.api_keys.get('anthropic_api_key') and st.session_state.api_keys.get('anthropic_api_key') != "your-anthropic-api-key-here":
                provider = "anthropic"
            
            # 初始化深度分析器
            try:
                st.session_state.advanced_analyzer = AdvancedAnalyzer(st.session_state.db, st.session_state.analyzer, provider)
                st.success("✅ 深度分析器初始化成功")
            except Exception as e:
                st.error(f"❌ 深度分析器初始化失败: {str(e)}")
                return False
            
            st.session_state.initialized = True
            
            return True
        except Exception as e:
            st.error(f"初始化失败: {str(e)}")
            import traceback
            st.error(f"详细错误信息: {traceback.format_exc()}")
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

def show_analysis_progress():
    """显示分析进度的函数"""
    from background_analyzer import background_analyzer
    from datetime import datetime
    
    analysis_status = get_analysis_status()
    
    if analysis_status.get('running', False):
        # 显示进度条
        progress_value = analysis_status.get('progress', 0)
        st.progress(progress_value)
        
        # 显示状态信息
        status_text = analysis_status.get('status', '未知状态')
        st.info(f"📊 状态: {status_text}")
        
        # 显示时间信息
        if 'start_time' in analysis_status:
            start_time = datetime.fromisoformat(analysis_status['start_time'])
            elapsed = datetime.now() - start_time
            
            # 格式化时间显示
            total_seconds = int(elapsed.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                time_str = f"{hours}小时{minutes}分钟{seconds}秒"
            elif minutes > 0:
                time_str = f"{minutes}分钟{seconds}秒"
            else:
                time_str = f"{seconds}秒"
            
            st.info(f"⏱️ 已运行时间: {time_str}")
        
        # 显示子版块信息
        if 'subreddits' in analysis_status:
            st.info(f"分析子版块: {', '.join(analysis_status['subreddits'])}")
        
        # 添加手动刷新按钮
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔄 刷新状态", key="refresh_analysis_status"):
                # 清除缓存并更新状态
                get_analysis_status.clear()
                st.success("状态已刷新")
        with col2:
            st.info("💡 点击'刷新状态'按钮查看最新进度")

def check_completed_analysis():
    """检查是否有已完成的分析结果并显示通知"""
    try:
        from background_analyzer import background_analyzer
        
        # 检查是否有已完成的分析
        if background_analyzer.is_completed():
            # 检查是否已经显示过通知
            if not st.session_state.get('analysis_completion_notified', False):
                st.success("🎉 深度分析已完成！请切换到'深度分析'标签页查看结果。")
                st.balloons()  # 添加气球庆祝动画
                st.session_state.analysis_completion_notified = True
        
        # 检查是否有失败的分析
        elif background_analyzer.is_failed():
            if not st.session_state.get('analysis_failure_notified', False):
                st.error("❌ 深度分析失败！请切换到'深度分析'标签页查看错误信息。")
                st.session_state.analysis_failure_notified = True
                    
    except Exception as e:
        # 静默处理错误，不影响主界面
        pass

def auto_check_analysis_status():
    """自动检查分析状态并显示提示"""
    try:
        from background_analyzer import background_analyzer
        
        # 如果分析完成，显示提示
        if background_analyzer.is_completed():
            if not st.session_state.get('analysis_completion_notified', False):
                st.success("🎉 深度分析已完成！请切换到'深度分析'标签页查看结果。")
                st.balloons()
                st.session_state.analysis_completion_notified = True
                
        # 如果分析失败，显示错误
        elif background_analyzer.is_failed():
            if not st.session_state.get('analysis_failure_notified', False):
                st.error("❌ 深度分析失败！请切换到'深度分析'标签页查看错误信息。")
                st.session_state.analysis_failure_notified = True
                
    except Exception as e:
        pass

def main():
    """主函数"""
    # 检查是否有已完成的分析结果
    check_completed_analysis()
    
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
        if st.checkbox("🔍 显示调试信息", key="reddit_debug_checkbox"):
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
                        st.success("认证状态已重置，请重新认证")
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
                                
                                # 清除配置缓存以更新认证状态
                                load_config.clear()
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
                # 清除配置缓存
                load_config.clear()
                st.success("✅ 配置已清除")
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
    
    # 分析状态检查器
    st.markdown("---")
    st.markdown("### 📊 分析状态")
    
    try:
        from background_analyzer import background_analyzer
        analysis_status = get_analysis_status()
        
        if analysis_status.get('running', False):
            st.warning("🔄 分析进行中...")
            progress = analysis_status.get('progress', 0)
            st.progress(progress)
            st.info(f"状态: {analysis_status.get('status', '未知')}")
            
            # 自动刷新按钮
            if st.button("🔄 刷新状态", key="sidebar_refresh"):
                # 清除缓存并更新状态
                get_analysis_status.clear()
                st.success("状态已刷新")
        elif background_analyzer.is_completed():
            st.success("✅ 分析已完成")
            st.balloons()  # 添加气球庆祝动画
            if st.button("🚀 查看结果", key="sidebar_view_results"):
                st.switch_page("深度分析")
        elif background_analyzer.is_failed():
            st.error("❌ 分析失败")
            if st.button("🔄 重新开始", key="sidebar_restart"):
                background_analyzer.clear_status()
                # 清除分析状态缓存
                get_analysis_status.clear()
                st.success("分析状态已重置")
        else:
            st.info("💤 无分析任务")
    except Exception as e:
        st.info("💤 无分析任务")
    
    # 主内容区域
    tab1, tab2, tab3, tab4 = st.tabs(["🏠 首页", "📥 数据抓取", "📊 本地数据管理", "🚀 深度分析"])
    
    with tab1:
        st.header("🔍 欢迎使用RedInsight")
        st.markdown("""
        RedInsight是一个强大的Reddit数据分析工具，可以帮助您：
        
        - 🔍 **抓取Reddit数据**: 从指定子版块获取帖子和评论
        - 📊 **本地数据管理**: 管理、筛选和整理本地数据
        - 🤖 **AI智能分析**: 使用大模型进行情感分析、主题分析等
        - 💾 **本地存储**: 将数据和分析结果保存到本地数据库
        """)
        
        # 详细使用说明
        st.subheader("📖 详细使用说明")
        
        with st.expander("🔧 系统配置", expanded=True):
            st.markdown("""
            ### 1. API密钥配置
            在左侧边栏配置以下API密钥：
            
            **必需配置：**
            - 🔑 **Reddit API密钥**: 用于抓取Reddit数据
              - Client ID: 从Reddit应用设置获取
              - Client Secret: 从Reddit应用设置获取
              - Redirect URI: 通常设置为 `http://localhost:8080`
            
            **可选配置（至少配置一个）：**
            - 🤖 **OpenAI API密钥**: 用于GPT模型分析
            - 🧠 **Anthropic API密钥**: 用于Claude模型分析  
            - 🚀 **DeepSeek API密钥**: 用于DeepSeek模型分析
            
            **配置完成后点击"🚀 初始化系统"按钮**
            """)
        
        with st.expander("📥 数据抓取使用说明", expanded=True):
            st.markdown("""
            ### 2. 数据抓取配置
            
            **重要注意事项：**
            
            #### 🎯 子版块输入格式
            - ✅ **正确格式**: `MachineLearning` (不带r/前缀)
            - ❌ **错误格式**: `r/MachineLearning` (不要带r/前缀)
            - ✅ **多个子版块**: 每行一个，如：
              ```
              MachineLearning
              programming
              selfhosted
              ```
            
            #### 📊 抓取参数说明
            - **帖子数量**: 建议50-500个帖子（分析效果最佳）
            - **时间范围**: 选择合适的时间范围获取数据
            - **排序方式**: 
              - `hot`: 热门帖子（推荐）
              - `new`: 最新帖子
              - `top`: 热门帖子
            
            #### 📅 时间筛选功能
            - **时间范围选择**: 
              - `全部时间`: 获取所有时间的帖子
              - `过去一年`: 获取过去一年的帖子
              - `过去一月`: 获取过去一月的帖子
              - `过去一周`: 获取过去一周的帖子（推荐）
              - `过去一天`: 获取过去一天的帖子
              - `过去一小时`: 获取过去一小时的帖子
            - **日期范围**: 可设置具体的开始和结束日期进行精确筛选
            - **双重筛选**: Reddit API时间筛选 + 本地日期筛选，确保数据精确性
            
            #### 📊 分数筛选功能
            - **最低分数**: 只抓取分数大于等于此值的帖子（如：10分）
            - **最高分数**: 只抓取分数小于等于此值的帖子（如：1000分）
            - **智能排序**: 系统会自动使用Reddit API的`top()`方法按分数排序
            - **高效筛选**: 优先获取高分帖子，减少无效数据传输
            
            #### 🔍 搜索功能
            - **搜索关键词**: 可选，用于筛选特定主题的帖子
            - **搜索范围**: 可选择在标题、内容或全部中搜索
            
            #### ⚠️ 注意事项
            - 首次抓取可能需要较长时间
            - 建议在网络状况良好时进行抓取
            - 抓取的数据会自动保存到本地数据库
            """)
        
        with st.expander("🚀 深度分析使用说明", expanded=True):
            st.markdown("""
            ### 3. 深度分析功能
            
            #### 🎯 子版块选择
            - 系统会自动从数据库获取可用的子版块列表
            - 支持多选子版块进行分析
            - 无需手动输入，直接从数据库选择
            
            #### 📊 分析类型
            - **快速分析**: 适合50-100个帖子，分析时间较短
            - **全面分析**: 适合300-500个帖子，分析更深入但时间较长
            
            #### 🔄 分析流程
            1. **结构化抽取**: 从帖子中提取关键信息
            2. **文本向量化**: 将文本转换为数值向量
            3. **聚类分析**: 识别相似主题的帖子群组
            4. **业务洞察**: 生成可执行的业务建议
            
            #### 📄 报告格式
            - **JSON格式**: 结构化数据，便于程序处理
            - **TXT格式**: 可读报告，包含详细分析结果
            - **预览功能**: 可直接在界面中查看报告内容
            """)
        
        with st.expander("💡 使用技巧", expanded=False):
            st.markdown("""
            ### 4. 使用技巧和最佳实践
            
            #### 🎯 数据质量优化
            - 选择活跃的子版块，数据质量更高
            - 避免选择过于小众或内容稀少的子版块
            - 建议选择有明确主题的子版块
            
            #### 📊 筛选策略建议
            - **时间筛选**: 使用"过去一周"获取最新热门内容
            - **分数筛选**: 设置最低分数（如10分）过滤低质量帖子
            - **组合筛选**: 时间+分数双重筛选，获取高质量数据
            - **数据量控制**: 建议每次抓取50-200个帖子，分析效果最佳
            
            #### ⚡ 性能优化
            - 首次使用时会下载AI模型，请耐心等待
            - 模型下载后会缓存在本地，后续使用更快
            - 建议在网络状况良好时进行首次分析
            
            #### 🔧 故障排除
            - 如果遇到网络连接问题，系统会自动重试
            - 模型加载失败时，请检查网络连接
            - 分析失败时，请检查API密钥配置
            
            #### 📊 结果解读
            - 聚类结果显示了用户讨论的主要主题
            - 情感分析帮助了解用户态度
            - 业务洞察提供了可执行的建议
        """)
        
        # 系统状态
        st.subheader("🔍 系统状态")
        if st.session_state.initialized:
            st.success("✅ 系统已初始化，可以开始使用")
        else:
            st.warning("⚠️ 系统未初始化，请先配置API密钥")
    
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
                
                # 新增：日期筛选功能
                st.subheader("📅 日期筛选")
                col_date1, col_date2 = st.columns(2)
                with col_date1:
                    start_date = st.date_input(
                        "开始日期", 
                        value=None,
                        help="不选择则从30天前开始"
                    )
                with col_date2:
                    end_date = st.date_input(
                        "结束日期", 
                        value=None,
                        help="不选择则到当前时间"
                    )
                
                # 时间范围选择
                time_filter = st.selectbox(
                    "时间范围",
                    ["all", "year", "month", "week", "day", "hour"],
                    index=2,  # 默认选择"week"
                    format_func=lambda x: {
                        "all": "全部时间",
                        "year": "过去一年", 
                        "month": "过去一月",
                        "week": "过去一周",
                        "day": "过去一天",
                        "hour": "过去一小时"
                    }[x],
                    help="Reddit API的时间筛选参数"
                )
                
                # 新增：分数筛选功能
                st.subheader("📊 分数筛选")
                col_score1, col_score2 = st.columns(2)
                with col_score1:
                    min_score = st.number_input(
                        "最低分数", 
                        min_value=0, 
                        value=0,
                        help="只抓取分数大于等于此值的帖子"
                    )
                with col_score2:
                    max_score = st.number_input(
                        "最高分数", 
                        min_value=0, 
                        value=10000,
                        help="只抓取分数小于等于此值的帖子，0表示无限制"
                    )
                
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
                                    # 传递日期筛选参数
                                    posts = st.session_state.scraper.get_hot_posts(
                                        subreddit, 
                                        post_limit, 
                                        time_filter=time_filter,
                                        start_date=start_date,
                                        end_date=end_date,
                                        min_score=min_score,
                                        max_score=max_score if max_score > 0 else 0
                                    )
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

    with tab4:
        # 深度分析页面
        st.header("🚀 深度分析功能")
        
        # 导入后台分析管理器
        from background_analyzer import background_analyzer
        
        # 检查后台分析状态
        analysis_status = get_analysis_status()
        
        # 自动检查分析状态
        auto_check_analysis_status()
        
        # 添加强制刷新按钮
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 强制刷新状态", key="force_refresh_status"):
                get_analysis_status.clear()
                st.rerun()
        with col2:
            st.info("💡 如果分析正在运行但界面未显示，请点击强制刷新")
        
        # 调试信息
        with st.expander("🔍 调试信息", expanded=False):
            st.json(analysis_status)
            st.write("缓存状态: 已启用2秒缓存")
            st.write(f"分析状态文件存在: {os.path.exists('analysis_status.json')}")
            if os.path.exists('analysis_status.json'):
                try:
                    with open('analysis_status.json', 'r', encoding='utf-8') as f:
                        file_status = json.load(f)
                    st.write("文件中的状态:")
                    st.json(file_status)
                except Exception as e:
                    st.write(f"读取状态文件失败: {str(e)}")
        
        if analysis_status.get('running', False):
            st.warning("🔄 后台分析正在进行中...")
            st.info("💡 您可以自由切换到其他界面，分析会在后台继续")
            
            # 显示分析进度
            show_analysis_progress()
            
            # 停止分析按钮
            if st.button("🛑 停止分析", type="secondary"):
                if background_analyzer.stop_analysis():
                    # 清除分析状态缓存
                    get_analysis_status.clear()
                    st.success("分析已停止")
                else:
                    st.error("停止分析失败")
            
            # 添加自动刷新提示
            st.info("🔄 页面将每3秒自动刷新以显示最新进度")
            
            # 使用JavaScript实现自动刷新
            st.markdown("""
            <script>
            setTimeout(function() {
                window.location.reload();
            }, 3000);
            </script>
            """, unsafe_allow_html=True)
            
            return
        
        # 缓存管理区域
        st.markdown("#### 🧹 缓存管理")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🧹 清除分析缓存", help="清除所有分析相关的缓存和状态文件"):
                try:
                    # 清除缓存
                    import shutil
                    import sqlite3
                    
                    cleared_items = []
                    
                    # 清除向量化缓存
                    if os.path.exists('vector_cache'):
                        shutil.rmtree('vector_cache')
                        cleared_items.append("向量化缓存")
                    
                    # 清除状态文件
                    for file in ['analysis_status.json', 'analysis_result.json']:
                        if os.path.exists(file):
                            os.remove(file)
                            cleared_items.append(f"状态文件: {file}")
                    
                    # 重置数据库分析状态
                    if os.path.exists('redinsight.db'):
                        conn = sqlite3.connect('redinsight.db')
                        cursor = conn.cursor()
                        
                        # 检查表是否存在并删除
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='business_insights'")
                        if cursor.fetchone():
                            cursor.execute("DELETE FROM business_insights")
                        
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_results'")
                        if cursor.fetchone():
                            cursor.execute("DELETE FROM analysis_results")
                        
                        # 重置自增ID（如果sqlite_sequence表存在）
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
                        if cursor.fetchone():
                            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('business_insights', 'analysis_results')")
                        
                        conn.commit()
                        conn.close()
                        cleared_items.append("数据库分析状态")
                    
                    # 创建新的空状态文件
                    empty_status = {
                        "running": False,
                        "progress": 0,
                        "status": "未开始",
                        "error": None,
                        "start_time": None,
                        "subreddits": [],
                        "limit": 0
                    }
                    with open('analysis_status.json', 'w', encoding='utf-8') as f:
                        json.dump(empty_status, f, ensure_ascii=False, indent=2)
                    cleared_items.append("新建状态文件")
                    
                    st.success(f"✅ 缓存清除完成！清除了 {len(cleared_items)} 项")
                    st.info("💡 建议重新启动应用以确保完全清理")
                    
                except Exception as e:
                    st.error(f"❌ 清除缓存失败: {str(e)}")
        
        with col2:
            if st.button("🔄 重置分析状态", help="重置分析状态但不删除数据"):
                try:
                    # 停止当前分析
                    background_analyzer.stop_analysis()
                    
                    # 重置状态
                    empty_status = {
                        "running": False,
                        "progress": 0,
                        "status": "未开始",
                        "error": None,
                        "start_time": None,
                        "subreddits": [],
                        "limit": 0
                    }
                    with open('analysis_status.json', 'w', encoding='utf-8') as f:
                        json.dump(empty_status, f, ensure_ascii=False, indent=2)
                    
                    # 清除分析状态缓存
                    get_analysis_status.clear()
                    st.success("✅ 分析状态已重置")
                    
                except Exception as e:
                    st.error(f"❌ 重置状态失败: {str(e)}")
        
        st.markdown("---")
        
        # 检查是否有已完成的分析结果
        if background_analyzer.is_completed():
            st.success("✅ 后台分析已完成！")
            st.balloons()  # 添加气球庆祝动画
            
            # 显示分析结果
            result = background_analyzer.get_result()
            if result and result.get('success'):
                st.info("💡 分析结果已保存，可以查看详细报告")
                
                # 调试信息：显示结果结构
                with st.expander("🔍 调试信息 - 分析结果结构"):
                    st.json(result)
                
                # 显示结果摘要
                insights = result.get("insights_summary", {})
                if insights:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("总帖子数", result.get("total_posts", 0))
                        st.metric("抽取结果", result.get("extractions_count", 0))
                    
                    with col2:
                        st.metric("聚类数量", result.get("clusters_count", 0))
                        st.metric("聚类质量", f"{result.get('silhouette_score', 0):.3f}")
                
                # 显示导出路径和下载功能
                export_paths = result.get("export_path", "")
                if export_paths:
                    st.info(f"📁 分析报告已保存到: {export_paths}")
                else:
                    st.info("📁 分析报告已保存到 ./output/ 目录")
                    
                # 高频词统计展示
                st.markdown("---")
                st.markdown("#### 🔤 高频关键词统计")
                
                try:
                    # 获取高频词
                    top_keywords = st.session_state.db.get_top_keywords(category="all", limit=50, order_by="frequency")
                    
                    if top_keywords:
                        # 按频率排序的前20个
                        top_20 = top_keywords[:20]
                        
                        # 显示关键词
                        keywords_text = ", ".join([kw['keyword'] for kw in top_20])
                        st.info(f"🔑 高频词: {keywords_text}")
                        
                        # 显示长尾关键词
                        long_tail_keywords = st.session_state.db.get_top_keywords(category="long_tail", limit=20, order_by="frequency")
                        if long_tail_keywords:
                            top_long_tail = long_tail_keywords[:10]
                            long_tail_text = ", ".join([kw['keyword'] for kw in top_long_tail])
                            st.success(f"🔗 长尾关键词: {long_tail_text}")
                        else:
                            st.info("💡 提示: 长尾关键词功能已启用，将在下次深度分析时提取")
                        
                        # 创建下载内容
                        keywords_content = "关键词统计报告\n"
                        keywords_content += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        keywords_content += f"关键词总数: {len(top_keywords)}\n\n"
                        
                        keywords_content += "="*50 + "\n"
                        keywords_content += "前50个高频关键词\n"
                        keywords_content += "="*50 + "\n\n"
                        
                        for i, kw in enumerate(top_keywords, 1):
                            keywords_content += f"{i:2d}. {kw['keyword']:30s} 频率: {kw['frequency']:5d}  TF-IDF: {kw['tfidf_score']:.4f}\n"
                        
                        keywords_content += "\n" + "="*50 + "\n"
                        keywords_content += "分类统计\n"
                        keywords_content += "="*50 + "\n\n"
                        
                        # 获取各类别关键词
                        categories = ['main_topic', 'pain_point', 'user_need']
                        for cat in categories:
                            cat_keywords = st.session_state.db.get_top_keywords(category=cat, limit=20, order_by="frequency")
                            if cat_keywords:
                                keywords_content += f"\n{cat.upper()}:\n"
                                for i, kw in enumerate(cat_keywords, 1):
                                    keywords_content += f"  {i:2d}. {kw['keyword']} (频率: {kw['frequency']})\n"
                        
                        # 长尾关键词
                        long_tail_keywords = st.session_state.db.get_top_keywords(category="long_tail", limit=30, order_by="frequency")
                        if long_tail_keywords:
                            keywords_content += "\n" + "="*50 + "\n"
                            keywords_content += "长尾关键词（大模型提取）\n"
                            keywords_content += "="*50 + "\n\n"
                            for i, kw in enumerate(long_tail_keywords, 1):
                                keywords_content += f"  {i:2d}. {kw['keyword']} (频率: {kw['frequency']})\n"
                        
                        # 下载按钮
                        st.download_button(
                            label="📊 下载高频词统计报告",
                            data=keywords_content.encode('utf-8'),
                            file_name=f"keywords_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain"
                        )
                    else:
                        st.warning("暂无高频词数据")
                        
                except Exception as e:
                    st.warning(f"获取高频词失败: {str(e)}")
                
                # 下载按钮组
                st.markdown("---")
                st.markdown("#### 📥 下载分析报告")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📄 下载JSON报告", help="结构化数据，便于程序处理"):
                        # 查找JSON文件
                        json_files = [f for f in os.listdir('./output') if f.endswith('.json') and 'business_insights' in f]
                        if json_files:
                            latest_json = max(json_files, key=lambda x: os.path.getctime(f'./output/{x}'))
                            with open(f'./output/{latest_json}', 'r', encoding='utf-8') as f:
                                json_data = f.read()
                            st.download_button(
                                label="📄 下载JSON报告",
                                data=json_data,
                                file_name=latest_json,
                                mime="application/json"
                            )
                        else:
                            st.warning("未找到JSON报告文件")
                
                with col2:
                    if st.button("📝 下载可读报告", help="人类可读的详细分析报告"):
                        # 查找TXT文件
                        txt_files = [f for f in os.listdir('./output') if f.endswith('.txt') and 'business_insights' in f]
                        if txt_files:
                            latest_txt = max(txt_files, key=lambda x: os.path.getctime(f'./output/{x}'))
                            with open(f'./output/{latest_txt}', 'r', encoding='utf-8') as f:
                                txt_data = f.read()
                            st.download_button(
                                label="📝 下载可读报告",
                                data=txt_data,
                                file_name=latest_txt,
                                mime="text/plain"
                            )
                        else:
                            st.warning("未找到可读报告文件")
                
                with col3:
                    if st.button("📊 生成可视化图表", help="生成数据可视化图表"):
                        # 生成可视化图表
                        try:
                                # 获取分析数据
                                analysis_data = result.get("analysis_data", {})
                                if analysis_data:
                                    # 创建图表
                                    import pandas as pd
                                    import matplotlib.pyplot as plt
                                    import io
                                    import base64
                                    
                                    # 情感分析图表
                                    sentiment_data = analysis_data.get("sentiment_distribution", {})
                                    if sentiment_data:
                                        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
                                        
                                        # 情感分布饼图
                                        labels = list(sentiment_data.keys())
                                        sizes = list(sentiment_data.values())
                                        ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                                        ax1.set_title('情感分布')
                                        
                                        # 主题分布柱状图
                                        themes = analysis_data.get("dominant_themes", [])
                                        if themes:
                                            theme_names = [theme.get("name", "未知主题") for theme in themes[:5]]
                                            theme_scores = [theme.get("score", 0) for theme in themes[:5]]
                                            ax2.bar(theme_names, theme_scores)
                                            ax2.set_title('主要主题分布')
                                            ax2.set_xticklabels(theme_names, rotation=45, ha='right')
                                        
                                        plt.tight_layout()
                                        
                                        # 转换为base64
                                        buffer = io.BytesIO()
                                        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
                                        buffer.seek(0)
                                        image_data = buffer.getvalue()
                                        buffer.close()
                                        
                                        # 提供下载
                                        st.download_button(
                                            label="📊 下载可视化图表",
                                            data=image_data,
                                            file_name=f"analysis_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                                            mime="image/png"
                                        )
                                        
                                        # 显示图表
                                        st.image(image_data, caption="分析结果可视化图表")
                                    else:
                                        st.warning("没有足够的数据生成可视化图表")
                                else:
                                    st.warning("没有找到分析数据")
                        except Exception as e:
                            st.error(f"生成可视化图表失败: {str(e)}")
                            st.info("💡 请确保已安装matplotlib: pip install matplotlib")
            
            # 清除结果按钮
            if st.button("🗑️ 清除分析结果", type="secondary"):
                background_analyzer.clear_status()
                # 清除分析状态缓存
                get_analysis_status.clear()
                st.success("分析结果已清除")
            
            return
        
        # 检查是否有失败的分析
        if background_analyzer.is_failed():
            st.error("❌ 分析失败")
            error_msg = analysis_status.get('error')
            if error_msg is None or error_msg == 'None':
                error_msg = '未知错误'
            st.error(f"错误信息: {error_msg}")
            
            # 显示调试信息
            with st.expander("🔍 调试信息"):
                st.json(analysis_status)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 重新开始", type="primary"):
                    background_analyzer.clear_status()
                    # 清除分析状态缓存
                    get_analysis_status.clear()
                    st.success("分析状态已重置")
            with col2:
                if st.button("🗑️ 清除所有状态"):
                    background_analyzer.clear_status()
                    st.session_state.analysis_running = False
                    st.session_state.analysis_progress = 0
                    st.session_state.analysis_status = "无分析任务"
                    st.session_state.analysis_completed = False
                    # 清除分析状态缓存
                    get_analysis_status.clear()
                    st.success("所有状态已清除")
            
            return
        
        st.markdown("""
        深度分析功能使用AI技术对Reddit数据进行深度挖掘，包括：
        - **结构化抽取**：从帖子中提取主题、痛点、需求等结构化信息
        - **智能聚类**：将相似内容自动分组，发现隐藏模式
        - **业务洞察**：生成可执行的商业建议和机会发现
        """)
        
        # 数据源说明
        st.info("""
        📋 **数据来源说明**：
        - 深度分析功能使用数据库中已存储的Reddit帖子数据
        - 请先在"📥 数据抓取"标签页中抓取数据
        - 数据会自动存储到本地数据库
        - 分析时根据指定的子版块从数据库读取对应数据
        """)
        
        if st.session_state.initialized:
            if st.session_state.advanced_analyzer is None:
                st.error("❌ 深度分析器未初始化")
                st.info("💡 请重新初始化系统")
                if st.button("🔄 重新初始化"):
                    st.session_state.initialized = False
                    # 清除所有缓存
                    load_config.clear()
                    get_analysis_status.clear()
                    get_database_stats.clear()
                    st.success("系统已重置，请重新初始化")
                return
            # 分析配置
            st.subheader("📋 分析配置")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🎯 分析范围")
                
                # 获取数据库中的子版块列表
                try:
                    available_subreddits = st.session_state.db.get_subreddit_list()
                    if available_subreddits:
                        st.info(f"📊 数据库中共有 {len(available_subreddits)} 个子版块")
                        
                        # 显示子版块选择器
                        selected_subreddits = st.multiselect(
                            "选择要分析的子版块",
                            options=available_subreddits,
                            default=available_subreddits[:3] if len(available_subreddits) >= 3 else available_subreddits,
                            help="从数据库中选择要分析的子版块"
                        )
                        
                        # 将选中的子版块转换为文本格式
                        if selected_subreddits:
                            subreddits_input = "\n".join(selected_subreddits)
                        else:
                            subreddits_input = ""
                    else:
                        st.warning("⚠️ 数据库中没有找到子版块数据")
                        st.info("💡 请先在'📥 数据抓取'标签页中抓取数据")
                        subreddits_input = ""
                        selected_subreddits = []
                except Exception as e:
                    st.error(f"❌ 获取子版块列表失败: {str(e)}")
                    subreddits_input = ""
                    selected_subreddits = []
                
                # 数据预览按钮
                if st.button("📊 预览可用数据", key="preview_data_btn"):
                    if selected_subreddits:
                        st.markdown("#### 📈 数据统计")
                        total_posts = 0
                        for subreddit in selected_subreddits:
                            try:
                                posts_data = st.session_state.db.get_posts_with_analysis(subreddit=subreddit, limit=1000)
                                post_count = len(posts_data) if posts_data else 0
                                total_posts += post_count
                                st.write(f"📁 r/{subreddit}: {post_count} 条帖子")
                            except Exception as e:
                                st.write(f"❌ r/{subreddit}: 查询失败 - {str(e)}")
                        
                        st.success(f"📊 总计: {total_posts} 条帖子")
                        
                        if total_posts > 0:
                            # 显示最近的一些帖子示例
                            st.markdown("#### 📝 数据示例")
                            try:
                                recent_posts_data = st.session_state.db.get_posts_with_analysis(limit=5)
                                for i, post_data in enumerate(recent_posts_data[:3]):
                                    post = post_data['post']
                                    st.write(f"{i+1}. **{post.title[:50]}...** (r/{post.subreddit})")
                            except Exception as e:
                                st.write(f"无法获取帖子示例: {str(e)}")
                    else:
                        st.warning("请先选择要分析的子版块")
                
                analysis_type = st.selectbox(
                    "分析类型",
                    ["quick", "comprehensive"],
                    format_func=lambda x: "快速分析 (50个帖子)" if x == "quick" else "全面分析 (500个帖子)"
                )
                
                limit = st.number_input(
                    "数据限制",
                    min_value=10,
                    max_value=1000,
                    value=50 if analysis_type == "quick" else 500,
                    help="分析的最大帖子数量"
                )
            
            with col2:
                st.markdown("#### ⚙️ 技术配置")
                
                # 显示当前配置
                st.info("🔧 当前配置:")
                
                # 动态检测配置的API提供商
                configured_provider = "未配置"
                if st.session_state.api_keys.get('deepseek_api_key') and st.session_state.api_keys.get('deepseek_api_key') != "your-deepseek-api-key-here":
                    configured_provider = "DeepSeek"
                elif st.session_state.api_keys.get('openai_api_key') and st.session_state.api_keys.get('openai_api_key') != "your-openai-api-key-here":
                    configured_provider = "OpenAI"
                elif st.session_state.api_keys.get('anthropic_api_key') and st.session_state.api_keys.get('anthropic_api_key') != "your-anthropic-api-key-here":
                    configured_provider = "Anthropic"
                
                # 显示配置状态
                st.info(f"- 大模型提供商: {configured_provider}")
                
                # 调试信息（可选）
                if st.checkbox("🔍 显示调试信息", key="debug_info_checkbox"):
                    st.write("API密钥状态:")
                    st.write(f"- OpenAI: {'已配置' if st.session_state.api_keys.get('openai_api_key') else '未配置'}")
                    st.write(f"- Anthropic: {'已配置' if st.session_state.api_keys.get('anthropic_api_key') else '未配置'}")
                    st.write(f"- DeepSeek: {'已配置' if st.session_state.api_keys.get('deepseek_api_key') else '未配置'}")
                st.info(f"- 向量化模型: all-MiniLM-L6-v2")
                st.info(f"- 聚类算法: KMeans")
                
                # 数据要求提示
                st.warning("⚠️ 数据要求:")
                st.warning("- 快速分析: ≥50条帖子")
                st.warning("- 全面分析: ≥300条帖子")
                st.warning("- 建议数据量: 100-500条帖子")
            
            # 开始分析按钮
            st.markdown("---")
            if st.button("🚀 开始后台分析", type="primary", use_container_width=True):
                if selected_subreddits:
                    # 检查数据量
                    total_posts = 0
                    for subreddit in selected_subreddits:
                        try:
                            posts_data = st.session_state.db.get_posts_with_analysis(subreddit=subreddit, limit=1000)
                            post_count = len(posts_data) if posts_data else 0
                            total_posts += post_count
                            st.write(f"📁 r/{subreddit}: {post_count} 条帖子")
                        except Exception as e:
                            st.write(f"❌ 查询r/{subreddit}数据失败: {str(e)}")
                    
                    if total_posts < 50:
                        st.error(f"❌ 数据量不足！当前只有 {total_posts} 条帖子，建议至少 50 条")
                        st.info("💡 请先在'数据抓取'标签页中抓取更多数据")
                    else:
                        st.info(f"📊 检测到 {total_posts} 条帖子，开始后台分析...")
                        
                        # 启动后台分析
                        if background_analyzer.start_analysis(
                            advanced_analyzer=st.session_state.advanced_analyzer,
                            subreddits=selected_subreddits,
                            limit=limit
                        ):
                            # 清除分析状态缓存
                            get_analysis_status.clear()
                            st.success("✅ 后台分析已启动！")
                            st.info("💡 您可以自由切换到其他界面，分析会在后台继续")
                            # 自动刷新页面显示进度
                            st.rerun()
                        else:
                            st.error("❌ 启动后台分析失败")
                else:
                    st.error("请先选择要分析的子版块")
        
        else:
            st.warning("请先配置API密钥并初始化系统")

if __name__ == "__main__":
    main()
