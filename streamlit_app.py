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

logger = logging.getLogger(__name__)

from reddit_scraper import RedditScraper
from database import DatabaseManager
from llm_analyzer import LLMAnalyzer

# 导入激活模块
try:
    from activation import (
        check_activation_status,
        verify_existing_activation,
        get_machine_code_silently,
        validate_email_format,
        validate_activation_code,
        send_registration_to_server,
        save_activation_info,
        ACTIVATION_FILE
    )
    ACTIVATION_AVAILABLE = True
except ImportError as e:
    ACTIVATION_AVAILABLE = False
    logger.warning(f"激活模块导入失败: {str(e)}")

# 可选导入：高级分析器（如果模块存在）
try:
    from advanced_analyzer import AdvancedAnalyzer
    ADVANCED_ANALYZER_AVAILABLE = True
except ImportError:
    AdvancedAnalyzer = None
    ADVANCED_ANALYZER_AVAILABLE = False

# 可选导入：后台分析器（如果模块存在）
try:
    from background_analyzer import background_analyzer
    BACKGROUND_ANALYZER_AVAILABLE = True
except ImportError:
    background_analyzer = None
    BACKGROUND_ANALYZER_AVAILABLE = False

# 导入tab功能模块
from tab_data_scraping import render_data_scraping_tab
from tab_data_management import render_data_management_tab
from tab_subreddit_recommendation import render_subreddit_recommendation_tab
from tab_smart_filter import render_smart_filter_tab

# 导入智能发帖模块
try:
    from modules.posting.smart_posting_tab import render_smart_posting_tab
    SMART_POSTING_AVAILABLE = True
except ImportError as e:
    SMART_POSTING_AVAILABLE = False
    SMART_POSTING_ERROR = str(e)
    logger.warning(f"智能发帖模块导入失败: {str(e)}")

# 自动化运营模块
try:
    from rpta_scorer import RPTAScorer
    from auto_config import AutoConfig
    from task_executor import TaskExecutor
    from auto_scheduler import AutoScheduler
    AUTO_MODULES_AVAILABLE = True
    AUTO_MODULES_ERROR = None
except ImportError as e:
    AUTO_MODULES_AVAILABLE = False
    AUTO_MODULES_ERROR = str(e)

