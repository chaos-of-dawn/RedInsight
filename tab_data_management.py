"""
Tab3: 本地数据管理模块
"""
import streamlit as st

def render_data_management_tab():
    """渲染本地数据管理页面"""
    try:
        if not st.session_state.initialized:
            st.warning("⚠️ 请先配置API密钥并初始化系统")
            st.info("💡 请在左侧边栏配置Reddit API密钥，然后点击'初始化系统'按钮")
            return
        
        try:
            from merged_analysis_page import create_merged_analysis_page
            create_merged_analysis_page()
        except ImportError as e:
            st.error(f"❌ 导入本地数据管理模块失败: {str(e)}")
            st.info("💡 请确保merged_analysis_page.py文件存在")
        except Exception as e:
            st.error(f"❌ 加载本地数据管理页面失败: {str(e)}")
            import traceback
            with st.expander("查看错误详情"):
                st.code(traceback.format_exc())
    except Exception as e:
        st.error(f"❌ 本地数据管理页面加载失败: {str(e)}")
        import traceback
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())

