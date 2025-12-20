"""
帖子库管理模块
"""
import streamlit as st
import logging
from typing import List, Dict, Any
from datetime import datetime
from modules.posting.shared.post_manager import PostManager
from modules.posting.shared.ui_components import render_media_preview

logger = logging.getLogger(__name__)

def render_post_library():
    """渲染帖子库管理页面"""
    try:
        if not st.session_state.get('initialized'):
            st.warning("⚠️ 请先初始化系统")
            return
        
        db = st.session_state.db
        post_manager = PostManager(db)
        
        # 子标签页
        create_tab, manage_tab, schedule_tab = st.tabs(["➕ 创建帖子", "📚 帖子库", "📅 发布计划"])
        
        with create_tab:
            render_create_post(post_manager)
        
        with manage_tab:
            render_post_list(post_manager)
        
        with schedule_tab:
            render_schedule_list(db, post_manager)
    
    except Exception as e:
        st.error(f"❌ 帖子库页面加载失败: {str(e)}")
        logger.error(f"帖子库页面错误: {str(e)}", exc_info=True)

def render_create_post(post_manager: PostManager):
    """渲染创建帖子界面"""
    st.subheader("创建新帖子")
    
    # 标题输入
    title = st.text_input("标题", key="create_post_title", placeholder="请输入帖子标题")
    
    # 内容编辑器
    content_type = st.selectbox(
        "内容类型",
        ["text", "markdown"],
        key="create_post_content_type"
    )
    
    content = st.text_area(
        "内容",
        key="create_post_content",
        height=300,
        placeholder="请输入帖子内容"
    )
    
    # 文件上传
    st.markdown("#### 📎 上传文件（可选）")
    uploaded_files = st.file_uploader(
        "选择文件",
        type=['txt', 'md', 'jpg', 'jpeg', 'png', 'gif', 'webp'],
        accept_multiple_files=True,
        key="create_post_files"
    )
    
    media_files = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # 检查文件类型和大小
            file_type = 'image' if uploaded_file.type.startswith('image/') else 'text'
            file_size = len(uploaded_file.getvalue())
            
            # Reddit图片限制：20MB
            if file_type == 'image' and file_size > 20 * 1024 * 1024:
                st.warning(f"⚠️ {uploaded_file.name} 文件过大（超过20MB），请压缩后上传")
                continue
            
            # 保存文件
            import os
            save_dir = "uploaded_files"
            if file_type == 'image':
                save_dir = os.path.join(save_dir, "images")
            else:
                save_dir = os.path.join(save_dir, "text")
            
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, uploaded_file.name)
            
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            media_files.append({
                'file_name': uploaded_file.name,
                'file_path': file_path,
                'file_type': file_type,
                'file_size': file_size,
                'reddit_compatible': True
            })
            
            if file_type == 'image':
                st.image(file_path, caption=uploaded_file.name, width=300)
    
    # 保存按钮
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 保存为草稿", type="primary", key="save_draft"):
            if title and content:
                post_id = post_manager.create_post(
                    title=title,
                    content=content,
                    content_type=content_type,
                    media_files=media_files if media_files else None,
                    source='manual'
                )
                if post_id:
                    st.success(f"✅ 帖子已保存为草稿（ID: {post_id}）")
                    st.rerun()
                else:
                    st.error("❌ 保存失败")
            else:
                st.warning("⚠️ 请填写标题和内容")
    
    with col2:
        if st.button("✅ 保存为就绪", key="save_ready"):
            if title and content:
                post_id = post_manager.create_post(
                    title=title,
                    content=content,
                    content_type=content_type,
                    media_files=media_files if media_files else None,
                    source='manual',
                    status='ready'
                )
                if post_id:
                    st.success(f"✅ 帖子已保存为就绪状态（ID: {post_id}）")
                    st.rerun()
                else:
                    st.error("❌ 保存失败")
            else:
                st.warning("⚠️ 请填写标题和内容")

