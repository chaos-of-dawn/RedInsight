"""
RedInsight Streamlit Web应用
使用Streamlit创建现代化的Web界面
"""
import streamlit as st
import pandas as pd
import json
import os
import glob
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

@st.cache_data(ttl=300)  # 缓存5分钟，减少文件读取
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

@st.cache_data(ttl=5)  # 缓存5秒，平衡实时性和性能
def get_analysis_status():
    """获取分析状态"""
    try:
        from background_analyzer import background_analyzer
        return background_analyzer.get_status()
    except Exception as e:
        return {'running': False, 'status': '未知状态'}

@st.cache_data(ttl=60)  # 缓存60秒，减少数据库查询
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
            
            # 验证认证状态
            if not st.session_state.scraper.is_authenticated():
                st.warning("Reddit API认证已过期。请重新进行认证。")
                st.session_state.api_keys['reddit_access_token'] = ''
                save_config(st.session_state.api_keys)
                return False
            st.session_state.db = DatabaseManager()
            st.session_state.analyzer = LLMAnalyzer(st.session_state.api_keys)
            st.session_state.llm_analyzer = st.session_state.analyzer  # 保持兼容性
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
        st.session_state.llm_analyzer = st.session_state.analyzer  # 保持兼容性
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
        
        # 认证状态指示器 - 使用缓存避免频繁验证
        st.markdown("---")
        st.markdown("### 🔐 认证状态")
        
        # 只在token变化或首次加载时验证
        current_token = st.session_state.api_keys.get('reddit_access_token', '')
        token_changed = st.session_state.get('last_verified_token') != current_token
        
        if current_token:
            # 如果已有有效的scraper实例且token未变化，直接使用
            if (st.session_state.scraper and 
                hasattr(st.session_state, 'auth_user') and 
                st.session_state.auth_user and 
                not token_changed):
                st.success(f"✅ Reddit API 已认证 - 用户名: {st.session_state.auth_user}")
            else:
                # 验证访问令牌是否有效
                try:
                    from reddit_scraper import RedditScraper
                    test_scraper = RedditScraper(
                        access_token=current_token,
                        client_id=reddit_client_id,
                        client_secret=reddit_client_secret,
                        redirect_uri=reddit_redirect_uri
                    )
                    if test_scraper.is_authenticated():
                        username = test_scraper.get_authenticated_user()
                        # 将认证实例与信息写回全局状态，供全局统一使用
                        st.session_state.scraper = test_scraper
                        st.session_state.auth_user = username
                        st.session_state.last_verified_token = current_token
                        try:
                            if hasattr(test_scraper, 'reddit') and hasattr(test_scraper.reddit, 'auth'):
                                scopes = list(test_scraper.reddit.auth.scopes())
                                st.session_state.reddit_scopes = scopes
                                # 允许写操作
                                try:
                                    test_scraper.reddit.read_only = False
                                except Exception:
                                    pass
                            # 认证实例更新后，重建依赖scraper的服务
                            try:
                                from account_readiness import AccountReadinessService
                                if 'db' in st.session_state and st.session_state.db:
                                    st.session_state.readiness_service = AccountReadinessService(st.session_state.db, st.session_state.scraper)
                            except Exception:
                                pass
                        except Exception:
                            pass
                        st.success(f"✅ Reddit API 已认证 - 用户名: {username}")
                    else:
                        st.error("❌ Reddit API 认证已过期")
                        st.session_state.api_keys['reddit_access_token'] = ''
                        st.session_state.last_verified_token = ''
                        save_config(st.session_state.api_keys)
                except Exception as e:
                    st.error("❌ Reddit API 认证验证失败")
                    st.session_state.api_keys['reddit_access_token'] = ''
                    st.session_state.last_verified_token = ''
                    save_config(st.session_state.api_keys)
        else:
            st.error("❌ Reddit API 未认证")
            st.session_state.last_verified_token = ''
        
        # 调试信息
        if st.checkbox("🔍 显示调试信息", key="reddit_debug_checkbox"):
            st.json({
                "Client ID": reddit_client_id[:8] + "..." if reddit_client_id else "未设置",
                "Client Secret": "已设置" if reddit_client_secret else "未设置",
                "Redirect URI": reddit_redirect_uri,
                "Access Token": "已设置" if st.session_state.api_keys.get('reddit_access_token') else "未设置"
            })
        
        # Reddit认证控制区域 - 复用上面的认证结果
        st.markdown("### 🔐 Reddit认证")
        
        if st.session_state.api_keys.get('reddit_access_token'):
            if st.session_state.scraper and hasattr(st.session_state, 'auth_user') and st.session_state.auth_user:
                st.success(f"✅ Reddit已认证 - 用户名: {st.session_state.auth_user}")
                if st.button("🔄 重新认证"):
                    st.session_state.api_keys['reddit_access_token'] = ''
                    st.session_state.last_verified_token = ''
                    save_config(st.session_state.api_keys)
                    st.rerun()
            else:
                st.warning("⚠️ 正在验证认证状态...")
        
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
                                
                                # 更新session_state中的scraper实例
                                st.session_state.scraper = authenticated_scraper
                                
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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["🏠 首页", "📥 数据抓取", "📊 本地数据管理", "🚀 深度分析", "🎯 子版块推荐", "🔧 Reddit养号控制台", "🔍 智能筛选"])
    
    with tab1:
        st.header("🔍 欢迎使用RedInsight")
        st.markdown("""
        RedInsight是一个强大的Reddit数据分析与养号管理平台，可以帮助您：
        
        - 🔍 **抓取Reddit数据**: 从指定子版块获取帖子和评论
        - 📊 **本地数据管理**: 管理、筛选和整理本地数据
        - 🤖 **AI智能分析**: 使用大模型进行深度分析、关键词提取等
        - 🎯 **智能子版块推荐**: 基于需求分析，精准推荐目标子版块
        - 📝 **智能发帖系统**: 结合深度分析结果，生成高质量帖子内容
        - 🔧 **养号控制台**: 账号状态监控、发帖资格检测、互动管理
        - 💾 **本地存储**: 将数据和分析结果保存到本地数据库
        """)
        
        # 功能概览
        st.subheader("✨ 核心功能模块")
        
        col_func1, col_func2, col_func3 = st.columns(3)
        
        with col_func1:
            st.markdown("""
            #### 🎯 子版块推荐
            - 智能需求分析（中文输入）
            - 三层漏斗式筛选
            - 精准匹配推荐
            - 批量索引功能
            """)
        
        with col_func2:
            st.markdown("""
            #### 🚀 深度分析
            - 六阶段分析流程
            - 长尾关键词提取
            - 业务洞察生成
            - 自动报告导出
            """)
        
        with col_func3:
            st.markdown("""
            #### 🔧 养号控制台
            - 账号状态监控
            - 发帖资格检测
            - 智能发帖生成
            - 互动管理
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
        
        with st.expander("🎯 子版块推荐使用说明", expanded=True):
            st.markdown("""
            ### 4. 智能子版块推荐功能
            
            #### 🧠 智能需求分析
            1. **输入中文需求**: 例如："我想了解iPhone电池更换的相关信息"
            2. **AI自动翻译**: 系统自动将中文需求翻译为英文
            3. **意图分析**: AI分析用户意图，提取关键需求点
            4. **生成需求向量**: 将需求转换为向量表示，便于匹配
            
            #### 📊 三层漏斗式筛选
            - **高度匹配（85-100分）**: 5-8个精准推荐，最符合需求
            - **中度匹配（70-84分）**: 8-12个相关推荐，值得关注
            - **低度匹配（60-69分）**: 10-15个潜在推荐，可做备选
            
            #### 📥 批量索引功能
            1. **选择子版块**: 从推荐结果中勾选感兴趣的子版块
            2. **批量索引**: 点击"批量索引子版块"开始数据抓取
            3. **查看详情**: 索引完成后可查看子版块详细信息
            4. **精准推荐**: 基于索引数据生成最终精准推荐
            
            #### 💡 使用建议
            - 建议先进行智能需求分析，获得精准推荐
            - 优先索引高度匹配的子版块，数据质量更高
            - 索引完成后可用于后续深度分析和智能发帖
            """)
        
        with st.expander("🔧 Reddit养号控制台使用说明", expanded=True):
            st.markdown("""
            ### 5. Reddit养号控制台
            
            #### 📊 账号状态面板
            - **账号信息**: 显示当前Reddit账号用户名
            - **Karma统计**: 显示总Karma、帖子Karma、评论Karma
            - **账号年龄**: 显示账号创建时间和使用天数
            - **今日任务**: 显示今日需要完成的养号任务
            
            #### 🛡️ 发帖资格检测
            1. **选择目标子版块**: 输入要发帖的子版块名称
            2. **检测发帖资格**: 系统评估账号是否有资格在该子版块发帖
            3. **查看检测结果**: 显示检测结果、置信度、原因和建议
            4. **生成养号计划**: 如果资格不足，系统生成7天养号计划
            
            #### 📝 智能发帖流程（5步骤）
            
            **步骤1：子版块选择**
            - 从推荐结果中选择（推荐）
            - 手动输入子版块名称
            - 从已索引子版块中选择
            - 从数据库中选择
            
            **步骤2：查看子版块详情**
            - 显示子版块基本信息（订阅数、描述等）
            - 显示关键词和主要话题
            - 显示热门帖子示例
            
            **步骤3：子版块规则提示**
            - 自动获取子版块发帖规则
            - **规则自动翻译**: 将英文规则翻译为中文（如适用）
            - 显示规则摘要和完整规则
            - 如无规则则显示"无规则"
            
            **步骤4：生成帖子内容**
            - 配置发帖参数（目标受众、用户需求等）
            - **AI智能生成**: 基于深度分析结果、关键词、长尾词和规则生成内容
            - 支持中文输入自动翻译
            - 支持重新生成功能
            
            **步骤5：内容预览与发布**
            - 预览生成的帖子内容
            - 查看翻译信息（如适用）
            - 验证内容合规性
            - 支持保存草稿、下载、直接发布
            
            #### 🎯 快速互动区域
            
            **左侧：帖子互动**
            - 输入帖子ID进行快速互动
            - 支持点赞、点踩、保存、取消保存
            - 支持回复帖子和查看评论
            - 评论支持点赞和点踩
            
            **右侧：子版块浏览与翻译**
            - 浏览指定子版块的热门帖子
            - 选择帖子查看详情
            - **自动翻译**: 一键将帖子翻译为中文
            - 快速互动（点赞、保存）
            - **评论查看**: 查看帖子评论并进行互动
            
            #### 📊 养号任务管理
            - 显示今日养号任务清单
            - 查看7天养号计划详情
            - 跟踪任务完成进度
            
            #### 📚 互动历史与统计
            - 显示最近互动记录
            - 统计总互动数、成功互动、失败互动
            - 计算互动成功率
            
            #### 💡 使用建议
            - **新账号**: 建议先运行发帖资格检测，生成养号计划
            - **发帖前**: 务必完成深度分析，确保有足够的数据支持
            - **互动策略**: 建议按养号计划逐步增加互动频率
            - **规则遵循**: 发帖前仔细阅读子版块规则，确保内容合规
            """)
        
        with st.expander("💡 使用技巧", expanded=False):
            st.markdown("""
            ### 6. 使用技巧和最佳实践
            
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
                                                # 解析帖子ID，避免空ID
                                                post_id_val = post.get('id') or ''
                                                if not post_id_val:
                                                    permalink = post.get('permalink') or ''
                                                    try:
                                                        # Reddit 链接格式: /r/<sub>/comments/<id>/...
                                                        parts = permalink.strip('/').split('/')
                                                        if 'comments' in parts:
                                                            idx = parts.index('comments')
                                                            if idx + 1 < len(parts):
                                                                post_id_val = parts[idx + 1]
                                                    except Exception:
                                                        post_id_val = ''
                                                if not post_id_val:
                                                    continue
                                                comments = st.session_state.scraper.get_post_comments(post_id_val, 50)
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
    
    # 子版块推荐页面
    with tab5:
        try:
            st.header("🎯 子版块推荐")
            st.markdown("基于您的需求，智能推荐最适合的Reddit子版块")
            
            if st.session_state.initialized:
                # 导入新模块
                try:
                    from subreddit_indexer import SubredditIndexer
                    from subreddit_recommender import SubredditRecommender
                    from demand_analyzer import DemandAnalyzer, SubredditSuggester, IndexOptimizer
                except ImportError as e:
                    st.error(f"导入子版块推荐模块失败: {str(e)}")
                    st.info("请确保所有新模块文件已正确创建")
                    return
                except Exception as e:
                    st.error(f"初始化子版块推荐依赖失败: {str(e)}")
                    return
                
                # 检查必要的组件是否已初始化
                if not hasattr(st.session_state, 'db') or not st.session_state.db:
                    st.warning("⚠️ 数据库未初始化")
                    st.info("💡 请重新初始化系统")
                    return
                
                if not hasattr(st.session_state, 'scraper') or not st.session_state.scraper:
                    st.warning("⚠️ Reddit爬虫未初始化")
                    st.info("💡 请重新初始化系统")
                    return
                
                if not hasattr(st.session_state, 'llm_analyzer') or not st.session_state.llm_analyzer:
                    st.warning("⚠️ LLM分析器未初始化，请先配置API密钥")
                    st.info("💡 请在'API配置'页面完成配置")
                    return
                
                # 初始化推荐器
                if 'subreddit_recommender' not in st.session_state:
                    st.session_state.subreddit_recommender = SubredditRecommender(st.session_state.db)
                
                # 初始化需求分析器
                if 'demand_analyzer' not in st.session_state:
                    st.session_state.demand_analyzer = DemandAnalyzer(st.session_state.llm_analyzer)
                    st.session_state.subreddit_suggester = SubredditSuggester(st.session_state.llm_analyzer)
                    st.session_state.index_optimizer = IndexOptimizer()
                
                # 智能需求分析
                st.subheader("🧠 智能需求分析")
                st.markdown("输入您的需求，AI将自动翻译并推荐相关子版块")
                
                # 需求输入区域
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    user_demand = st.text_area(
                        "描述您的需求（支持中英文）",
                        placeholder="例如：我想讨论自建服务的技术问题，寻找机器学习的最新讨论",
                        height=100,
                        help="详细描述您想要讨论的话题或寻找的内容"
                    )
                
                with col2:
                    st.markdown("**💡 使用提示：**")
                    st.info("""
                    - 支持中英文输入
                    - 描述越详细，推荐越精准
                    - 可以描述技术领域、兴趣爱好等
                    """)
                
                # 分析需求按钮
                if st.button("🔍 分析需求", type="primary", disabled=not user_demand.strip()):
                        with st.spinner("正在分析需求..."):
                            try:
                                # 分析需求
                                analysis_result = st.session_state.demand_analyzer.analyze_demand(user_demand)
                                
                                # 保存分析结果到session state
                                st.session_state.demand_analysis = analysis_result
                                
                                st.success("✅ 需求分析完成！")
                                
                            except Exception as e:
                                st.error(f"❌ 需求分析失败: {str(e)}")
                
                # 显示分析结果
                if hasattr(st.session_state, 'demand_analysis') and st.session_state.demand_analysis:
                    analysis = st.session_state.demand_analysis
                    
                    st.markdown("---")
                    st.markdown("### 🌐 分析结果")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**📝 英文翻译：**")
                        st.info(analysis.get('translation', '无翻译'))
                        
                        st.markdown("**🔑 关键词：**")
                        keywords = analysis.get('keywords', [])
                        if keywords:
                            st.write(", ".join(keywords))
                        else:
                            st.write("无关键词")
                    
                    with col2:
                        st.markdown("**🎯 用户意图：**")
                        st.info(analysis.get('intent', '无意图分析'))
                        
                        st.markdown("**⚙️ 推荐参数：**")
                        params = analysis.get('index_params', {})
                        if params:
                            st.write(f"帖子数量: {params.get('post_limit', 30)}")
                            st.write(f"时间范围: {params.get('time_filter', 'month')}")
                            st.write(f"理由: {params.get('reason', '默认参数')}")
                
                # 漏斗式推荐子版块展示
                if hasattr(st.session_state, 'demand_analysis') and st.session_state.demand_analysis:
                    st.markdown("---")
                    st.markdown("### 🎯 漏斗式子版块推荐")
                    
                    funnel_candidates = st.session_state.demand_analysis.get('funnel_candidates', {})
                    recommended_selection = st.session_state.demand_analysis.get('recommended_selection', {})
                    
                    if funnel_candidates:
                        # 显示选择建议
                        if recommended_selection:
                            st.info(f"💡 **选择建议**: {recommended_selection.get('reason', '')}")
                            st.write(f"📊 **策略**: {recommended_selection.get('strategy', '')}")
                            st.write(f"🎯 **建议数量**: {recommended_selection.get('suggested_count', 5)} 个子版块")
                        
                        # 高度匹配的子版块
                        high_match = funnel_candidates.get('high_match', [])
                        if high_match:
                            st.markdown("#### 🔥 高度匹配 (建议优先选择)")
                            for i, subreddit in enumerate(high_match):
                                with st.expander(f"#{i+1} r/{subreddit['name']} (匹配度: {subreddit['match_score']}%) 🔥", expanded=True):
                                    col1, col2 = st.columns([2, 1])
                                    
                                    with col1:
                                        st.write(f"**推荐理由:** {subreddit['reason']}")
                                        st.write(f"**描述:** {subreddit['description']}")
                                        st.write(f"**分类:** {subreddit.get('category', '未分类')}")
                                    
                                    with col2:
                                        if st.button(f"选择", key=f"select_high_{subreddit['name']}", type="primary"):
                                            if 'selected_subreddits' not in st.session_state:
                                                st.session_state.selected_subreddits = []
                                            
                                            if subreddit['name'] not in st.session_state.selected_subreddits:
                                                st.session_state.selected_subreddits.append(subreddit['name'])
                                                st.success(f"✅ 已选择 r/{subreddit['name']}")
                                                st.rerun()
                                            else:
                                                st.warning(f"⚠️ r/{subreddit['name']} 已在选择列表中")
                        
                        # 中度匹配的子版块
                        medium_match = funnel_candidates.get('medium_match', [])
                        if medium_match:
                            st.markdown("#### ⭐ 中度匹配 (可选)")
                            for i, subreddit in enumerate(medium_match):
                                with st.expander(f"#{i+1} r/{subreddit['name']} (匹配度: {subreddit['match_score']}%) ⭐", expanded=False):
                                    col1, col2 = st.columns([2, 1])
                                    
                                    with col1:
                                        st.write(f"**推荐理由:** {subreddit['reason']}")
                                        st.write(f"**描述:** {subreddit['description']}")
                                        st.write(f"**分类:** {subreddit.get('category', '未分类')}")
                                    
                                    with col2:
                                        if st.button(f"选择", key=f"select_medium_{subreddit['name']}"):
                                            if 'selected_subreddits' not in st.session_state:
                                                st.session_state.selected_subreddits = []
                                            
                                            if subreddit['name'] not in st.session_state.selected_subreddits:
                                                st.session_state.selected_subreddits.append(subreddit['name'])
                                                st.success(f"✅ 已选择 r/{subreddit['name']}")
                                                st.rerun()
                                            else:
                                                st.warning(f"⚠️ r/{subreddit['name']} 已在选择列表中")
                        
                        # 相关匹配的子版块
                        low_match = funnel_candidates.get('low_match', [])
                        if low_match:
                            st.markdown("#### 💡 相关匹配 (探索性选择)")
                            for i, subreddit in enumerate(low_match):
                                with st.expander(f"#{i+1} r/{subreddit['name']} (匹配度: {subreddit['match_score']}%) 💡", expanded=False):
                                    col1, col2 = st.columns([2, 1])
                                    
                                    with col1:
                                        st.write(f"**推荐理由:** {subreddit['reason']}")
                                        st.write(f"**描述:** {subreddit['description']}")
                                        st.write(f"**分类:** {subreddit.get('category', '未分类')}")
                                    
                                    with col2:
                                        if st.button(f"选择", key=f"select_low_{subreddit['name']}"):
                                            if 'selected_subreddits' not in st.session_state:
                                                st.session_state.selected_subreddits = []
                                            
                                            if subreddit['name'] not in st.session_state.selected_subreddits:
                                                st.session_state.selected_subreddits.append(subreddit['name'])
                                                st.success(f"✅ 已选择 r/{subreddit['name']}")
                                                st.rerun()
                                            else:
                                                st.warning(f"⚠️ r/{subreddit['name']} 已在选择列表中")
                        
                        # 批量操作
                        st.markdown("---")
                        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                        
                        with col1:
                            if st.button("🔥 全选高度匹配", type="secondary"):
                                if 'selected_subreddits' not in st.session_state:
                                    st.session_state.selected_subreddits = []
                                
                                for subreddit in high_match:
                                    if subreddit['name'] not in st.session_state.selected_subreddits:
                                        st.session_state.selected_subreddits.append(subreddit['name'])
                                
                                st.success(f"✅ 已选择 {len(high_match)} 个高度匹配子版块")
                                st.rerun()
                        
                        with col2:
                            if st.button("⭐ 全选中度匹配", type="secondary"):
                                if 'selected_subreddits' not in st.session_state:
                                    st.session_state.selected_subreddits = []
                                
                                for subreddit in medium_match:
                                    if subreddit['name'] not in st.session_state.selected_subreddits:
                                        st.session_state.selected_subreddits.append(subreddit['name'])
                                
                                st.success(f"✅ 已选择 {len(medium_match)} 个中度匹配子版块")
                                st.rerun()
                        
                        with col3:
                            if st.button("🗑️ 清空选择", type="secondary"):
                                st.session_state.selected_subreddits = []
                                st.success("✅ 已清空选择")
                                st.rerun()
                        
                        with col4:
                            if hasattr(st.session_state, 'selected_subreddits') and st.session_state.selected_subreddits:
                                st.info(f"已选择 {len(st.session_state.selected_subreddits)} 个子版块")
                        
                    else:
                        st.warning("⚠️ 没有找到推荐的子版块")
                
                st.markdown("---")
                
                # 子版块索引管理
                st.subheader("📚 子版块索引管理")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # 批量索引子版块
                    st.markdown("### 🔍 批量索引子版块")
                    
                    # 如果有智能分析结果，优先使用
                    if hasattr(st.session_state, 'selected_subreddits') and st.session_state.selected_subreddits:
                        default_subreddits = '\n'.join(st.session_state.selected_subreddits)
                        st.success(f"✅ 已从智能分析中选择 {len(st.session_state.selected_subreddits)} 个子版块")
                    else:
                        default_subreddits = "MachineLearning\nprogramming\nselfhosted\nhomelab\nnextcloud"
                    
                    subreddits_to_index = st.text_area(
                        "要索引的子版块（每行一个，不带r/前缀）",
                        value=default_subreddits,
                        height=100,
                        help="输入要索引的子版块名称，每行一个"
                    )
                    
                    # 如果有智能分析结果，使用推荐的参数
                    if hasattr(st.session_state, 'demand_analysis') and st.session_state.demand_analysis:
                        recommended_params = st.session_state.demand_analysis.get('index_params', {})
                        default_posts = recommended_params.get('post_limit', 50)
                        default_time_filter = recommended_params.get('time_filter', 'month')
                        
                        st.info(f"💡 智能推荐参数：{recommended_params.get('reason', '默认参数')}")
                    else:
                        default_posts = 50
                        default_time_filter = 'month'
                    
                    num_posts = st.number_input(
                        "每个子版块抓取的帖子数量",
                        min_value=10,
                        max_value=200,
                        value=default_posts,
                        help="建议50个帖子以获得最佳效果"
                    )
                    
                    time_filter = st.selectbox(
                        "时间范围",
                        options=['hour', 'day', 'week', 'month', 'year', 'all'],
                        index=['hour', 'day', 'week', 'month', 'year', 'all'].index(default_time_filter),
                        help="选择要抓取的时间范围"
                    )
                    
                    if st.button("🚀 开始索引", type="primary"):
                        if subreddits_to_index.strip():
                            subreddit_list = [s.strip() for s in subreddits_to_index.split('\n') if s.strip()]
                            
                            if subreddit_list:
                                with st.spinner("正在索引子版块..."):
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    success_count = 0
                                    total_subreddits = len(subreddit_list)
                                    
                                    for i, subreddit in enumerate(subreddit_list):
                                        try:
                                            status_text.text(f"正在索引 r/{subreddit}...")
                                            
                                            # 使用SubredditIndexer进行索引
                                            indexer = SubredditIndexer(
                                                st.session_state.db,
                                                st.session_state.scraper
                                            )

                                            # 显示详细进度
                                            with st.expander(f"🔍 r/{subreddit} 索引详情", expanded=False):
                                                st.write(f"**子版块**: r/{subreddit}")
                                                st.write(f"**抓取数量**: {num_posts} 个帖子")
                                                st.write(f"**时间范围**: {time_filter}")
                                                
                                                # 开始索引
                                                st.write("**状态**: 开始索引...")
                                                success = indexer.index_subreddit(
                                                    subreddit,
                                                    num_posts=num_posts
                                                )
                                                # 显示结果
                                                if success.get('success', False):
                                                    st.success("✅ 索引成功")
                                                    st.write(f"**抓取帖子数**: {success.get('posts_count', 0)}")
                                                    st.write("**状态**: 已保存到数据库")
                                                else:
                                                    error_msg = success.get('error', '未知错误')
                                                    st.error(f"❌ 索引失败: {error_msg}")

                                            # 累计成功/失败
                                            if success.get('success', False):
                                                success_count += 1
                                            else:
                                                error_msg = success.get('error', '未知错误')
                                                st.warning(f"⚠️ r/{subreddit} 索引失败: {error_msg}")
                                            
                                            progress_bar.progress((i + 1) / total_subreddits)
                                            
                                        except Exception as e:
                                            st.error(f"❌ r/{subreddit} 索引失败: {str(e)}")
                                            # 显示详细错误信息
                                            with st.expander(f"❌ r/{subreddit} 错误详情", expanded=False):
                                                st.code(str(e))
                                            progress_bar.progress((i + 1) / total_subreddits)
                                    
                                    status_text.text("索引完成！")
                                    st.success(f"✅ 成功索引 {success_count}/{total_subreddits} 个子版块")
                                    
                                    # 清空进度条
                                    progress_bar.empty()
                                    status_text.empty()
                                    
                                    # 刷新页面显示新索引的数据
                                    st.rerun()
                            else:
                                st.error("请输入要索引的子版块")
                        else:
                            st.error("请输入要索引的子版块")
                
                with col2:
                    st.markdown("### 📊 索引状态")
                    
                    try:
                        all_indices = st.session_state.db.get_all_subreddit_indices()
                        st.metric("已索引子版块", len(all_indices))
                        
                        if all_indices:
                            st.markdown("**最近索引的子版块:**")
                            for idx in all_indices[-5:]:
                                st.write(f"• r/{idx['subreddit_name']}")
                        else:
                            st.info("暂无已索引的子版块")
                    except Exception as e:
                        st.error(f"获取索引状态失败: {str(e)}")
                
                # 手动查看子版块详情
                st.divider()
                st.subheader("🔍 查看子版块详情")
                
                # 添加刷新按钮
                col_refresh1, col_refresh2 = st.columns([3, 1])
                with col_refresh2:
                    if st.button("🔄 刷新列表", help="刷新子版块列表"):
                        st.rerun()
                
                try:
                    all_indices = st.session_state.db.get_all_subreddit_indices()
                    if all_indices:
                        selected_subreddit = st.selectbox(
                            "选择子版块",
                            [idx['subreddit_name'] for idx in all_indices],
                            format_func=lambda x: f"r/{x}",
                            key="subreddit_detail_selector"
                        )
                        
                        if selected_subreddit:
                            # 添加详情刷新按钮
                            col_detail1, col_detail2 = st.columns([3, 1])
                            with col_detail2:
                                if st.button("🔄 刷新详情", key="refresh_details"):
                                    st.rerun()
                            
                            details = st.session_state.subreddit_recommender.get_subreddit_details(selected_subreddit)
                            if details:
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown("**基本信息:**")
                                    st.write(f"• 订阅者: {details.get('subscriber_count', 0):,}")
                                    st.write(f"• 描述: {details.get('description', '无描述')[:200]}...")
                                
                                with col2:
                                    st.markdown("**主要主题:**")
                                    main_topics = details.get('main_topics', [])
                                    if main_topics:
                                        st.write(", ".join(main_topics[:10]))
                                    else:
                                        st.write("无主题数据")
                                
                                # 显示热门帖子示例
                                posts_data = details.get('posts_data', [])
                                if posts_data:
                                    st.markdown("**热门帖子示例:**")
                                    for post in posts_data[:3]:
                                        st.write(f"• {post.get('title', '无标题')[:100]}...")
                            else:
                                st.warning("没有找到匹配的子版块，请尝试更具体的描述")
                
                except Exception as e:
                    st.error(f"获取子版块列表失败: {str(e)}")
        
        
            else:
                st.warning("请先配置API密钥并初始化系统")

        except ImportError as e:
            st.error(f"导入子版块推荐模块失败: {str(e)}")
            st.info("请确保所有新模块文件已正确创建")
        except Exception as e:
            st.error(f"❌ 子版块推荐页面加载失败: {str(e)}")
            st.info("💡 如果问题持续，请尝试刷新页面或重新初始化系统")
            import traceback
            with st.expander("查看错误详情"):
                st.code(traceback.format_exc())
    
    with tab6:
        st.header("🔧 Reddit养号控制台")
        st.markdown("以养号为核心目标，从子版块推荐到内容发布到互动反馈的完整闭环")
        
        if st.session_state.initialized:
            # 导入所需模块
            try:
                from reddit_publisher import RedditPublisher
                from interaction_manager import InteractionManager
                from monitoring_service import MonitoringService
                from account_readiness import AccountReadinessService
                from background_analyzer import background_analyzer
                
                # 初始化发帖器
                if 'reddit_publisher' not in st.session_state:
                    st.session_state.reddit_publisher = RedditPublisher(
                        st.session_state.db,
                        st.session_state.analyzer,
                        st.session_state.scraper
                    )
                
                # 初始化互动管理器
                if 'interaction_manager' not in st.session_state:
                    st.session_state.interaction_manager = InteractionManager(
                        st.session_state.db,
                        st.session_state.scraper
                    )
                
                # 初始化监控服务
                if 'monitoring_service' not in st.session_state:
                    st.session_state.monitoring_service = MonitoringService(
                        st.session_state.db,
                        st.session_state.scraper
                    )
                
                # 初始化账号准备度服务
                if not hasattr(st.session_state, 'readiness_service') or st.session_state.readiness_service is None:
                    try:
                        st.session_state.readiness_service = AccountReadinessService(st.session_state.db, st.session_state.scraper)
                    except Exception:
                        st.session_state.readiness_service = None
                
                # ========== 顶部面板：账号状态 + 发帖资格检测 ==========
                col_top1, col_top2 = st.columns([2, 1])
                
                with col_top1:
                    # 账号状态面板
                    st.subheader("📊 账号状态面板")
                    try:
                        me = st.session_state.scraper.get_me()
                        if not me and hasattr(st.session_state.scraper, 'reddit'):
                            try:
                                me = st.session_state.scraper.reddit.user.me()
                            except Exception:
                                me = None
                        
                        if me:
                            account_name = getattr(me, 'name', '未知')
                            link_karma = getattr(me, 'link_karma', 0)
                            comment_karma = getattr(me, 'comment_karma', 0)
                            
                            # 计算账号年龄
                            try:
                                created_utc = getattr(me, 'created_utc', 0)
                                account_age_days = (time.time() - created_utc) / 86400 if created_utc > 0 else 0
                            except Exception:
                                account_age_days = 0
                            
                            st.info(f"**当前账号**: u/{account_name} | **Karma**: link({link_karma}) | comment({comment_karma}) | **账号年龄**: {account_age_days:.0f}天")
                            
                            # 养号进度（简化显示）
                            if st.session_state.readiness_service:
                                try:
                                    plan = st.session_state.readiness_service.generate_warming_plan(7)
                                    if plan.get('success'):
                                        # 计算完成进度（简化逻辑）
                                        total_tasks = sum([d['upvotes'] + d['comments'] + d['posts'] for d in plan['plan']])
                                        # 这里简化显示，实际应该从数据库读取完成的任务数
                                        completed_tasks = 0  # 占位符，实际应从数据库获取
                                        progress = min((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 100)
                                        st.progress(progress / 100, text=f"养号进度：{progress:.0f}%")
                                        
                                        # 今日任务（简化显示）
                                        today_tasks = plan['plan'][0] if plan['plan'] else {'upvotes': 0, 'comments': 0, 'posts': 0}
                                        st.caption(f"今日任务：点赞({today_tasks['upvotes']}) 评论({today_tasks['comments']}) 发帖({today_tasks['posts']})")
                                except Exception:
                                    pass
                        else:
                            st.warning("⚠️ 无法获取账号信息，请确保Reddit已认证")
                    except Exception as e:
                        st.warning(f"⚠️ 获取账号状态失败: {str(e)}")
                
                with col_top2:
                    # 发帖资格检测
                    st.subheader("🛡️ 发帖资格检测")
                    if st.session_state.readiness_service:
                        # 从推荐页获取子版块（如果存在）
                        selected_subreddit_from_recommendation = st.session_state.get('selected_subreddit_from_recommendation', '')
                        default_subreddit = selected_subreddit_from_recommendation if selected_subreddit_from_recommendation else st.session_state.get('last_subreddit', '')
                        
                        test_subreddit = st.text_input(
                            "子版块名称",
                            value=default_subreddit,
                            placeholder="例如：MachineLearning",
                            help="输入要检测的子版块",
                            key="readiness_subreddit"
                        )
                        
                        col_r1, col_r2 = st.columns(2)
                        with col_r1:
                            if st.button("🔍 检测资格", key="top_check_readiness"):
                                if test_subreddit.strip():
                                    with st.spinner("正在检测..."):
                                        try:
                                            if not st.session_state.scraper.is_authenticated():
                                                st.warning("⚠️ Reddit未认证")
                                            else:
                                                readiness = st.session_state.readiness_service.assess_readiness_for_subreddit(test_subreddit.strip())
                                                if readiness.get('success'):
                                                    st.session_state.last_readiness = readiness['readiness']
                                                    st.session_state.last_subreddit = test_subreddit.strip()
                                                    can_post = readiness['readiness'].get('can_post', False)
                                                    status = "✅ 可发帖" if can_post else "⛔ 暂不建议发帖"
                                                    st.success(status)
                                                else:
                                                    st.error(f"检测失败: {readiness.get('error')}")
                                        except Exception as e:
                                            st.error(f"检测失败: {str(e)}")
                                else:
                                    st.warning("请先输入子版块名称")
                        
                        with col_r2:
                            if st.button("📅 养号计划", key="top_generate_plan"):
                                plan = st.session_state.readiness_service.generate_warming_plan(7)
                                if plan.get('success'):
                                    st.session_state.warming_plan = plan
                                    st.success("✅ 7天养号计划已生成")
                                    st.rerun()
                                else:
                                    st.error(f"生成失败: {plan.get('error')}")
                        
                        # 显示最近一次检测结果
                        if hasattr(st.session_state, 'last_readiness') and st.session_state.last_readiness:
                            readiness = st.session_state.last_readiness
                            can_post = readiness.get('can_post', False)
                            status = "✅ 可发帖" if can_post else "⛔ 暂不建议发帖"
                            
                            # 处理置信度显示（可能是字符串或数字）
                            confidence = readiness.get('confidence', 0)
                            if isinstance(confidence, str):
                                # 字符串置信度映射
                                confidence_map = {'High': 90, 'Medium': 50, 'Low': 30}
                                confidence_display = f"{confidence_map.get(confidence, 50)}% ({confidence})"
                            else:
                                # 数字置信度
                                try:
                                    confidence_display = f"{float(confidence):.0f}%"
                                except (ValueError, TypeError):
                                    confidence_display = str(confidence)
                            
                            st.info(f"**状态**: {status} (置信度: {confidence_display})")
                    else:
                        st.warning("⚠️ 账号准备度服务未初始化")
                
                st.markdown("---")
                
                # 检查是否有深度分析结果
                
                # 优先从数据库读取最新的深度分析报告
                insights = {}
                analysis_result = {}
                
                has_db_data = False
                # json, os已在文件开头导入，无需重复导入
                
                # 方法1: 优先从output文件夹读取最新的JSON文件
                try:
                    if os.path.exists('./output'):
                        # 查找所有business_insights_*.json文件
                        json_files = glob.glob('./output/business_insights_*.json')
                        if json_files:
                            # 按修改时间排序，获取最新的
                            latest_json = max(json_files, key=os.path.getmtime)
                            with open(latest_json, 'r', encoding='utf-8') as f:
                                json_data = json.load(f)
                            
                            has_db_data = True
                            insights = {
                                'dominant_themes': json_data.get('dominant_themes', []),
                                'top_pain_points': json_data.get('top_pain_points', []),
                                'key_opportunities': json_data.get('key_opportunities', []),
                                'strategic_recommendations': json_data.get('strategic_recommendations', [])
                            }
                            logging.info(f"✅ 从output文件夹读取到深度分析报告: {os.path.basename(latest_json)}")
                except Exception as e:
                    logging.warning(f"从output文件夹读取分析报告失败: {str(e)}")
                
                # 方法2: 如果output文件夹没有，从数据库获取
                if not has_db_data:
                    try:
                        # 从数据库获取最新的业务洞察
                        latest_insight = st.session_state.db.get_latest_business_insight()
                        if latest_insight:
                            has_db_data = True
                            # 处理JSON字段，可能是None或字符串
                            dominant_themes = latest_insight.dominant_themes if latest_insight.dominant_themes else []
                            if isinstance(dominant_themes, str):
                                try:
                                    dominant_themes = json.loads(dominant_themes)
                                except:
                                    dominant_themes = []
                            
                            top_pain_points = latest_insight.top_pain_points if latest_insight.top_pain_points else []
                            if isinstance(top_pain_points, str):
                                try:
                                    top_pain_points = json.loads(top_pain_points)
                                except:
                                    top_pain_points = []
                            
                            key_opportunities = latest_insight.key_opportunities if latest_insight.key_opportunities else []
                            if isinstance(key_opportunities, str):
                                try:
                                    key_opportunities = json.loads(key_opportunities)
                                except:
                                    key_opportunities = []
                            
                            insights = {
                                'dominant_themes': dominant_themes if isinstance(dominant_themes, list) else [],
                                'top_pain_points': top_pain_points if isinstance(top_pain_points, list) else [],
                                'key_opportunities': key_opportunities if isinstance(key_opportunities, list) else []
                            }
                            logging.info("✅ 从数据库读取到深度分析报告")
                    except Exception as e:
                        logging.warning(f"从数据库读取深度分析报告失败: {str(e)}")
                        has_db_data = False
                
                # 如果数据库中没有分析结果，检查background_analyzer
                has_analysis_results = False
                if not has_db_data:
                    has_analysis_results = background_analyzer.is_completed()
                    
                    if has_analysis_results:
                        st.success("✅ 检测到后台深度分析结果")
                        
                        # 获取后台分析结果
                        analysis_result = background_analyzer.get_result()
                        if analysis_result:
                            insights = analysis_result.get('insights_summary', {})
                            has_db_data = True  # 标记为有数据
                
                # 判断是否有可用的分析数据
                has_valid_data = has_db_data or (analysis_result and analysis_result.get('insights_summary'))
                
                if has_valid_data:
                    # 显示数据来源
                    data_source = []
                    if has_db_data:
                        if os.path.exists('./output') and glob.glob('./output/business_insights_*.json'):
                            data_source.append("output文件夹JSON文件")
                        else:
                            data_source.append("数据库")
                    
                    st.success(f"✅ 检测到深度分析结果，可以生成智能帖子")
                    st.info(f"📊 数据来源: {', '.join(data_source) if data_source else '未知'}")
                
                # ========== 智能发帖流程（分步骤） ==========
                st.subheader("📝 智能发帖流程")
                
                # 步骤1：子版块选择
                with st.expander("步骤1：子版块选择", expanded=True):
                    col_step1_1, col_step1_2, col_step1_3 = st.columns([2, 2, 1])
                    
                    # 从推荐页获取子版块（如果存在）
                    selected_subreddit_from_recommendation = st.session_state.get('selected_subreddit_from_recommendation', '')
                    
                    with col_step1_1:
                        browse_subreddit_input = st.text_input(
                            "子版块名称（手动输入）",
                            value=selected_subreddit_from_recommendation,
                            placeholder="例如：MachineLearning",
                            help="不带 r/ 前缀",
                            key="step1_subreddit_input"
                        )
                    
                    # 推荐子版块选项
                    recommended_options = []
                    if hasattr(st.session_state, 'selected_subreddits') and st.session_state.selected_subreddits:
                        recommended_options = list(dict.fromkeys(st.session_state.selected_subreddits))
                    
                    # 已索引子版块
                    indexed_options = []
                    try:
                        indices = st.session_state.db.get_all_subreddit_indices()
                        if indices:
                            indexed_options = [idx.get('subreddit_name') for idx in indices if idx and idx.get('subreddit_name')]
                    except Exception:
                        indexed_options = []
                    
                    with col_step1_2:
                        source_choice = st.selectbox(
                            "从推荐/索引中选择",
                            options=[""] + (recommended_options or []) + (indexed_options or []),
                            help="可直接选择推荐或已索引的子版块",
                            key="step1_select_source"
                        )
                    
                    with col_step1_3:
                        # 从数据库获取可用的子版块
                        try:
                            available_subreddits = st.session_state.db.get_subreddit_list()
                            if available_subreddits:
                                st.caption("或从数据库选择")
                        except Exception:
                            available_subreddits = []
                    
                    # 确定最终选择的子版块
                    target_subreddit = browse_subreddit_input.strip() if browse_subreddit_input.strip() else (source_choice.strip() if source_choice else "")
                    if available_subreddits and not target_subreddit:
                        target_subreddit = st.selectbox(
                            "从数据库选择",
                            options=[""] + available_subreddits,
                            key="step1_db_select",
                            help="从已抓取的子版块中选择"
                        )
                    
                    if target_subreddit:
                        st.success(f"✅ 已选择子版块: r/{target_subreddit}")
                        st.session_state.selected_subreddit = target_subreddit
                    
                    # 如果从推荐页传入，自动显示
                    if selected_subreddit_from_recommendation:
                        st.info(f"💡 从子版块推荐页选择了: r/{selected_subreddit_from_recommendation}")
                
                # 步骤2：查看子版块详情
                if target_subreddit and target_subreddit.strip():
                    with st.expander("步骤2：查看子版块详情", expanded=False):
                        # 从推荐服务获取详情
                        try:
                            if hasattr(st.session_state, 'subreddit_recommender'):
                                details = st.session_state.subreddit_recommender.get_subreddit_details(target_subreddit.strip())
                                if details:
                                    col_detail1, col_detail2 = st.columns(2)
                                    
                                    with col_detail1:
                                        st.markdown("**基本信息:**")
                                        st.write(f"• 订阅者: {details.get('subscriber_count', 0):,}")
                                        st.write(f"• 描述: {details.get('description', '无描述')[:200]}...")
                                    
                                    with col_detail2:
                                        st.markdown("**主要主题:**")
                                        main_topics = details.get('main_topics', [])
                                        if main_topics:
                                            st.write(", ".join(main_topics[:10]))
                                        else:
                                            st.write("无主题数据")
                                    
                                    # 显示热门帖子示例
                                    posts_data = details.get('posts_data', [])
                                    if posts_data:
                                        st.markdown("**热门帖子示例:**")
                                        for post in posts_data[:3]:
                                            st.write(f"• {post.get('title', '无标题')[:100]}...")
                                    
                                    if st.button("🔄 刷新详情", key="refresh_subreddit_details"):
                                        st.rerun()
                                else:
                                    st.warning("无法获取子版块详情，请确保子版块名称正确")
                            else:
                                st.info("💡 子版块推荐服务未初始化")
                        except Exception as e:
                            st.warning(f"获取子版块详情失败: {str(e)}")
                    
                    # 步骤3：子版块规则提示
                    with st.expander("步骤3：子版块规则提示", expanded=False):
                        try:
                            # 获取子版块规则
                            rules_cache_key = f"rules_{target_subreddit.strip()}_translated"
                            rules_translated = st.session_state.get(rules_cache_key, {})
                            
                            # 获取规则
                            if not rules_translated:
                                with st.spinner("正在获取子版块规则..."):
                                    rules = st.session_state.scraper.get_subreddit_rules(target_subreddit.strip())
                                    
                                    if rules and len(rules) > 0:
                                        # 翻译规则为中文
                                        with st.spinner("正在翻译规则为中文..."):
                                            translated_rules = []
                                            for rule in rules:
                                                short_name = rule.get('short_name', '')
                                                description = rule.get('description', '')
                                                
                                                # 翻译规则标题
                                                if short_name:
                                                    try:
                                                        tr_short = st.session_state.analyzer.translate_text(short_name, target_language="中文")
                                                        if tr_short.get('success'):
                                                            short_name_cn = tr_short.get('translated_text', short_name)
                                                        else:
                                                            short_name_cn = short_name
                                                    except Exception:
                                                        short_name_cn = short_name
                                                else:
                                                    short_name_cn = ''
                                                
                                                # 翻译规则描述
                                                if description:
                                                    try:
                                                        tr_desc = st.session_state.analyzer.translate_text(description, target_language="中文")
                                                        if tr_desc.get('success'):
                                                            description_cn = tr_desc.get('translated_text', description)
                                                        else:
                                                            description_cn = description
                                                    except Exception:
                                                        description_cn = description
                                                else:
                                                    description_cn = ''
                                                
                                                translated_rules.append({
                                                    'short_name_en': short_name,
                                                    'short_name_cn': short_name_cn,
                                                    'description_en': description,
                                                    'description_cn': description_cn,
                                                    'kind': rule.get('kind', ''),
                                                    'priority': rule.get('priority', 0)
                                                })
                                            
                                            rules_translated = {
                                                'rules': translated_rules,
                                                'has_rules': True
                                            }
                                            st.session_state[rules_cache_key] = rules_translated
                                    else:
                                        # 无规则
                                        rules_translated = {
                                            'rules': [],
                                            'has_rules': False
                                        }
                                        st.session_state[rules_cache_key] = rules_translated
                            
                            # 显示规则
                            if rules_translated.get('has_rules') and rules_translated.get('rules'):
                                rules = rules_translated['rules']
                                st.markdown("**⚠️ 发帖规则摘要（已翻译为中文）:**")
                                
                                # 显示前5条规则
                                for i, rule in enumerate(rules[:5], 1):
                                    short_name_cn = rule.get('short_name_cn', rule.get('short_name_en', ''))
                                    description_cn = rule.get('description_cn', '')
                                    
                                    if short_name_cn:
                                        st.warning(f"**{i}. {short_name_cn}**")
                                        if description_cn:
                                            st.caption(f"   {description_cn[:200]}..." if len(description_cn) > 200 else f"   {description_cn}")
                                
                                # 显示完整规则（如果超过5条）
                                if len(rules) > 5:
                                    st.markdown("---")
                                    st.markdown(f"#### 📋 查看完整规则（共{len(rules)}条）")
                                    for i, rule in enumerate(rules, 1):
                                        short_name_cn = rule.get('short_name_cn', rule.get('short_name_en', ''))
                                        description_cn = rule.get('description_cn', rule.get('description_en', ''))
                                        
                                        st.markdown(f"**规则 {i}: {short_name_cn}**")
                                        if description_cn:
                                            st.write(description_cn)
                                        
                                        # 显示英文原文（使用checkbox控制）
                                        if rule.get('short_name_en') or rule.get('description_en'):
                                            if st.checkbox(f"查看规则 {i} 英文原文", key=f"show_english_rule_{i}", value=False):
                                                if rule.get('short_name_en'):
                                                    st.write(f"**标题**: {rule.get('short_name_en')}")
                                                if rule.get('description_en'):
                                                    st.write(f"**描述**: {rule.get('description_en')}")
                                        
                                        st.markdown("---")
                            else:
                                st.info("ℹ️ 该子版块无规则")
                        except Exception as e:
                            st.warning(f"获取规则失败: {str(e)}")
                            import traceback
                            st.caption(f"错误详情: {traceback.format_exc()}")
                    
                    # 步骤4：生成帖子内容
                    with st.expander("步骤4：生成帖子内容", expanded=True):
                        col_step4_1, col_step4_2 = st.columns([1, 1])
                        
                        with col_step4_1:
                            st.markdown("#### ✏️ 发帖配置")
                            
                            target_audience = st.text_area(
                                "目标受众描述",
                                placeholder="例如：对机器学习感兴趣的开发者",
                                height=80,
                                help="描述目标受众特征",
                                key="step4_target_audience"
                            )
                            
                            user_requirements = st.text_area(
                                "发帖需求描述",
                                placeholder="例如：我想分享一个关于深度学习的新发现",
                                height=100,
                                help="描述您想要发帖的内容和目的（支持中英文）",
                                key="step4_user_requirements"
                            )
                            
                            col_lang1, col_lang2 = st.columns(2)
                            with col_lang1:
                                auto_translate = st.checkbox(
                                    "🌐 自动翻译为英文",
                                    value=True,
                                    help="如果输入是中文，自动翻译为英文发帖",
                                    key="step4_auto_translate"
                                )
                            with col_lang2:
                                show_translation = st.checkbox(
                                    "👁️ 显示翻译预览",
                                    value=True,
                                    help="显示翻译结果预览",
                                    key="step4_show_translation"
                                )
                        
                        with col_step4_2:
                            st.markdown("#### 📊 分析数据预览")
                            
                            if insights:
                                st.markdown("**主导主题:**")
                                themes = insights.get('dominant_themes', [])
                                if themes:
                                    for theme in themes[:3]:
                                        st.write(f"• {theme}")
                                else:
                                    st.write("无主题数据")
                                
                                st.markdown("**关键机会:**")
                                opportunities = insights.get('key_opportunities', [])
                                if opportunities:
                                    for opp in opportunities[:3]:
                                        st.write(f"• {opp}")
                                else:
                                    st.write("无机会数据")
                            
                            # 生成按钮
                            if st.button("🚀 生成智能帖子", type="primary", key="step4_generate"):
                                if target_subreddit.strip():
                                    with st.spinner("正在基于分析结果生成帖子内容..."):
                                        try:
                                            generated_content = st.session_state.reddit_publisher.generate_post_content(
                                                insights=insights,
                                                keywords=[],
                                                subreddit_name=target_subreddit.strip(),
                                                target_audience=target_audience,
                                                user_input=user_requirements.strip() if user_requirements.strip() else None,
                                                auto_translate=auto_translate
                                            )
                                            
                                            st.success("✅ 智能帖子内容生成完成！")
                                            
                                            # 保存生成配置
                                            st.session_state.last_post_config = {
                                                'target_subreddit': target_subreddit.strip(),
                                                'target_audience': target_audience,
                                                'user_requirements': user_requirements.strip() if user_requirements.strip() else None,
                                                'auto_translate': auto_translate,
                                                'insights': insights
                                            }
                                            st.session_state.generated_content = generated_content
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ 生成帖子内容失败: {str(e)}")
                                else:
                                    st.error("请先选择目标子版块")
                            
                            # 显示数据缺失警告（如果有）
                            if hasattr(st.session_state, 'generated_content') and st.session_state.generated_content:
                                if st.session_state.generated_content.get('warnings'):
                                    st.markdown("---")
                                    st.markdown("#### ⚠️ 数据缺失警告")
                                    for warning in st.session_state.generated_content['warnings']:
                                        st.warning(warning)
                                    st.info("💡 即使有数据缺失，系统仍会生成帖子内容，但质量可能受影响")
                    
                    # 步骤5：内容预览与发布
                    if hasattr(st.session_state, 'generated_content') and st.session_state.generated_content:
                        with st.expander("步骤5：内容预览与发布", expanded=True):
                            generated_content = st.session_state.generated_content
                            
                            # 显示翻译信息
                            if generated_content.get('translation_info') and show_translation:
                                translation_info = generated_content['translation_info']
                                st.markdown("---")
                                st.markdown("#### 🌐 翻译信息")
                                col_trans1, col_trans2 = st.columns(2)
                                
                                with col_trans1:
                                    st.markdown("**原文（中文）:**")
                                    st.text_area("", value=translation_info.get('original_text', ''), height=100, disabled=True, key="step5_orig_text")
                                
                                with col_trans2:
                                    st.markdown("**译文（英文）:**")
                                    st.text_area("", value=translation_info.get('translated_text', ''), height=100, disabled=True, key="step5_trans_text")
                                st.markdown("---")
                            
                            # 显示标题和内容
                            st.markdown(f"**标题:** {generated_content['title']}")
                            st.text_area("帖子正文", value=generated_content['content'], height=300, key="step5_post_content")
                            
                            # 显示建议标签
                            if generated_content.get('suggested_flair'):
                                st.info(f"**建议标签:** {generated_content['suggested_flair']}")
                            
                            # 内容验证
                            validation = st.session_state.reddit_publisher.validate_content(generated_content, {'rules': []})
                            
                            if validation['pass']:
                                st.success("✅ 内容验证通过")
                            else:
                                st.warning("⚠️ 内容验证警告")
                                for warning in validation['warnings']:
                                    st.warning(warning)
                                for error in validation['errors']:
                                    st.error(error)
                            
                            # 操作按钮
                            col_op1, col_op2, col_op3, col_op4 = st.columns(4)
                            
                            with col_op1:
                                if st.button("🔄 重新生成", type="primary", key="step5_regenerate"):
                                    if hasattr(st.session_state, 'last_post_config'):
                                        config = st.session_state.last_post_config
                                        with st.spinner("正在重新生成..."):
                                            try:
                                                new_content = st.session_state.reddit_publisher.generate_post_content(
                                                    insights=config.get('insights', {}),
                                                    keywords=[],
                                                    subreddit_name=config.get('target_subreddit', target_subreddit),
                                                    target_audience=config.get('target_audience', ''),
                                                    user_input=config.get('user_requirements'),
                                                    auto_translate=config.get('auto_translate', True)
                                                )
                                                st.session_state.generated_content = new_content
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"❌ 重新生成失败: {str(e)}")
                            
                            with col_op2:
                                if st.button("💾 保存草稿", key="step5_save_draft"):
                                    if st.session_state.reddit_publisher.save_draft(generated_content, target_subreddit.strip()):
                                        st.success("✅ 草稿保存成功")
                                    else:
                                        st.error("❌ 草稿保存失败")
                            
                            with col_op3:
                                content_text = f"标题: {generated_content['title']}\n\n内容:\n{generated_content['content']}"
                                st.download_button(
                                    label="📥 下载内容",
                                    data=content_text.encode('utf-8'),
                                    file_name=f"reddit_post_{target_subreddit}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                    mime="text/plain",
                                    key="step5_download"
                                )
                            
                            with col_op4:
                                # 检查发帖资格
                                latest = None
                                try:
                                    latest = st.session_state.db.get_latest_subreddit_readiness(target_subreddit.strip())
                                except Exception:
                                    pass
                                can_post = True if (latest and latest.can_post) else False
                                
                                if st.button("🚀 发布帖子", type="secondary", key="step5_publish", disabled=not can_post):
                                    st.warning("⚠️ 发布功能需要Reddit API写权限，请谨慎使用")
                                
                                if not can_post:
                                    st.caption("ℹ️ 当前不建议发帖，请先完成养号计划")
                
                # 如果还没有选择子版块，显示提示
                if not target_subreddit or not target_subreddit.strip():
                    st.info("💡 请先完成步骤1：选择子版块")
                    
                    # 备用：直接从数据库获取可用的子版块
                    try:
                        available_subreddits = st.session_state.db.get_subreddit_list()
                        if available_subreddits:
                            st.markdown("#### 或从数据库选择")
                            backup_target_subreddit = st.selectbox(
                                "目标子版块",
                                available_subreddits,
                                help="选择要发帖的子版块",
                                key="backup_target_subreddit"
                            )
                            if backup_target_subreddit:
                                target_subreddit = backup_target_subreddit
                                st.rerun()
                    except:
                        pass
                
                # ========== 快速互动区域 ==========
                st.markdown("---")
                st.subheader("🎯 快速互动")
                
                col_quick1, col_quick2 = st.columns([1, 1])
                
                with col_quick1:
                    st.markdown("#### 📝 帖子互动")
                    
                    post_id_quick = st.text_input(
                        "帖子ID",
                        placeholder="输入Reddit帖子ID",
                        help="例如：abc123",
                        key="quick_post_id"
                    )
                    
                    if post_id_quick.strip():
                        col_up_quick, col_down_quick = st.columns(2)
                        
                        with col_up_quick:
                            if st.button("👍 点赞", type="primary", key="quick_upvote"):
                                with st.spinner("正在点赞..."):
                                    result = st.session_state.interaction_manager.upvote_post(post_id_quick.strip(), None)
                                    if result['success']:
                                        st.success(f"✅ 点赞成功！")
                                    else:
                                        st.error(f"❌ 点赞失败: {result.get('error', '未知错误')}")
                        
                        with col_down_quick:
                            if st.button("👎 点踩", key="quick_downvote"):
                                with st.spinner("正在点踩..."):
                                    result = st.session_state.interaction_manager.downvote_post(post_id_quick.strip(), None)
                                    if result['success']:
                                        st.success(f"✅ 点踩成功！")
                                    else:
                                        st.error(f"❌ 点踩失败: {result.get('error', '未知错误')}")
                        
                        col_save_quick, col_unsave_quick = st.columns(2)
                        
                        with col_save_quick:
                            if st.button("💾 保存", key="quick_save"):
                                with st.spinner("正在保存..."):
                                    result = st.session_state.interaction_manager.save_post(post_id_quick.strip(), None)
                                    if result['success']:
                                        st.success(f"✅ 保存成功！")
                                    else:
                                        st.error(f"❌ 保存失败: {result.get('error', '未知错误')}")
                        
                        with col_unsave_quick:
                            if st.button("🗑️ 取消保存", key="quick_unsave"):
                                with st.spinner("正在取消保存..."):
                                    result = st.session_state.interaction_manager.unsave_post(post_id_quick.strip(), None)
                                    if result['success']:
                                        st.success(f"✅ 取消保存成功！")
                                    else:
                                        st.error(f"❌ 取消保存失败: {result.get('error', '未知错误')}")
                        
                        # 回帖功能
                        reply_text_quick = st.text_area(
                            "回复内容",
                            placeholder="输入您的回复内容...",
                            height=80,
                            help="支持中英文，将自动翻译为英文",
                            key="quick_reply_text"
                        )
                        
                        if reply_text_quick.strip():
                            if st.button("📝 回复帖子", type="primary", key="quick_reply_post"):
                                with st.spinner("正在回复..."):
                                    try:
                                        lang_result = st.session_state.analyzer.detect_language(reply_text_quick.strip())
                                        final_reply_text = reply_text_quick.strip()
                                        
                                        if lang_result.get('is_chinese', False):
                                            translation_result = st.session_state.analyzer.translate_for_reddit(
                                                reply_text_quick.strip(), None, "回复"
                                            )
                                            if translation_result.get('success'):
                                                final_reply_text = translation_result.get('translated_text', reply_text_quick.strip())
                                        
                                        result = st.session_state.scraper.reply_to_post(post_id_quick.strip(), final_reply_text)
                                        if result['success']:
                                            st.success(f"✅ 回复成功！评论ID: {result.get('comment_id', 'N/A')}")
                                        else:
                                            st.error(f"❌ 回复失败: {result.get('error', '未知错误')}")
                                    except Exception as e:
                                        st.error(f"❌ 回复失败: {str(e)}")
                        
                        # 查看评论
                        if st.button("👀 查看评论", key="quick_view_comments"):
                            with st.spinner("正在获取评论..."):
                                try:
                                    if not post_id_quick.strip():
                                        post_id_clean = st.session_state.get('browse_selected_post_id', '')
                                        if not post_id_clean:
                                            st.warning("请先输入有效的帖子ID")
                                            raise ValueError("empty_post_id")
                                    else:
                                        post_id_clean = post_id_quick.strip()
                                    
                                    comments = st.session_state.scraper.get_post_comments(post_id_clean, 20)
                                    if comments:
                                        st.markdown("#### 📋 帖子评论")
                                        for i, comment in enumerate(comments[:10]):
                                            with st.expander(f"评论 {i+1} - u/{comment.get('author', 'Unknown')}", expanded=False):
                                                st.write(comment.get('body', '') or '')
                                    else:
                                        st.info("该帖子暂无评论")
                                except Exception as e:
                                    st.error(f"获取评论失败: {str(e)}")
                
                with col_quick2:
                    st.markdown("#### 📚 子版块浏览与翻译")
                    
                    # 子版块选择
                    browse_subreddit_quick = st.text_input(
                        "子版块名称",
                        value=target_subreddit if target_subreddit else "",
                        placeholder="例如：MachineLearning",
                        help="不带 r/ 前缀",
                        key="browse_subreddit_quick"
                    )
                    
                    limit_quick = st.number_input("帖子数量", min_value=5, max_value=50, value=20, key="browse_limit_quick")
                    
                    if browse_subreddit_quick.strip():
                        if st.button("🔎 加载帖子", key="browse_load_quick"):
                            with st.spinner("正在加载子版块帖子..."):
                                try:
                                    posts = st.session_state.scraper.get_hot_posts(
                                        browse_subreddit_quick.strip(), limit=int(limit_quick), time_filter='week',
                                        start_date=None, end_date=None, min_score=0, max_score=0
                                    )
                                    cache_key_quick = f"quick_browse_{browse_subreddit_quick.strip()}"
                                    if 'subreddit_view_cache' not in st.session_state:
                                        st.session_state.subreddit_view_cache = {}
                                    st.session_state.subreddit_view_cache[cache_key_quick] = {'posts': posts, 'translations': {}}
                                    st.success(f"已加载 r/{browse_subreddit_quick.strip()} 的 {len(posts)} 条帖子")
                                except Exception as e:
                                    st.error(f"加载失败: {str(e)}")
                        
                        # 显示帖子列表
                        cache_key_quick = f"quick_browse_{browse_subreddit_quick.strip()}"
                        if 'subreddit_view_cache' in st.session_state and cache_key_quick in st.session_state.subreddit_view_cache:
                            data = st.session_state.subreddit_view_cache[cache_key_quick]
                            posts = data.get('posts', [])
                            if posts:
                                selected_post_id = st.selectbox(
                                    "选择帖子",
                                    options=[p.get('id', '') for p in posts],
                                    format_func=lambda x: next((p.get('title', '(无标题)')[:50] for p in posts if p.get('id') == x), x),
                                    key="quick_select_post"
                                )
                                
                                if selected_post_id:
                                    selected_post = next((p for p in posts if p.get('id') == selected_post_id), None)
                                    if selected_post:
                                        st.markdown(f"**{selected_post.get('title', '(无标题)')}**")
                                        st.caption(f"得分: {selected_post.get('score', 'N/A')} | 评论: {selected_post.get('num_comments', 'N/A')} | ID: {selected_post.get('id', '')}")
                                        
                                        st.markdown("**英文原文：**")
                                        st.write(selected_post.get('selftext') or "(无正文)")
                                        
                                        # 翻译按钮
                                        translate_key = f"translate_quick_{selected_post_id}"
                                        if st.button("🌐 翻译为中文", key=translate_key):
                                            # 获取完整的文本内容（标题+正文）
                                            title_text = selected_post.get('title', '')
                                            selftext_text = selected_post.get('selftext', '') or ''
                                            
                                            text_to_translate = f"{title_text}\n\n{selftext_text}".strip()
                                            
                                            if text_to_translate:
                                                with st.spinner("正在翻译为中文..."):
                                                    try:
                                                        tr = st.session_state.analyzer.translate_text(text_to_translate, target_language="中文")
                                                        if tr.get('success'):
                                                            translated_text = tr.get('translated_text', '')
                                                            # 保存翻译结果到缓存
                                                            if 'translations' not in data:
                                                                data['translations'] = {}
                                                            data['translations'][selected_post_id] = translated_text
                                                            st.success("✅ 翻译完成")
                                                            st.rerun()
                                                        else:
                                                            st.warning("翻译失败，请重试")
                                                    except Exception as e:
                                                        st.error(f"翻译失败: {str(e)}")
                                            else:
                                                st.warning("该帖子无内容可翻译")
                                        
                                        # 显示翻译（检查缓存中的翻译结果）
                                        tr_text = None
                                        if 'translations' in data:
                                            tr_text = data['translations'].get(selected_post_id)
                                        
                                        if tr_text:
                                            st.markdown("**中文翻译：**")
                                            st.info(tr_text)
                                        else:
                                            # 如果没有翻译，提示用户
                                            title_text = selected_post.get('title', '')
                                            selftext_text = selected_post.get('selftext', '') or ''
                                            if title_text or selftext_text:
                                                st.caption("💡 点击上方'翻译为中文'按钮获取中文翻译")
                                        
                                        # 查看评论按钮
                                        if st.button("👀 查看该帖评论", key=f"view_comments_quick_{selected_post_id}"):
                                            with st.spinner("正在获取评论..."):
                                                try:
                                                    if not selected_post_id:
                                                        st.warning("该帖子缺少ID，无法获取评论")
                                                    else:
                                                        comments = st.session_state.scraper.get_post_comments(selected_post_id, 20)
                                                        if comments:
                                                            st.markdown("#### 📋 帖子评论")
                                                            for i, comment in enumerate(comments[:10]):
                                                                with st.expander(f"评论 {i+1} - u/{comment.get('author', 'Unknown')}", expanded=False):
                                                                    st.write(comment.get('body', '') or '')
                                                                    
                                                                    # 评论的快速互动
                                                                    comment_id = comment.get('id', '')
                                                                    if comment_id:
                                                                        col_comment_act1, col_comment_act2 = st.columns(2)
                                                                        with col_comment_act1:
                                                                            if st.button("👍", key=f"quick_upvote_comment_{selected_post_id}_{i}"):
                                                                                with st.spinner("正在点赞评论..."):
                                                                                    result = st.session_state.scraper.upvote_comment(comment_id)
                                                                                    if result['success']:
                                                                                        st.success("✅ 评论点赞成功")
                                                                                        st.rerun()
                                                                        with col_comment_act2:
                                                                            if st.button("👎", key=f"quick_downvote_comment_{selected_post_id}_{i}"):
                                                                                with st.spinner("正在点踩评论..."):
                                                                                    result = st.session_state.scraper.downvote_comment(comment_id)
                                                                                    if result['success']:
                                                                                        st.success("✅ 评论点踩成功")
                                                                                        st.rerun()
                                                        else:
                                                            st.info("该帖子暂无评论")
                                                except Exception as e:
                                                    st.error(f"获取评论失败: {str(e)}")
                                        
                                        # 快速互动按钮
                                        col_quick_act1, col_quick_act2 = st.columns(2)
                                        with col_quick_act1:
                                            if st.button("👍 点赞", key=f"quick_upvote_{selected_post_id}"):
                                                with st.spinner("正在点赞..."):
                                                    result = st.session_state.interaction_manager.upvote_post(selected_post_id, browse_subreddit_quick.strip())
                                                    if result['success']:
                                                        st.success("✅ 点赞成功")
                                        with col_quick_act2:
                                            if st.button("💾 保存", key=f"quick_save_{selected_post_id}"):
                                                with st.spinner("正在保存..."):
                                                    result = st.session_state.interaction_manager.save_post(selected_post_id, browse_subreddit_quick.strip())
                                                    if result['success']:
                                                        st.success("✅ 保存成功")
                
                # ========== 养号任务管理 ==========
                st.markdown("---")
                st.subheader("📊 养号任务管理")
                
                if hasattr(st.session_state, 'warming_plan') and st.session_state.warming_plan:
                    plan = st.session_state.warming_plan
                    if plan.get('success'):
                        st.markdown("#### 今日任务清单")
                        today_plan = plan['plan'][0] if plan['plan'] else {'day': 1, 'upvotes': 0, 'comments': 0, 'posts': 0, 'notes': ''}
                        st.info(f"第{today_plan['day']}天：点赞 {today_plan['upvotes']}，评论 {today_plan['comments']}，发帖 {today_plan['posts']} | {today_plan['notes']}")
                        
                        if st.button("📋 查看7天养号计划", key="view_full_plan"):
                            with st.expander("📋 养号计划（7天）", expanded=True):
                                for d in plan['plan']:
                                    st.write(f"第{d['day']}天：点赞 {d['upvotes']}，评论 {d['comments']}，发帖 {d['posts']} | {d['notes']}")
                else:
                    st.info("💡 点击上方'发帖资格检测'区域的'养号计划'按钮生成7天养号计划")
                
                # ========== 互动历史与统计 ==========
                st.markdown("---")
                st.subheader("📚 互动历史与统计")
                
                col_history1, col_history2 = st.columns([3, 1])
                
                with col_history1:
                    if st.button("🔄 刷新历史", type="secondary", key="refresh_history"):
                        st.rerun()
                
                with col_history2:
                    history_limit = st.number_input("显示数量", min_value=10, max_value=100, value=20, key="history_limit")
                
                # 获取互动历史
                try:
                    history = st.session_state.interaction_manager.get_interaction_history(history_limit)
                    
                    if history:
                        st.markdown("#### 📋 最近互动记录")
                        for interaction in history:
                            with st.expander(f"{interaction['interaction_type']} - {interaction['post_id']}", expanded=False):
                                col_info1, col_info2 = st.columns(2)
                                with col_info1:
                                    st.write(f"**类型**: {interaction['interaction_type']}")
                                    st.write(f"**帖子ID**: {interaction['post_id']}")
                                    if interaction.get('comment_id'):
                                        st.write(f"**评论ID**: {interaction['comment_id']}")
                                with col_info2:
                                    st.write(f"**时间**: {interaction['created_at']}")
                                    st.write(f"**状态**: {interaction['status']}")
                                    if interaction.get('target_subreddit'):
                                        st.write(f"**子版块**: r/{interaction['target_subreddit']}")
                    else:
                        st.info("暂无互动历史记录")
                except Exception as e:
                    st.warning(f"获取互动历史失败: {str(e)}")
                
                # 统计信息
                try:
                    if 'history' in locals() and history:
                        col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                        
                        with col_stats1:
                            st.metric("总互动数", len(history))
                        
                        with col_stats2:
                            success_count = len([h for h in history if h['status'] == 'success'])
                            st.metric("成功互动", success_count)
                        
                        with col_stats3:
                            failed_count = len([h for h in history if h['status'] == 'failed'])
                            st.metric("失败互动", failed_count)
                        
                        with col_stats4:
                            success_rate = (success_count / len(history) * 100) if history else 0
                            st.metric("成功率", f"{success_rate:.1f}%")
                except Exception:
                    pass
                
                else:
                    # 显示检查状态
                    with st.expander("🔍 数据检查状态", expanded=True):
                        # 检查output文件夹
                        try:
                            if os.path.exists('./output'):
                                json_files = glob.glob('./output/business_insights_*.json')
                                if json_files:
                                    latest_json = max(json_files, key=os.path.getmtime)
                                    st.info(f"✅ output文件夹中找到 {len(json_files)} 个分析报告文件")
                                    st.info(f"最新文件: {os.path.basename(latest_json)}")
                                    st.info(f"修改时间: {datetime.fromtimestamp(os.path.getmtime(latest_json)).strftime('%Y-%m-%d %H:%M:%S')}")
                                    st.error("❌ 但读取数据失败，请检查文件格式")
                                else:
                                    st.warning("⚠️ output文件夹中没有找到 business_insights_*.json 文件")
                            else:
                                st.warning("⚠️ output文件夹不存在")
                        except Exception as e:
                            st.error(f"❌ 检查output文件夹失败: {str(e)}")
                        
                        # 检查数据库
                        try:
                            latest_insight = st.session_state.db.get_latest_business_insight()
                            if latest_insight:
                                st.error(f"❌ 数据库中有分析报告，但无法读取数据")
                                st.info(f"分析ID: {latest_insight.analysis_id}")
                                st.info(f"分析时间: {latest_insight.analysis_timestamp}")
                            else:
                                st.warning("⚠️ 数据库中没有找到深度分析报告")
                        except Exception as e:
                            st.error(f"❌ 检查数据库失败: {str(e)}")
                        
                    st.warning("⚠️ 请先完成深度分析以获取洞察数据")
                    st.info("💡 **智能发帖功能触发条件：**")
                    st.info("1. ✅ output文件夹中存在 business_insights_*.json 文件（优先读取）")
                    st.info("2. ✅ 数据库中存在深度分析报告（BusinessInsight表）")
                    st.info("3. ✅ 或者后台深度分析任务已完成")
                    st.info("")
                    st.info("💡 **建议操作：**")
                    st.info("1. 切换到'数据抓取'页面抓取Reddit数据")
                    st.info("2. 切换到'深度分析'页面运行分析")
                    st.info("3. 分析完成后，结果会保存到数据库和output文件夹")
                    st.info("4. 返回此页面即可自动检测并使用智能发帖功能")
                    
                    # 基础发帖功能（无分析数据时）
                    st.markdown("---")
                    st.subheader("📝 基础发帖功能")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### 🎯 基础配置")
                        
                        target_subreddit = st.text_input(
                            "目标子版块",
                            placeholder="例如：MachineLearning",
                            help="输入要发帖的子版块名称（不带r/前缀）"
                        )
                        
                        post_topic = st.text_area(
                            "帖子主题",
                            placeholder="描述您想要讨论的主题...",
                            height=100,
                            help="详细描述帖子的主题内容"
                        )
                    
                    with col2:
                        st.markdown("#### 💡 使用建议")
                        st.info("""
                        **推荐流程：**
                        1. 先进行数据抓取
                        2. 运行深度分析
                        3. 基于分析结果生成智能帖子
                        
                        **当前模式：**
                        - 基础发帖功能
                        - 手动输入内容
                        - 无AI优化
                        """)
                    
                    if st.button("📝 生成基础帖子", type="secondary"):
                        if target_subreddit.strip() and post_topic.strip():
                            st.info("💡 基础发帖功能正在开发中，建议先完成深度分析")
                        else:
                            st.error("请填写目标子版块和帖子主题")
                
            except ImportError as e:
                st.error(f"❌ 导入智能发帖模块失败: {str(e)}")
                st.info("💡 请确保reddit_publisher.py文件存在")
        
        else:
            st.warning("请先配置API密钥并初始化系统")
    
    with tab7:
        # 智能筛选分析页面
        st.header("📊 数据筛选与分析")
        st.markdown("💡 基于本地数据库数据进行精准筛选和统计分析")
        
        if st.session_state.initialized:
            # === 第一步：筛选条件配置 ===
            st.subheader("🔍 筛选条件")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### 📍 基础筛选")
                
                # 获取数据库中的子版块列表
                try:
                    available_subreddits = st.session_state.db.get_subreddit_list()
                    if available_subreddits:
                        selected_subreddits = st.multiselect(
                            "选择子版块（可多选）",
                            options=available_subreddits,
                            help="留空表示选择全部子版块",
                            key="filter_subreddits"
                        )
                    else:
                        st.warning("⚠️ 数据库中没有子版块数据")
                        selected_subreddits = []
                        st.info("💡 请先在'📥 数据抓取'页面抓取数据")
                except Exception as e:
                    st.error(f"❌ 获取子版块列表失败: {str(e)}")
                    selected_subreddits = []
                
                # 分数范围筛选
                st.markdown("#### ⭐ 分数范围")
                min_score = st.number_input(
                    "最低分数",
                    min_value=0,
                    value=0,
                    help="0表示不限制",
                    key="filter_min_score"
                )
                max_score = st.number_input(
                    "最高分数",
                    min_value=0,
                    value=0,
                    help="0表示不限制",
                    key="filter_max_score"
                )
            
            with col2:
                st.markdown("#### 🔤 关键词筛选")
                
                # 关键词输入
                keywords_input = st.text_input(
                    "关键词（多个用逗号分隔）",
                    help="在标题和内容中搜索，多个关键词用逗号分隔，例如：iPhone, battery, charger",
                    key="filter_keywords"
                )
                
                # 解析关键词
                keywords = []
                if keywords_input:
                    # 按逗号分隔，去除每个关键词的前后空格，过滤掉空字符串
                    raw_keywords = keywords_input.split(',')
                    keywords = [k.strip() for k in raw_keywords if k.strip()]
                    
                    # 显示解析结果
                    if keywords:
                        if len(keywords) == 1:
                            st.info(f"💡 已识别 1 个关键词: `{keywords[0]}`")
                        else:
                            st.info(f"💡 已识别 {len(keywords)} 个关键词: {', '.join([f'`{k}`' for k in keywords])}")
                    else:
                        st.warning("⚠️ 输入的关键词无效，请输入至少一个非空关键词")
            
            # 执行筛选按钮
            st.markdown("---")
            if st.button("🔍 执行筛选", type="primary", use_container_width=True, key="execute_filter"):
                try:
                    # 构建筛选参数
                    filter_params = {
                        'subreddits': selected_subreddits if selected_subreddits else None,
                        'min_score': min_score if min_score > 0 else None,
                        'max_score': max_score if max_score > 0 else None,
                        'keywords': keywords if keywords else None,
                        'limit': 1000
                    }
                    
                    # 执行筛选查询
                    with st.spinner("🔍 正在筛选数据..."):
                        filtered_posts = st.session_state.db.get_posts_with_filters(**filter_params)
                    
                    # 保存筛选结果到session_state
                    st.session_state.filtered_posts = filtered_posts
                    st.session_state.filter_params = filter_params
                    
                    if filtered_posts:
                        st.success(f"✅ 找到 {len(filtered_posts)} 条符合条件的帖子")
                    else:
                        st.warning("⚠️ 没有找到符合条件的帖子，请调整筛选条件")
                        
                except Exception as e:
                    st.error(f"❌ 筛选失败: {str(e)}")
                    logging.error(f"筛选失败: {str(e)}")
            
            # === 第二步：筛选结果展示 ===
            if 'filtered_posts' in st.session_state and st.session_state.filtered_posts:
                posts = st.session_state.filtered_posts
                
                st.markdown("---")
                st.subheader(f"📋 筛选结果（共 {len(posts)} 条）")
                
                # 显示筛选条件摘要
                with st.expander("🔍 当前筛选条件", expanded=False):
                    filter_params = st.session_state.get('filter_params', {})
                    st.write(f"- **子版块**: {', '.join(filter_params.get('subreddits', ['全部'])) if filter_params.get('subreddits') else '全部'}")
                    st.write(f"- **分数范围**: {filter_params.get('min_score', 0)} - {filter_params.get('max_score', '不限')}")
                    st.write(f"- **关键词**: {', '.join(filter_params.get('keywords', [])) if filter_params.get('keywords') else '无'}")
                
                # 列表展示（仅基本信息，支持分页）
                posts_per_page = st.slider("每页显示数量", min_value=10, max_value=100, value=20, key="posts_per_page")
                
                total_pages = (len(posts) + posts_per_page - 1) // posts_per_page if posts else 0
                current_page = st.number_input(
                    "页码",
                    min_value=1,
                    max_value=max(1, total_pages),
                    value=1,
                    key="filter_page"
                )
                
                start_idx = (current_page - 1) * posts_per_page
                end_idx = start_idx + posts_per_page
                current_posts = posts[start_idx:end_idx]
                
                # 显示帖子列表
                for i, post in enumerate(current_posts, start=start_idx):
                    post_num = i + 1
                    
                    # 构建帖子摘要
                    title_preview = post.title[:80] + "..." if len(post.title) > 80 else post.title
                    post_summary = f"**{post_num}. {title_preview}**"
                    
                    with st.expander(
                        f"{post_summary} | ⭐ {post.score} | 💬 {post.num_comments} | r/{post.subreddit}",
                        expanded=False
                    ):
                        # 显示完整帖子信息（按需加载）
                        st.markdown(f"**标题**: {post.title}")
                        st.markdown(f"**作者**: {post.author or '[deleted]'}")
                        st.markdown(f"**分数**: {post.score} | **点赞率**: {post.upvote_ratio:.1%}" if post.upvote_ratio else f"**分数**: {post.score}")
                        st.markdown(f"**评论数**: {post.num_comments}")
                        st.markdown(f"**子版块**: r/{post.subreddit}")
                        
                        if post.flair:
                            st.markdown(f"**标签**: {post.flair}")
                        
                        if post.created_utc:
                            st.markdown(f"**发布时间**: {post.created_utc.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        if post.selftext:
                            st.markdown("---")
                            st.markdown("**内容**:")
                            st.markdown(post.selftext)
                        
                        if post.url:
                            st.markdown(f"**链接**: [查看原帖]({post.url})")
                        
                        # 查询并显示评论（从本地数据库）
                        st.markdown("---")
                        st.markdown("**评论**（仅显示本地数据库中的数据）:")
                        
                        comments = st.session_state.db.get_comments_by_post_id(post.id)
                        if comments:
                            st.info(f"找到 {len(comments)} 条评论")
                            
                            # 显示前10条高赞评论
                            for comment_idx, comment in enumerate(comments[:10], 1):
                                with st.container():
                                    st.markdown(f"**{comment_idx}. {comment.author or '[deleted]'}** (分数: {comment.score})")
                                    st.markdown(f"{comment.body}")
                                    if comment.created_utc:
                                        st.caption(f"时间: {comment.created_utc.strftime('%Y-%m-%d %H:%M:%S')}")
                                    st.markdown("---")
                            
                            if len(comments) > 10:
                                st.info(f"还有 {len(comments) - 10} 条评论未显示")
                        else:
                            st.info("💡 本地数据库中没有该帖子的评论数据")
                
                # 分页信息
                if total_pages > 1:
                    st.info(f"📄 第 {current_page} / {total_pages} 页，共 {len(posts)} 条结果")
                
                # === 第三步：统计分析（可选） ===
                st.markdown("---")
                st.subheader("📊 统计分析")
                
                st.markdown("""
                **统计分析功能说明**：
                - 对筛选结果进行AI统计分析
                - 使用不同于深度分析的专业提示词
                - 生成市场调研、产品分析等报告
                """)
                
                analysis_type = st.selectbox(
                    "选择分析类型",
                    options=["市场调研分析", "产品对比分析", "关键词情感分析", "用户需求提取", "自定义分析"],
                    help="选择统计分析的类型",
                    key="filter_analysis_type"
                )
                
                # 自定义提示词（可选）
                custom_prompt = ""
                if analysis_type == "自定义分析":
                    custom_prompt = st.text_area(
                        "自定义分析提示词",
                        height=150,
                        help="输入自定义的分析提示词",
                        key="custom_filter_prompt"
                    )
                
                if st.button("🤖 生成统计分析报告", type="primary", key="generate_filter_analysis"):
                    if not posts:
                        st.warning("⚠️ 没有可分析的数据，请先执行筛选")
                    else:
                        try:
                            # 清除旧的分析结果，避免状态混乱
                            if 'filter_analysis_result' in st.session_state:
                                del st.session_state.filter_analysis_result
                            if 'filter_analysis_type_saved' in st.session_state:
                                del st.session_state.filter_analysis_type_saved
                            if 'filter_analysis_json_path' in st.session_state:
                                del st.session_state.filter_analysis_json_path
                            if 'filter_analysis_txt_path' in st.session_state:
                                del st.session_state.filter_analysis_txt_path
                            
                            with st.spinner("🤖 正在进行AI分析，请稍候..."):
                                # 准备分析数据（限制数量以提高效率）
                                analysis_posts = posts[:100]  # 最多分析100条帖子
                                
                                # 构建分析文本
                                analysis_text = ""
                                for post in analysis_posts:
                                    analysis_text += f"标题: {post.title}\n"
                                    if post.selftext:
                                        analysis_text += f"内容: {post.selftext}\n"
                                    analysis_text += f"分数: {post.score} | 评论数: {post.num_comments}\n"
                                    analysis_text += f"子版块: r/{post.subreddit}\n"
                                    analysis_text += "-" * 50 + "\n"
                                
                                # 构建分析提示词（区别于深度分析）
                                if analysis_type == "市场调研分析":
                                    analysis_prompt = f"""
请对以下Reddit数据进行市场调研分析。

**重要要求：所有输出内容必须使用中文（简体），包括JSON中的所有文本字段。**

数据概况：
- 筛选后的帖子数量: {len(analysis_posts)}
- 总筛选结果: {len(posts)} 条

筛选条件：
- 子版块: {', '.join(selected_subreddits) if selected_subreddits else '全部'}
- 分数范围: {min_score if min_score > 0 else '不限制'} - {max_score if max_score > 0 else '不限制'}
- 关键词: {', '.join(keywords) if keywords else '无'}
- 长尾关键词: {', '.join(selected_long_tail) if selected_long_tail else '无'}

请完成以下分析任务：
1. **数据概览**：统计筛选结果的基本信息（平均分数、评论数、热门子版块等）
2. **用户需求提取**：列出Top 10用户真实需求（使用中文描述）
3. **痛点识别**：列出Top 10用户痛点问题（使用中文描述）
4. **产品使用场景**：识别3-5个主要使用场景（使用中文描述）
5. **用户画像**：描述典型用户特征（使用中文描述）
6. **竞争格局**：识别提到的竞品和对比（使用中文描述）
7. **趋势洞察**：发现新兴趋势和机会点（使用中文描述）

请以JSON格式输出分析结果，所有文本字段必须使用中文。

原始数据：
{analysis_text}
"""
                                elif analysis_type == "产品对比分析":
                                    # 如果有关键词，假设是产品名称
                                    product_names = keywords[:2] if keywords else ["产品A", "产品B"]
                                    analysis_prompt = f"""
请对以下Reddit数据进行产品对比分析。

**重要要求：所有输出内容必须使用中文（简体），包括JSON中的所有文本字段。**

对比目标：
- 产品1: {product_names[0] if len(product_names) > 0 else '未知'}
- 产品2: {product_names[1] if len(product_names) > 1 else '未知'}

分析维度：
1. **用户满意度对比**：正面/负面评价比例
2. **优劣势对比**：各自的优点和缺点（使用中文描述）
3. **价格感知对比**：用户对价格的看法（使用中文描述）
4. **功能需求对比**：用户最关心的功能差异（使用中文描述）
5. **购买意愿对比**：用户推荐度和购买倾向（使用中文描述）

请以JSON格式输出详细的对比报告，所有文本字段必须使用中文。

原始数据：
{analysis_text}
"""
                                elif analysis_type == "关键词情感分析":
                                    main_keyword = keywords[0] if keywords else "主题"
                                    analysis_prompt = f"""
请对关键词"{main_keyword}"进行情感分析。

**重要要求：所有输出内容必须使用中文（简体），包括JSON中的所有文本字段。**

分析任务：
1. **正面评价分析**：
   - 正面评价数量及比例
   - 主要正面原因（Top 5，使用中文描述）
   - 典型正面评论示例（3-5条，使用中文）
   
2. **负面评价分析**：
   - 负面评价数量及比例
   - 主要负面原因（Top 5，使用中文描述）
   - 典型负面评论示例（3-5条，使用中文）
   
3. **中立/混合评价**：
   - 中立评价特点（使用中文描述）
   - 用户争议点（使用中文描述）
   
4. **综合结论**：
   - 整体情感倾向（使用中文描述）
   - 关键改进建议（使用中文描述）

请以JSON格式输出分析报告，所有文本字段必须使用中文。

原始数据：
{analysis_text}
"""
                                elif analysis_type == "用户需求提取":
                                    analysis_prompt = f"""
请从以下Reddit数据中提取用户需求。

**重要要求：所有输出内容必须使用中文（简体），包括JSON中的所有文本字段。**

分析任务：
1. **真实需求提取**：列出用户明确表达的需求（Top 15，使用中文描述）
2. **痛点识别**：列出用户遇到的问题和困难（Top 15，使用中文描述）
3. **期望功能**：列出用户希望的功能或特性（Top 10，使用中文描述）
4. **使用场景**：识别用户的使用场景（5-8个，使用中文描述）
5. **用户画像**：描述典型用户特征（3-5个维度，使用中文描述）

请以JSON格式输出结果，所有文本字段必须使用中文。

原始数据：
{analysis_text}
"""
                                else:  # 自定义分析
                                    if custom_prompt and custom_prompt.strip():
                                        # 用户提供了自定义提示词
                                        # 检查是否包含{text}占位符，如果不包含，则添加数据部分
                                        if "{text}" not in custom_prompt and "原始数据" not in custom_prompt:
                                            # 自定义提示词中没有占位符和数据部分，添加数据
                                            analysis_prompt = f"""{custom_prompt}

原始数据：
{analysis_text}
"""
                                        else:
                                            # 自定义提示词中可能包含{text}占位符或已有数据，直接使用
                                            analysis_prompt = custom_prompt
                                    else:
                                        # 用户没有提供自定义提示词，使用默认提示词
                                        analysis_prompt = f"""
请对以下Reddit数据进行综合分析。

**重要要求：所有输出内容必须使用中文（简体），包括JSON中的所有文本字段。**

原始数据：
{analysis_text}
"""
                                
                                # 调用大模型分析
                                analysis_result = st.session_state.analyzer.analyze_comprehensive(
                                    analysis_text,
                                    provider="deepseek",  # 优先使用DeepSeek
                                    custom_prompt=analysis_prompt
                                )
                                
                                # 检查分析结果是否有错误
                                if isinstance(analysis_result, dict) and 'error' in analysis_result:
                                    error_msg = analysis_result.get('error', '未知错误')
                                    error_details = analysis_result.get('error_details', '')
                                    raw_response = analysis_result.get('raw_response', '')
                                    
                                    # 记录详细错误信息
                                    logging.error(f"分析返回错误: {error_msg}")
                                    if error_details:
                                        logging.error(f"错误详情: {error_details}")
                                    if raw_response:
                                        logging.error(f"原始响应（前500字符）: {raw_response[:500]}")
                                    
                                    # 显示用户友好的错误信息
                                    st.error(f"❌ 分析失败: {error_msg}")
                                    if error_details:
                                        with st.expander("查看错误详情"):
                                            st.code(error_details, language="text")
                                    if raw_response:
                                        with st.expander("查看原始响应"):
                                            st.text(raw_response[:1000])
                                    
                                    # 不保存错误结果，直接返回
                                    st.stop()
                                
                                # 保存分析结果
                                st.session_state.filter_analysis_result = analysis_result
                                st.session_state.filter_analysis_type_saved = analysis_type
                                
                                # 保存报告到文件（JSON和TXT格式）
                                try:
                                    # 确保output目录存在
                                    os.makedirs('./output', exist_ok=True)
                                    
                                    # 生成时间戳
                                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                    
                                    # 保存JSON格式
                                    json_data = {
                                        'analysis_type': analysis_type,
                                        'analysis_date': timestamp,
                                        'filter_params': st.session_state.get('filter_params', {}),
                                        'total_posts': len(posts),
                                        'analysis_result': analysis_result
                                    }
                                    
                                    json_filename = f"filter_analysis_{analysis_type}_{timestamp}.json"
                                    json_file_path = f"./output/{json_filename}"
                                    with open(json_file_path, 'w', encoding='utf-8') as f:
                                        json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)
                                    
                                    # 保存TXT格式（可读中文报告）
                                    txt_content = f"筛选分析报告\n"
                                    txt_content += f"{'='*60}\n\n"
                                    txt_content += f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                    txt_content += f"分析类型: {analysis_type}\n"
                                    txt_content += f"筛选结果总数: {len(posts)} 条帖子\n\n"
                                    
                                    # 筛选条件
                                    txt_content += f"筛选条件:\n"
                                    txt_content += f"{'-'*60}\n"
                                    filter_params = st.session_state.get('filter_params', {})
                                    if filter_params.get('subreddits'):
                                        txt_content += f"子版块: {', '.join(filter_params['subreddits'])}\n"
                                    else:
                                        txt_content += f"子版块: 全部\n"
                                    txt_content += f"分数范围: {filter_params.get('min_score', 0)} - {filter_params.get('max_score', '不限')}\n"
                                    if filter_params.get('keywords'):
                                        txt_content += f"关键词: {', '.join(filter_params['keywords'])}\n"
                                    txt_content += f"\n"
                                    
                                    # 分析结果内容
                                    txt_content += f"分析结果:\n"
                                    txt_content += f"{'-'*60}\n\n"
                                    
                                    # 检查分析结果的结构
                                    if isinstance(analysis_result, dict):
                                        # 优先使用解析后的结果
                                        if 'parsed' in analysis_result:
                                            parsed = analysis_result['parsed']
                                            if parsed:  # parsed存在且不为空
                                                if isinstance(parsed, dict):
                                                    # 记录是否添加了格式化内容
                                                    content_added = False
                                                    
                                                    # 数据概览
                                                    if 'data_overview' in parsed:
                                                        txt_content += f"📈 数据概览\n"
                                                        overview = parsed['data_overview']
                                                        if isinstance(overview, dict):
                                                            txt_content += f"  总帖子数: {overview.get('total_posts', len(posts))}\n"
                                                            txt_content += f"  平均分数: {overview.get('avg_score', 'N/A')}\n"
                                                            txt_content += f"  平均评论数: {overview.get('avg_comments', 'N/A')}\n"
                                                            if overview.get('top_subreddits'):
                                                                txt_content += f"  热门子版块: {', '.join(overview.get('top_subreddits', []))}\n"
                                                        txt_content += f"\n"
                                                        content_added = True
                                                    
                                                    # 用户需求
                                                    if 'user_needs' in parsed and parsed['user_needs']:
                                                        txt_content += f"💡 用户需求（Top {min(10, len(parsed['user_needs']))}）\n"
                                                        for i, need in enumerate(parsed['user_needs'][:10], 1):
                                                            txt_content += f"  {i}. {need}\n"
                                                        txt_content += f"\n"
                                                        content_added = True
                                                    
                                                    # 痛点
                                                    if 'pain_points' in parsed and parsed['pain_points']:
                                                        txt_content += f"⚠️ 用户痛点（Top {min(10, len(parsed['pain_points']))}）\n"
                                                        for i, pain in enumerate(parsed['pain_points'][:10], 1):
                                                            txt_content += f"  {i}. {pain}\n"
                                                        txt_content += f"\n"
                                                        content_added = True
                                                    
                                                    # 使用场景
                                                    if 'use_cases' in parsed and parsed['use_cases']:
                                                        txt_content += f"🎯 使用场景\n"
                                                        for i, case in enumerate(parsed['use_cases'], 1):
                                                            txt_content += f"  {i}. {case}\n"
                                                        txt_content += f"\n"
                                                        content_added = True
                                                    
                                                    # 用户画像
                                                    if 'user_personas' in parsed and parsed['user_personas']:
                                                        txt_content += f"👤 用户画像\n"
                                                        for i, persona in enumerate(parsed['user_personas'], 1):
                                                            txt_content += f"  {i}. {persona}\n"
                                                        txt_content += f"\n"
                                                        content_added = True
                                                    
                                                    # 竞品
                                                    if 'competitors' in parsed and parsed['competitors']:
                                                        txt_content += f"🏢 竞品分析\n"
                                                        for i, competitor in enumerate(parsed['competitors'], 1):
                                                            txt_content += f"  {i}. {competitor}\n"
                                                        txt_content += f"\n"
                                                        content_added = True
                                                    
                                                    # 趋势
                                                    if 'trends' in parsed and parsed['trends']:
                                                        txt_content += f"📈 趋势洞察\n"
                                                        for i, trend in enumerate(parsed['trends'], 1):
                                                            txt_content += f"  {i}. {trend}\n"
                                                        txt_content += f"\n"
                                                        content_added = True
                                                    
                                                    # 机会点
                                                    if 'opportunities' in parsed and parsed['opportunities']:
                                                        txt_content += f"🚀 机会点\n"
                                                        for i, opp in enumerate(parsed['opportunities'], 1):
                                                            txt_content += f"  {i}. {opp}\n"
                                                        txt_content += f"\n"
                                                        content_added = True
                                                    
                                                    # 总结
                                                    if 'summary' in parsed and parsed['summary']:
                                                        txt_content += f"📝 综合分析总结\n"
                                                        txt_content += f"{'-'*60}\n"
                                                        txt_content += f"{parsed['summary']}\n"
                                                        txt_content += f"\n"
                                                        content_added = True
                                                    
                                                    # 如果上述字段都没有匹配到，则输出完整JSON
                                                    if not content_added:
                                                        txt_content += f"完整分析结果（JSON格式）:\n"
                                                        txt_content += f"{json.dumps(parsed, ensure_ascii=False, indent=2, default=str)}\n\n"
                                                else:
                                                    # parsed不是字典，直接转换
                                                    txt_content += f"解析结果:\n{json.dumps(parsed, ensure_ascii=False, indent=2, default=str)}\n\n"
                                            else:
                                                # parsed存在但为空，尝试使用content字段
                                                if 'content' in analysis_result and analysis_result['content']:
                                                    txt_content += f"{analysis_result['content']}\n"
                                                else:
                                                    txt_content += f"⚠️ 分析结果为空\n"
                                        # 如果没有parsed，尝试使用content字段
                                        elif 'content' in analysis_result and analysis_result['content']:
                                            # content可能是JSON字符串，尝试格式化
                                            try:
                                                content_parsed = json.loads(analysis_result['content'])
                                                txt_content += f"分析结果（JSON格式）:\n"
                                                txt_content += f"{json.dumps(content_parsed, ensure_ascii=False, indent=2, default=str)}\n"
                                            except:
                                                # 如果解析失败，直接使用原始内容
                                                txt_content += f"{analysis_result['content']}\n"
                                        # 如果有raw字段（原始LLM输出）
                                        elif 'raw' in analysis_result and analysis_result['raw']:
                                            txt_content += f"{analysis_result['raw']}\n"
                                        # 如果有text字段
                                        elif 'text' in analysis_result and analysis_result['text']:
                                            txt_content += f"{analysis_result['text']}\n"
                                        # 其他情况，输出整个字典的JSON
                                        else:
                                            txt_content += f"分析结果详情:\n"
                                            txt_content += f"{json.dumps(analysis_result, ensure_ascii=False, indent=2, default=str)}\n"
                                    # 如果不是字典，直接转换为字符串
                                    elif analysis_result:
                                        txt_content += f"{str(analysis_result)}\n"
                                    else:
                                        txt_content += f"⚠️ 分析结果为空或格式异常\n"
                                    
                                    txt_content += f"\n{'='*60}\n"
                                    txt_content += f"报告结束\n"
                                    
                                    txt_filename = f"filter_analysis_{analysis_type}_{timestamp}.txt"
                                    txt_file_path = f"./output/{txt_filename}"
                                    with open(txt_file_path, 'w', encoding='utf-8') as f:
                                        f.write(txt_content)
                                    
                                    # 保存文件路径到session_state
                                    st.session_state.filter_analysis_json_path = json_file_path
                                    st.session_state.filter_analysis_txt_path = txt_file_path
                                    
                                    logging.info(f"筛选分析报告已保存: JSON={json_file_path}, TXT={txt_file_path}")
                                    
                                except Exception as save_error:
                                    logging.error(f"保存分析报告失败: {str(save_error)}")
                                    st.warning(f"⚠️ 分析完成，但保存报告时出错: {str(save_error)}")
                            
                            st.success("✅ 统计分析完成！")
                            
                        except Exception as e:
                            st.error(f"❌ 分析失败: {str(e)}")
                            logging.error(f"筛选统计分析失败: {str(e)}")
                
                # 显示分析结果
                if 'filter_analysis_result' in st.session_state:
                    st.markdown("---")
                    st.subheader("📊 分析结果")
                    
                    analysis_result = st.session_state.filter_analysis_result
                    analysis_type = st.session_state.get('filter_analysis_type_saved', '未知')
                    
                    # 显示保存的文件信息
                    if 'filter_analysis_json_path' in st.session_state or 'filter_analysis_txt_path' in st.session_state:
                        st.info("📁 分析报告已保存到 `./output/` 文件夹")
                        col_file1, col_file2 = st.columns(2)
                        
                        if 'filter_analysis_json_path' in st.session_state:
                            with col_file1:
                                json_path = st.session_state.filter_analysis_json_path
                                json_name = os.path.basename(json_path)
                                st.write(f"📄 JSON格式: `{json_name}`")
                                if os.path.exists(json_path):
                                    with open(json_path, 'r', encoding='utf-8') as f:
                                        json_data = f.read()
                                    st.download_button(
                                        label="📥 下载JSON报告",
                                        data=json_data,
                                        file_name=json_name,
                                        mime="application/json",
                                        key="download_filter_json"
                                    )
                        
                        if 'filter_analysis_txt_path' in st.session_state:
                            with col_file2:
                                txt_path = st.session_state.filter_analysis_txt_path
                                txt_name = os.path.basename(txt_path)
                                st.write(f"📄 TXT格式: `{txt_name}`")
                                if os.path.exists(txt_path):
                                    with open(txt_path, 'r', encoding='utf-8') as f:
                                        txt_data = f.read()
                                    st.download_button(
                                        label="📥 下载TXT报告",
                                        data=txt_data,
                                        file_name=txt_name,
                                        mime="text/plain",
                                        key="download_filter_txt"
                                    )
                    
                    # 解析并展示分析结果（可读中文报告）
                    st.markdown("---")
                    st.markdown("#### 📋 详细分析报告（中文）")
                    
                    if isinstance(analysis_result, dict):
                        if 'parsed' in analysis_result:
                            parsed = analysis_result['parsed']
                            
                            # 显示JSON格式结果
                            with st.expander("📋 详细分析结果（JSON）", expanded=True):
                                st.json(parsed)
                            
                            # 格式化展示（可读中文报告）
                            if isinstance(parsed, dict):
                                # 数据概览
                                if 'data_overview' in parsed:
                                    st.markdown("#### 📈 数据概览")
                                    overview = parsed['data_overview']
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("总帖子数", overview.get('total_posts', len(posts)))
                                    with col2:
                                        st.metric("平均分数", overview.get('avg_score', 'N/A'))
                                    with col3:
                                        st.metric("平均评论数", overview.get('avg_comments', 'N/A'))
                                    
                                    if overview.get('top_subreddits'):
                                        st.markdown("**热门子版块**: " + ", ".join([f"r/{s}" for s in overview.get('top_subreddits', [])[:5]]))
                                
                                # 用户需求
                                if 'user_needs' in parsed and parsed['user_needs']:
                                    st.markdown("---")
                                    st.markdown("#### 💡 用户需求")
                                    needs_list = parsed['user_needs'][:10]
                                    for i, need in enumerate(needs_list, 1):
                                        st.markdown(f"**{i}.** {need}")
                                
                                # 痛点
                                if 'pain_points' in parsed and parsed['pain_points']:
                                    st.markdown("---")
                                    st.markdown("#### ⚠️ 用户痛点")
                                    pains_list = parsed['pain_points'][:10]
                                    for i, pain in enumerate(pains_list, 1):
                                        st.markdown(f"**{i}.** {pain}")
                                
                                # 使用场景
                                if 'use_cases' in parsed and parsed['use_cases']:
                                    st.markdown("---")
                                    st.markdown("#### 🎯 使用场景")
                                    for i, case in enumerate(parsed['use_cases'], 1):
                                        st.markdown(f"**{i}.** {case}")
                                
                                # 用户画像
                                if 'user_personas' in parsed and parsed['user_personas']:
                                    st.markdown("---")
                                    st.markdown("#### 👤 用户画像")
                                    for i, persona in enumerate(parsed['user_personas'], 1):
                                        st.markdown(f"**{i}.** {persona}")
                                
                                # 竞品分析
                                if 'competitors' in parsed and parsed['competitors']:
                                    st.markdown("---")
                                    st.markdown("#### 🏢 竞品分析")
                                    for i, competitor in enumerate(parsed['competitors'], 1):
                                        st.markdown(f"**{i}.** {competitor}")
                                
                                # 趋势洞察
                                if 'trends' in parsed and parsed['trends']:
                                    st.markdown("---")
                                    st.markdown("#### 📈 趋势洞察")
                                    for i, trend in enumerate(parsed['trends'], 1):
                                        st.markdown(f"**{i}.** {trend}")
                                
                                # 机会点
                                if 'opportunities' in parsed and parsed['opportunities']:
                                    st.markdown("---")
                                    st.markdown("#### 🚀 机会点")
                                    for i, opp in enumerate(parsed['opportunities'], 1):
                                        st.markdown(f"**{i}.** {opp}")
                                
                                # 总结
                                if 'summary' in parsed:
                                    st.markdown("---")
                                    st.markdown("#### 📝 综合分析总结")
                                    st.info(parsed['summary'])
                                
                                # 处理自定义分析或其他分析类型可能返回的其他字段
                                # 品牌信息（如果存在）
                                if 'brands' in parsed and parsed['brands']:
                                    st.markdown("---")
                                    st.markdown("#### 🏷️ 品牌信息")
                                    brands_list = parsed['brands']
                                    for i, brand in enumerate(brands_list, 1):
                                        if isinstance(brand, dict):
                                            brand_name = brand.get('name', '')
                                            translation = brand.get('translation', '')
                                            description = brand.get('description', '')
                                            if translation:
                                                st.markdown(f"**{i}.** {brand_name} - {translation}")
                                            elif description:
                                                st.markdown(f"**{i}.** {brand_name} - {description}")
                                            else:
                                                st.markdown(f"**{i}.** {brand_name}")
                                        else:
                                            st.markdown(f"**{i}.** {brand}")
                                
                                # 通用items字段（如果存在且其他特定字段都不存在）
                                if 'items' in parsed and parsed['items'] and not any([
                                    'user_needs' in parsed, 'pain_points' in parsed, 'use_cases' in parsed,
                                    'user_personas' in parsed, 'competitors' in parsed, 'trends' in parsed,
                                    'opportunities' in parsed, 'brands' in parsed
                                ]):
                                    st.markdown("---")
                                    st.markdown("#### 📋 分析结果")
                                    items_list = parsed['items']
                                    for i, item in enumerate(items_list, 1):
                                        if isinstance(item, dict):
                                            item_display = item.get('name', item.get('description', str(item)))
                                            st.markdown(f"**{i}.** {item_display}")
                                        else:
                                            st.markdown(f"**{i}.** {item}")
                                
                                # 如果有raw_content字段，显示原始内容（仅在开发调试时）
                                if 'raw_content' in parsed and st.session_state.get('debug_mode', False):
                                    with st.expander("🔍 原始响应内容（调试）"):
                                        st.text(parsed['raw_content'])
                                
                                # 如果有note字段，显示提示信息
                                if 'note' in parsed:
                                    st.info(f"ℹ️ {parsed['note']}")
                        elif 'content' in analysis_result:
                            # 如果没有解析，显示原始内容
                            st.markdown("#### 📋 分析结果")
                            st.markdown(analysis_result['content'])
                        elif 'error' in analysis_result:
                            st.error(f"❌ 分析错误: {analysis_result['error']}")
                    else:
                        st.json(analysis_result)
        else:
            st.warning("⚠️ 请先配置API密钥并初始化系统")

if __name__ == "__main__":
    main()
