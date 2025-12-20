"""
智能发帖管理页面 - 统一入口
"""
import streamlit as st
import logging
from modules.posting.post_library_module import render_post_library
from modules.posting.ai_generator_module import render_ai_generator

logger = logging.getLogger(__name__)

def render_smart_posting_tab():
    """渲染智能发帖管理页面"""
    try:
        st.header("📝 智能发帖管理平台")
        st.markdown("💡 一站式管理帖子创建和AI生成")
        
        # 检查初始化状态
        if not st.session_state.get('initialized'):
            st.warning("⚠️ 请先配置API密钥并初始化系统")
            st.info("💡 请在左侧边栏配置Reddit API密钥和AI模型API密钥，然后点击'初始化系统'按钮")
            return
        
        # 标签页导航
        tab1, tab2 = st.tabs([
            "📚 帖子库",
            "🤖 AI生成"
        ])
        
        # 模块1: 帖子库管理
        with tab1:
            render_post_library()
        
        # 模块2: AI内容生成
        with tab2:
            render_ai_generator()
    
    except Exception as e:
        st.error(f"❌ 智能发帖页面加载失败: {str(e)}")
        logger.error(f"智能发帖页面错误: {str(e)}", exc_info=True)


