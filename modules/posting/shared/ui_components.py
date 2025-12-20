"""
共享UI组件
"""
import streamlit as st
from typing import Dict, Any, Optional, List
import json

def render_post_card(post: Dict[str, Any], 
                    show_actions: bool = True,
                    editable: bool = True,
                    key_prefix: str = "post") -> Dict[str, Any]:
    """
    渲染帖子卡片组件
    
    Args:
        post: 帖子数据字典
        show_actions: 是否显示操作按钮
        editable: 是否可编辑
        key_prefix: 唯一键前缀
    
    Returns:
        更新后的帖子数据字典
    """
    post_id = post.get('id', post.get('temp_id', 'unknown'))
    card_key = f"{key_prefix}_{post_id}"
    
    with st.container():
        st.markdown("---")
        
        # 标题编辑
        if editable:
            title_key = f"{card_key}_title"
            title = st.text_input(
                "标题",
                value=post.get('title', ''),
                key=title_key,
                label_visibility="collapsed"
            )
            post['title'] = title
        else:
            st.markdown(f"### {post.get('title', '无标题')}")
        
        # 内容编辑
        if editable:
            content_key = f"{card_key}_content"
            content = st.text_area(
                "内容",
                value=post.get('content', ''),
                key=content_key,
                height=150,
                label_visibility="collapsed"
            )
            post['content'] = content
        else:
            st.markdown(post.get('content', ''))
        
        # 操作按钮
        if show_actions:
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("✏️ 编辑", key=f"{card_key}_edit"):
                    post['_edit_mode'] = not post.get('_edit_mode', False)
            
            with col2:
                if st.button("🗑️ 删除", key=f"{card_key}_delete"):
                    post['_deleted'] = True
            
            with col3:
                if st.button("📋 复制", key=f"{card_key}_copy"):
                    post['_copied'] = True
            
            with col4:
                if st.button("🔗 链接", key=f"{card_key}_link"):
                    post['_link_copied'] = True
            
            with col5:
                if st.button("💾 保存到计划", key=f"{card_key}_save"):
                    post['_save_to_schedule'] = True
        
        return post

def render_rule_check_result(subreddit: str, result: Dict[str, Any]):
    """
    渲染规则检查结果组件
    
    Args:
        subreddit: 子版块名称
        result: 检查结果字典
    """
    is_compliant = result.get('is_compliant', False)
    score = result.get('compliance_score', 0)
    suggestions = result.get('suggestions', [])
    
    if is_compliant:
        st.success(f"✅ r/{subreddit}: 符合规则 (评分: {score}分)")
    else:
        st.warning(f"⚠️ r/{subreddit}: 建议修改 (评分: {score}分)")
    
    if suggestions:
        with st.expander("查看修改建议"):
            for i, suggestion in enumerate(suggestions, 1):
                st.markdown(f"{i}. {suggestion}")

def render_media_preview(media_files: List[Dict[str, Any]]):
    """
    渲染媒体文件预览
    
    Args:
        media_files: 媒体文件列表
    """
    if not media_files:
        return
    
    st.markdown("#### 📎 附件")
    for media in media_files:
        file_type = media.get('file_type', '')
        file_path = media.get('file_path', '')
        
        if file_type == 'image':
            try:
                st.image(file_path, caption=media.get('file_name', ''))
            except:
                st.error(f"无法加载图片: {file_path}")
        else:
            st.markdown(f"📄 {media.get('file_name', '未知文件')}")


