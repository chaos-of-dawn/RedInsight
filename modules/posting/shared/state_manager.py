"""
状态管理器 - 管理模块间的共享状态
"""
import streamlit as st
from typing import List, Dict, Any, Optional

class PostingStateManager:
    """发帖功能状态管理器"""
    
    @staticmethod
    def _safe_get_session_state(key: str, default: Any = None) -> Any:
        """安全地获取 session_state 值"""
        try:
            if hasattr(st, 'session_state') and st.session_state is not None:
                return st.session_state.get(key, default)
        except (AttributeError, RuntimeError, KeyError):
            pass
        return default
    
    @staticmethod
    def _safe_set_session_state(key: str, value: Any):
        """安全地设置 session_state 值"""
        try:
            if hasattr(st, 'session_state') and st.session_state is not None:
                st.session_state[key] = value
        except (AttributeError, RuntimeError, KeyError):
            pass
    
    @staticmethod
    def get_selected_posts() -> List[Dict[str, Any]]:
        """获取当前选中的帖子（跨模块）"""
        return PostingStateManager._safe_get_session_state('selected_posts', [])
    
    @staticmethod
    def set_selected_posts(posts: List[Dict[str, Any]]):
        """设置选中的帖子"""
        PostingStateManager._safe_set_session_state('selected_posts', posts)
    
    @staticmethod
    def get_ai_generated_posts() -> List[Dict[str, Any]]:
        """获取AI生成的帖子（临时存储）"""
        return PostingStateManager._safe_get_session_state('ai_generated_posts', [])
    
    @staticmethod
    def set_ai_generated_posts(posts: List[Dict[str, Any]]):
        """设置AI生成的帖子"""
        PostingStateManager._safe_set_session_state('ai_generated_posts', posts)
    
    @staticmethod
    def get_posts_for_schedule() -> List[Dict[str, Any]]:
        """获取准备保存到计划的帖子"""
        return PostingStateManager._safe_get_session_state('posts_for_schedule', [])
    
    @staticmethod
    def set_posts_for_schedule(posts: List[Dict[str, Any]]):
        """设置准备保存到计划的帖子"""
        PostingStateManager._safe_set_session_state('posts_for_schedule', posts)
    
    @staticmethod
    def clear_posts_for_schedule():
        """清除准备保存到计划的帖子"""
        try:
            if hasattr(st, 'session_state') and st.session_state is not None:
                if 'posts_for_schedule' in st.session_state:
                    del st.session_state.posts_for_schedule
        except (AttributeError, RuntimeError, KeyError):
            pass
    
    @staticmethod
    def get_active_tab() -> str:
        """获取当前活动标签页"""
        return PostingStateManager._safe_get_session_state('posting_active_tab', '帖子库')
    
    @staticmethod
    def set_active_tab(tab_name: str):
        """设置当前活动标签页"""
        PostingStateManager._safe_set_session_state('posting_active_tab', tab_name)


