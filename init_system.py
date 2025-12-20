"""
系统初始化模块
独立于主应用，避免导入时的 set_page_config 冲突
"""
import streamlit as st
import os
from importlib import reload
import app_config as config

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
            
            # 设置环境变量
            for key, value in st.session_state.api_keys.items():
                if value:
                    os.environ[key.upper()] = value
            
            # 重新加载配置
            reload(config)
            
            # 导入必要的模块
            from reddit_scraper import RedditScraper
            from database import DatabaseManager
            from llm_analyzer import LLMAnalyzer
            
            # 检查是否已有认证的scraper
            if not st.session_state.scraper or not st.session_state.scraper.is_authenticated():
                # 检查Reddit认证状态
                if not st.session_state.api_keys.get('reddit_access_token'):
                    st.warning("Reddit API未认证。请点击'开始Reddit认证'按钮完成认证。")
                    return False
                
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
                    from config_utils import save_config
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
            
            # 初始化深度分析器（可选）
            try:
                from advanced_analyzer import AdvancedAnalyzer
                ADVANCED_ANALYZER_AVAILABLE = True
            except ImportError:
                ADVANCED_ANALYZER_AVAILABLE = False
                AdvancedAnalyzer = None
            
            if ADVANCED_ANALYZER_AVAILABLE and AdvancedAnalyzer:
                try:
                    st.session_state.advanced_analyzer = AdvancedAnalyzer(st.session_state.db, st.session_state.analyzer, provider)
                    st.success("✅ 深度分析器初始化成功")
                except Exception as e:
                    st.warning(f"⚠️ 深度分析器初始化失败: {str(e)}")
                    st.session_state.advanced_analyzer = None
            else:
                st.session_state.advanced_analyzer = None
                st.info("ℹ️ 深度分析器模块未找到，相关功能将不可用")
            
            st.session_state.initialized = True
            
            return True
        except Exception as e:
            st.error(f"初始化失败: {str(e)}")
            import traceback
            st.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    return True