def render_post_list(post_manager: PostManager):
    """渲染帖子列表界面"""
    st.subheader("帖子库")
    
    # 去重功能区域
    with st.expander("🔍 去重功能", expanded=False):
        col_scan, col_clear = st.columns([1, 1])
        with col_scan:
            if st.button("🔎 扫描重复帖子", key="scan_duplicates"):
                with st.spinner("正在扫描重复帖子..."):
                    duplicate_groups = post_manager.find_duplicate_posts()
                    # 将结果保存到 session_state，以便删除后仍可使用
                    st.session_state['duplicate_groups'] = duplicate_groups
                    st.session_state['duplicate_groups_scanned'] = True
        
        with col_clear:
            if st.button("🔄 清除扫描结果", key="clear_duplicates"):
                if 'duplicate_groups' in st.session_state:
                    del st.session_state['duplicate_groups']
                st.session_state['duplicate_groups_scanned'] = False
                st.rerun()
        
        # 显示扫描结果
        if st.session_state.get('duplicate_groups_scanned', False):
            duplicate_groups = st.session_state.get('duplicate_groups', {})
            
            if duplicate_groups:
                total_duplicates = sum(len(group) for group in duplicate_groups.values())
                st.warning(f"⚠️ 发现 {len(duplicate_groups)} 组重复帖子，共 {total_duplicates} 条")
                
                # 显示重复组
                for group_idx, (group_key, duplicate_posts) in enumerate(duplicate_groups.items(), 1):
                    if len(duplicate_posts) > 1:
                        st.markdown("---")
                        st.markdown(f"**重复组 #{group_idx}** ({len(duplicate_posts)} 条)")
                        
                        # 显示重复的帖子
                        selected_ids_for_group = []
                        for dup_post in duplicate_posts:
                            col_info, col_action = st.columns([4, 1])
                            with col_info:
                                st.markdown(f"**ID: {dup_post['id']}** | {dup_post['title'][:50]}...")
                                st.caption(f"状态: {dup_post['status']} | 来源: {dup_post['source']} | 创建时间: {dup_post['created_at']}")
                            
                            with col_action:
                                # 标记要删除的复选框
                                delete_key = f"delete_dup_{group_key}_{dup_post['id']}"
                                if st.checkbox("删除", key=delete_key, value=False):
                                    selected_ids_for_group.append(dup_post['id'])
                        
                        # 统一的删除按钮
                        if selected_ids_for_group:
                            if st.button(f"🗑️ 删除选中 ({len(selected_ids_for_group)})", key=f"delete_selected_{group_key}", type="primary"):
                                deleted_count = 0
                                failed_count = 0
                                for post_id in selected_ids_for_group:
                                    if post_manager.delete_post(post_id):
                                        deleted_count += 1
                                    else:
                                        failed_count += 1
                                
                                if deleted_count > 0:
                                    if failed_count > 0:
                                        st.warning(f"⚠️ 成功删除 {deleted_count} 条，失败 {failed_count} 条")
                                    else:
                                        st.success(f"✅ 已删除 {deleted_count} 条选中的帖子")
                                    # 清除扫描结果，需要重新扫描
                                    if 'duplicate_groups' in st.session_state:
                                        del st.session_state['duplicate_groups']
                                    st.session_state['duplicate_groups_scanned'] = False
                                    st.rerun()
                                else:
                                    st.error(f"❌ 删除失败，请检查日志")
                        else:
                            st.info("💡 请勾选要删除的帖子，然后点击删除按钮")
            else:
                st.success("✅ 未发现重复帖子")
    
    # 筛选器
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "状态筛选",
            ["全部", "draft", "ready", "scheduled", "published", "archived"],
            key="post_list_status_filter"
        )
    with col2:
        source_filter = st.selectbox(
            "来源筛选",
            ["全部", "manual", "ai_generated"],
            key="post_list_source_filter"
        )
    with col3:
        limit = st.number_input("显示数量", min_value=10, max_value=500, value=50, key="post_list_limit")
    
    # 获取帖子列表
    status = None if status_filter == "全部" else status_filter
    source = None if source_filter == "全部" else source_filter
    
    posts = post_manager.list_posts(status=status, source=source, limit=limit)
    
    if not posts:
        st.info("📭 没有找到帖子")
        return
    
    st.markdown(f"**共找到 {len(posts)} 条帖子**")
    
    # 显示帖子列表
    for post in posts:
        with st.expander(f"📝 {post['title'][:50]}... ({post['status']})", expanded=st.session_state.get(f"editing_post_{post['id']}", False)):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**标题:** {post['title']}")
                
                # 显示完整内容
                content = post.get('content', '')
                if not content:
                    content = "(无内容)"
                
                st.markdown("**内容:**")
                
                # 使用可滚动的文本区域显示完整内容
                content_lines = max(1, content.count('\n') + 1)
                # 计算高度：每行约25px，最小200px，最大800px
                estimated_height = min(800, max(200, content_lines * 25 + 50))
                
                # 使用 text_area 显示完整内容（只读模式，可滚动）
                st.text_area(
                    "帖子完整内容",
                    value=content,
                    height=estimated_height,
                    key=f"view_content_{post['id']}",
                    disabled=True,
                    label_visibility="collapsed",
                    help=f"内容长度: {len(content)} 字符，{content_lines} 行。可在此区域滚动查看完整内容。"
                )
                
                # 如果内容很长，提供一个提示和额外的文本显示（不使用expander，避免嵌套）
                if len(content) > 2000:
                    st.info(f"💡 内容较长（{len(content)} 字符，{content_lines} 行），请在上方文本框中滚动查看完整内容")
                    # 使用 st.text 作为备用显示（直接显示，不嵌套）
                    st.markdown("**完整文本（备用视图）:**")
                    st.text(content)
                
                st.markdown(f"**状态:** {post['status']} | **来源:** {post['source']}")
                if post.get('keywords'):
                    st.markdown(f"**关键词:** {post['keywords']}")
                st.markdown(f"**创建时间:** {post['created_at']}")
            
            with col2:
                if st.button("✏️ 编辑", key=f"edit_{post['id']}"):
                    st.session_state[f"editing_post_{post['id']}"] = True
                    st.rerun()
                
                if st.button("🗑️ 删除", key=f"delete_{post['id']}"):
                    if post_manager.delete_post(post['id']):
                        st.success("✅ 已删除")
                        st.rerun()
                
                if st.button("💾 保存到计划", key=f"schedule_{post['id']}"):
                    # 保存到计划
                    from modules.posting.shared.state_manager import PostingStateManager
                    PostingStateManager.set_posts_for_schedule([post])
                    st.session_state.posting_active_tab = "发布计划"
                    st.rerun()

                if st.button("⏰ 定时发布", key=f"timed_publish_{post['id']}"):
                    st.session_state[f"show_timed_publish_{post['id']}"] = True
                    st.rerun()

            # 定时发布配置（在右侧按钮下方展开，避免额外弹窗依赖）
            if st.session_state.get(f"show_timed_publish_{post['id']}", False):
                st.markdown("---")
                st.markdown("#### ⏰ 定时发布（自动排程：2小时/篇；任意8小时最多4篇）")

                # 默认取增强分析里的最佳子版块前3个（如果有）
                analysis_summary = st.session_state.get('last_enhanced_analysis', {}) or {}
                best_subreddits = analysis_summary.get('best_subreddits', []) or []
                default_subs = [s.get('subreddit') for s in best_subreddits[:3] if isinstance(s, dict) and s.get('subreddit')]
                subs_text = st.text_input(
                    "目标子版块（最多3个，用逗号分隔）",
                    value=", ".join(default_subs) if default_subs else "",
                    help="例如: subreddit1, subreddit2, subreddit3（不需要写r/，可选择1-3个子版块）",
                    key=f"lib_publish_subs_{post['id']}"
                )

                col_dt1, col_dt2 = st.columns(2)
                from datetime import datetime, timedelta
                with col_dt1:
                    start_date = st.date_input("开始日期（UTC）", value=datetime.utcnow().date(), key=f"lib_publish_date_{post['id']}")
                with col_dt2:
                    start_time = st.time_input("开始时间（UTC）", value=datetime.utcnow().time().replace(second=0, microsecond=0), key=f"lib_publish_time_{post['id']}")

                auto_start_service = st.checkbox(
                    "创建计划后启动自动发帖后台服务（推荐）",
                    value=True,
                    key=f"lib_publish_autostart_{post['id']}"
                )

                col_act1, col_act2 = st.columns(2)
                with col_act1:
                    if st.button("✅ 创建计划", type="primary", key=f"lib_publish_confirm_{post['id']}"):
                        try:
                            subs = [s.strip() for s in (subs_text or "").split(",") if s.strip()]
                            if len(subs) == 0:
                                st.error("请至少填写1个子版块")
                                return
                            if len(subs) > 3:
                                st.error("最多只能选择3个子版块")
                                return

                            scheduled_dt = datetime.combine(start_date, start_time)
                            from modules.posting.shared.schedule_manager import ScheduleManager
                            from modules.posting.shared.rule_checker import SubredditRuleChecker
                            
                            schedule_manager = ScheduleManager(st.session_state.db)
                            
                            # 预检查：验证Reddit API认证状态（复用左侧边栏已有的认证，不进行额外验证）
                            # 注意：只检查 scraper 是否存在和 is_authenticated()，不检查 user.me()
                            # 因为 user.me() 在某些认证方式下可能返回 None，但不影响发布功能
                            auth_warning = None
                            if st.session_state.get('scraper'):
                                scraper = st.session_state.scraper
                                # 只检查 is_authenticated()，这是最可靠的认证检查方法
                                if not scraper.is_authenticated():
                                    auth_warning = "⚠️ Reddit API未认证或认证已过期。计划将创建，但执行时会失败。请在左侧边栏重新进行OAuth2认证。"
                                # 不再检查 user.me()，因为：
                                # 1. 使用 access_token 方式认证时，user.me() 可能返回 None，但不影响发布
                                # 2. 左侧边栏已经认证过，直接复用即可
                                # 3. 如果认证有问题，执行时会返回具体错误信息
                            else:
                                auth_warning = "⚠️ Reddit API未初始化。计划将创建，但执行时会失败。请在左侧边栏完成Reddit API认证。"
                            
                            if auth_warning:
                                st.warning(auth_warning)
                            
                            # 创建规则检查器（用于检查帖子内容是否符合子版块规则）
                            rule_checker = None
                            if st.session_state.get('analyzer') and st.session_state.get('scraper'):
                                rule_checker = SubredditRuleChecker(
                                    db_manager=st.session_state.db,
                                    llm_analyzer=st.session_state.analyzer,
                                    reddit_scraper=st.session_state.scraper
                                )
                            
                            # 显示规则检查进度
                            if rule_checker:
                                with st.spinner("正在检查帖子内容是否符合子版块规则..."):
                                    created_ids = schedule_manager.create_schedules_for_posts(
                                        post_ids=[int(post['id'])],
                                        subreddits=subs,
                                        scheduled_time=scheduled_dt,
                                        rule_checker=rule_checker,
                                        provider=st.session_state.get('ai_provider', 'deepseek'),
                                        batch_min_interval=timedelta(hours=2),
                                        rolling_window=timedelta(hours=8),
                                        rolling_window_max_batches=4,
                                        auto_shift=True,
                                        subreddit_spacing_seconds=30
                                    )
                            else:
                                # 如果没有analyzer或scraper，仍然创建计划但不进行规则检查
                                st.warning("⚠️ AI分析器或Reddit API未初始化，跳过规则检查")
                                created_ids = schedule_manager.create_schedules_for_posts(
                                    post_ids=[int(post['id'])],
                                    subreddits=subs,
                                    scheduled_time=scheduled_dt,
                                    rule_checker=None,
                                    provider=st.session_state.get('ai_provider', 'deepseek'),
                                    batch_min_interval=timedelta(hours=2),
                                    rolling_window=timedelta(hours=8),
                                    rolling_window_max_batches=4,
                                    auto_shift=True,
                                    subreddit_spacing_seconds=30
                                )

                            if created_ids:
                                st.success(f"✅ 已创建 {len(created_ids)} 条发布计划（1篇帖子 × {len(subs)}个子版块）")
                            else:
                                st.warning("未创建任何计划")

                            if auto_start_service:
                                try:
                                    from posting_auto_execution_service import PostingAutoExecutionService
                                    svc = st.session_state.get('posting_auto_service')
                                    if not svc or not hasattr(svc, 'is_alive') or not svc.is_alive():
                                        # 创建新的后台服务，使用当前已认证的 scraper
                                        svc = PostingAutoExecutionService(st.session_state.db, st.session_state.scraper, poll_interval_seconds=20)
                                        st.session_state.posting_auto_service = svc
                                    else:
                                        # 如果服务已存在，更新为最新的认证状态（确保使用最新的认证）
                                        svc.set_scraper(st.session_state.scraper)
                                    svc.start()
                                    st.info("✅ 后台自动发帖服务已启动（使用当前认证状态）")
                                except Exception as e:
                                    st.warning(f"后台服务启动失败（不影响计划创建）：{str(e)}")

                            st.session_state[f"show_timed_publish_{post['id']}"] = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"创建计划失败: {str(e)}")

                with col_act2:
                    if st.button("取消", key=f"lib_publish_cancel_{post['id']}"):
                        st.session_state[f"show_timed_publish_{post['id']}"] = False
                        st.rerun()
            
            # 编辑模式
            if st.session_state.get(f"editing_post_{post['id']}", False):
                st.markdown("---")
                st.markdown("#### ✏️ 编辑帖子")
                
                edit_title = st.text_input("标题", value=post['title'], key=f"edit_title_{post['id']}")
                
                # 编辑模式下显示完整内容，高度根据内容长度自适应
                content_length = len(post.get('content', ''))
                content_lines = max(1, post.get('content', '').count('\n') + 1)
                # 根据行数计算高度，每行约25px，最小400px，最大800px
                edit_height = min(800, max(400, content_lines * 25 + 100))
                
                st.markdown(f"**内容长度:** {content_length} 字符，{content_lines} 行")
                edit_content = st.text_area(
                    "内容（全文，可滚动编辑）", 
                    value=post.get('content', ''), 
                    height=edit_height, 
                    key=f"edit_content_{post['id']}",
                    help="可在此文本框中滚动查看和编辑完整内容"
                )
                edit_status = st.selectbox(
                    "状态",
                    ["draft", "ready", "scheduled", "published", "archived"],
                    index=["draft", "ready", "scheduled", "published", "archived"].index(post['status']),
                    key=f"edit_status_{post['id']}"
                )
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("💾 保存", key=f"save_edit_{post['id']}"):
                        if post_manager.update_post(
                            post['id'],
                            title=edit_title,
                            content=edit_content,
                            status=edit_status
                        ):
                            st.success("✅ 已更新")
                            st.session_state[f"editing_post_{post['id']}"] = False
                            st.rerun()
                
                with col_cancel:
                    if st.button("❌ 取消", key=f"cancel_edit_{post['id']}"):
                        st.session_state[f"editing_post_{post['id']}"] = False
                        st.rerun()