# 页面配置
st.set_page_config(
    page_title="RedInsight - Reddit自动化、数据分析工具",
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
        if BACKGROUND_ANALYZER_AVAILABLE and background_analyzer:
            return background_analyzer.get_status()
        else:
            return {'running': False, 'status': '后台分析器不可用'}
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

# 添加缓存函数用于频繁的数据库查询
@st.cache_data(ttl=5)  # 缓存5秒，平衡实时性和性能
def get_cached_pending_tasks(_db, limit=1000):
    """获取待执行任务（带缓存）"""
    try:
        return _db.get_pending_interactions(limit=limit)
    except Exception as e:
        logger.error(f"获取待执行任务失败: {str(e)}")
        return []

@st.cache_data(ttl=30)  # 缓存30秒，子版块列表变化不频繁
def get_cached_subreddit_list(_db):
    """获取子版块列表（带缓存）"""
    try:
        return _db.get_subreddit_list()
    except Exception as e:
        logger.error(f"获取子版块列表失败: {str(e)}")
        return []

@st.cache_data(ttl=60)  # 缓存60秒，索引变化不频繁
def get_cached_subreddit_indices(_db):
    """获取子版块索引（带缓存）"""
    try:
        return _db.get_all_subreddit_indices()
    except Exception as e:
        logger.error(f"获取子版块索引失败: {str(e)}")
        return []

@st.cache_data(ttl=2)  # 缓存2秒，活动日志更新频繁但不需要实时
def get_cached_activity_logs(_db):
    """获取活动日志（带缓存）"""
    try:
        session = _db.SessionLocal()
        try:
            log_config = session.query(_db.AutoInteractionConfig).filter_by(
                config_key='auto_activity_logs'
            ).first()
            
            if log_config and log_config.config_value:
                import json
                return json.loads(log_config.config_value)
            return []
        finally:
            session.close()
    except Exception as e:
        logger.error(f"获取活动日志失败: {str(e)}")
        return []

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
    """初始化组件（从app_init模块导入）"""
    from app_init import init_components as _init_components
    return _init_components()

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
    if not BACKGROUND_ANALYZER_AVAILABLE or not background_analyzer:
        st.warning("⚠️ 后台分析器不可用")
        return
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
        if not BACKGROUND_ANALYZER_AVAILABLE or not background_analyzer:
            return
        
        # 检查是否有已完成的分析
        if BACKGROUND_ANALYZER_AVAILABLE and background_analyzer and background_analyzer.is_completed():
            # 检查是否已经显示过通知
            if not st.session_state.get('analysis_completion_notified', False):
                st.success("🎉 深度分析已完成！请切换到'深度分析'标签页查看结果。")
                st.balloons()  # 添加气球庆祝动画
                st.session_state.analysis_completion_notified = True
        
        # 检查是否有失败的分析
        elif BACKGROUND_ANALYZER_AVAILABLE and background_analyzer and background_analyzer.is_failed():
            if not st.session_state.get('analysis_failure_notified', False):
                st.error("❌ 深度分析失败！请切换到'深度分析'标签页查看错误信息。")
                st.session_state.analysis_failure_notified = True
                    
    except Exception as e:
        # 静默处理错误，不影响主界面
        pass

def render_activation_page():
    """渲染激活页面（Streamlit版本）"""
    st.title("🔐 RedInsight 激活")
    st.markdown("---")
    
    # 初始化session state
    if 'activation_step' not in st.session_state:
        st.session_state.activation_step = 1
    if 'activation_email' not in st.session_state:
        st.session_state.activation_email = ""
    if 'activation_machine_code' not in st.session_state:
        st.session_state.activation_machine_code = None
    if 'activation_sent' not in st.session_state:
        st.session_state.activation_sent = False
    
    # 获取机器码
    if st.session_state.activation_machine_code is None:
        with st.spinner("正在获取机器码..."):
            machine_code = get_machine_code_silently()
            if not machine_code:
                st.error("❌ 无法获取机器码，请检查系统环境")
                st.stop()
            st.session_state.activation_machine_code = machine_code
    
    machine_code = st.session_state.activation_machine_code
    
    # 步骤1: 输入邮箱
    if st.session_state.activation_step == 1:
        st.markdown("### 步骤 1/3: 输入邮箱地址")
        st.info("请输入您的邮箱地址，用于激活验证")
        
        email = st.text_input("邮箱地址", value=st.session_state.activation_email, key="activation_email_input")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("下一步", type="primary"):
                if not email:
                    st.error("❌ 请输入邮箱地址")
                elif not validate_email_format(email):
                    st.error("❌ 邮箱格式不正确（例如: user@example.com）")
                else:
                    st.session_state.activation_email = email
                    st.session_state.activation_step = 2
                    st.rerun()
    
    # 步骤2: 发送注册信息到服务器
    elif st.session_state.activation_step == 2:
        st.markdown("### 步骤 2/3: 发送注册信息")
        
        email = st.session_state.activation_email
        
        # 显示机器码和邮箱信息
        st.info(f"**机器码:** `{machine_code}`")
        st.info(f"**邮箱:** `{email}`")
        
        if not st.session_state.activation_sent:
            if st.button("发送注册信息", type="primary"):
                with st.spinner("正在发送注册信息到服务器..."):
                    send_success, send_message = send_registration_to_server(machine_code, email)
                    
                    if send_success:
                        st.success("✅ 注册信息发送成功！")
                        st.session_state.activation_sent = True
                        st.rerun()
                    else:
                        st.error(f"❌ 发送失败: {send_message}")
                        st.info("💡 请检查网络连接后重试，或联系管理员")
        else:
            st.success("✅ 注册信息已发送")
            st.markdown("---")
            st.markdown("### 📋 下一步操作：")
            st.markdown("""
            1. 请通过微信联系项目管理员
            2. 提供以下信息给管理员：
               - **机器码**: `{}`
               - **邮箱**: `{}`
            3. 管理员将为您生成激活码
            4. 收到激活码后，请在下方输入
            """.format(machine_code, email))
            st.markdown("---")
            st.markdown("**管理员微信号：** `whj7087824`")
            st.markdown("**加好友时请注明：** `RedInsight激活`")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("重新发送", use_container_width=True):
                    st.session_state.activation_sent = False
                    st.rerun()
            with col2:
                if st.button("我已收到激活码", type="primary", use_container_width=True):
                    st.session_state.activation_step = 3
                    st.rerun()
    
    # 步骤3: 输入激活码
    elif st.session_state.activation_step == 3:
        st.markdown("### 步骤 3/3: 输入激活码")
        
        email = st.session_state.activation_email
        
        st.info(f"**邮箱:** `{email}`")
        st.info(f"**机器码:** `{machine_code}`")
        
        activation_code = st.text_input(
            "激活码",
            key="activation_code_input",
            help="激活码格式为 LICENSE-XXXX-XXXX-XXXX-... (可能有多个组)"
        )
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("返回上一步", use_container_width=True):
                st.session_state.activation_step = 2
                st.rerun()
        with col2:
            if st.button("验证激活码", type="primary", use_container_width=True):
                if not activation_code:
                    st.error("❌ 请输入激活码")
                else:
                    # 清理激活码（移除空格）
                    activation_code = activation_code.replace(' ', '').strip()
                    
                    with st.spinner("正在验证激活码..."):
                        is_valid, message = validate_activation_code(activation_code, email, machine_code)
                        
                        if is_valid:
                            # 保存激活信息
                            if save_activation_info(machine_code, email, activation_code):
                                st.success(f"✅ {message}")
                                st.success("🎉 激活成功！正在重新加载...")
                                time.sleep(1)
                                # 清除激活相关的session state
                                for key in ['activation_step', 'activation_email', 'activation_machine_code', 'activation_sent']:
                                    if key in st.session_state:
                                        del st.session_state[key]
                                st.rerun()
                            else:
                                st.error("❌ 保存激活信息失败")
                        else:
                            st.error(f"❌ 激活码验证失败")
                            st.warning(f"**原因:** {message}")
                            st.info("""
                            **请确认：**
                            1. 激活码是否正确（注意大小写和连字符）
                            2. 邮箱是否与提供给管理员的一致
                            3. 是否在正确的机器上激活
                            """)
    
    # 显示帮助信息
    with st.expander("ℹ️ 激活帮助"):
        st.markdown("""
        **激活流程说明：**
        1. 输入您的邮箱地址
        2. 系统会生成机器码并发送注册信息到服务器
        3. 联系管理员获取激活码（提供机器码和邮箱）
        4. 输入激活码完成激活
        
        **常见问题：**
        - 如果机器码变化（如更换硬件），需要重新激活
        - 激活码与机器码和邮箱绑定，不能跨机器使用
        - 如有问题，请联系管理员：**微信号 `whj7087824`**
        """)


def check_and_handle_activation():
    """检查激活状态，如果未激活则显示激活页面"""
    if not ACTIVATION_AVAILABLE:
        # 如果激活模块不可用，允许继续（向后兼容）
        logger.warning("激活模块不可用，跳过激活检查")
        return True
    
    try:
        # 检查是否已激活
        if check_activation_status():
            # 验证现有激活
            if verify_existing_activation():
                return True
            else:
                # 验证失败，需要重新激活
                # 删除旧激活信息
                if os.path.exists(ACTIVATION_FILE):
                    try:
                        os.remove(ACTIVATION_FILE)
                    except:
                        pass
                # 显示激活页面
                render_activation_page()
                st.stop()
        else:
            # 未激活，显示激活页面
            render_activation_page()
            st.stop()
    except Exception as e:
        logger.error(f"激活检查过程出错: {str(e)}")
        # 出错时允许继续（向后兼容），但记录错误
        st.warning(f"⚠️ 激活检查失败: {str(e)}")
        return True


def auto_check_analysis_status():
    """自动检查分析状态并显示提示"""
    try:
        if not BACKGROUND_ANALYZER_AVAILABLE or not background_analyzer:
            return
        
        # 如果分析完成，显示提示
        if BACKGROUND_ANALYZER_AVAILABLE and background_analyzer and background_analyzer.is_completed():
            if not st.session_state.get('analysis_completion_notified', False):
                st.success("🎉 深度分析已完成！请切换到'深度分析'标签页查看结果。")
                st.balloons()
                st.session_state.analysis_completion_notified = True
                
        # 如果分析失败，显示错误
        elif BACKGROUND_ANALYZER_AVAILABLE and background_analyzer and background_analyzer.is_failed():
            if not st.session_state.get('analysis_failure_notified', False):
                st.error("❌ 深度分析失败！请切换到'深度分析'标签页查看错误信息。")
                st.session_state.analysis_failure_notified = True
                
    except Exception as e:
        pass

def auto_restore_reddit_auth():
    """自动恢复Reddit认证状态（项目启动时调用）"""
    try:
        # 检查是否有保存的认证信息
        api_keys = st.session_state.api_keys
        access_token = api_keys.get('reddit_access_token', '')
        reddit_username = api_keys.get('reddit_username', '')
        reddit_password = api_keys.get('reddit_password', '')
        reddit_client_id = api_keys.get('reddit_client_id', '')
        reddit_client_secret = api_keys.get('reddit_client_secret', '')
        reddit_redirect_uri = api_keys.get('reddit_redirect_uri', 'http://localhost:8080')
        
        # 如果没有必要的配置，跳过自动恢复
        if not reddit_client_id or not reddit_client_secret:
            return False
        
        # 如果有access_token，先验证是否有效
        if access_token:
            try:
                from reddit_scraper import RedditScraper
                test_scraper = RedditScraper(
                    access_token=access_token,
                    client_id=reddit_client_id,
                    client_secret=reddit_client_secret,
                    redirect_uri=reddit_redirect_uri
                )
                
                # 验证token是否有效
                if test_scraper.is_authenticated():
                    username = test_scraper.get_authenticated_user()
                    if username:
                        # Token有效，恢复认证状态
                        st.session_state.scraper = test_scraper
                        st.session_state.auth_user = username
                        st.session_state.last_verified_token = access_token
                        st.session_state['last_verify_time'] = time.time()
                        
                        # 更新后台自动发帖服务的 scraper（如果服务正在运行）
                        try:
                            if 'posting_auto_service' in st.session_state:
                                svc = st.session_state.posting_auto_service
                                if svc and hasattr(svc, 'is_alive') and svc.is_alive():
                                    svc.set_scraper(test_scraper)
                                    logger.info("已更新后台自动发帖服务的认证状态（自动恢复）")
                        except Exception as e:
                            logger.warning(f"更新后台自动发帖服务认证状态失败: {str(e)}")
                        
                        logger.info(f"✅ 自动恢复Reddit认证成功 - 用户名: {username}")
                        return True
            except Exception as e:
                logger.warning(f"验证保存的access_token失败: {str(e)}")
        
        # 如果access_token无效或不存在，尝试使用保存的username/password重新认证
        if reddit_username and reddit_password:
            try:
                from reddit_scraper import RedditScraper
                import praw
                
                logger.info("尝试使用保存的username/password重新认证...")
                
                # 创建scraper实例
                scraper = RedditScraper(
                    client_id=reddit_client_id,
                    client_secret=reddit_client_secret,
                    redirect_uri=reddit_redirect_uri
                )
                
                # 使用密码认证获取新的access_token
                new_access_token = scraper.authenticate_with_password(reddit_username, reddit_password)
                
                # 使用username/password创建PRAW实例（推荐方式，支持写操作）
                praw_instance = praw.Reddit(
                    client_id=reddit_client_id,
                    client_secret=reddit_client_secret,
                    user_agent='RedInsight Bot 1.0',
                    username=reddit_username,
                    password=reddit_password
                )
                
                # 确保PRAW实例不是只读模式
                try:
                    praw_instance.read_only = False
                except Exception:
                    pass
                
                # 替换PRAW实例
                scraper.reddit = praw_instance
                scraper.access_token = new_access_token
                scraper._using_username_password = True
                
                # 验证认证结果
                try:
                    user = praw_instance.user.me()
                    if user:
                        username = str(user)
                    else:
                        username = reddit_username  # 如果无法获取，使用保存的用户名
                except Exception:
                    username = reddit_username
                
                # 更新配置中的access_token
                api_keys['reddit_access_token'] = new_access_token
                save_config(api_keys)
                
                # 更新session_state
                st.session_state.scraper = scraper
                st.session_state.auth_user = username
                st.session_state.last_verified_token = new_access_token
                st.session_state['last_verify_time'] = time.time()
                
                # 更新后台自动发帖服务的 scraper（如果服务正在运行）
                try:
                    if 'posting_auto_service' in st.session_state:
                        svc = st.session_state.posting_auto_service
                        if svc and hasattr(svc, 'is_alive') and svc.is_alive():
                            svc.set_scraper(scraper)
                            logger.info("已更新后台自动发帖服务的认证状态（自动恢复）")
                except Exception as e:
                    logger.warning(f"更新后台自动发帖服务认证状态失败: {str(e)}")
                
                logger.info(f"✅ 使用保存的凭据重新认证成功 - 用户名: {username}")
                return True
                
            except Exception as e:
                logger.error(f"使用保存的凭据重新认证失败: {str(e)}")
                return False
        
        return False
        
    except Exception as e:
        logger.error(f"自动恢复Reddit认证失败: {str(e)}")
        return False

def main():
    """主函数"""
    # 首先检查激活状态（必须在最前面）
    if not check_and_handle_activation():
        return  # 如果未激活，已在check_and_handle_activation中显示激活页面并stop()
    
    # 自动恢复Reddit认证状态（仅在首次加载时执行）
    if not st.session_state.get('auth_restored', False):
        auto_restore_reddit_auth()
        st.session_state.auth_restored = True
    
    # 检查是否有已完成的分析结果
    check_completed_analysis()
    
    # 标题
    st.markdown('<h1 class="main-header">🔍 RedInsight - Reddit自动化、数据分析工具</h1>', unsafe_allow_html=True)
    
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
        
        # 优化：只在token变化或首次加载时验证，使用缓存减少验证频率
        current_token = st.session_state.api_keys.get('reddit_access_token', '')
        last_verified_token = st.session_state.get('last_verified_token', '')
        token_changed = current_token != last_verified_token
        last_verify_time = st.session_state.get('last_verify_time', 0)
        current_time = time.time()
        
        # 如果token未变化且最近5分钟内已验证过，跳过验证
        # 如果已经通过自动恢复认证，也跳过验证
        should_verify = (token_changed or 
                        current_time - last_verify_time > 300 or  # 5分钟缓存
                        not st.session_state.get('auth_user'))
        
        if current_token:
            # 如果已有有效的scraper实例且token未变化且最近已验证，直接使用
            # 或者已经通过自动恢复认证成功
            if (st.session_state.scraper and 
                hasattr(st.session_state, 'auth_user') and 
                st.session_state.auth_user and 
                (not should_verify or st.session_state.get('auth_restored', False))):
                st.success(f"✅ Reddit API 已认证 - 用户名: {st.session_state.auth_user}")
                # 如果是从自动恢复获得的认证，显示提示
                if st.session_state.get('auth_restored', False) and not st.session_state.get('auth_restore_notified', False):
                    st.info("ℹ️ 已自动恢复认证状态，无需重新登录")
                    st.session_state.auth_restore_notified = True
            elif should_verify:
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
                        st.session_state['last_verify_time'] = current_time
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
                        
                        # 更新后台自动发帖服务的 scraper（如果服务正在运行）
                        try:
                            if 'posting_auto_service' in st.session_state:
                                svc = st.session_state.posting_auto_service
                                if svc and hasattr(svc, 'is_alive') and svc.is_alive():
                                    svc.set_scraper(test_scraper)
                                    logger.info("已更新后台自动发帖服务的认证状态")
                        except Exception as e:
                            logger.warning(f"更新后台自动发帖服务认证状态失败: {str(e)}")
                    else:
                        st.error("❌ Reddit API 认证已过期")
                        st.session_state.api_keys['reddit_access_token'] = ''
                        st.session_state.last_verified_token = ''
                        st.session_state['last_verify_time'] = 0
                        save_config(st.session_state.api_keys)
                except Exception as e:
                    st.error("❌ Reddit API 认证验证失败")
                    st.session_state.api_keys['reddit_access_token'] = ''
                    st.session_state.last_verified_token = ''
                    st.session_state['last_verify_time'] = 0
                    save_config(st.session_state.api_keys)
        else:
            st.error("❌ Reddit API 未认证")
            st.session_state.last_verified_token = ''
            st.session_state['last_verify_time'] = 0
        
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
                            import app_config as config
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
                                # 保存用户名和密码，以便后台服务重新认证时使用
                                # 注意：虽然保存密码有安全风险，但对于自动化系统是必要的
                                st.session_state.api_keys['reddit_username'] = reddit_username
                                st.session_state.api_keys['reddit_password'] = reddit_password
                            
                            # 立即保存到配置文件
                            save_config(st.session_state.api_keys)
                            
                            # 重要：使用username/password创建PRAW实例，而不是使用access_token
                            # 这样PRAW会正确设置用户认证状态，可以执行点赞等操作
                            from reddit_scraper import RedditScraper
                            import praw
                            
                            # 使用username/password创建PRAW实例（推荐方式，PRAW会自动处理OAuth2认证）
                            praw_instance = praw.Reddit(
                                client_id=reddit_client_id,
                                client_secret=reddit_client_secret,
                                user_agent='RedInsight Bot 1.0',
                                username=reddit_username,
                                password=reddit_password
                            )
                            
                            # 确保PRAW实例不是只读模式
                            try:
                                praw_instance.read_only = False
                            except Exception:
                                pass
                            
                            # 创建RedditScraper实例，但不传入access_token（避免创建只读实例）
                            # 然后替换PRAW实例为我们使用username/password创建的实例
                            authenticated_scraper = RedditScraper(
                                client_id=reddit_client_id,
                                client_secret=reddit_client_secret,
                                redirect_uri=reddit_redirect_uri
                                # 注意：不传入 access_token，避免创建只读实例
                            )
                            # 替换PRAW实例为我们创建的实例（使用username/password，可写）
                            authenticated_scraper.reddit = praw_instance
                            authenticated_scraper.access_token = access_token  # 保存access_token用于is_authenticated()验证
                            authenticated_scraper._using_username_password = True  # 标记是使用username/password创建的
                            
                            # 验证认证结果
                            try:
                                user = praw_instance.user.me()
                                if user:
                                    username = str(user)
                                    with result_container:
                                        st.success(f"✅ 认证成功！用户名: {username}")
                                        st.balloons()
                                    
                                    # 更新session_state中的scraper实例（使用username/password创建的PRAW实例）
                                    st.session_state.scraper = authenticated_scraper
                                    
                                    # 更新后台自动发帖服务的 scraper（如果服务正在运行）
                                    try:
                                        if 'posting_auto_service' in st.session_state:
                                            svc = st.session_state.posting_auto_service
                                            if svc and hasattr(svc, 'is_alive') and svc.is_alive():
                                                svc.set_scraper(authenticated_scraper)
                                                logger.info("已更新后台自动发帖服务的认证状态（username/password方式）")
                                    except Exception as e:
                                        logger.warning(f"更新后台自动发帖服务认证状态失败: {str(e)}")
                                else:
                                    # 即使user.me()返回None，也继续使用（可能仍然可以执行操作）
                                    with result_container:
                                        st.success(f"✅ 认证成功！access_token已获取")
                                        st.info("⚠️ 注意：无法获取用户信息，但PRAW实例已创建，应该可以执行操作")
                                    
                                    # 确保标记已设置
                                    authenticated_scraper._using_username_password = True
                                    st.session_state.scraper = authenticated_scraper
                                    
                                    # 更新后台自动发帖服务的 scraper（如果服务正在运行）
                                    try:
                                        if 'posting_auto_service' in st.session_state:
                                            svc = st.session_state.posting_auto_service
                                            if svc and hasattr(svc, 'is_alive') and svc.is_alive():
                                                svc.set_scraper(authenticated_scraper)
                                                logger.info("已更新后台自动发帖服务的认证状态（username/password方式，user.me()返回None）")
                                    except Exception as e:
                                        logger.warning(f"更新后台自动发帖服务认证状态失败: {str(e)}")
                            except Exception as e:
                                # 如果user.me()失败，仍然使用创建的实例
                                with result_container:
                                    st.warning(f"⚠️ 无法获取用户信息: {str(e)}，但PRAW实例已创建")
                                
                                # 确保标记已设置
                                authenticated_scraper._using_username_password = True
                                st.session_state.scraper = authenticated_scraper
                                
                                # 更新后台自动发帖服务的 scraper（如果服务正在运行）
                                try:
                                    if 'posting_auto_service' in st.session_state:
                                        svc = st.session_state.posting_auto_service
                                        if svc and hasattr(svc, 'is_alive') and svc.is_alive():
                                            svc.set_scraper(authenticated_scraper)
                                            logger.info("已更新后台自动发帖服务的认证状态（username/password方式，异常情况）")
                                except Exception as update_e:
                                    logger.warning(f"更新后台自动发帖服务认证状态失败: {str(update_e)}")
                                
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
        
        # 初始化系统按钮
        st.divider()
        if st.button("🚀 初始化系统", type="primary", key="init_system"):
            with st.spinner("正在初始化系统..."):
                if init_components():
                    st.success("✅ 系统初始化成功！")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ 系统初始化失败，请检查配置")
        
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
            if not BACKGROUND_ANALYZER_AVAILABLE or not background_analyzer:
                st.info("ℹ️ 后台分析器不可用")
            else:
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
                elif BACKGROUND_ANALYZER_AVAILABLE and background_analyzer and background_analyzer.is_completed():
                    st.success("✅ 分析已完成")
                    st.balloons()  # 添加气球庆祝动画
                    if st.button("🚀 查看结果", key="sidebar_view_results"):
                        st.switch_page("深度分析")
                elif BACKGROUND_ANALYZER_AVAILABLE and background_analyzer and background_analyzer.is_failed():
                    st.error("❌ 分析失败")
                    if st.button("🔄 重新开始", key="sidebar_restart"):
                        if BACKGROUND_ANALYZER_AVAILABLE and background_analyzer:
                            background_analyzer.clear_status()
                        # 清除分析状态缓存
                        get_analysis_status.clear()
                        st.success("分析状态已重置")
                else:
                    st.info("💤 无分析任务")
        except Exception as e:
            st.info("💤 无分析任务")
    
    # 主内容区域
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📥 数据抓取", 
        "📊 本地数据管理", 
        "🎯 子版块推荐", 
        "🔧 自动点赞回帖控制台", 
        "🔍 智能筛选",
        "📝 智能发帖"
    ])
    
    with tab1:
        try:
            render_data_scraping_tab()
        except Exception as e:
            st.error(f"❌ 加载数据抓取页面失败: {str(e)}")
            import traceback
            with st.expander("查看错误详情"):
                st.code(traceback.format_exc())
    
    with tab2:
        try:
            render_data_management_tab()
        except Exception as e:
            st.error(f"❌ 加载本地数据管理页面失败: {str(e)}")
            import traceback
            with st.expander("查看错误详情"):
                st.code(traceback.format_exc())
    
    with tab3:
        try:
            render_subreddit_recommendation_tab()
        except Exception as e:
            st.error(f"❌ 加载子版块推荐页面失败: {str(e)}")
            import traceback
            with st.expander("查看错误详情"):
                st.code(traceback.format_exc())
    
    with tab4:
        # 自动点赞回帖控制台
        if st.session_state.initialized:
            # 导入所需模块
            try:
                from reddit_publisher import RedditPublisher
                from interaction_manager import InteractionManager
                from monitoring_service import MonitoringService
                from account_readiness import AccountReadinessService
                # background_analyzer 已在文件顶部导入（可选）
                
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
                
                # ========== 功能标签页 ==========
                tab_auto, tab_tasks = st.tabs([
                    "🤖 自动化运营",
                    "📋 任务管理"
                ])
                
                # ========== 自动化运营 ==========
                with tab_auto:
                    st.subheader("🤖 自动化运营")
                    
                    # 检查模块是否可用
                    modules_available = AUTO_MODULES_AVAILABLE and not st.session_state.get('auto_modules_failed', False)
                    
                    if not modules_available:
                        error_msg = AUTO_MODULES_ERROR if AUTO_MODULES_ERROR else '未知错误'
                        st.error(f"❌ 自动化模块未加载: {error_msg}")
                        st.stop()
                    
                    # 初始化组件（如果未初始化）
                    try:
                        if 'auto_config' not in st.session_state:
                            st.session_state.auto_config = AutoConfig(st.session_state.db)
                        auto_config = st.session_state.auto_config

                        if 'rpta_scorer' not in st.session_state:
                            rpta_config = auto_config.get_rpta_config() or auto_config.get_default_config()
                            st.session_state.rpta_scorer = RPTAScorer(
                                st.session_state.analyzer,
                                rpta_config.get('keywords', []),
                                db_manager=st.session_state.db
                            )
                            st.session_state.rpta_scorer.set_weights(
                                rpta_config['weights']['r'],
                                rpta_config['weights']['p'],
                                rpta_config['weights']['t'],
                                rpta_config['weights']['a']
                            )

                        if 'task_executor' not in st.session_state:
                            st.session_state.task_executor = TaskExecutor(
                                st.session_state.db,
                                st.session_state.interaction_manager,
                                st.session_state.analyzer,
                                st.session_state.scraper
                            )
                        else:
                            # 确保执行器使用最新scraper（避免认证更新后仍引用旧对象）
                            try:
                                st.session_state.task_executor.scraper = st.session_state.scraper
                            except Exception:
                                pass

                        if 'auto_scheduler' not in st.session_state:
                            st.session_state.auto_scheduler = AutoScheduler(
                                st.session_state.db,
                                st.session_state.scraper,
                                st.session_state.rpta_scorer,
                                st.session_state.task_executor,
                                auto_config
                            )
                        else:
                            try:
                                st.session_state.auto_scheduler.scraper = st.session_state.scraper
                            except Exception:
                                pass

                        def _ensure_auto_service():
                            """确保后台服务存在（避免点击开始后还需要手动刷新/停留页面）。"""
                            try:
                                from auto_execution_service import AutoExecutionService
                            except Exception as e:
                                logger.warning(f"无法导入后台执行服务: {str(e)}")
                                st.session_state.auto_service = None
                                return None

                            service = st.session_state.get('auto_service')
                            # 已存在且存活则复用
                            if service and hasattr(service, 'is_alive') and service.is_alive():
                                return service

                            st.session_state.auto_service = AutoExecutionService(
                                st.session_state.db,
                                st.session_state.scraper,
                                st.session_state.rpta_scorer,
                                st.session_state.task_executor,
                                auto_config,
                                st.session_state.auto_scheduler,
                                post_executor=None
                            )
                            return st.session_state.auto_service

                        # 如果还没有auto_service，先占位（真正启动时再确保创建）
                        if 'auto_service' not in st.session_state:
                            st.session_state.auto_service = None
                    except Exception as e:
                        st.error(f"初始化自动化组件失败: {str(e)}")
                        st.session_state.auto_modules_failed = True
                        st.stop()
                    
                    # ========== 控制面板 ==========
                    st.markdown("### 🎛️ 控制面板")
                    
                    # 获取运行状态
                    try:
                        status = st.session_state.db.get_status()
                        is_running = status.get('is_running', False) if status else False
                    except:
                        is_running = False
                    
                    # 运行/停止控制
                    col_control1, col_control2, col_control3 = st.columns([2, 2, 2])
                    
                    with col_control1:
                        if is_running:
                            if st.button("⏸️ 停止运行", type="primary", key="stop_auto"):
                                try:
                                    st.session_state.db.update_status(is_running=False, is_paused=True)
                                    # 停止后台服务
                                    if 'auto_service' in st.session_state and st.session_state.auto_service:
                                        st.session_state.auto_service.stop()
                                    st.success("✅ 已停止运行")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"停止失败: {str(e)}")
                        else:
                            if st.button("▶️ 开始运行", type="primary", key="start_auto"):
                                try:
                                    # 先更新数据库状态
                                    st.session_state.db.update_status(is_running=True, is_paused=False)
                                    
                                    # 启动后台服务
                                    service = None
                                    try:
                                        service = _ensure_auto_service()
                                    except Exception:
                                        service = st.session_state.get('auto_service')

                                    if service:
                                        try:
                                            service.start()
                                            # 等待一小段时间，确保线程启动
                                            time.sleep(0.5)
                                            
                                            # 验证服务是否成功启动
                                            if service.is_alive():
                                                st.success("✅ 已开始运行（后台服务已启动）")
                                            else:
                                                st.warning("⚠️ 后台服务启动可能失败，请检查日志")
                                        except Exception as start_error:
                                            st.error(f"启动后台服务失败: {str(start_error)}")
                                            import traceback
                                            logger.error(f"启动后台服务异常: {traceback.format_exc()}")
                                    else:
                                        st.warning("⚠️ 后台服务未初始化，将使用页面刷新模式执行任务（需停留在本页）")
                                    
                                    # 清除缓存
                                    get_cached_pending_tasks.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"启动失败: {str(e)}")
                                    import traceback
                                    logger.error(f"启动自动化运营失败: {traceback.format_exc()}")
                    
                    with col_control2:
                        if st.button("🔄 重置失败任务", key="reset_failed_tasks"):
                            try:
                                # 重置失败和卡住的任务为pending状态
                                reset_count = st.session_state.db.reset_failed_tasks(reset_executing=True)
                                if reset_count > 0:
                                    st.success(f"✅ 已重置 {reset_count} 个失败/卡住的任务为待执行状态")
                                    # 清除缓存，确保显示最新数据
                                    get_cached_pending_tasks.clear()
                                    if 'get_task_statistics_cached' in globals():
                                        get_task_statistics_cached.clear()
                                    st.rerun()
                                else:
                                    st.info("ℹ️ 没有需要重置的任务")
                            except Exception as e:
                                st.error(f"重置失败: {str(e)}")
                                import traceback
                                st.caption(traceback.format_exc())
                    
                    with col_control3:
                        if st.button("🗑️ 清空队列", key="clear_queue"):
                            try:
                                session = st.session_state.db.SessionLocal()
                                try:
                                    # 删除所有pending状态的任务
                                    deleted = session.query(st.session_state.db.AutoInteractionQueue).filter_by(
                                        status='pending'
                                    ).delete()
                                    session.commit()
                                    st.success(f"✅ 已清空 {deleted} 个待执行任务")
                                    # 清除缓存，确保显示最新数据
                                    get_cached_pending_tasks.clear()
                                    if 'get_task_statistics_cached' in globals():
                                        get_task_statistics_cached.clear()
                                    st.rerun()
                                finally:
                                    session.close()
                            except Exception as e:
                                st.error(f"清空失败: {str(e)}")
                    
                    # 完整重置功能
                    st.markdown("---")
                    st.markdown("#### 🔄 完整重置功能")
                    st.warning("⚠️ 此操作将停止运行、清理所有待执行任务、重置统计信息并清理活动日志。已完成的任务将保留作为历史记录。")
                    
                    col_reset1, col_reset2 = st.columns(2)
                    
                    with col_reset1:
                        clear_all_tasks = st.checkbox("清理所有待执行任务", value=True, key="reset_clear_tasks", help="删除所有pending、executing、failed状态的任务")
                        reset_statistics = st.checkbox("重置运行统计", value=True, key="reset_statistics", help="重置累计扫描数、评分数、执行数")
                        clear_activity_logs = st.checkbox("清理活动日志", value=True, key="reset_clear_logs", help="清理所有活动日志记录")
                    
                    with col_reset2:
                        if st.button("🔄 完整重置自动运营", type="primary", key="full_reset_auto_operation"):
                            try:
                                # 停止后台服务
                                if 'auto_service' in st.session_state and st.session_state.auto_service:
                                    try:
                                        st.session_state.auto_service.stop()
                                    except:
                                        pass
                                
                                # 执行完整重置
                                reset_result = st.session_state.db.reset_auto_operation(
                                    clear_all_tasks=clear_all_tasks,
                                    reset_statistics=reset_statistics,
                                    clear_activity_logs=clear_activity_logs
                                )
                                
                                # 清理session_state中的活动日志
                                if 'auto_activity_log' in st.session_state:
                                    st.session_state.auto_activity_log = []
                                
                                # 清理其他相关状态
                                if 'last_auto_exec_time' in st.session_state:
                                    del st.session_state['last_auto_exec_time']
                                if 'last_status_log_time' in st.session_state:
                                    del st.session_state['last_status_log_time']
                                if 'last_no_task_check' in st.session_state:
                                    del st.session_state['last_no_task_check']
                                
                                # 显示重置结果
                                result_msg = "✅ 自动运营功能已完整重置：\n"
                                if clear_all_tasks:
                                    result_msg += f"- 已删除 {reset_result['tasks_deleted']} 个任务\n"
                                    if reset_result['tasks_reset'] > 0:
                                        result_msg += f"- 已重置 {reset_result['tasks_reset']} 个任务\n"
                                if reset_statistics and reset_result['statistics_reset']:
                                    result_msg += "- 已重置运行统计\n"
                                if clear_activity_logs and reset_result['logs_cleared']:
                                    result_msg += "- 已清理活动日志\n"
                                
                                st.success(result_msg)
                                st.info("💡 页面将自动刷新，请稍候...")
                                
                                # 等待一下再刷新，让用户看到成功消息
                                time.sleep(1)
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"重置失败: {str(e)}")
                                import traceback
                                with st.expander("查看错误详情"):
                                    st.code(traceback.format_exc())
                    
                    # 配置区域
                    with st.expander("⚙️ 执行配置", expanded=False):
                        # 获取当前配置
                        scheduler_config = st.session_state.auto_config.get_scheduler_config() or st.session_state.auto_config.get_default_scheduler_config()
                        
                        col_config1, col_config2 = st.columns(2)
                        
                        with col_config1:
                            st.markdown("#### ⏰ 执行时间设定")
                            exec_time = scheduler_config.get('execution_time', {})
                            start_time = st.time_input(
                                "开始时间",
                                value=datetime.strptime(exec_time.get('start', '08:00'), '%H:%M').time(),
                                key="exec_start_time"
                            )
                            end_time = st.time_input(
                                "结束时间",
                                value=datetime.strptime(exec_time.get('end', '20:00'), '%H:%M').time(),
                                key="exec_end_time"
                            )
                        
                        with col_config2:
                            st.markdown("#### 📊 执行次数设置")
                            exec_limits = scheduler_config.get('execution_limits', {})
                            deep_limit = st.number_input(
                                "深度互动次数/日",
                                min_value=0,
                                max_value=50,
                                value=exec_limits.get('deep', 3),
                                key="exec_deep_limit",
                                help="评分≥0.85的帖子"
                            )
                            standard_limit = st.number_input(
                                "中度互动次数/日",
                                min_value=0,
                                max_value=50,
                                value=exec_limits.get('standard', 5),
                                key="exec_standard_limit",
                                help="评分0.65-0.85的帖子"
                            )
                            light_limit = st.number_input(
                                "轻度互动次数/日",
                                min_value=0,
                                max_value=50,
                                value=exec_limits.get('light', 10),
                                key="exec_light_limit",
                                help="评分0.50-0.65的帖子"
                            )
                        
                        # 自动延续未完成任务
                        auto_resume = st.checkbox(
                            "自动延续未完成任务",
                            value=scheduler_config.get('auto_resume', True),
                            key="auto_resume_check",
                            help="再次开启时自动执行之前未完成的任务"
                        )
                        
                        # 保存配置
                        if st.button("💾 保存配置", type="primary", key="save_scheduler_config"):
                            try:
                                new_config = {
                                    'execution_time': {
                                        'start': start_time.strftime('%H:%M'),
                                        'end': end_time.strftime('%H:%M')
                                    },
                                    'execution_limits': {
                                        'deep': int(deep_limit),
                                        'standard': int(standard_limit),
                                        'light': int(light_limit)
                                    },
                                    'auto_resume': auto_resume
                                }
                                if st.session_state.auto_config.save_scheduler_config(new_config):
                                    st.success("✅ 配置已保存")
                                    st.rerun()
                                else:
                                    st.error("❌ 保存配置失败")
                            except Exception as e:
                                st.error(f"保存配置失败: {str(e)}")
                    
                    # 关键词输入和自动处理
                    st.markdown("---")
                    col_keyword1, col_keyword2 = st.columns([3, 1])
                    
                    with col_keyword1:
                        search_keywords = st.text_input(
                            "🔑 输入关键词",
                            value="",
                            placeholder="例如：portable charger, power bank, camping",
                            key="auto_search_keywords",
                            help="系统将根据关键词自动搜索Reddit帖子、评分并加入执行队列（仅抓取6个月内的帖子）"
                        )
                    
                    with col_keyword2:
                        search_limit = st.number_input(
                            "搜索数量",
                            min_value=10,
                            max_value=200,
                            value=100,
                            key="auto_search_limit",
                            help="每次搜索的帖子数量"
                        )
                    
                    # 自动处理关键词（当系统运行中且有关键词时）
                    if is_running and search_keywords and search_keywords.strip():
                        # 保存关键词到历史记录
                        try:
                            if st.session_state.get('db'):
                                st.session_state.db.save_keywords_to_history(search_keywords, source="auto_scheduler")
                        except Exception:
                            pass  # 静默失败，不影响处理流程
                        
                        # 初始化活动日志
                        if 'auto_activity_log' not in st.session_state:
                            st.session_state.auto_activity_log = []
                        
                        # 检查是否已经处理过这个关键词（避免重复处理）
                        keyword_key = f"processed_keyword_{search_keywords.strip()}"
                        last_processed = st.session_state.get(keyword_key)
                        
                        # 如果关键词改变或首次输入，自动处理
                        if last_processed != search_keywords.strip():
                            try:
                                # 定义进度回调函数
                                def progress_callback(log_type, message):
                                    timestamp = datetime.now().strftime("%H:%M:%S")
                                    st.session_state.auto_activity_log.append({
                                        'type': log_type,
                                        'timestamp': timestamp,
                                        'message': message
                                    })
                                
                                # 开始处理
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                st.session_state.auto_activity_log.append({
                                    'type': 'info',
                                    'timestamp': timestamp,
                                    'message': f"🚀 开始处理关键词: {search_keywords.strip()} (搜索数量: {search_limit})"
                                })
                                
                                # 处理关键词（带进度回调）
                                result = st.session_state.auto_scheduler.process_keywords(
                                    search_keywords.strip(),
                                    search_limit,
                                    progress_callback=progress_callback
                                )
                                
                                if result.get('success'):
                                    st.session_state[keyword_key] = search_keywords.strip()
                                    
                                    # 更新统计
                                    try:
                                        current_status = st.session_state.db.get_status()
                                        if current_status:
                                            new_scanned = current_status.get('total_scanned', 0) + result.get('total_searched', 0)
                                            new_scored = current_status.get('total_scored', 0) + result.get('scored', 0)
                                            st.session_state.db.update_status(
                                                total_scanned=new_scanned,
                                                total_scored=new_scored
                                            )
                                    except:
                                        pass
                                    
                                    # 最终结果日志
                                    timestamp = datetime.now().strftime("%H:%M:%S")
                                    st.session_state.auto_activity_log.append({
                                        'type': 'success',
                                        'timestamp': timestamp,
                                        'message': f"🎉 关键词处理完成！搜索 {result.get('total_searched', 0)} 个 → 评分 {result.get('scored', 0)} 个 → 通过 {result.get('passed_threshold', 0)} 个 → 加入队列 {result.get('added_to_queue', 0)} 个任务"
                                    })
                                    
                                    # 清除缓存，确保下次获取最新数据
                                    get_cached_pending_tasks.clear()
                                    time.sleep(2)  # 短暂延迟后刷新
                                    st.rerun()
                                else:
                                    # 失败日志已在progress_callback中记录
                                    timestamp = datetime.now().strftime("%H:%M:%S")
                                    st.session_state.auto_activity_log.append({
                                        'type': 'error',
                                        'timestamp': timestamp,
                                        'message': f"❌ 关键词处理失败: {result.get('error', '未知错误')}"
                                    })
                            except Exception as e:
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                st.session_state.auto_activity_log.append({
                                    'type': 'error',
                                    'timestamp': timestamp,
                                    'message': f"❌ 处理关键词异常: {str(e)}"
                                })
                                import traceback
                                logger.error(traceback.format_exc())
                    
                    # 检查后台服务状态
                    use_backend_service = False
                    if 'auto_service' in st.session_state and st.session_state.auto_service:
                        use_backend_service = st.session_state.auto_service.is_alive()
                        if use_backend_service:
                            service_status = "🟢 运行中"
                        else:
                            service_status = "⚪ 已停止"
                        st.caption(f"后台服务状态: {service_status}")
                    
                    # 自动执行任务（当系统运行中时，每次页面刷新执行一个任务）
                    # 注意：如果后台服务运行中，这里只做状态显示，不执行任务（避免重复执行）
                    if is_running and not use_backend_service:
                        # 初始化活动日志
                        if 'auto_activity_log' not in st.session_state:
                            st.session_state.auto_activity_log = []
                        
                        try:
                            # 检查是否在本次会话中已执行过任务（避免同一刷新周期重复执行）
                            last_exec_time = st.session_state.get('last_auto_exec_time', 0)
                            current_time = time.time()
                            
                            # 获取配置信息
                            scheduler_config = st.session_state.auto_config.get_scheduler_config() or st.session_state.auto_config.get_default_scheduler_config()
                            exec_time = scheduler_config.get('execution_time', {})
                            
                            # 检查执行时间
                            current_dt = datetime.now()
                            start_str = exec_time.get('start', '08:00')
                            end_str = exec_time.get('end', '20:00')
                            start_time = datetime.strptime(start_str, '%H:%M').time()
                            end_time = datetime.strptime(end_str, '%H:%M').time()
                            current_time_only = current_dt.time()
                            
                            # 获取待执行任务（使用缓存）
                            pending_tasks = get_cached_pending_tasks(st.session_state.db, limit=1000)
                            pending_count = len(pending_tasks) if pending_tasks else 0
                            
                            # 添加状态检查日志（每10秒一次，避免日志过多）
                            last_status_log = st.session_state.get('last_status_log_time', 0)
                            if current_time - last_status_log > 10:
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                status_msg = f"系统运行中 | 当前时间: {current_time_only.strftime('%H:%M')} | 执行时间段: {start_str}-{end_str} | 待执行任务: {pending_count}"
                                
                                # 检查是否在执行时间段内
                                if start_time <= current_time_only <= end_time:
                                    status_msg += " | ✅ 在执行时间段内"
                                else:
                                    status_msg += " | ⏸️ 不在执行时间段内"
                                
                                st.session_state.auto_activity_log.append({
                                    'type': 'info',
                                    'timestamp': timestamp,
                                    'message': status_msg
                                })
                                st.session_state['last_status_log_time'] = current_time
                            
                            # 优化：如果距离上次执行超过5秒，才执行新任务（避免过快刷新，从3秒增加到5秒）
                            if current_time - last_exec_time > 5:
                                if pending_tasks:
                                    task = pending_tasks[0]
                                    
                                    # 添加开始执行日志
                                    timestamp = datetime.now().strftime("%H:%M:%S")
                                    st.session_state.auto_activity_log.append({
                                        'type': 'info',
                                        'timestamp': timestamp,
                                        'message': f"准备执行任务 #{task['id']} ({task['interaction_type']}) - r/{task['subreddit']} (评分: {task['post_score']:.2f})"
                                    })
                                    
                                    # 执行下一个任务
                                    exec_result = st.session_state.auto_scheduler.execute_next_task()
                                    
                                    if exec_result.get('success'):
                                        st.session_state['last_auto_exec_time'] = time.time()
                                        
                                        # 添加成功日志
                                        actions = exec_result.get('actions', [])
                                        actions_str = ', '.join(actions) if actions else '无'
                                        timestamp = datetime.now().strftime("%H:%M:%S")
                                        st.session_state.auto_activity_log.append({
                                            'type': 'success',
                                            'timestamp': timestamp,
                                            'message': f"✅ 任务 #{task['id']} 执行成功！执行动作: {actions_str}"
                                        })
                                        
                                        # 优化：减少刷新频率，使用更长的延迟
                                        # 使用后台服务时，不进行频繁刷新，避免WebSocket错误
                                        if not use_backend_service:
                                            # 清除缓存，确保下次获取最新数据
                                            get_cached_pending_tasks.clear()
                                            # 增加延迟到5秒，减少刷新频率（从3秒增加到5秒）
                                            # 注意：不立即刷新，让用户继续操作，通过手动刷新或自然刷新获取更新
                                            st.session_state['needs_refresh'] = True
                                            st.session_state['last_refresh_time'] = time.time()
                                    elif exec_result.get('error'):
                                        error_msg = exec_result.get('error', '')
                                        
                                        # 添加详细错误日志
                                        timestamp = datetime.now().strftime("%H:%M:%S")
                                        if '不满足执行条件' in error_msg:
                                            # 详细说明为什么不满足条件
                                            reason = []
                                            if not (start_time <= current_time_only <= end_time):
                                                reason.append(f"当前时间 {current_time_only.strftime('%H:%M')} 不在执行时间段 {start_str}-{end_str} 内")
                                            
                                            # 检查次数限制
                                            exec_limits = scheduler_config.get('execution_limits', {})
                                            limit = exec_limits.get(task['interaction_type'], 0)
                                            if limit > 0:
                                                today_count = st.session_state.auto_scheduler.get_today_execution_count(task['interaction_type'])
                                                if today_count >= limit:
                                                    reason.append(f"{task['interaction_type']}类型任务今日已达上限 ({today_count}/{limit})")
                                            
                                            reason_str = '; '.join(reason) if reason else error_msg
                                            st.session_state.auto_activity_log.append({
                                                'type': 'warning',
                                                'timestamp': timestamp,
                                                'message': f"⚠️ 任务 #{task['id']} 暂不执行: {reason_str}"
                                            })
                                        elif '没有待执行任务' in error_msg:
                                            # 这个错误不应该出现，因为我们刚检查了pending_tasks
                                            pass
                                        else:
                                            st.session_state.auto_activity_log.append({
                                                'type': 'error',
                                                'timestamp': timestamp,
                                                'message': f"❌ 任务 #{task['id']} 执行失败: {error_msg}"
                                            })
                                            logger.warning(f"任务执行失败: {error_msg}")
                                        
                                        # 优化：失败时不立即刷新，标记需要刷新即可
                                        # 使用后台服务时，不进行频繁刷新，避免WebSocket错误
                                        if not use_backend_service:
                                            # 标记需要刷新，但不立即刷新（减少频繁刷新）
                                            st.session_state['needs_refresh'] = True
                                            st.session_state['last_refresh_time'] = time.time()
                                else:
                                    # 没有待执行任务，但也要定期刷新检查
                                    last_check_time = st.session_state.get('last_no_task_check', 0)
                                    if current_time - last_check_time > 30:  # 每30秒检查一次
                                        timestamp = datetime.now().strftime("%H:%M:%S")
                                        st.session_state.auto_activity_log.append({
                                            'type': 'info',
                                            'timestamp': timestamp,
                                            'message': "💡 当前没有待执行任务，等待新任务加入队列..."
                                        })
                                        st.session_state['last_no_task_check'] = current_time
                                        # 优化：不立即刷新，标记需要刷新即可（减少频繁刷新）
                                        if not use_backend_service:
                                            st.session_state['needs_refresh'] = True
                                            st.session_state['last_refresh_time'] = time.time()
                        except Exception as e:
                            logger.error(f"自动执行任务失败: {str(e)}")
                            # 添加异常日志
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            st.session_state.auto_activity_log.append({
                                'type': 'error',
                                'timestamp': timestamp,
                                'message': f"❌ 自动执行异常: {str(e)}"
                            })
                            import traceback
                            logger.error(traceback.format_exc())
                    
                    # ========== 实时运行状态显示 ==========
                    st.markdown("---")
                    st.markdown("### 📊 实时运行状态")
                    
                    # 获取运行状态
                    try:
                        status = st.session_state.db.get_status()
                        is_running = status.get('is_running', False) if status else False
                        is_paused = status.get('is_paused', False) if status else False
                    except:
                        is_running = False
                        is_paused = False
                        status = {}
                    
                    # 优化：实时状态指标（使用缓存减少查询）
                    @st.cache_data(ttl=5)  # 缓存5秒
                    def get_today_executed_count(_interaction_manager):
                        """获取今日已执行任务数（带缓存）"""
                        try:
                            today = datetime.now().date()
                            history = _interaction_manager.get_interaction_history(limit=1000)
                            return len([h for h in history if h.get('created_at') and 
                                       datetime.fromisoformat(str(h['created_at'])).date() == today]) if history else 0
                        except:
                            return 0
                    
                    col_status1, col_status2, col_status3, col_status4, col_status5 = st.columns(5)
                    
                    with col_status1:
                        # 运行状态
                        if is_running and not is_paused:
                            status_text = "🟢 运行中"
                            status_color = "green"
                        elif is_paused:
                            status_text = "⏸️ 已暂停"
                            status_color = "orange"
                        else:
                            status_text = "⚪ 已停止"
                            status_color = "gray"
                        st.metric("运行状态", status_text)
                    
                    with col_status2:
                        # 待执行任务数（使用缓存）
                        try:
                            pending_tasks = get_cached_pending_tasks(st.session_state.db, limit=1000)
                            pending_count = len(pending_tasks) if pending_tasks else 0
                            st.metric("待执行任务", pending_count)
                        except:
                            st.metric("待执行任务", 0)
                    
                    with col_status3:
                        # 今日已执行任务数（使用缓存）
                        try:
                            today_executed = get_today_executed_count(st.session_state.interaction_manager)
                            st.metric("今日已执行", today_executed)
                        except:
                            st.metric("今日已执行", 0)
                    
                    with col_status4:
                        # 累计扫描数
                        try:
                            total_scanned = status.get('total_scanned', 0) if status else 0
                            st.metric("累计扫描", total_scanned)
                        except:
                            st.metric("累计扫描", 0)
                    
                    with col_status5:
                        # 累计执行数
                        try:
                            total_executed = status.get('total_executed', 0) if status else 0
                            st.metric("累计执行", total_executed)
                        except:
                            st.metric("累计执行", 0)
                    
                    # 优化：实时活动日志显示区域（使用st.empty()进行局部更新）
                    if is_running:
                        st.markdown("#### 📋 实时活动日志")
                        # 使用st.empty()容器，支持局部更新而不刷新整个页面
                        activity_log_container = st.empty()
                        
                        # 初始化活动日志
                        if 'auto_activity_log' not in st.session_state:
                            st.session_state.auto_activity_log = []
                        
                        # 优化：如果后台服务运行中，从数据库读取最新日志（使用缓存，增加更新间隔）
                        if use_backend_service:
                            # 从数据库读取后台服务的日志（使用缓存，减少数据库查询）
                            try:
                                # 优化：增加更新间隔从2秒到5秒，减少频繁更新
                                last_log_update = st.session_state.get('last_log_update_time', 0)
                                current_time = time.time()
                                
                                if current_time - last_log_update > 5:  # 每5秒更新一次（从2秒增加到5秒）
                                    backend_logs = get_cached_activity_logs(st.session_state.db)
                                    # 合并到session_state的日志中（去重）
                                    existing_timestamps = {log.get('timestamp', '') + log.get('message', '') for log in st.session_state.auto_activity_log}
                                    new_logs_count = 0
                                    for log in backend_logs:
                                        log_key = log.get('timestamp', '') + log.get('message', '')
                                        if log_key not in existing_timestamps:
                                            st.session_state.auto_activity_log.append(log)
                                            existing_timestamps.add(log_key)
                                            new_logs_count += 1
                                    # 只在有新日志时更新，避免不必要的状态变化
                                    if new_logs_count > 0:
                                        st.session_state['last_log_update_time'] = current_time
                            except Exception as e:
                                logger.error(f"读取后台服务日志失败: {str(e)}")
                        
                        # 优化：显示最近的活动日志（最多20条），使用容器局部更新
                        recent_logs = st.session_state.auto_activity_log[-20:]
                        if recent_logs:
                            # 构建日志内容（使用容器更新，不刷新整个页面）
                            log_content = []
                            for log in reversed(recent_logs):  # 最新的在上面
                                log_type = log.get('type', 'info')
                                timestamp = log.get('timestamp', '')
                                message = log.get('message', '')
                                
                                if log_type == 'success':
                                    log_content.append(f"✅ [{timestamp}] {message}")
                                elif log_type == 'error':
                                    log_content.append(f"❌ [{timestamp}] {message}")
                                elif log_type == 'warning':
                                    log_content.append(f"⚠️ [{timestamp}] {message}")
                                else:
                                    log_content.append(f"ℹ️ [{timestamp}] {message}")
                            
                            # 使用容器显示日志，支持局部更新
                            with activity_log_container.container():
                                for log_line in log_content:
                                    if log_line.startswith("✅"):
                                        st.success(log_line)
                                    elif log_line.startswith("❌"):
                                        st.error(log_line)
                                    elif log_line.startswith("⚠️"):
                                        st.warning(log_line)
                                    else:
                                        st.info(log_line)
                        else:
                            with activity_log_container.container():
                                if use_backend_service:
                                    st.info("💡 后台服务运行中，等待任务执行...")
                                else:
                                    st.info("💡 等待活动...")
                        
                        # 优化：自动刷新按钮（清除缓存后刷新）
                        col_refresh1, col_refresh2 = st.columns([1, 4])
                        with col_refresh1:
                            if st.button("🔄 刷新状态", key="refresh_auto_status"):
                                # 清除相关缓存，确保获取最新数据
                                get_cached_pending_tasks.clear()
                                get_task_statistics_cached.clear()
                                get_today_executed_count.clear()
                                st.rerun()
                        with col_refresh2:
                            if use_backend_service:
                                st.caption("💡 后台服务运行中，任务自动执行。点击按钮手动刷新状态")
                            else:
                                st.caption("💡 系统会智能刷新，或点击按钮手动刷新")
                    else:
                        st.info("💡 系统已停止，点击'开始运行'按钮启动自动化运营")
                    
                    # 自动化任务管理
                    st.markdown("---")
                    st.markdown("#### 📋 自动化任务列表")
                    
                    # 优化：获取任务统计信息（使用缓存减少数据库查询）
                    @st.cache_data(ttl=10)  # 缓存10秒，减少频繁查询
                    def get_task_statistics_cached(_db):
                        """获取任务统计信息（带缓存）"""
                        session = _db.SessionLocal()
                        try:
                            # 统计各种状态的任务数量
                            total_tasks = session.query(_db.AutoInteractionQueue).count()
                            pending_count = session.query(_db.AutoInteractionQueue).filter_by(status='pending').count()
                            failed_count = session.query(_db.AutoInteractionQueue).filter_by(status='failed').count()
                            executing_count = session.query(_db.AutoInteractionQueue).filter_by(status='executing').count()
                            completed_count = session.query(_db.AutoInteractionQueue).filter_by(status='completed').count()
                            return {
                                'total': total_tasks,
                                'pending': pending_count,
                                'failed': failed_count,
                                'executing': executing_count,
                                'completed': completed_count
                            }
                        finally:
                            session.close()
                    
                    try:
                        stats = get_task_statistics_cached(st.session_state.db)
                        total_tasks = stats['total']
                        pending_count = stats['pending']
                        failed_count = stats['failed']
                        executing_count = stats['executing']
                        completed_count = stats['completed']
                        
                        # 显示任务统计
                        col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
                        with col_stat1:
                            st.metric("总任务数", total_tasks)
                        with col_stat2:
                            st.metric("待执行", pending_count, delta=None)
                        with col_stat3:
                            st.metric("失败", failed_count, delta=None)
                        with col_stat4:
                            st.metric("执行中", executing_count, delta=None)
                        with col_stat5:
                            st.metric("已完成", completed_count, delta=None)
                        
                        # 如果有失败或卡住的任务，显示重置按钮
                        if failed_count > 0 or executing_count > 0:
                            st.warning(f"⚠️ 检测到 {failed_count} 个失败任务和 {executing_count} 个卡住的任务")
                            if st.button("🔄 重置所有失败/卡住的任务为待执行", key="reset_all_failed_tasks"):
                                try:
                                    reset_count = st.session_state.db.reset_failed_tasks(reset_executing=True)
                                    if reset_count > 0:
                                        st.success(f"✅ 已重置 {reset_count} 个任务为待执行状态")
                                        st.rerun()
                                    else:
                                        st.info("ℹ️ 没有需要重置的任务")
                                except Exception as e:
                                    st.error(f"重置失败: {str(e)}")
                                    import traceback
                                    st.caption(traceback.format_exc())
                        
                        st.markdown("---")
                    except Exception as e:
                        st.warning(f"获取任务统计失败: {str(e)}")
                    
                    # 获取待执行的自动化任务
                    try:
                        pending_tasks = get_cached_pending_tasks(st.session_state.db, limit=50)
                        
                        if pending_tasks:
                            st.info(f"📊 当前有 {len(pending_tasks)} 个待执行的自动化任务")
                            
                            # 显示任务列表
                            for task in pending_tasks[:10]:  # 只显示前10个
                                with st.expander(f"任务 #{task['id']} - {task['interaction_type']} - r/{task['subreddit']}", expanded=False):
                                    col_task1, col_task2 = st.columns(2)
                                    with col_task1:
                                        st.write(f"**帖子ID**: {task['post_id']}")
                                        st.write(f"**子版块**: r/{task['subreddit']}")
                                        st.write(f"**互动类型**: {task['interaction_type']}")
                                        st.write(f"**帖子评分**: {task['post_score']:.2f}")
                                    with col_task2:
                                        st.write(f"**状态**: {task['status']}")
                                        st.write(f"**创建时间**: {task['created_at']}")
                                        if task.get('executed_at'):
                                            st.write(f"**执行时间**: {task['executed_at']}")
                                        if task.get('error_message'):
                                            st.error(f"**错误**: {task['error_message']}")
                                    
                                    if task.get('ai_comment'):
                                        st.markdown("**AI生成的评论**:")
                                        st.write(task['ai_comment'])
                                    
                                    # 任务操作按钮
                                    col_act1, col_act2, col_act3 = st.columns(3)
                                    with col_act1:
                                        if st.button("▶️ 立即执行", key=f"execute_task_{task['id']}"):
                                            modules_available = AUTO_MODULES_AVAILABLE and not st.session_state.get('auto_modules_failed', False)
                                            if modules_available and 'task_executor' in st.session_state:
                                                with st.spinner("正在执行任务..."):
                                                    try:
                                                        result = st.session_state.task_executor.execute_task(task['id'])
                                                        if result.get('success'):
                                                            st.success(f"✅ 任务执行成功！执行动作: {', '.join(result.get('actions', []))}")
                                                            st.rerun()
                                                        else:
                                                            st.error(f"❌ 执行失败: {result.get('error', '未知错误')}")
                                                    except Exception as e:
                                                        st.error(f"执行失败: {str(e)}")
                                            else:
                                                st.warning("⚠️ 任务执行器未初始化")
                                    with col_act2:
                                        if st.button("🗑️ 删除任务", key=f"delete_task_{task['id']}"):
                                            try:
                                                session = st.session_state.db.SessionLocal()
                                                try:
                                                    task_obj = session.query(st.session_state.db.AutoInteractionQueue).filter_by(id=task['id']).first()
                                                    if task_obj:
                                                        session.delete(task_obj)
                                                        session.commit()
                                                        st.success("✅ 任务已删除")
                                                        st.rerun()
                                                finally:
                                                    session.close()
                                            except Exception as e:
                                                st.error(f"删除失败: {str(e)}")
                                    with col_act3:
                                        if task.get('requires_review'):
                                            review_status = task.get('review_status') or 'pending'
                                            st.write(f"**审核状态**: {review_status}")
                                            st.caption("当前自动运营为全自动模式：评论/点赞不会等待审核。审核按钮仅用于兼容旧数据。")
                                            if review_status == 'pending':
                                                if st.button("✅ 批准", key=f"approve_task_{task['id']}"):
                                                    try:
                                                        session = st.session_state.db.SessionLocal()
                                                        try:
                                                            task_obj = session.query(st.session_state.db.AutoInteractionQueue).filter_by(id=task['id']).first()
                                                            if task_obj:
                                                                task_obj.review_status = 'approved'
                                                                session.commit()
                                                                st.success("✅ 任务已批准")
                                                                st.rerun()
                                                        finally:
                                                            session.close()
                                                    except Exception as e:
                                                        st.error(f"批准失败: {str(e)}")
                        else:
                            st.info("💡 当前没有待执行的自动化任务")
                    except Exception as e:
                        st.warning(f"获取自动化任务失败: {str(e)}")
                        import traceback
                        with st.expander("查看错误详情"):
                            st.code(traceback.format_exc())
                
                # ========== 任务执行简报 ==========
                with tab_tasks:
                    st.subheader("📋 任务执行简报")
                    st.markdown("显示已完成任务的执行记录")
                    
                    # 获取已完成的任务
                    try:
                        completed_tasks = st.session_state.db.get_interaction_history(limit=50, status='completed')
                        
                        if completed_tasks:
                            st.success(f"✅ 共找到 {len(completed_tasks)} 条已完成任务记录")
                            
                            # 按执行时间倒序显示
                            for task in completed_tasks[:30]:  # 显示最近30条
                                # 判断任务类型
                                interaction_type = task.get('interaction_type', '')
                                post_id = task.get('post_id', '')
                                subreddit = task.get('subreddit', '')
                                executed_at = task.get('executed_at')
                                ai_comment = task.get('ai_comment', '')
                                
                                # 构建 Reddit 帖子链接
                                # 处理 post_id 可能包含的 t3_ 前缀
                                clean_post_id = post_id.replace('t3_', '') if post_id else ''
                                reddit_url = f"https://www.reddit.com/r/{subreddit}/comments/{clean_post_id}/" if clean_post_id and subreddit else None
                                
                                # 格式化执行时间
                                if executed_at:
                                    if isinstance(executed_at, str):
                                        exec_time_str = executed_at
                                    else:
                                        exec_time_str = executed_at.strftime("%Y-%m-%d %H:%M:%S")
                                else:
                                    exec_time_str = "未知时间"
                                
                                # 根据互动类型显示不同的简报
                                if interaction_type == 'deep':
                                    # 深度互动：点赞 + 评论 + 关注
                                    st.markdown("---")
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.markdown(f"**✅ 深度互动** | r/{subreddit} | {exec_time_str}")
                                        st.markdown(f"📌 帖子ID: `{post_id}`")
                                        if reddit_url:
                                            st.markdown(f"🔗 [在 Reddit 上查看此帖子]({reddit_url})")
                                        if ai_comment:
                                            st.markdown("**执行动作：**")
                                            st.markdown("1. 👍 已点赞该帖子")
                                            st.markdown("2. 💬 已发表评论")
                                            st.markdown("3. ⭐ 已关注该帖子")
                                            st.markdown("**评论内容：**")
                                            st.info(ai_comment)
                                        else:
                                            st.markdown("**执行动作：**")
                                            st.markdown("1. 👍 已点赞该帖子")
                                            st.markdown("2. ⭐ 已关注该帖子")
                                    with col2:
                                        st.caption(f"任务ID: #{task.get('id', 'N/A')}")
                                        st.caption(f"评分: {task.get('post_score', 0):.2f}")
                                        
                                elif interaction_type == 'standard':
                                    # 标准互动：点赞 + 评论
                                    st.markdown("---")
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.markdown(f"**✅ 标准互动** | r/{subreddit} | {exec_time_str}")
                                        st.markdown(f"📌 帖子ID: `{post_id}`")
                                        if reddit_url:
                                            st.markdown(f"🔗 [在 Reddit 上查看此帖子]({reddit_url})")
                                        if ai_comment:
                                            st.markdown("**执行动作：**")
                                            st.markdown("1. 👍 已点赞该帖子")
                                            st.markdown("2. 💬 已发表评论")
                                            st.markdown("**评论内容：**")
                                            st.info(ai_comment)
                                        else:
                                            st.markdown("**执行动作：**")
                                            st.markdown("1. 👍 已点赞该帖子")
                                    with col2:
                                        st.caption(f"任务ID: #{task.get('id', 'N/A')}")
                                        st.caption(f"评分: {task.get('post_score', 0):.2f}")
                                        
                                elif interaction_type == 'light':
                                    # 轻度互动：仅点赞
                                    st.markdown("---")
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.markdown(f"**✅ 轻度互动** | r/{subreddit} | {exec_time_str}")
                                        st.markdown(f"📌 帖子ID: `{post_id}`")
                                        if reddit_url:
                                            st.markdown(f"🔗 [在 Reddit 上查看此帖子]({reddit_url})")
                                        st.markdown("**执行动作：**")
                                        st.markdown("1. 👍 已点赞该帖子")
                                    with col2:
                                        st.caption(f"任务ID: #{task.get('id', 'N/A')}")
                                        st.caption(f"评分: {task.get('post_score', 0):.2f}")
                                else:
                                    # 其他类型
                                    st.markdown("---")
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.markdown(f"**✅ {interaction_type}互动** | r/{subreddit} | {exec_time_str}")
                                        st.markdown(f"📌 帖子ID: `{post_id}`")
                                        if reddit_url:
                                            st.markdown(f"🔗 [在 Reddit 上查看此帖子]({reddit_url})")
                                        if ai_comment:
                                            st.markdown("**评论内容：**")
                                            st.info(ai_comment)
                                    with col2:
                                        st.caption(f"任务ID: #{task.get('id', 'N/A')}")
                                        st.caption(f"评分: {task.get('post_score', 0):.2f}")
                        else:
                            st.info("💡 暂无已完成的任务记录")
                            st.caption("任务执行完成后，会在这里显示执行简报")
                            
                    except Exception as e:
                        st.warning(f"获取任务记录失败: {str(e)}")
                        import traceback
                        with st.expander("查看错误详情"):
                            st.code(traceback.format_exc())
                
            except ImportError as e:
                st.error(f"❌ 导入模块失败: {str(e)}")
        
        else:
            st.warning("请先配置API密钥并初始化系统")
    
    with tab5:
        try:
            render_smart_filter_tab()
        except Exception as e:
            st.error(f"❌ 加载智能筛选页面失败: {str(e)}")
            import traceback
            with st.expander("查看错误详情"):
                st.code(traceback.format_exc())
    
    # ========== 智能发帖 ==========
    with tab6:
        try:
            if SMART_POSTING_AVAILABLE:
                render_smart_posting_tab()
            else:
                st.error(f"❌ 智能发帖模块不可用: {SMART_POSTING_ERROR if 'SMART_POSTING_ERROR' in globals() else '未知错误'}")
                st.info("💡 请检查模块文件是否存在")
        except Exception as e:
            st.error(f"❌ 加载智能发帖页面失败: {str(e)}")
            import traceback
            with st.expander("查看错误详情"):
                st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