def render_schedule_list(db, post_manager: PostManager):
    """渲染发布计划列表界面"""
    st.subheader("📅 发布计划管理")
    
    from modules.posting.shared.schedule_manager import ScheduleManager
    from posting_execution_service import PostingExecutionService
    from datetime import datetime, timedelta
    import json
    
    schedule_manager = ScheduleManager(db)
    
    # 状态筛选
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        status_filter = st.selectbox(
            "状态筛选",
            ["全部", "pending", "posting", "posted", "failed"],
            key="schedule_status_filter"
        )
    with col_filter2:
        limit = st.number_input("显示数量", min_value=10, max_value=500, value=50, key="schedule_limit")
    with col_filter3:
        if st.button("🔄 刷新数据", key="refresh_schedules"):
            st.rerun()
    
    # 获取发布计划列表
    status = None if status_filter == "全部" else status_filter
    schedules = schedule_manager.list_schedules(status=status, limit=limit)
    
    if not schedules:
        st.info("📭 没有找到发布计划")
        return
    
    st.markdown(f"**共找到 {len(schedules)} 条发布计划**")
    
    # 统计信息
    status_counts = {}
    for schedule in schedules:
        status = schedule['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    if status_counts:
        col_stat1, col_stat2, col_stat3, col_stat4, col_stat5, col_stat6 = st.columns(6)
        with col_stat1:
            st.metric("待发布", status_counts.get('pending', 0))
        with col_stat2:
            st.metric("发布中", status_counts.get('posting', 0))
        with col_stat3:
            st.metric("已发布", status_counts.get('posted', 0))
        with col_stat4:
            st.metric("失败", status_counts.get('failed', 0))
        with col_stat5:
            st.metric("已取消", status_counts.get('cancelled', 0))
        with col_stat6:
            st.metric("总计", len(schedules))
    
    st.markdown("---")
    
    # 显示发布计划列表
    for schedule in schedules:
        # 根据状态设置不同的图标和颜色
        status_icons = {
            'pending': '⏳',
            'posting': '🔄',
            'posted': '✅',
            'failed': '❌',
            'approved': '✓',
            'rejected': '✗',
            'cancelled': '🚫'
        }
        status_icon = status_icons.get(schedule['status'], '📋')
        
        # 计算时间差
        scheduled_time = schedule['scheduled_time']
        if isinstance(scheduled_time, str):
            try:
                scheduled_time = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
            except:
                scheduled_time = datetime.fromisoformat(scheduled_time)
        now = datetime.utcnow()
        time_diff = scheduled_time - now
        
        # 格式化时间差
        if time_diff.total_seconds() > 0:
            time_str = f"还有 {str(time_diff).split('.')[0]}"
        elif time_diff.total_seconds() < 0:
            time_str = f"已过 {str(-time_diff).split('.')[0]}"
        else:
            time_str = "现在"
        
        # 展开器标题
        expander_title = f"{status_icon} {schedule['post_title'][:40]}... → r/{schedule['subreddit']} ({schedule['status']})"
        
        with st.expander(expander_title, expanded=False):
            col_info, col_action = st.columns([3, 1])
            
            with col_info:
                st.markdown(f"**计划ID:** {schedule['id']}")
                st.markdown(f"**帖子ID:** {schedule['post_content_id']}")
                st.markdown(f"**帖子标题:** {schedule['post_title']}")
                st.markdown(f"**目标子版块:** r/{schedule['subreddit']}")
                st.markdown(f"**计划时间:** {schedule['scheduled_time']} (UTC) - {time_str}")
                st.markdown(f"**状态:** {schedule['status']}")
                st.markdown(f"**发布顺序:** {schedule['posting_order']}")
                st.markdown(f"**创建时间:** {schedule['created_at']}")
                
                # 显示规则检查结果
                if schedule.get('rule_check_result'):
                    rule_result = schedule['rule_check_result']
                    if isinstance(rule_result, str):
                        try:
                            rule_result = json.loads(rule_result)
                        except:
                            pass
                    
                    if isinstance(rule_result, dict):
                        is_compliant = rule_result.get('is_compliant', False)
                        compliance_score = rule_result.get('compliance_score', 0)
                        if is_compliant:
                            st.success(f"✅ 规则检查通过 (评分: {compliance_score}/100)")
                        else:
                            st.warning(f"⚠️ 规则检查未通过 (评分: {compliance_score}/100)")
                            violated_rules = rule_result.get('violated_rules', [])
                            if violated_rules:
                                st.markdown("**违反的规则:**")
                                for rule in violated_rules:
                                    st.markdown(f"- {rule}")
                
                # 显示发布结果
                if schedule.get('posting_result'):
                    posting_result = schedule['posting_result']
                    if isinstance(posting_result, str):
                        try:
                            posting_result = json.loads(posting_result)
                        except:
                            pass
                    
                    if isinstance(posting_result, dict):
                        if schedule['status'] == 'posted':
                            post_id = posting_result.get('post_id', '')
                            url = posting_result.get('url', '')
                            permalink = posting_result.get('permalink', '')
                            posted_at = posting_result.get('posted_at', '')
                            
                            st.success("✅ 发布成功")
                            if url:
                                st.markdown(f"**链接:** [{url}]({url})")
                            if post_id:
                                st.markdown(f"**Reddit帖子ID:** {post_id}")
                            if posted_at:
                                st.markdown(f"**发布时间:** {posted_at}")
                        elif schedule['status'] == 'failed':
                            error = posting_result.get('error', '未知错误')
                            error_type = posting_result.get('error_type', 'unknown')
                            suggestion = posting_result.get('suggestion', '')
                            
                            st.error(f"❌ 发布失败: {error}")
                            if error_type:
                                st.markdown(f"**错误类型:** {error_type}")
                            if suggestion:
                                st.info(f"💡 建议: {suggestion}")
                        elif schedule['status'] == 'cancelled':
                            reason = posting_result.get('reason', '已取消') if posting_result else '已取消'
                            cancelled_at = posting_result.get('cancelled_at', '') if posting_result else ''
                            
                            st.warning(f"🚫 计划已取消: {reason}")
                            if cancelled_at:
                                st.markdown(f"**取消时间:** {cancelled_at}")
            
            with col_action:
                # 根据状态显示不同的操作按钮
                if schedule['status'] == 'failed':
                    st.markdown("### 重新发送")
                    
                    # 确认当前时间
                    current_time = datetime.utcnow()
                    st.markdown(f"**当前时间 (UTC):** {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # 选择新的发布时间
                    new_date = st.date_input(
                        "新发布日期 (UTC)",
                        value=current_time.date(),
                        key=f"reschedule_date_{schedule['id']}"
                    )
                    new_time = st.time_input(
                        "新发布时间 (UTC)",
                        value=current_time.time().replace(second=0, microsecond=0),
                        key=f"reschedule_time_{schedule['id']}"
                    )
                    
                    new_scheduled_time = datetime.combine(new_date, new_time)
                    
                    # 显示时间差
                    time_diff = new_scheduled_time - current_time
                    if time_diff.total_seconds() < 0:
                        st.warning("⚠️ 选择的发布时间已过期")
                    elif time_diff.total_seconds() < 60:
                        st.info(f"⏰ 将在 {int(time_diff.total_seconds())} 秒后发布")
                    else:
                        st.info(f"⏰ 将在 {str(time_diff).split('.')[0]} 后发布")
                    
                    if st.button("🔄 重新发送", type="primary", key=f"reschedule_{schedule['id']}"):
                        # 确认操作
                        if new_scheduled_time < current_time:
                            st.error("❌ 不能选择过去的时间")
                        else:
                            # 更新计划状态和时间
                            if schedule_manager.update_schedule(
                                schedule_id=schedule['id'],
                                scheduled_time=new_scheduled_time
                            ):
                                # 重置状态为 pending
                                schedule_manager.update_schedule_status(
                                    schedule['id'],
                                    'pending',
                                    None
                                )
                                st.success(f"✅ 已重新安排发布计划，新时间: {new_scheduled_time} (UTC)")
                                st.rerun()
                            else:
                                st.error("❌ 更新失败，请检查日志")
                
                elif schedule['status'] == 'pending':
                    # 对于待发布的任务，可以手动触发执行
                    if st.button("▶️ 立即执行", key=f"execute_now_{schedule['id']}"):
                        if not st.session_state.get('scraper') or not st.session_state.scraper.is_authenticated():
                            st.error("❌ Reddit API未认证或认证已过期。请在左侧边栏重新进行OAuth2认证。")
                        else:
                            try:
                                executor = PostingExecutionService(db, st.session_state.scraper)
                                result = executor.execute_single_schedule(schedule['id'])
                                
                                if result.get('success'):
                                    st.success("✅ 执行成功")
                                    st.rerun()
                                else:
                                    st.error(f"❌ 执行失败: {result.get('error', '未知错误')}")
                            except Exception as e:
                                st.error(f"❌ 执行异常: {str(e)}")
                
                # 删除按钮（所有状态都可以删除）
                if st.button("🗑️ 删除", key=f"delete_schedule_{schedule['id']}"):
                    # 确认删除
                    if st.session_state.get(f"confirm_delete_{schedule['id']}", False):
                        session = db.get_session()
                        try:
                            schedule_obj = session.query(db.PostingSchedule).filter(
                                db.PostingSchedule.id == schedule['id']
                            ).first()
                            if schedule_obj:
                                session.delete(schedule_obj)
                                session.commit()
                                st.success("✅ 已删除")
                                st.rerun()
                            else:
                                st.error("❌ 计划不存在")
                        except Exception as e:
                            st.error(f"❌ 删除失败: {str(e)}")
                            session.rollback()
                        finally:
                            session.close()
                    else:
                        st.session_state[f"confirm_delete_{schedule['id']}"] = True
                        st.warning("⚠️ 再次点击删除按钮确认删除")
                        st.rerun()

