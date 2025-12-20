"""
数据分析与结果展示页面
包含数据管理、数据整理和本地筛选功能
"""
import streamlit as st
import json
import time
import hashlib
from datetime import datetime, timedelta
import logging
from database import DatabaseManager
from llm_analyzer import LLMAnalyzer
from data_organizer import DataOrganizer

# 缓存装饰器用于优化数据库查询
# 注意：使用下划线前缀避免对DatabaseManager对象进行哈希
@st.cache_data(ttl=60)  # 缓存60秒
def get_cached_analysis_statistics(_db_manager):
    """获取分析统计信息（带缓存）"""
    try:
        return _db_manager.get_analysis_statistics()
    except Exception as e:
        return {}

@st.cache_data(ttl=120)  # 缓存2分钟
def get_cached_subreddit_list(_db_manager):
    """获取子版块列表（带缓存）"""
    try:
        return _db_manager.get_subreddit_list()
    except Exception as e:
        return []

@st.cache_data(ttl=120)  # 缓存2分钟
def get_cached_posts_grouped(_db_manager):
    """获取分组数据（带缓存）"""
    try:
        return _db_manager.get_posts_grouped_by_date_subreddit()
    except Exception as e:
        return {}

def create_unique_key(prefix, group_key, suffix=""):
    """创建唯一的key，避免冲突"""
    # 使用group_key的hash值来确保唯一性
    key_hash = hashlib.md5(f"{group_key}_{suffix}".encode()).hexdigest()[:8]
    return f"{prefix}_{key_hash}"

def create_state_key(prefix, group_key):
    """创建唯一的状态键"""
    return f"{prefix}_{group_key}"

def get_state_value(key, default=False):
    """安全地获取状态值"""
    return st.session_state.get(key, default)

def toggle_state(key, value):
    """切换状态值并重新运行"""
    st.session_state[key] = value
    st.rerun()

def _invalidate_local_data_caches():
    """删除数据后清理相关缓存，保证界面数据及时刷新"""
    try:
        get_cached_analysis_statistics.clear()
        get_cached_subreddit_list.clear()
        get_cached_posts_grouped.clear()
    except Exception:
        # cache clear失败不应阻塞主流程
        pass

def _to_display_value(v):
    """把常见类型转换为适合在表格里展示的值"""
    if v is None:
        return None
    try:
        # numpy / pandas 标量
        if hasattr(v, "item"):
            v = v.item()
    except Exception:
        pass
    if isinstance(v, (datetime,)):
        return v.isoformat(sep=" ", timespec="seconds")
    # JSON字段一般是list/dict
    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    return v

def _get_model_pk_info(model):
    """返回主键列名列表与列对象列表（支持复合主键）"""
    from sqlalchemy.inspection import inspect as sa_inspect
    mapper = sa_inspect(model)
    pk_cols = list(mapper.primary_key)
    pk_names = [c.key for c in pk_cols]
    return pk_names, pk_cols

def _get_model_columns(model):
    """返回模型的列名列表（仅表字段，不含关系）"""
    from sqlalchemy.inspection import inspect as sa_inspect
    mapper = sa_inspect(model)
    return [c.key for c in mapper.columns]

def _build_dataframe(rows, columns):
    """把ORM行转换成DataFrame（延迟导入pandas）"""
    import pandas as pd
    data = []
    for r in rows:
        item = {}
        for col in columns:
            item[col] = _to_display_value(getattr(r, col, None))
        data.append(item)
    return pd.DataFrame(data)

def _delete_by_pk(session, model, pk_names, pk_values):
    """按主键删除一条记录。pk_values: 单主键值或复合主键tuple"""
    try:
        obj = session.get(model, pk_values)
    except Exception:
        obj = None
    if obj is None:
        # 兼容旧Query.get
        try:
            obj = session.query(model).get(pk_values)
        except Exception:
            obj = None
    if obj is None:
        # 最后兜底：按字段过滤
        q = session.query(model)
        if len(pk_names) == 1:
            q = q.filter(getattr(model, pk_names[0]) == pk_values)
        else:
            for k, v in zip(pk_names, pk_values):
                q = q.filter(getattr(model, k) == v)
        obj = q.first()
    if obj is None:
        return False
    session.delete(obj)
    return True

def render_model_browser(*, title, description, model, default_order_col=None, page_size_default=50, key_prefix=None):
    """通用：分页查看 + 单条/多选删除"""
    key_prefix = key_prefix or getattr(model, "__tablename__", model.__name__)

    st.markdown(f"#### {title}")
    if description:
        st.caption(description)

    pk_names, pk_cols = _get_model_pk_info(model)
    all_cols = _get_model_columns(model)
    # 默认展示：主键 + 前若干列（避免一次性塞太多）
    display_cols_default = []
    for c in pk_names:
        if c in all_cols:
            display_cols_default.append(c)
    for c in all_cols:
        if c not in display_cols_default:
            display_cols_default.append(c)
        if len(display_cols_default) >= 12:
            break

    with st.expander("筛选与分页", expanded=False):
        colf1, colf2, colf3 = st.columns(3)
        with colf1:
            search_text = st.text_input("关键词搜索（仅对文本列模糊匹配）", key=f"{key_prefix}_search")
        with colf2:
            page_size = st.selectbox("每页数量", [20, 50, 100, 200], index=[20, 50, 100, 200].index(page_size_default) if page_size_default in [20, 50, 100, 200] else 1, key=f"{key_prefix}_page_size")
        with colf3:
            order_col = st.selectbox("排序字段", options=all_cols, index=all_cols.index(default_order_col) if default_order_col in all_cols else 0, key=f"{key_prefix}_order_col")
        colf4, colf5 = st.columns(2)
        with colf4:
            order_desc = st.checkbox("倒序（最新在前）", value=True, key=f"{key_prefix}_order_desc")
        with colf5:
            visible_cols = st.multiselect("显示字段", options=all_cols, default=display_cols_default, key=f"{key_prefix}_visible_cols")

    session = st.session_state.db.get_session()
    try:
        q = session.query(model)

        # 简单关键词搜索：对前几个文本列 OR 匹配
        if search_text:
            from sqlalchemy import or_
            text_cols = []
            for c in pk_cols + [getattr(model, n, None) for n in all_cols]:
                try:
                    col_obj = c if hasattr(c, "type") else None
                except Exception:
                    col_obj = None
                # 只匹配String/Text类型
                if col_obj is not None:
                    tname = col_obj.type.__class__.__name__.lower()
                    if "string" in tname or "text" in tname:
                        text_cols.append(col_obj)
                if len(text_cols) >= 6:
                    break
            if text_cols:
                pattern = f"%{search_text}%"
                q = q.filter(or_(*[c.ilike(pattern) for c in text_cols]))

        total = q.count()
        if total == 0:
            st.info("暂无数据。")
            return

        max_page = max(1, (total + page_size - 1) // page_size)
        page = st.number_input("页码", min_value=1, max_value=max_page, value=1, step=1, key=f"{key_prefix}_page")
        offset = int((page - 1) * page_size)

        order_attr = getattr(model, order_col, None)
        if order_attr is not None:
            q = q.order_by(order_attr.desc() if order_desc else order_attr.asc())
        rows = q.offset(offset).limit(int(page_size)).all()

        # 生成DataFrame
        cols_for_df = [c for c in visible_cols if c in all_cols]
        # 确保主键列始终存在（删除需要）
        for c in pk_names:
            if c not in cols_for_df:
                cols_for_df.insert(0, c)
        df = _build_dataframe(rows, cols_for_df)

        import pandas as pd
        if df.empty:
            st.info("当前页无数据。")
            return

        df_edit = df.copy()
        df_edit.insert(0, "删除", False)

        st.caption(f"共 {total} 条 | 当前第 {page}/{max_page} 页")
        edited = st.data_editor(
            df_edit,
            key=f"{key_prefix}_editor",
            hide_index=True,
            disabled=[c for c in df_edit.columns if c != "删除"],
            use_container_width=True,
        )

        selected = edited[edited["删除"] == True]  # noqa: E712
        selected_count = int(selected.shape[0])

        col_del1, col_del2, col_del3 = st.columns([2, 2, 6])
        with col_del1:
            confirm = st.checkbox("确认删除", key=f"{key_prefix}_confirm_delete")
        with col_del2:
            do_delete = st.button(f"🗑️ 删除选中 ({selected_count})", type="secondary", disabled=(selected_count == 0 or not confirm), key=f"{key_prefix}_delete_btn")
        with col_del3:
            st.caption("提示：勾选“删除”列可单条或多条删除。")

        if do_delete:
            deleted = 0
            try:
                for _, r in selected.iterrows():
                    if len(pk_names) == 1:
                        pk_val = _to_display_value(r[pk_names[0]])
                    else:
                        pk_val = tuple(_to_display_value(r[k]) for k in pk_names)
                    if _delete_by_pk(session, model, pk_names, pk_val):
                        deleted += 1
                session.commit()
                _invalidate_local_data_caches()
                st.success(f"✅ 已删除 {deleted} 条记录")
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"❌ 删除失败: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    finally:
        session.close()

def render_reddit_data_section():
    st.info("📥 这里展示从 Reddit 抓取/索引得到的原始数据。支持关键词搜索、分页浏览、单条/多选删除。")
    render_model_browser(
        title="🧾 Reddit帖子（reddit_posts）",
        description="抓取到的帖子正文、标题、作者、分数、板块等。",
        model=st.session_state.db.RedditPost,
        default_order_col="scraped_at",
        key_prefix="reddit_posts",
    )
    st.markdown("---")
    render_model_browser(
        title="💬 Reddit评论（reddit_comments）",
        description="抓取到的评论正文、所属帖子ID、作者、分数等。",
        model=st.session_state.db.RedditComment,
        default_order_col="scraped_at",
        key_prefix="reddit_comments",
    )
    st.markdown("---")
    render_model_browser(
        title="📌 子版块信息（subreddit_info）",
        description="子版块基础信息（订阅数、描述、是否成人等）。",
        model=st.session_state.db.SubredditInfo,
        default_order_col="last_updated",
        key_prefix="subreddit_info",
    )
    st.markdown("---")
    render_model_browser(
        title="🗂️ 子版块索引（subreddit_index）",
        description="用于推荐/检索的子版块索引与关键词、向量等（如果启用过索引功能）。",
        model=st.session_state.db.SubredditIndex,
        default_order_col="indexed_at",
        key_prefix="subreddit_index",
    )

def render_analysis_data_section():
    st.info("📊 这里展示智能筛选功能产生的分析结果数据（痛点提取、情绪分析、需求分析、综合分析、自定义分析等）。")
    
    # 显示智能筛选的分析结果（按分析类型分类显示）
    try:
        session = st.session_state.db.get_session()
        try:
            # 获取所有智能筛选相关的分析类型
            from sqlalchemy import distinct
            all_types = session.query(distinct(st.session_state.db.AnalysisResult.analysis_type)).all()
            # 筛选智能筛选相关的分析类型
            smart_filter_types = {
                'pain_point_analysis': '痛点提取',
                'sentiment_analysis': '情绪分析',
                'need_analysis': '需求分析',
                'comprehensive_analysis': '综合分析',
                'custom_analysis': '自定义分析'
            }
            
            # 检查数据库中是否有这些类型的分析结果
            found_types = []
            for analysis_type, display_name in smart_filter_types.items():
                count = session.query(st.session_state.db.AnalysisResult).filter(
                    st.session_state.db.AnalysisResult.analysis_type == analysis_type
                ).count()
                if count > 0:
                    found_types.append((analysis_type, display_name, count))
            
            if not found_types:
                st.info("📭 暂无智能筛选分析结果，请在'智能筛选'功能中进行分析")
                return
            
            # 按分析类型分组显示
            for analysis_type, display_name, count in found_types:
                st.markdown(f"#### 📊 {display_name}（{count}条记录）")
                st.caption(f"智能筛选功能中的{display_name}结果（analysis_type: {analysis_type}）")
                
                # 使用自定义查询来过滤分析类型
                render_analysis_results_by_type(analysis_type, display_name, key_prefix=f"smart_filter_{analysis_type}")
                st.markdown("---")
        finally:
            session.close()
    except Exception as e:
        st.error(f"❌ 加载智能筛选分析结果失败: {str(e)}")
        import traceback
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())

def render_analysis_results_by_type(analysis_type: str, display_name: str, key_prefix: str):
    """按分析类型显示分析结果"""
    try:
        session = st.session_state.db.get_session()
        try:
            # 查询该类型的所有分析结果
            query = session.query(st.session_state.db.AnalysisResult).filter(
                st.session_state.db.AnalysisResult.analysis_type == analysis_type
            ).order_by(st.session_state.db.AnalysisResult.created_at.desc())
            
            # 分页
            page_size = st.session_state.get(f"{key_prefix}_page_size", 50)
            page_num = st.session_state.get(f"{key_prefix}_page_num", 1)
            
            total_count = query.count()
            total_pages = (total_count + page_size - 1) // page_size
            
            if total_count == 0:
                st.info("暂无记录")
                return
            
            # 分页控件
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.caption(f"共 {total_count} 条记录，第 {page_num}/{total_pages} 页")
            with col2:
                page_size = st.selectbox("每页数量", [20, 50, 100, 200], 
                                        index=[20, 50, 100, 200].index(page_size) if page_size in [20, 50, 100, 200] else 1,
                                        key=f"{key_prefix}_page_size")
                st.session_state[f"{key_prefix}_page_size"] = page_size
            with col3:
                if total_pages > 1:
                    page_num = st.number_input("页码", min_value=1, max_value=total_pages, value=page_num, key=f"{key_prefix}_page_num")
                    st.session_state[f"{key_prefix}_page_num"] = page_num
            
            # 获取当前页的数据
            offset = (page_num - 1) * page_size
            results = query.offset(offset).limit(page_size).all()
            
            # 显示结果
            for idx, result in enumerate(results):
                with st.expander(f"记录 #{result.id} - {result.content_id} ({result.created_at.strftime('%Y-%m-%d %H:%M:%S') if result.created_at else 'N/A'})"):
                    col_info1, col_info2 = st.columns([2, 1])
                    with col_info1:
                        st.write(f"**内容ID**: {result.content_id}")
                        st.write(f"**内容类型**: {result.content_type}")
                        st.write(f"**分析类型**: {result.analysis_type}")
                        if result.model_used:
                            st.write(f"**使用模型**: {result.model_used}")
                    with col_info2:
                        if st.button("🗑️ 删除", key=f"delete_{key_prefix}_{result.id}"):
                            try:
                                session.delete(result)
                                session.commit()
                                st.success("✅ 已删除")
                                st.rerun()
                            except Exception as e:
                                session.rollback()
                                st.error(f"❌ 删除失败: {str(e)}")
                    
                    # 显示分析结果
                    st.markdown("**分析结果:**")
                    try:
                        import json
                        if isinstance(result.result, str):
                            try:
                                result_json = json.loads(result.result)
                                st.json(result_json)
                            except:
                                st.text(result.result)
                        else:
                            st.json(result.result)
                    except:
                        st.text(str(result.result))
                
                if idx < len(results) - 1:
                    st.markdown("---")
        finally:
            session.close()
    except Exception as e:
        st.error(f"❌ 加载分析结果失败: {str(e)}")

def render_posting_data_section():
    st.info("📝 这里展示“智能发帖/发帖计划/规则/互动监控”相关的本地数据。")
    render_model_browser(
        title="📝 帖子内容库（post_contents）",
        description="准备发布的帖子内容、状态等。",
        model=st.session_state.db.PostContent,
        default_order_col="created_at",
        key_prefix="post_contents",
    )
    st.markdown("---")
    render_model_browser(
        title="📅 发布计划（posting_schedules）",
        description="计划发布的帖子与时间、目标子版块、状态等。",
        model=st.session_state.db.PostingSchedule,
        default_order_col="created_at",
        key_prefix="posting_schedules",
    )
    st.markdown("---")
    render_model_browser(
        title="📜 子版块规则（subreddit_rules）",
        description="抓取/维护的子版块规则，用于内容合规检查。",
        model=st.session_state.db.SubredditRule,
        default_order_col="fetched_at",
        key_prefix="subreddit_rules",
    )
    st.markdown("---")
    render_model_browser(
        title="👀 发帖后互动监控（post_interactions）",
        description="用于跟踪发帖后的评论/点赞/自动回复触发等状态。",
        model=st.session_state.db.PostInteraction,
        default_order_col="created_at",
        key_prefix="post_interactions",
    )
    st.markdown("---")
    render_model_browser(
        title="💬 自动回复记录（auto_replies）",
        description="自动回复的内容、状态、错误信息等。",
        model=st.session_state.db.AutoReply,
        default_order_col="created_at",
        key_prefix="auto_replies",
    )

def render_automation_data_section():
    st.info("🤖 这里展示自动化运营（评分/队列/配额/配置/状态）相关数据。")
    render_model_browser(
        title="⭐ 帖子评分（post_scoring）",
        description="自动化运营对帖子打分的结果与原因。",
        model=st.session_state.db.PostScoring,
        default_order_col="scored_at",
        key_prefix="post_scoring",
    )
    st.markdown("---")
    render_model_browser(
        title="🧾 互动任务队列（auto_interaction_queue）",
        description="待执行/执行中/已完成的点赞/评论等任务。",
        model=st.session_state.db.AutoInteractionQueue,
        default_order_col="created_at",
        key_prefix="auto_interaction_queue",
    )
    st.markdown("---")
    render_model_browser(
        title="📝 自动发帖队列（auto_post_queue）",
        description="自动发帖任务队列（待执行/执行中/完成/失败）。",
        model=st.session_state.db.AutoPostQueue,
        default_order_col="created_at",
        key_prefix="auto_post_queue",
    )
    st.markdown("---")
    render_model_browser(
        title="📈 每日配额（daily_quota）",
        description="自动化运营的每日限额与统计。",
        model=st.session_state.db.DailyQuota,
        default_order_col="date",
        key_prefix="daily_quota",
    )
    st.markdown("---")
    render_model_browser(
        title="⚙️ 互动配置（auto_interaction_config）",
        description="自动化运营配置（如RPTA配置、调度器配置等）。",
        model=st.session_state.db.AutoInteractionConfig,
        default_order_col="updated_at",
        key_prefix="auto_interaction_config",
    )
    st.markdown("---")
    render_model_browser(
        title="📊 互动状态（auto_interaction_status）",
        description="自动化运营运行状态与统计信息。",
        model=st.session_state.db.AutoInteractionStatus,
        default_order_col="updated_at",
        key_prefix="auto_interaction_status",
    )

def render_account_data_section():
    st.info("👤 这里展示账号画像、关注、互动统计、发帖资格检测等数据。")
    render_model_browser(
        title="🤝 用户互动（user_interactions）",
        description="用户级互动记录。",
        model=st.session_state.db.UserInteractions,
        default_order_col="created_at",
        key_prefix="user_interactions",
    )
    st.markdown("---")
    render_model_browser(
        title="🔭 帖子监控（post_monitoring）",
        description="监控的帖子与监控状态。",
        model=st.session_state.db.PostMonitoring,
        default_order_col="created_at",
        key_prefix="post_monitoring",
    )
    st.markdown("---")
    render_model_browser(
        title="📊 互动统计（interaction_stats）",
        description="聚合后的互动统计。",
        model=st.session_state.db.InteractionStats,
        default_order_col="updated_at",
        key_prefix="interaction_stats",
    )
    st.markdown("---")
    render_model_browser(
        title="👣 用户关注（user_follows）",
        description="关注的用户列表与状态。",
        model=st.session_state.db.UserFollows,
        default_order_col="followed_at",
        key_prefix="user_follows",
    )
    st.markdown("---")
    render_model_browser(
        title="📸 账号快照（account_snapshots）",
        description="账号Karma、账号年龄、加入子版块数等快照记录。",
        model=st.session_state.db.AccountSnapshots,
        default_order_col="snapshot_time",
        key_prefix="account_snapshots",
    )
    st.markdown("---")
    render_model_browser(
        title="✅ 子版块发帖资格（subreddit_readiness）",
        description="对子版块是否可发帖的评估结果与建议。",
        model=st.session_state.db.SubredditReadiness,
        default_order_col="checked_at",
        key_prefix="subreddit_readiness",
    )

def render_other_data_section():
    st.info("📎 这里是其他杂项数据（提示词模板、上传文件记录、关键词历史等）。")
    render_model_browser(
        title="🧾 提示词模板（prompt_templates）",
        description="提示词模板及其内容。",
        model=st.session_state.db.PromptTemplate,
        default_order_col="updated_at",
        key_prefix="prompt_templates",
    )
    st.markdown("---")
    render_model_browser(
        title="📎 上传文件（uploaded_files）",
        description="上传到本地的文件记录（文本/图片等）。",
        model=st.session_state.db.UploadedFile,
        default_order_col="uploaded_at",
        key_prefix="uploaded_files",
    )
    st.markdown("---")
    render_keyword_history_section()
    render_subreddit_history_section()

def render_keyword_history_section():
    """渲染关键词历史记录部分"""
    from sqlalchemy import distinct
    
    st.markdown("### 🔑 关键词历史记录（keyword_history）")
    st.info("💡 存储用户在项目中输入过的所有关键词，支持按来源筛选和删除。**已启用自动去重功能**：相同关键词会自动合并，使用次数累加，来源信息会合并显示。")
    
    try:
        session = st.session_state.db.get_session()
        try:
            # 获取所有来源
            sources = session.query(distinct(st.session_state.db.KeywordHistory.source)).all()
            source_list = [s[0] for s in sources if s[0]]
            source_list.insert(0, "全部")
            
            # 来源筛选
            col_filter1, col_filter2 = st.columns([1, 3])
            with col_filter1:
                selected_source = st.selectbox(
                    "筛选来源",
                    source_list,
                    key="keyword_history_source_filter"
                )
            
            with col_filter2:
                search_keyword = st.text_input(
                    "搜索关键词",
                    placeholder="输入关键词进行搜索...",
                    key="keyword_history_search"
                )
            
            # 构建查询（已实现自动去重，每个关键词只保留一条记录）
            from sqlalchemy import distinct
            query = session.query(st.session_state.db.KeywordHistory)
            
            # 如果选择了特定来源，需要检查来源字段是否包含该来源（因为来源可能已合并）
            if selected_source != "全部":
                # 使用 LIKE 查询，因为来源可能是多个来源的逗号分隔字符串
                query = query.filter(
                    (st.session_state.db.KeywordHistory.source == selected_source) |
                    (st.session_state.db.KeywordHistory.source.contains(f", {selected_source}")) |
                    (st.session_state.db.KeywordHistory.source.contains(f"{selected_source},"))
                )
            
            if search_keyword:
                query = query.filter(
                    st.session_state.db.KeywordHistory.keyword.contains(search_keyword)
                )
            
            # 排序和限制（按最后使用时间降序）
            keyword_history = query.order_by(
                st.session_state.db.KeywordHistory.last_used_at.desc()
            ).limit(500).all()
            
            if not keyword_history:
                st.info("📭 没有找到关键词历史记录")
                return
            
            st.markdown(f"**共找到 {len(keyword_history)} 条记录**")
            
            # 显示关键词列表
            for idx, record in enumerate(keyword_history):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.markdown(f"**{record.keyword}**")
                
                with col2:
                    # 显示来源（可能是多个来源的合并）
                    source_display = record.source or '未知'
                    if ',' in source_display:
                        st.caption(f"来源: {source_display} (已合并)")
                    else:
                        st.caption(f"来源: {source_display}")
                    st.caption(f"使用次数: {record.usage_count}")
                
                with col3:
                    st.caption(f"首次使用: {record.created_at.strftime('%Y-%m-%d %H:%M') if record.created_at else '未知'}")
                    st.caption(f"最后使用: {record.last_used_at.strftime('%Y-%m-%d %H:%M') if record.last_used_at else '未知'}")
                
                with col4:
                    if st.button("🗑️ 删除", key=f"delete_keyword_{record.id}"):
                        try:
                            session.delete(record)
                            session.commit()
                            st.success(f"✅ 已删除关键词: {record.keyword}")
                            st.rerun()
                        except Exception as e:
                            session.rollback()
                            st.error(f"❌ 删除失败: {str(e)}")
                
                if idx < len(keyword_history) - 1:
                    st.markdown("---")
            
            # 批量删除
            st.markdown("---")
            st.markdown("#### 🗑️ 批量操作")
            col_batch1, col_batch2 = st.columns([1, 1])
            with col_batch1:
                if st.button("🗑️ 删除所有记录", type="secondary", key="delete_all_keywords"):
                    try:
                        count = session.query(st.session_state.db.KeywordHistory).count()
                        session.query(st.session_state.db.KeywordHistory).delete()
                        session.commit()
                        st.success(f"✅ 已删除所有 {count} 条关键词历史记录")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ 批量删除失败: {str(e)}")
            
            with col_batch2:
                if selected_source != "全部" and st.button("🗑️ 删除当前来源记录", type="secondary", key="delete_source_keywords"):
                    try:
                        count = session.query(st.session_state.db.KeywordHistory).filter(
                            st.session_state.db.KeywordHistory.source == selected_source
                        ).count()
                        session.query(st.session_state.db.KeywordHistory).filter(
                            st.session_state.db.KeywordHistory.source == selected_source
                        ).delete()
                        session.commit()
                        st.success(f"✅ 已删除来源 '{selected_source}' 的 {count} 条记录")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ 批量删除失败: {str(e)}")
                        
        finally:
            session.close()
    except Exception as e:
        st.error(f"❌ 加载关键词历史记录失败: {str(e)}")
        import traceback
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())

def render_subreddit_history_section():
    """渲染子版块历史记录部分"""
    from sqlalchemy import distinct
    
    st.markdown("### 📍 子版块历史记录（subreddit_history）")
    st.info("💡 存储智能推荐和AI生成功能推荐的子版块，**已启用自动去重功能**：相同子版块会自动合并，使用次数累加，来源信息会合并显示。")
    
    try:
        session = st.session_state.db.get_session()
        try:
            # 获取所有来源
            sources = session.query(distinct(st.session_state.db.SubredditHistory.source)).all()
            source_list = [s[0] for s in sources if s[0]]
            source_list.insert(0, "全部")
            
            # 来源筛选
            col_filter1, col_filter2 = st.columns([1, 3])
            with col_filter1:
                selected_source = st.selectbox(
                    "筛选来源",
                    source_list,
                    key="subreddit_history_source_filter"
                )
            
            with col_filter2:
                search_subreddit = st.text_input(
                    "搜索子版块",
                    placeholder="输入子版块名称进行搜索...",
                    key="subreddit_history_search"
                )
            
            # 构建查询（已实现自动去重，每个子版块只保留一条记录）
            query = session.query(st.session_state.db.SubredditHistory)
            
            # 如果选择了特定来源，需要检查来源字段是否包含该来源（因为来源可能已合并）
            if selected_source != "全部":
                # 使用 LIKE 查询，因为来源可能是多个来源的逗号分隔字符串
                query = query.filter(
                    (st.session_state.db.SubredditHistory.source == selected_source) |
                    (st.session_state.db.SubredditHistory.source.contains(f", {selected_source}")) |
                    (st.session_state.db.SubredditHistory.source.contains(f"{selected_source},"))
                )
            
            if search_subreddit:
                query = query.filter(
                    st.session_state.db.SubredditHistory.subreddit_name.contains(search_subreddit)
                )
            
            # 排序和限制（按最后使用时间降序）
            subreddit_history = query.order_by(
                st.session_state.db.SubredditHistory.last_used_at.desc()
            ).limit(500).all()
            
            if not subreddit_history:
                st.info("📭 没有找到子版块历史记录")
                return
            
            st.markdown(f"**共找到 {len(subreddit_history)} 条记录**")
            
            # 显示子版块列表
            for idx, record in enumerate(subreddit_history):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.markdown(f"**r/{record.subreddit_name}**")
                    if record.rank:
                        st.caption(f"排名: #{record.rank}")
                
                with col2:
                    # 显示来源（可能是多个来源的合并）
                    source_display = record.source or '未知'
                    if ',' in source_display:
                        st.caption(f"来源: {source_display} (已合并)")
                    else:
                        st.caption(f"来源: {source_display}")
                    st.caption(f"使用次数: {record.usage_count}")
                
                with col3:
                    # 显示分数信息
                    score_info = []
                    if record.match_score is not None:
                        score_info.append(f"匹配度: {record.match_score:.1f}")
                    if record.heat_score is not None:
                        score_info.append(f"热度: {record.heat_score:.1f}")
                    if record.combined_score is not None:
                        score_info.append(f"综合: {record.combined_score:.1f}")
                    if score_info:
                        st.caption(" | ".join(score_info))
                    st.caption(f"首次收录: {record.created_at.strftime('%Y-%m-%d %H:%M') if record.created_at else '未知'}")
                    st.caption(f"最后使用: {record.last_used_at.strftime('%Y-%m-%d %H:%M') if record.last_used_at else '未知'}")
                
                with col4:
                    if st.button("🗑️ 删除", key=f"delete_subreddit_{record.id}"):
                        try:
                            session.delete(record)
                            session.commit()
                            st.success(f"✅ 已删除子版块: r/{record.subreddit_name}")
                            st.rerun()
                        except Exception as e:
                            session.rollback()
                            st.error(f"❌ 删除失败: {str(e)}")
                
                if idx < len(subreddit_history) - 1:
                    st.markdown("---")
            
            # 批量删除
            st.markdown("---")
            st.markdown("#### 🗑️ 批量操作")
            col_batch1, col_batch2 = st.columns([1, 1])
            with col_batch1:
                if st.button("🗑️ 删除所有记录", type="secondary", key="delete_all_subreddits"):
                    try:
                        count = session.query(st.session_state.db.SubredditHistory).count()
                        session.query(st.session_state.db.SubredditHistory).delete()
                        session.commit()
                        st.success(f"✅ 已删除所有 {count} 条子版块历史记录")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ 批量删除失败: {str(e)}")
            
            with col_batch2:
                if selected_source != "全部" and st.button("🗑️ 删除当前来源记录", type="secondary", key="delete_source_subreddits"):
                    try:
                        count = session.query(st.session_state.db.SubredditHistory).filter(
                            (st.session_state.db.SubredditHistory.source == selected_source) |
                            (st.session_state.db.SubredditHistory.source.contains(f", {selected_source}")) |
                            (st.session_state.db.SubredditHistory.source.contains(f"{selected_source},"))
                        ).count()
                        session.query(st.session_state.db.SubredditHistory).filter(
                            (st.session_state.db.SubredditHistory.source == selected_source) |
                            (st.session_state.db.SubredditHistory.source.contains(f", {selected_source}")) |
                            (st.session_state.db.SubredditHistory.source.contains(f"{selected_source},"))
                        ).delete()
                        session.commit()
                        st.success(f"✅ 已删除来源 '{selected_source}' 的 {count} 条记录")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ 批量删除失败: {str(e)}")
                        
        finally:
            session.close()
    except Exception as e:
        st.error(f"❌ 加载子版块历史记录失败: {str(e)}")
        import traceback
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())

def create_merged_analysis_page():
    """创建合并的数据分析与结果展示页面"""

    if not st.session_state.initialized:
        st.warning("请先配置API密钥并初始化系统")
        return

    st.info("💡 本页面仅用于查看本地数据库数据，并支持单条/多选删除（不会影响其他页面功能）。")
    show_data_management()

def show_data_management():
    """显示数据管理功能 - 整合所有数据库表的数据查看和删除"""
    
    # 数据概览统计
    st.subheader("📊 数据概览")
    try:
        session = st.session_state.db.get_session()
        try:
            # 统计所有表的数据量
            stats = {
                # Reddit原始数据
                'reddit_posts': session.query(st.session_state.db.RedditPost).count(),
                'reddit_comments': session.query(st.session_state.db.RedditComment).count(),
                'subreddit_info': session.query(st.session_state.db.SubredditInfo).count(),
                'subreddit_index': session.query(st.session_state.db.SubredditIndex).count(),
                # 分析结果数据
                'analysis_result': session.query(st.session_state.db.AnalysisResult).count(),
                # 智能筛选分析结果统计（替换原来的结构化抽取、向量化文本、聚类结果、业务洞察）
                'smart_filter_pain_point': session.query(st.session_state.db.AnalysisResult).filter(
                    st.session_state.db.AnalysisResult.analysis_type == 'pain_point_analysis'
                ).count(),
                'smart_filter_sentiment': session.query(st.session_state.db.AnalysisResult).filter(
                    st.session_state.db.AnalysisResult.analysis_type == 'sentiment_analysis'
                ).count(),
                'smart_filter_need': session.query(st.session_state.db.AnalysisResult).filter(
                    st.session_state.db.AnalysisResult.analysis_type == 'need_analysis'
                ).count(),
                'smart_filter_comprehensive': session.query(st.session_state.db.AnalysisResult).filter(
                    st.session_state.db.AnalysisResult.analysis_type == 'comprehensive_analysis'
                ).count(),
                'smart_filter_custom': session.query(st.session_state.db.AnalysisResult).filter(
                    st.session_state.db.AnalysisResult.analysis_type == 'custom_analysis'
                ).count(),
                # 智能发帖数据
                'post_content': session.query(st.session_state.db.PostContent).count(),
                'posting_schedule': session.query(st.session_state.db.PostingSchedule).count(),
                'subreddit_rule': session.query(st.session_state.db.SubredditRule).count(),
                'post_interaction': session.query(st.session_state.db.PostInteraction).count(),
                'auto_reply': session.query(st.session_state.db.AutoReply).count(),
                # 自动化运营数据
                'post_scoring': session.query(st.session_state.db.PostScoring).count(),
                'auto_interaction_queue': session.query(st.session_state.db.AutoInteractionQueue).count(),
                'auto_post_queue': session.query(st.session_state.db.AutoPostQueue).count(),
                'daily_quota': session.query(st.session_state.db.DailyQuota).count(),
                'auto_interaction_config': session.query(st.session_state.db.AutoInteractionConfig).count(),
                'auto_interaction_status': session.query(st.session_state.db.AutoInteractionStatus).count(),
                # 账号管理数据
                'user_interactions': session.query(st.session_state.db.UserInteractions).count(),
                'post_monitoring': session.query(st.session_state.db.PostMonitoring).count(),
                'interaction_stats': session.query(st.session_state.db.InteractionStats).count(),
                'user_follows': session.query(st.session_state.db.UserFollows).count(),
                'account_snapshots': session.query(st.session_state.db.AccountSnapshots).count(),
                'subreddit_readiness': session.query(st.session_state.db.SubredditReadiness).count(),
                # 其他数据
                'prompt_template': session.query(st.session_state.db.PromptTemplate).count(),
                'uploaded_file': session.query(st.session_state.db.UploadedFile).count(),
            }
            
            # 显示统计卡片（按分类分组）
            st.markdown("#### 📥 Reddit原始数据")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Reddit帖子", stats['reddit_posts'])
            with col2:
                st.metric("Reddit评论", stats['reddit_comments'])
            with col3:
                st.metric("子版块信息", stats['subreddit_info'])
            with col4:
                st.metric("子版块索引", stats['subreddit_index'])
            
            st.markdown("#### 📊 智能筛选分析结果数据")
            col5, col6, col7, col8, col9 = st.columns(5)
            with col5:
                st.metric("痛点提取", stats.get('smart_filter_pain_point', 0))
            with col6:
                st.metric("情绪分析", stats.get('smart_filter_sentiment', 0))
            with col7:
                st.metric("需求分析", stats.get('smart_filter_need', 0))
            with col8:
                st.metric("综合分析", stats.get('smart_filter_comprehensive', 0))
            with col9:
                st.metric("自定义分析", stats.get('smart_filter_custom', 0))
            
            st.markdown("#### 📝 智能发帖数据")
            col10, col11, col12, col13, col14 = st.columns(5)
            with col10:
                st.metric("帖子内容", stats['post_content'])
            with col11:
                st.metric("发布计划", stats['posting_schedule'])
            with col12:
                st.metric("子版块规则", stats['subreddit_rule'])
            with col13:
                st.metric("互动监控", stats['post_interaction'])
            with col14:
                st.metric("自动回复", stats['auto_reply'])
            
            st.markdown("#### 🤖 自动化运营数据")
            col15, col16, col17, col18, col19, col20 = st.columns(6)
            with col15:
                st.metric("帖子评分", stats['post_scoring'])
            with col16:
                st.metric("互动队列", stats['auto_interaction_queue'])
            with col17:
                st.metric("发帖队列", stats['auto_post_queue'])
            with col18:
                st.metric("每日配额", stats['daily_quota'])
            with col19:
                st.metric("互动配置", stats['auto_interaction_config'])
            with col20:
                st.metric("互动状态", stats['auto_interaction_status'])
            
            st.markdown("#### 👤 账号管理数据")
            col21, col22, col23, col24, col25, col26 = st.columns(6)
            with col21:
                st.metric("用户互动", stats['user_interactions'])
            with col22:
                st.metric("帖子监控", stats['post_monitoring'])
            with col23:
                st.metric("互动统计", stats['interaction_stats'])
            with col24:
                st.metric("用户关注", stats['user_follows'])
            with col25:
                st.metric("账号快照", stats['account_snapshots'])
            with col26:
                st.metric("子版块就绪", stats['subreddit_readiness'])
            
            st.markdown("#### 📎 其他数据")
            col27, col28 = st.columns(2)
            with col27:
                st.metric("提示词模板", stats['prompt_template'])
            with col28:
                st.metric("上传文件", stats['uploaded_file'])
        finally:
            session.close()
    except Exception as e:
        st.error(f"获取统计信息失败: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # 数据分类标签页
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📥 Reddit原始数据",
        "📊 分析结果数据",
        "📝 智能发帖数据",
        "🤖 自动化运营数据",
        "👤 账号管理数据",
        "📎 其他数据"
    ])
    
    with tab1:
        render_reddit_data_section()
    
    with tab2:
        render_analysis_data_section()
    
    with tab3:
        render_posting_data_section()
    
    with tab4:
        render_automation_data_section()
    
    with tab5:
        render_account_data_section()
    
    with tab6:
        render_other_data_section()

def show_group_packaging(group_key, group_info):
    """显示分组数据打包功能"""
    st.write("**数据打包选项:**")
    
    col_pack1, col_pack2 = st.columns(2)
    
    with col_pack1:
        output_format = st.selectbox("输出格式", ["JSON", "TXT", "Markdown"], key=create_unique_key("format", group_key))
        include_metadata = st.checkbox("包含元数据", value=True, key=create_unique_key("meta", group_key))
    
    with col_pack2:
        use_llm_summary = st.checkbox("使用LLM生成精准梗概", value=False, key=create_unique_key("llm_summary", group_key))
        ai_provider = st.selectbox("AI提供商", ["openai", "anthropic", "deepseek"], key=create_unique_key("provider", group_key))
    
    if st.button("📦 开始打包", key=create_unique_key("start_package", group_key)):
        try:
            from data_organizer import DataOrganizer
            
            # 初始化LLM分析器（如果需要）
            llm_analyzer = None
            if use_llm_summary and st.session_state.analyzer:
                llm_analyzer = st.session_state.analyzer
            
            # 创建数据整理器
            organizer = DataOrganizer(st.session_state.db, llm_analyzer)
            
            # 整理该分组的数据
            organized_data = {
                "metadata": {
                    "total_groups": 1,
                    "total_posts": group_info['total_posts'],
                    "total_comments": group_info['total_comments'],
                    "date_range": {"start": group_info['date'], "end": group_info['date']},
                    "subreddits": [group_info['subreddit']],
                    "organized_at": datetime.now().isoformat()
                },
                "scraping_sessions": [{
                    "session_id": group_key,
                    "scraping_date": group_info['date'],
                    "subreddit": group_info['subreddit'],
                    "statistics": {
                        "total_posts": group_info['total_posts'],
                        "total_comments": group_info['total_comments'],
                        "avg_score": sum(post.score or 0 for post in group_info['posts']) / len(group_info['posts']) if group_info['posts'] else 0,
                        "top_author": max([post.author for post in group_info['posts'] if post.author], key=[post.author for post in group_info['posts'] if post.author].count) if group_info['posts'] else "无"
                    },
                    "content_summary": "待生成",
                    "key_topics": [],
                    "sentiment_overview": {"positive": 0, "negative": 0, "neutral": 0},
                    "posts": [{
                        "id": post.id,
                        "title": post.title,
                        "author": post.author,
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "created_utc": post.created_utc.isoformat() if post.created_utc else None,
                        "content": post.selftext,
                        "url": post.url,
                        "flair": post.flair,
                        "is_self": post.is_self,
                        "over_18": post.over_18
                    } for post in group_info['posts']]
                }]
            }
            
            # 创建数据包
            package_content = organizer.create_llm_ready_package(
                organized_data,
                output_format=output_format.lower(),
                include_metadata=include_metadata
            )
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reddit_data_{group_key}_{timestamp}.{output_format.lower()}"
            
            # 保存文件
            file_path = organizer.save_package_to_file(
                package_content,
                filename,
                "output"
            )
            
            st.success(f"✅ 数据包已保存到: {file_path}")
            
            # 提供下载按钮
            st.download_button(
                label="📥 下载数据包",
                data=package_content,
                file_name=filename,
                mime="application/octet-stream"
            )
            
        except Exception as e:
            st.error(f"❌ 数据打包失败: {str(e)}")

def show_group_llm_processing(group_key, group_info):
    """显示分组数据传递给大模型处理"""
    st.write("**大模型处理选项:**")
    
    # 选择处理规则
    processing_rules = st.session_state.get('llm_processing_rules', {})
    
    if not processing_rules:
        st.warning("请先在大模型处理规则页面设置处理规则")
        return
    
    col_llm1, col_llm2 = st.columns(2)
    
    with col_llm1:
        selected_rule = st.selectbox(
            "选择处理规则",
            list(processing_rules.keys()),
            key=create_unique_key("rule", group_key)
        )
        
        ai_provider = st.selectbox(
            "AI提供商",
            ["openai", "anthropic", "deepseek"],
            key=create_unique_key("llm_provider", group_key)
        )
    
    with col_llm2:
        batch_size = st.number_input("批处理大小", min_value=1, max_value=100, value=25, key=create_unique_key("batch", group_key))
        use_custom_prompt = st.checkbox("使用自定义提示词", value=False, key=create_unique_key("custom", group_key))
    
    if use_custom_prompt:
        custom_prompt = st.text_area(
            "自定义提示词",
            value=processing_rules[selected_rule]['prompt_template'],
            height=200,
            key=create_unique_key("prompt", group_key)
        )
    else:
        custom_prompt = processing_rules[selected_rule]['prompt_template']
    
    if st.button("🤖 开始大模型处理", key=create_unique_key("start_llm", group_key)):
        try:
            # 准备数据
            posts_data = []
            for post in group_info['posts'][:batch_size]:
                posts_data.append({
                    'id': post.id,
                    'title': post.title,
                    'content': post.selftext or "",
                    'author': post.author,
                    'score': post.score,
                    'subreddit': post.subreddit
                })
            
            # 执行大模型处理
            if processing_rules[selected_rule]['analysis_type'] == 'comprehensive':
                result = st.session_state.analyzer.analyze_comprehensive(
                    "\n".join([f"标题: {p['title']}\n内容: {p['content']}" for p in posts_data]),
                    ai_provider,
                    custom_prompt
                )
            else:
                result = st.session_state.analyzer.analyze_posts_batch(
                    posts_data,
                    ai_provider,
                    processing_rules[selected_rule]['analysis_type']
                )
            
            if "error" not in result:
                # 保存处理结果
                st.session_state.db.save_analysis_result(
                    f"manual_{group_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "manual", processing_rules[selected_rule]['analysis_type'],
                    str(result), ai_provider
                )
                
                st.success(f"✅ 大模型处理完成！处理了 {len(posts_data)} 个帖子")
                
                # 显示结果
                with st.expander("📊 处理结果"):
                    st.json(result)
            else:
                st.error(f"❌ 大模型处理失败: {result['error']}")
                
        except Exception as e:
            st.error(f"❌ 处理失败: {str(e)}")

def show_data_packaging():
    """显示数据整理打包功能"""
    st.subheader("📦 数据整理和打包")
    st.write("将抓取的数据整理成大模型可理解的格式，支持按条件筛选和多种输出格式")
    
    col_package1, col_package2 = st.columns(2)
    
    with col_package1:
        st.write("**数据筛选条件**")
        
        # 日期范围选择
        date_range = st.date_input(
            "选择日期范围",
            value=(datetime.now() - timedelta(days=7), datetime.now()),
            help="选择要整理的数据日期范围"
        )
        
        # 子版块选择
        available_subreddits = get_cached_subreddit_list(st.session_state.db)
        selected_subreddits = st.multiselect(
            "选择子版块",
            options=available_subreddits,
            default=available_subreddits[:3] if available_subreddits else [],
            help="选择要包含的子版块，留空表示全部"
        )
    
    with col_package2:
        st.write("**输出设置**")
        
        # 输出格式
        output_format = st.selectbox(
            "输出格式",
            ["JSON", "TXT", "Markdown"],
            help="选择数据包的输出格式"
        )
        
        # 是否包含元数据
        include_metadata = st.checkbox(
            "包含元数据",
            value=True,
            help="是否在数据包中包含统计信息和元数据",
            key="global_include_metadata"
        )
        
        # 是否使用LLM生成梗概
        use_llm_summary = st.checkbox(
            "使用LLM生成精准梗概",
            value=False,
            help="使用大模型生成更精准的内容梗概（需要配置API密钥）",
            key="global_use_llm_summary"
        )
        
    
    # 数据整理和打包按钮
    if st.button("🚀 开始数据整理和打包", type="primary"):
        try:
            from data_organizer import DataOrganizer
            
            # 准备参数
            start_date = date_range[0].strftime('%Y-%m-%d') if date_range[0] else None
            end_date = date_range[1].strftime('%Y-%m-%d') if date_range[1] else None
            subreddits = selected_subreddits if selected_subreddits else None
            
            # 初始化LLM分析器（如果需要）
            llm_analyzer = None
            if use_llm_summary and st.session_state.analyzer:
                llm_analyzer = st.session_state.analyzer
            
            # 创建数据整理器
            organizer = DataOrganizer(st.session_state.db, llm_analyzer)
            
            # 显示进度
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("正在整理数据...")
            progress_bar.progress(20)
            
            # 整理数据
            organized_data = organizer.organize_data_by_scraping_session(
                start_date=start_date,
                end_date=end_date,
                subreddits=subreddits
            )
            
            if "error" in organized_data:
                st.error(f"❌ 数据整理失败: {organized_data['error']}")
                return
            
            status_text.text("正在创建数据包...")
            progress_bar.progress(60)
            
            # 创建数据包
            package_content = organizer.create_llm_ready_package(
                organized_data,
                output_format=output_format.lower(),
                include_metadata=include_metadata
            )
            
            status_text.text("正在保存文件...")
            progress_bar.progress(80)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reddit_data_{timestamp}.{output_format.lower()}"
            
            # 保存文件
            file_path = organizer.save_package_to_file(
                package_content,
                filename,
                "output"
            )
            
            progress_bar.progress(100)
            status_text.text("✅ 数据打包完成!")
            
            # 显示结果
            metadata = organized_data.get('metadata', {})
            
            st.success("🎉 数据整理和打包完成!")
            
            col_result1, col_result2 = st.columns(2)
            
            with col_result1:
                st.write("**📊 统计信息**")
                st.metric("总分组数", metadata.get('total_groups', 0))
                st.metric("总帖子数", metadata.get('total_posts', 0))
                st.metric("总评论数", metadata.get('total_comments', 0))
                
                if metadata.get('subreddits'):
                    st.write("**📍 涉及子版块**")
                    for subreddit in metadata['subreddits']:
                        st.write(f"- r/{subreddit}")
            
            with col_result2:
                st.write("**📁 文件信息**")
                st.write(f"文件名: `{filename}`")
                st.write(f"格式: {output_format}")
                st.write(f"大小: {len(package_content.encode('utf-8')) / 1024:.1f} KB")
                
                # 提供下载按钮
                st.download_button(
                    label="📥 下载数据包",
                    data=package_content,
                    file_name=filename,
                    mime="application/octet-stream"
                )
            
            # 如果选择直接分析，进行大模型分析
            if direct_llm_analysis and processing_rules:
                st.write("---")
                st.write("**🤖 开始大模型分析**")
                
                try:
                    # 准备分析数据
                    analysis_data = []
                    for session_key, session_data in organized_data.get('sessions', {}).items():
                        for post in session_data.get('posts', []):
                            analysis_data.append({
                                'title': post.get('title', ''),
                                'content': post.get('content', ''),
                                'author': post.get('author', ''),
                                'score': post.get('score', 0),
                                'subreddit': post.get('subreddit', ''),
                                'created_utc': post.get('created_utc', ''),
                                'num_comments': post.get('num_comments', 0)
                            })
                    
                    if analysis_data:
                        # 分批处理
                        batch_size = st.session_state.get('package_batch_size', 10)
                        total_batches = (len(analysis_data) + batch_size - 1) // batch_size
                        
                        st.write(f"📊 将处理 {len(analysis_data)} 条数据，分为 {total_batches} 批")
                        
                        for i in range(0, len(analysis_data), batch_size):
                            batch_data = analysis_data[i:i + batch_size]
                            batch_num = i // batch_size + 1
                            
                            st.write(f"🔄 处理第 {batch_num}/{total_batches} 批...")
                            
                            # 使用选定的规则进行分析
                            if st.session_state.analyzer:
                                result = st.session_state.analyzer.analyze_posts_batch(
                                    batch_data,
                                    provider=st.session_state.get('package_ai_provider', 'openai'),
                                    analysis_type=processing_rules[selected_rule]['analysis_type']
                                )
                                
                                if 'error' not in result:
                                    # 保存分析结果
                                    st.session_state.db.save_analysis_result(
                                        analysis_type=processing_rules[selected_rule]['analysis_type'],
                                        result=result,
                                        posts_count=len(batch_data)
                                    )
                                    st.success(f"✅ 第 {batch_num} 批分析完成")
                                else:
                                    st.error(f"❌ 第 {batch_num} 批分析失败: {result['error']}")
                            else:
                                st.error("❌ 大模型分析器未初始化")
                                break
                        
                        st.success("🎉 所有批次分析完成！")
                    else:
                        st.warning("⚠️ 没有数据可供分析")
                        
                except Exception as e:
                    st.error(f"❌ 大模型分析失败: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
            
            # 显示数据包预览
            with st.expander("👀 数据包预览"):
                if output_format.lower() == "json":
                    st.json(organized_data)
                else:
                    # 显示前1000个字符
                    preview = package_content[:1000]
                    if len(package_content) > 1000:
                        preview += "\n\n... (数据包内容较长，已截断)"
                    st.text(preview)
            
        except Exception as e:
            st.error(f"❌ 数据整理和打包失败: {str(e)}")
            st.exception(e)

def show_llm_processing_rules():
    """显示大模型处理规则设定功能"""
    st.subheader("🤖 大模型处理规则设定")
    st.write("设定大模型处理数据的规则和提示词模板")
    
    # 初始化处理规则
    if 'llm_processing_rules' not in st.session_state:
        st.session_state.llm_processing_rules = {
            "综合分析": {
                "analysis_type": "comprehensive",
                "description": "综合分析，包含主题、情感、洞察和结构化分析",
                "prompt_template": """你是一位专业的社交媒体数据分析师。你的任务是深度分析Reddit社区中关于指定主题的讨论。

请根据下面提供的原始Reddit帖子和评论数据，完成以下四个部分的结构化分析和总结。

### 原始数据：{text}

### **任务一：情感与立场分析 (Sentiment & Stance)**
1. **整体情绪：** 总结这段数据流中用户讨论的整体情绪倾向
2. **核心情感识别：** 识别讨论中最突出的三种情感
3. **争议点（如果存在）：** 明确指出争议的核心焦点

### **任务二：主题与痛点提取 (Topic & Pain Points)**
1. **主要讨论主题：** 归纳为2到3个最集中的讨论主题
2. **提取核心痛点：** 总结用户最常见、最迫切的问题或挑战

### **任务三：实用建议和技巧归纳 (Actionable Advice)**
1. **Top 5 实用建议：** 提取五条最具操作性的建议
2. **工具/品牌提及：** 提取被提及最频繁的工具、产品或品牌

### **任务四：结构化摘要与总结 (Structured Output)**
以JSON格式输出最关键的洞察"""
            },
            "情感分析": {
                "analysis_type": "sentiment",
                "description": "分析文本的情感倾向和情绪状态",
                "prompt_template": "请分析以下文本的情感倾向：{text}"
            },
            "主题分析": {
                "analysis_type": "topic",
                "description": "提取文本的主要话题和关键词",
                "prompt_template": "请提取以下文本的主要话题：{text}"
            },
            "质量评估": {
                "analysis_type": "quality",
                "description": "评估内容的质量和价值",
                "prompt_template": "请评估以下内容的质量：{text}"
            }
        }
    
    # 显示现有规则
    st.write("**现有处理规则:**")
    
    for rule_name, rule_config in st.session_state.llm_processing_rules.items():
        with st.expander(f"📋 {rule_name} - {rule_config['description']}"):
            col_rule1, col_rule2 = st.columns([3, 1])
            
            with col_rule1:
                st.write(f"**分析类型:** {rule_config['analysis_type']}")
                st.write(f"**描述:** {rule_config['description']}")
                st.write("**提示词模板:**")
                st.code(rule_config['prompt_template'][:200] + "..." if len(rule_config['prompt_template']) > 200 else rule_config['prompt_template'])
            
            with col_rule2:
                if st.button("✏️ 编辑", key=create_unique_key("edit_rule", rule_name)):
                    toggle_state(f"editing_rule_{rule_name}", True)
                
                if st.button("🗑️ 删除", key=create_unique_key("delete_rule", rule_name), type="secondary"):
                    if rule_name in st.session_state.llm_processing_rules:
                        del st.session_state.llm_processing_rules[rule_name]
                        st.rerun()
    
    # 编辑规则
    for rule_name in st.session_state.llm_processing_rules.keys():
        if st.session_state.get(f"editing_rule_{rule_name}", False):
            show_rule_editor(rule_name)
    
    # 创建新规则
    st.write("---")
    st.write("**创建新处理规则**")
    
    if st.button("➕ 创建新规则"):
        toggle_state("creating_new_rule", True)
    
    if st.session_state.get("creating_new_rule", False):
        show_rule_editor("new")

def show_rule_editor(rule_name):
    """显示规则编辑器"""
    if rule_name == "new":
        st.write("**创建新规则**")
        new_rule_name = st.text_input("规则名称", key="new_rule_name")
        new_analysis_type = st.selectbox("分析类型", ["comprehensive", "sentiment", "topic", "quality"], key="new_analysis_type")
        new_description = st.text_input("规则描述", key="new_description")
        new_prompt = st.text_area("提示词模板", height=300, key="new_prompt", 
                                 value="请分析以下文本：{text}")
        
        col_save, col_cancel = st.columns(2)
        
        with col_save:
            if st.button("💾 保存规则", key="save_new_rule"):
                if new_rule_name and new_prompt:
                    st.session_state.llm_processing_rules[new_rule_name] = {
                        "analysis_type": new_analysis_type,
                        "description": new_description,
                        "prompt_template": new_prompt
                    }
                    st.session_state["creating_new_rule"] = False
                    st.success("✅ 新规则已创建")
                    st.rerun()
                else:
                    st.error("❌ 请填写规则名称和提示词模板")
        
        with col_cancel:
            if st.button("❌ 取消", key="cancel_new_rule"):
                toggle_state("creating_new_rule", False)
    else:
        st.write(f"**编辑规则: {rule_name}**")
        
        rule_config = st.session_state.llm_processing_rules[rule_name]
        
        edited_name = st.text_input("规则名称", value=rule_name, key=create_unique_key("edit_name", rule_name))
        edited_analysis_type = st.selectbox("分析类型", ["comprehensive", "sentiment", "topic", "quality"], 
                                          index=["comprehensive", "sentiment", "topic", "quality"].index(rule_config['analysis_type']),
                                          key=create_unique_key("edit_type", rule_name))
        edited_description = st.text_input("规则描述", value=rule_config['description'], key=create_unique_key("edit_desc", rule_name))
        edited_prompt = st.text_area("提示词模板", value=rule_config['prompt_template'], height=300, key=create_unique_key("edit_prompt", rule_name))
        
        col_save, col_cancel = st.columns(2)
        
        with col_save:
            if st.button("💾 保存修改", key=create_unique_key("save_edit", rule_name)):
                if edited_name and edited_prompt:
                    # 如果名称改变了，先删除旧规则
                    if edited_name != rule_name:
                        del st.session_state.llm_processing_rules[rule_name]
                    
                    # 添加新规则
                    st.session_state.llm_processing_rules[edited_name] = {
                        "analysis_type": edited_analysis_type,
                        "description": edited_description,
                        "prompt_template": edited_prompt
                    }
                    
                    st.session_state[f"editing_rule_{rule_name}"] = False
                    st.success("✅ 规则已更新")
                    st.rerun()
                else:
                    st.error("❌ 请填写规则名称和提示词模板")
        
        with col_cancel:
            if st.button("❌ 取消", key=create_unique_key("cancel_edit", rule_name)):
                toggle_state(f"editing_rule_{rule_name}", False)

def show_manual_processing():
    """显示手动数据处理功能"""
    st.subheader("🔄 手动数据处理")
    st.write("手动选择数据并传递给大模型进行处理")
    
    # 数据选择
    st.write("**选择要处理的数据**")
    
    col_select1, col_select2 = st.columns(2)
    
    with col_select1:
        # 按分组选择
        grouped_data = get_cached_posts_grouped(st.session_state.db)
        if grouped_data:
            selected_groups = st.multiselect(
                "选择数据分组",
                options=list(grouped_data.keys()),
                help="选择要处理的数据分组"
            )
        else:
            st.info("暂无数据分组")
            selected_groups = []
    
    with col_select2:
        # 按子版块选择
        available_subreddits = get_cached_subreddit_list(st.session_state.db)
        selected_subreddits = st.multiselect(
            "选择子版块",
            options=available_subreddits,
            help="选择要处理的子版块",
            key="manual_selected_subreddits"
        )
    
    # 处理规则选择
    st.write("**🤖 大模型处理规则选择**")
    
    processing_rules = st.session_state.get('llm_processing_rules', {})
    if not processing_rules:
        st.warning("⚠️ 请先在侧边栏选择 '🤖 大模型处理规则' 来设置处理规则")
        st.info("💡 设置好规则后，您就可以在这里选择规则来处理数据了")
        return
    
    # 显示可用的规则
    st.info(f"📋 当前有 {len(processing_rules)} 个可用的处理规则")
    
    col_rule1, col_rule2 = st.columns(2)
    
    with col_rule1:
        selected_rule = st.selectbox(
            "选择处理规则",
            list(processing_rules.keys()),
            key="manual_selected_rule",
            help="选择要使用的处理规则"
        )
        
        ai_provider = st.selectbox(
            "AI提供商",
            ["openai", "anthropic", "deepseek"],
            key="manual_ai_provider",
            help="选择AI提供商"
        )
    
    with col_rule2:
        batch_size = st.number_input("批处理大小", min_value=1, max_value=200, value=25, key="manual_batch_size", help="每批处理的帖子数量")
        use_custom_prompt = st.checkbox("使用自定义提示词", key="manual_use_custom_prompt", help="是否使用自定义提示词")
    
    if use_custom_prompt:
        custom_prompt = st.text_area(
            "自定义提示词",
            value=processing_rules[selected_rule]['prompt_template'],
            height=200,
            key="manual_custom_prompt",
            help="自定义提示词模板，使用{text}作为数据占位符"
        )
    else:
        custom_prompt = processing_rules[selected_rule]['prompt_template']
    
    # 显示选中的规则信息
    st.info(f"📋 已选择规则: **{selected_rule}** | 分析类型: **{processing_rules[selected_rule]['analysis_type']}** | AI提供商: **{ai_provider}**")
    
    # 开始处理
    if st.button("🚀 开始手动处理", type="primary"):
        try:
            # 收集要处理的数据
            posts_to_process = []
            
            # 从选中的分组收集数据
            for group_key in selected_groups:
                if group_key in grouped_data:
                    group_info = grouped_data[group_key]
                    for post in group_info['posts']:
                        # 只处理未分析的帖子
                        if not post.analyzed:
                            posts_to_process.append({
                                'id': post.id,
                                'title': post.title,
                                'content': post.selftext or "",
                                'author': post.author,
                                'score': post.score,
                                'subreddit': post.subreddit,
                                'group': group_key
                            })
            
            # 从选中的子版块收集数据
            if selected_subreddits:
                session = st.session_state.db.get_session()
                for subreddit in selected_subreddits:
                    # 只获取未分析的帖子
                    posts = session.query(st.session_state.db.RedditPost).filter(
                        st.session_state.db.RedditPost.subreddit == subreddit,
                        st.session_state.db.RedditPost.analyzed == False
                    ).limit(batch_size).all()
                    
                    for post in posts:
                        # 避免重复
                        if not any(p['id'] == post.id for p in posts_to_process):
                            posts_to_process.append({
                                'id': post.id,
                                'title': post.title,
                                'content': post.selftext or "",
                                'author': post.author,
                                'score': post.score,
                                'subreddit': post.subreddit,
                                'group': f"subreddit_{subreddit}"
                            })
                session.close()
            
            if not posts_to_process:
                st.warning("没有选择要处理的数据")
                return
            
            # 限制处理数量
            posts_to_process = posts_to_process[:batch_size]
            
            # 显示处理进度
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 执行处理
            results = []
            for i, post_data in enumerate(posts_to_process):
                status_text.text(f"处理帖子: {post_data['title'][:50]}...")
                progress_bar.progress((i + 1) / len(posts_to_process))
                
                # 准备文本内容
                text_content = f"标题: {post_data['title']}\n内容: {post_data['content']}"
                
                # 执行分析
                if processing_rules[selected_rule]['analysis_type'] == 'comprehensive':
                    result = st.session_state.analyzer.analyze_comprehensive(
                        text_content, ai_provider, custom_prompt
                    )
                else:
                    result = st.session_state.analyzer.analyze_posts_batch(
                        [post_data], ai_provider, processing_rules[selected_rule]['analysis_type']
                    )
                
                if "error" not in result:
                    # 保存结果
                    st.session_state.db.save_analysis_result(
                        post_data['id'], "post", processing_rules[selected_rule]['analysis_type'],
                        str(result), ai_provider
                    )
                    results.append({
                        'post': post_data,
                        'result': result
                    })
                
                time.sleep(1)  # 避免API限制
            
            progress_bar.progress(100)
            status_text.text("✅ 处理完成!")
            
            st.success(f"🎉 手动处理完成！共处理 {len(results)} 个帖子")
            
            # 显示处理结果
            st.write("**📊 处理结果**")
            for i, item in enumerate(results[:5]):  # 只显示前5个结果
                with st.expander(f"结果 {i+1}: {item['post']['title'][:50]}..."):
                    st.json(item['result'])
            
            if len(results) > 5:
                st.info(f"还有 {len(results) - 5} 个结果未显示...")
            
        except Exception as e:
            st.error(f"❌ 手动处理失败: {str(e)}")
            st.exception(e)

def show_results_display():
    """显示结果展示功能"""
    st.subheader("📊 结果展示")
    
    # 数据导出区域
    st.write("---")
    st.subheader("📥 数据导出")
    
    # 获取数据统计信息
    try:
        stats = get_cached_analysis_statistics(st.session_state.db)
        total_posts = stats.get('total_posts', 0)
        total_results = stats.get('total_analysis', 0)
        
        # 获取数据包数量
        import os
        import glob
        output_dir = "output"
        package_count = 0
        if os.path.exists(output_dir):
            package_files = glob.glob(os.path.join(output_dir, "reddit_data_*.json"))
            package_count = len(package_files)
    except:
        total_posts = 0
        total_results = 0
        package_count = 0
    
    # 数据类型选择（多选列表）
    st.write("**选择要导出的数据类型:**")
    
    data_types = []
    if total_posts > 0:
        data_types.append(f"原始数据 ({total_posts}条)")
    if total_results > 0:
        data_types.append(f"分析结果 ({total_results}条)")
    if package_count > 0:
        data_types.append(f"数据包 ({package_count}个)")
    
    if not data_types:
        st.info("暂无数据可供导出")
        return
    
    selected_data_types = st.multiselect(
        "数据类型",
        options=data_types,
        help="选择要导出的数据类型，可多选"
    )
    
    if not selected_data_types:
        st.warning("请至少选择一种数据类型")
        return
    
    # 筛选条件
    col_filter1, col_filter2, col_format = st.columns(3)
    
    with col_filter1:
        # 日期范围选择
        date_range = st.date_input(
            "选择日期范围",
            value=(datetime.now() - timedelta(days=30), datetime.now()),
            help="选择要导出的数据日期范围"
        )
    
    with col_filter2:
        # 子版块选择
        available_subreddits = get_cached_subreddit_list(st.session_state.db)
        selected_subreddits = st.multiselect(
            "选择子版块",
            options=available_subreddits,
            help="选择要导出的子版块，留空表示全部"
        )
    
    with col_format:
        # 格式选择
        export_format = st.selectbox(
            "导出格式",
            ["JSON", "CSV", "Excel"],
            help="选择导出文件的格式"
        )
    
    # 导出模式选择
    st.write("**导出模式:**")
    col_mode1, col_mode2 = st.columns(2)
    
    with col_mode1:
        # 简化为只有全量下载模式
        export_mode = "全量下载"
        st.info("📥 使用全量下载模式，直接导出所有数据")
    
    # 全量下载模式：显示导出按钮
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("📥 批量导出数据", type="primary"):
            try:
                export_data_batch(selected_data_types, date_range, selected_subreddits, export_format, export_mode, None)
            except Exception as e:
                st.error(f"导出失败: {str(e)}")
    
    with col_btn2:
        # Excel导出按钮 - 只在大模型分析数据后显示
        if st.button("📊 生成Excel分析报告", type="secondary", help="生成包含所有分析结果的Excel报告"):
            try:
                export_excel_report(date_range, selected_subreddits)
            except Exception as e:
                st.error(f"Excel报告生成失败: {str(e)}")

def export_raw_data(date_range, selected_subreddits, export_format):
    """导出原始数据"""
    st.write("**正在导出原始数据...**")
    
    # 构建查询条件
    session = st.session_state.db.get_session()
    try:
        query = session.query(st.session_state.db.RedditPost)
        
        # 日期筛选
        if date_range[0]:
            query = query.filter(st.session_state.db.RedditPost.scraped_at >= date_range[0])
        if date_range[1]:
            query = query.filter(st.session_state.db.RedditPost.scraped_at <= date_range[1])
        
        # 子版块筛选
        if selected_subreddits:
            query = query.filter(st.session_state.db.RedditPost.subreddit.in_(selected_subreddits))
        
        posts = query.all()
        
        if not posts:
            st.warning("没有找到符合条件的数据")
            return
        
        # 准备数据
        data = []
        for post in posts:
            data.append({
                'id': post.id,
                'title': post.title,
                'author': post.author,
                'score': post.score,
                'num_comments': post.num_comments,
                'created_utc': post.created_utc.isoformat() if post.created_utc else None,
                'subreddit': post.subreddit,
                'selftext': post.selftext,
                'url': post.url,
                'scraped_at': post.scraped_at.isoformat() if post.scraped_at else None
            })
        
        # 生成文件内容
        if export_format == "JSON":
            import json
            file_content = json.dumps(data, ensure_ascii=False, indent=2)
            file_extension = "json"
            mime_type = "application/json"
        else:  # CSV
            import pandas as pd
            df = pd.DataFrame(data)
            file_content = df.to_csv(index=False, encoding='utf-8-sig')
            file_extension = "csv"
            mime_type = "text/csv"
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reddit_raw_data_{timestamp}.{file_extension}"
        
        # 提供下载
        st.download_button(
            label=f"📥 下载原始数据 ({len(data)} 条记录)",
            data=file_content,
            file_name=filename,
            mime=mime_type
        )
        
        st.success(f"✅ 已准备 {len(data)} 条原始数据供下载")
        
    finally:
        session.close()

def export_analysis_results(date_range, selected_subreddits, export_format):
    """导出分析结果 - 借鉴Excel导出逻辑"""
    st.write("**正在导出分析结果...**")
    
    try:
        # 借鉴Excel导出逻辑：直接使用get_analysis_results()获取所有数据
        results = st.session_state.db.get_analysis_results()
        
        if not results:
            st.warning("没有找到分析结果数据")
            return
        
        # 准备数据
        data = []
        session = st.session_state.db.get_session()
        try:
            for result in results:
                # 获取关联的帖子信息
                post = session.query(st.session_state.db.RedditPost).filter(
                    st.session_state.db.RedditPost.id == result.content_id
                ).first()
                
                # 日期筛选
                if date_range[0] and result.created_at and result.created_at.date() < date_range[0]:
                    continue
                if date_range[1] and result.created_at and result.created_at.date() > date_range[1]:
                    continue
                
                # 子版块筛选
                if selected_subreddits and post and post.subreddit not in selected_subreddits:
                    continue
                
                data.append({
                    'analysis_id': result.id,
                    'content_id': result.content_id,
                    'content_type': result.content_type,
                    'analysis_type': result.analysis_type,
                    'model_used': result.model_used,
                    'created_at': result.created_at.isoformat() if result.created_at else None,
                    'result': result.result,
                    'post_title': post.title if post else None,
                    'post_subreddit': post.subreddit if post else None,
                    'post_author': post.author if post else None
                })
        finally:
            session.close()
        
        if not data:
            st.warning("没有找到符合条件的数据")
            return
        
        # 生成文件内容
        if export_format == "JSON":
            import json
            file_content = json.dumps(data, ensure_ascii=False, indent=2)
            file_extension = "json"
            mime_type = "application/json"
        else:  # CSV
            import pandas as pd
            df = pd.DataFrame(data)
            file_content = df.to_csv(index=False, encoding='utf-8-sig')
            file_extension = "csv"
            mime_type = "text/csv"
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_results_{timestamp}.{file_extension}"
        
        # 提供下载
        st.download_button(
            label=f"📥 下载分析结果 ({len(data)} 条记录)",
            data=file_content,
            file_name=filename,
            mime=mime_type
        )
        
        st.success(f"✅ 已准备 {len(data)} 条分析结果供下载")
        
    finally:
        session.close()

def export_data_packages(date_range, selected_subreddits, export_format):
    """导出数据包"""
    st.write("**正在导出数据包...**")
    
    # 获取output目录下的数据包文件
    import os
    import glob
    
    output_dir = "output"
    if not os.path.exists(output_dir):
        st.warning("没有找到数据包文件")
        return
    
    # 查找数据包文件
    pattern = os.path.join(output_dir, "reddit_data_*.json")
    package_files = glob.glob(pattern)
    
    if not package_files:
        st.warning("没有找到数据包文件")
        return
    
    # 显示可用的数据包文件
    st.write("**可用的数据包文件:**")
    for i, file_path in enumerate(package_files):
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / 1024  # KB
        st.write(f"{i+1}. {file_name} ({file_size:.1f} KB)")
    
    # 提供批量下载
    if st.button("📦 打包下载所有数据包"):
        import zipfile
        import io
        
        # 创建ZIP文件
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in package_files:
                file_name = os.path.basename(file_path)
                zip_file.write(file_path, file_name)
        
        zip_buffer.seek(0)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"reddit_data_packages_{timestamp}.zip"
        
        # 提供下载
        st.download_button(
            label=f"📥 下载所有数据包 ({len(package_files)} 个文件)",
            data=zip_buffer.getvalue(),
            file_name=zip_filename,
            mime="application/zip"
        )
        
        st.success(f"✅ 已准备 {len(package_files)} 个数据包供下载")

def export_data_batch(selected_data_types, date_range, selected_subreddits, export_format, export_mode, preview_limit=None):
    """批量导出数据"""
    st.write("**正在准备批量导出...**")
    
    # 解析选中的数据类型
    data_to_export = []
    for data_type in selected_data_types:
        if "原始数据" in data_type:
            data_to_export.append("raw_data")
        elif "分析结果" in data_type:
            data_to_export.append("analysis_results")
        elif "数据包" in data_type:
            data_to_export.append("data_packages")
    
    if export_mode == "全量下载":
        # 全量下载模式
        export_all_data(data_to_export, date_range, selected_subreddits, export_format)
    else:
        # 预览选择模式 - 导出时使用全量数据
        preview_and_select_data(data_to_export, date_range, selected_subreddits, export_format, None)

def export_all_data(data_to_export, date_range, selected_subreddits, export_format):
    """全量导出所有选中的数据"""
    import zipfile
    import io
    
    # 如果是Excel格式，直接生成Excel报告
    if export_format == "Excel":
        export_excel_report(date_range, selected_subreddits)
        return
    
    zip_buffer = io.BytesIO()
    file_count = 0
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for data_type in data_to_export:
            if data_type == "raw_data":
                file_content, filename = get_raw_data_content(date_range, selected_subreddits, export_format)
                if file_content:
                    zip_file.writestr(filename, file_content)
                    file_count += 1
            
            elif data_type == "analysis_results":
                file_content, filename = get_analysis_results_content(date_range, selected_subreddits, export_format)
                if file_content:
                    zip_file.writestr(filename, file_content)
                    file_count += 1
            
            elif data_type == "data_packages":
                # 数据包直接复制文件
                import os
                import glob
                output_dir = "output"
                if os.path.exists(output_dir):
                    package_files = glob.glob(os.path.join(output_dir, "reddit_data_*.json"))
                    for file_path in package_files:
                        file_name = os.path.basename(file_path)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            zip_file.writestr(file_name, f.read())
                        file_count += 1
    
    if file_count > 0:
        zip_buffer.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"reddit_data_export_{timestamp}.zip"
        
        st.download_button(
            label=f"📥 下载批量导出文件 ({file_count} 个文件)",
            data=zip_buffer.getvalue(),
            file_name=zip_filename,
            mime="application/zip"
        )
        
        st.success(f"✅ 已准备 {file_count} 个文件供下载")
    else:
        st.warning("没有找到符合条件的数据")

def preview_and_select_data(data_to_export, date_range, selected_subreddits, export_format, preview_limit):
    """预览并选择数据"""
    st.write("**数据预览和选择**")
    
    for data_type in data_to_export:
        if data_type == "raw_data":
            preview_raw_data_with_pagination(date_range, selected_subreddits, export_format, preview_limit)
        elif data_type == "analysis_results":
            preview_analysis_results_with_pagination(date_range, selected_subreddits, export_format, preview_limit)
        elif data_type == "data_packages":
            preview_data_packages()

def preview_raw_data_with_pagination(date_range, selected_subreddits, export_format, preview_limit):
    """带分页和筛选的原始数据预览"""
    st.write("**原始数据预览**")
    
    # 初始化分页状态
    if 'raw_data_page' not in st.session_state:
        st.session_state.raw_data_page = 0
    if 'raw_data_selected' not in st.session_state:
        st.session_state.raw_data_selected = []
    
    # 创建筛选条件的唯一标识
    filter_key = f"{date_range}_{selected_subreddits}_{preview_limit}"
    if 'raw_data_filter_key' not in st.session_state:
        st.session_state.raw_data_filter_key = filter_key
    elif st.session_state.raw_data_filter_key != filter_key:
        # 筛选条件改变，重置分页状态
        st.session_state.raw_data_page = 0
        st.session_state.raw_data_filter_key = filter_key
    
    # 高级筛选条件
    st.write("**高级筛选条件**")
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        keyword_filter = st.text_input("关键词筛选", help="在标题或内容中搜索关键词", key="raw_keyword_filter")
        min_score = st.number_input("最小分数", min_value=0, value=0, help="筛选分数大于等于此值的帖子", key="raw_min_score")
    
    with col_filter2:
        author_filter = st.text_input("作者筛选", help="筛选特定作者发布的帖子", key="raw_author_filter")
        max_score = st.number_input("最大分数", min_value=0, value=10000, help="筛选分数小于等于此值的帖子", key="raw_max_score")
    
    with col_filter3:
        min_comments = st.number_input("最小评论数", min_value=0, value=0, help="筛选评论数大于等于此值的帖子", key="raw_min_comments")
        sort_by = st.selectbox("排序方式", ["最新", "最旧", "分数最高", "分数最低", "评论最多"], help="选择数据排序方式", key="raw_sort_by")
    
    # 应用筛选按钮
    col_apply1, col_apply2, col_apply3 = st.columns([1, 1, 2])
    with col_apply1:
        if st.button("🔍 应用筛选", key="apply_raw_filter"):
            # 应用筛选条件，重置分页状态
            st.session_state.raw_data_page = 0
            st.session_state.raw_data_advanced_filter_key = f"{keyword_filter}_{author_filter}_{min_score}_{max_score}_{min_comments}_{sort_by}"
            st.rerun()
    
    with col_apply2:
        if st.button("🔄 重置筛选", key="reset_raw_filter"):
            # 重置筛选条件
            st.session_state.raw_data_page = 0
            st.session_state.raw_data_advanced_filter_key = ""
            st.rerun()
    
    # 获取当前应用的筛选条件
    current_advanced_filter = st.session_state.get('raw_data_advanced_filter_key', '')
    if current_advanced_filter:
        st.info(f"当前筛选条件: {current_advanced_filter}")
    
    session = st.session_state.db.get_session()
    try:
        query = session.query(st.session_state.db.RedditPost)
        
        # 基础筛选条件
        if date_range[0]:
            query = query.filter(st.session_state.db.RedditPost.scraped_at >= date_range[0])
        if date_range[1]:
            query = query.filter(st.session_state.db.RedditPost.scraped_at <= date_range[1])
        if selected_subreddits:
            query = query.filter(st.session_state.db.RedditPost.subreddit.in_(selected_subreddits))
        
        # 应用高级筛选条件（使用已保存的筛选条件）
        if current_advanced_filter:
            # 解析已保存的筛选条件
            filter_parts = current_advanced_filter.split('_')
            if len(filter_parts) >= 6:
                saved_keyword = filter_parts[0] if filter_parts[0] else ""
                saved_author = filter_parts[1] if filter_parts[1] else ""
                saved_min_score = int(filter_parts[2]) if filter_parts[2] else 0
                saved_max_score = int(filter_parts[3]) if filter_parts[3] else 10000
                saved_min_comments = int(filter_parts[4]) if filter_parts[4] else 0
                saved_sort_by = filter_parts[5] if filter_parts[5] else "最新"
                
                # 应用筛选条件
                if saved_keyword:
                    query = query.filter(
                        (st.session_state.db.RedditPost.title.contains(saved_keyword)) |
                        (st.session_state.db.RedditPost.selftext.contains(saved_keyword))
                    )
                if saved_author:
                    query = query.filter(st.session_state.db.RedditPost.author.contains(saved_author))
                if saved_min_score > 0:
                    query = query.filter(st.session_state.db.RedditPost.score >= saved_min_score)
                if saved_max_score < 10000:
                    query = query.filter(st.session_state.db.RedditPost.score <= saved_max_score)
                if saved_min_comments > 0:
                    query = query.filter(st.session_state.db.RedditPost.num_comments >= saved_min_comments)
                
                # 应用排序
                if saved_sort_by == "最新":
                    query = query.order_by(st.session_state.db.RedditPost.scraped_at.desc())
                elif saved_sort_by == "最旧":
                    query = query.order_by(st.session_state.db.RedditPost.scraped_at.asc())
                elif saved_sort_by == "分数最高":
                    query = query.order_by(st.session_state.db.RedditPost.score.desc())
                elif saved_sort_by == "分数最低":
                    query = query.order_by(st.session_state.db.RedditPost.score.asc())
                elif saved_sort_by == "评论最多":
                    query = query.order_by(st.session_state.db.RedditPost.num_comments.desc())
        
        total_count = query.count()
        
        if total_count == 0:
            st.warning("没有找到符合条件的数据")
            return
        
        # 分页计算
        total_pages = (total_count + preview_limit - 1) // preview_limit
        current_page = st.session_state.raw_data_page
        
        # 分页控制
        col_page1, col_page2, col_page3 = st.columns([1, 2, 1])
        
        with col_page1:
            if st.button("⬅️ 上一页", disabled=current_page == 0):
                st.session_state.raw_data_page = max(0, current_page - 1)
                st.rerun()
        
        with col_page2:
            st.write(f"**第 {current_page + 1} 页 / 共 {total_pages} 页** | 总计 {total_count} 条数据")
        
        with col_page3:
            if st.button("下一页 ➡️", disabled=current_page >= total_pages - 1):
                st.session_state.raw_data_page = min(total_pages - 1, current_page + 1)
                st.rerun()
        
        # 获取当前页数据
        offset = current_page * preview_limit
        posts = query.offset(offset).limit(preview_limit).all()
        
        # 全选功能
        col_select1, col_select2 = st.columns([1, 1])
        with col_select1:
            if st.button(f"✅ 全选当前页 ({len(posts)} 条)"):
                for post in posts:
                    if post.id not in st.session_state.raw_data_selected:
                        st.session_state.raw_data_selected.append(post.id)
                st.rerun()
        
        with col_select2:
            if st.button(f"✅ 全选所有数据 ({total_count} 条)"):
                all_posts = query.all()
                st.session_state.raw_data_selected = [post.id for post in all_posts]
                st.rerun()
        
        # 显示当前页数据
        if posts:
            for i, post in enumerate(posts):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{post.title[:80]}...** | r/{post.subreddit} | 分数: {post.score} | 评论: {post.num_comments}")
                    if post.author:
                        st.write(f"作者: u/{post.author} | 时间: {post.scraped_at.strftime('%Y-%m-%d %H:%M') if post.scraped_at else '未知'}")
                with col2:
                    is_selected = post.id in st.session_state.raw_data_selected
                    if st.checkbox("选择", value=is_selected, key=f"raw_post_{post.id}"):
                        if post.id not in st.session_state.raw_data_selected:
                            st.session_state.raw_data_selected.append(post.id)
                    else:
                        if post.id in st.session_state.raw_data_selected:
                            st.session_state.raw_data_selected.remove(post.id)
        
        # 显示已选择的数据统计
        if st.session_state.raw_data_selected:
            st.info(f"已选择 {len(st.session_state.raw_data_selected)} 条数据")
            
            if st.button(f"📥 下载选中的 {len(st.session_state.raw_data_selected)} 条原始数据", key="download_selected_raw"):
                # 获取选中的帖子数据
                selected_posts = session.query(st.session_state.db.RedditPost).filter(
                    st.session_state.db.RedditPost.id.in_(st.session_state.raw_data_selected)
                ).all()
                export_selected_posts(selected_posts, export_format)
        
    finally:
        session.close()

def preview_raw_data(date_range, selected_subreddits, export_format, preview_limit):
    """预览原始数据"""
    st.write("**原始数据预览**")
    
    session = st.session_state.db.get_session()
    try:
        query = session.query(st.session_state.db.RedditPost)
        
        # 应用筛选条件
        if date_range[0]:
            query = query.filter(st.session_state.db.RedditPost.scraped_at >= date_range[0])
        if date_range[1]:
            query = query.filter(st.session_state.db.RedditPost.scraped_at <= date_range[1])
        if selected_subreddits:
            query = query.filter(st.session_state.db.RedditPost.subreddit.in_(selected_subreddits))
        
        total_count = query.count()
        # 如果是导出模式，不限制数量；如果是预览模式，限制数量
        if preview_limit is None:  # 导出模式，获取所有数据
            posts = query.all()
        else:  # 预览模式，限制数量
            posts = query.limit(preview_limit).all()
        
        st.info(f"找到 {total_count} 条原始数据，显示前 {len(posts)} 条")
        
        if posts:
            # 创建选择框
            selected_posts = []
            for i, post in enumerate(posts):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{post.title[:80]}...** | r/{post.subreddit} | 分数: {post.score}")
                with col2:
                    if st.checkbox("选择", key=f"raw_post_{post.id}"):
                        selected_posts.append(post)
            
            if selected_posts:
                if st.button(f"📥 下载选中的 {len(selected_posts)} 条原始数据", key="download_selected_raw"):
                    export_selected_posts(selected_posts, export_format)
            
            if total_count > preview_limit:
                st.info(f"还有 {total_count - preview_limit} 条数据未显示，如需查看更多请调整预览数量限制")
        
    finally:
        session.close()

def preview_analysis_results_with_pagination(date_range, selected_subreddits, export_format, preview_limit):
    """带分页和筛选的分析结果预览"""
    st.write("**分析结果预览**")
    
    # 初始化分页状态
    if 'results_page' not in st.session_state:
        st.session_state.results_page = 0
    if 'results_selected' not in st.session_state:
        st.session_state.results_selected = []
    
    # 创建筛选条件的唯一标识
    filter_key = f"{date_range}_{selected_subreddits}_{preview_limit}"
    if 'results_filter_key' not in st.session_state:
        st.session_state.results_filter_key = filter_key
    elif st.session_state.results_filter_key != filter_key:
        # 筛选条件改变，重置分页状态
        st.session_state.results_page = 0
        st.session_state.results_filter_key = filter_key
    
    # 高级筛选条件
    st.write("**高级筛选条件**")
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        analysis_type_filter = st.multiselect(
            "分析类型筛选",
            ["comprehensive", "sentiment", "topic", "quality"],
            help="选择要显示的分析类型",
            key="results_analysis_type_filter"
        )
        model_filter = st.selectbox(
            "模型筛选",
            ["全部", "openai", "anthropic", "deepseek"],
            help="选择使用的AI模型",
            key="results_model_filter"
        )
    
    with col_filter2:
        keyword_filter = st.text_input("关键词筛选", help="在帖子标题中搜索关键词", key="results_keyword_filter")
        sort_by = st.selectbox("排序方式", ["最新", "最旧", "分析类型"], help="选择数据排序方式", key="results_sort_by")
    
    with col_filter3:
        # 这里可以添加更多筛选条件
        pass
    
    # 应用筛选按钮
    col_apply1, col_apply2, col_apply3 = st.columns([1, 1, 2])
    with col_apply1:
        if st.button("🔍 应用筛选", key="apply_results_filter"):
            # 应用筛选条件，重置分页状态
            st.session_state.results_page = 0
            st.session_state.results_advanced_filter_key = f"{analysis_type_filter}_{model_filter}_{keyword_filter}_{sort_by}"
            st.rerun()
    
    with col_apply2:
        if st.button("🔄 重置筛选", key="reset_results_filter"):
            # 重置筛选条件
            st.session_state.results_page = 0
            st.session_state.results_advanced_filter_key = ""
            st.rerun()
    
    # 获取当前应用的筛选条件
    current_advanced_filter = st.session_state.get('results_advanced_filter_key', '')
    if current_advanced_filter:
        st.info(f"当前筛选条件: {current_advanced_filter}")
    
    session = st.session_state.db.get_session()
    try:
        query = session.query(st.session_state.db.AnalysisResult)
        
        # 基础筛选条件
        if date_range[0]:
            query = query.filter(st.session_state.db.AnalysisResult.created_at >= date_range[0])
        if date_range[1]:
            query = query.filter(st.session_state.db.AnalysisResult.created_at <= date_range[1])
        
        # 应用高级筛选条件（使用已保存的筛选条件）
        if current_advanced_filter:
            # 解析已保存的筛选条件
            filter_parts = current_advanced_filter.split('_')
            if len(filter_parts) >= 4:
                saved_analysis_types = filter_parts[0] if filter_parts[0] else ""
                saved_model = filter_parts[1] if filter_parts[1] else ""
                saved_keyword = filter_parts[2] if filter_parts[2] else ""
                saved_sort_by = filter_parts[3] if filter_parts[3] else "最新"
                
                # 应用筛选条件
                if saved_analysis_types:
                    analysis_types = saved_analysis_types.split(',') if ',' in saved_analysis_types else [saved_analysis_types]
                    query = query.filter(st.session_state.db.AnalysisResult.analysis_type.in_(analysis_types))
                if saved_model != "全部":
                    query = query.filter(st.session_state.db.AnalysisResult.model_used == saved_model)
                
                # 应用排序
                if saved_sort_by == "最新":
                    query = query.order_by(st.session_state.db.AnalysisResult.created_at.desc())
                elif saved_sort_by == "最旧":
                    query = query.order_by(st.session_state.db.AnalysisResult.created_at.asc())
                elif saved_sort_by == "分析类型":
                    query = query.order_by(st.session_state.db.AnalysisResult.analysis_type)
        
        results = query.all()
        total_count = len(results)
        
        # 应用子版块和关键词筛选
        filtered_results = []
        for result in results:
            post = session.query(st.session_state.db.RedditPost).filter(
                st.session_state.db.RedditPost.id == result.content_id
            ).first()
            
            # 子版块筛选
            if selected_subreddits and post and post.subreddit not in selected_subreddits:
                continue
            
            # 关键词筛选（使用已保存的筛选条件）
            if current_advanced_filter:
                filter_parts = current_advanced_filter.split('_')
                if len(filter_parts) >= 3:
                    saved_keyword = filter_parts[2] if filter_parts[2] else ""
                    if saved_keyword and post and saved_keyword.lower() not in post.title.lower():
                        continue
            
            filtered_results.append(result)
        
        total_count = len(filtered_results)
        
        if total_count == 0:
            st.warning("没有找到符合条件的数据")
            return
        
        # 分页计算
        if preview_limit is None:  # 导出模式，不分页
            total_pages = 1
            current_page = 0
        else:  # 预览模式，计算分页
            total_pages = (total_count + preview_limit - 1) // preview_limit
            current_page = st.session_state.results_page
        
        # 分页控制
        col_page1, col_page2, col_page3 = st.columns([1, 2, 1])
        
        with col_page1:
            if st.button("⬅️ 上一页", disabled=current_page == 0, key="results_prev"):
                st.session_state.results_page = max(0, current_page - 1)
                st.rerun()
        
        with col_page2:
            st.write(f"**第 {current_page + 1} 页 / 共 {total_pages} 页** | 总计 {total_count} 条数据")
        
        with col_page3:
            if st.button("下一页 ➡️", disabled=current_page >= total_pages - 1, key="results_next"):
                st.session_state.results_page = min(total_pages - 1, current_page + 1)
                st.rerun()
        
        # 获取当前页数据
        if preview_limit is None:  # 导出模式，获取所有数据
            page_results = filtered_results
        else:  # 预览模式，使用分页
            offset = current_page * preview_limit
            page_results = filtered_results[offset:offset + preview_limit]
        
        # 全选功能
        col_select1, col_select2 = st.columns([1, 1])
        with col_select1:
            if st.button(f"✅ 全选当前页 ({len(page_results)} 条)", key="select_page_results"):
                for result in page_results:
                    if result.id not in st.session_state.results_selected:
                        st.session_state.results_selected.append(result.id)
                st.rerun()
        
        with col_select2:
            if st.button(f"✅ 全选所有数据 ({total_count} 条)", key="select_all_results"):
                st.session_state.results_selected = [result.id for result in filtered_results]
                st.rerun()
        
        # 显示当前页数据
        if page_results:
            for i, result in enumerate(page_results):
                post = session.query(st.session_state.db.RedditPost).filter(
                    st.session_state.db.RedditPost.id == result.content_id
                ).first()
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    post_title = post.title[:60] + "..." if post and post.title else "未知帖子"
                    st.write(f"**{result.analysis_type}** | {post_title} | {result.model_used}")
                    if post:
                        st.write(f"r/{post.subreddit} | 分数: {post.score} | 时间: {result.created_at.strftime('%Y-%m-%d %H:%M') if result.created_at else '未知'}")
                with col2:
                    is_selected = result.id in st.session_state.results_selected
                    if st.checkbox("选择", value=is_selected, key=f"result_{result.id}"):
                        if result.id not in st.session_state.results_selected:
                            st.session_state.results_selected.append(result.id)
                    else:
                        if result.id in st.session_state.results_selected:
                            st.session_state.results_selected.remove(result.id)
        
        # 显示已选择的数据统计
        if st.session_state.results_selected:
            st.info(f"已选择 {len(st.session_state.results_selected)} 条分析结果")
            
            if st.button(f"📥 下载选中的 {len(st.session_state.results_selected)} 条分析结果", key="download_selected_results"):
                # 获取选中的分析结果数据
                selected_results = session.query(st.session_state.db.AnalysisResult).filter(
                    st.session_state.db.AnalysisResult.id.in_(st.session_state.results_selected)
                ).all()
                export_selected_results(selected_results, export_format)
        
    finally:
        session.close()

def preview_analysis_results(date_range, selected_subreddits, export_format, preview_limit):
    """预览分析结果"""
    st.write("**分析结果预览**")
    
    session = st.session_state.db.get_session()
    try:
        query = session.query(st.session_state.db.AnalysisResult)
        
        # 应用筛选条件
        if date_range[0]:
            query = query.filter(st.session_state.db.AnalysisResult.created_at >= date_range[0])
        if date_range[1]:
            query = query.filter(st.session_state.db.AnalysisResult.created_at <= date_range[1])
        
        # 如果是导出模式，不限制数量；如果是预览模式，限制数量
        if preview_limit is None:  # 导出模式，获取所有数据
            results = query.all()
        else:  # 预览模式，限制数量
            results = query.limit(preview_limit).all()
        total_count = query.count()
        
        st.info(f"找到 {total_count} 条分析结果，显示前 {len(results)} 条")
        
        if results:
            selected_results = []
            for i, result in enumerate(results):
                # 获取关联的帖子信息
                post = session.query(st.session_state.db.RedditPost).filter(
                    st.session_state.db.RedditPost.id == result.content_id
                ).first()
                
                # 子版块筛选
                if selected_subreddits and post and post.subreddit not in selected_subreddits:
                    continue
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    post_title = post.title[:60] + "..." if post and post.title else "未知帖子"
                    st.write(f"**{result.analysis_type}** | {post_title} | {result.model_used}")
                with col2:
                    if st.checkbox("选择", key=f"result_{result.id}"):
                        selected_results.append(result)
            
            if selected_results:
                if st.button(f"📥 下载选中的 {len(selected_results)} 条分析结果", key="download_selected_results"):
                    export_selected_results(selected_results, export_format)
            
            if total_count > preview_limit:
                st.info(f"还有 {total_count - preview_limit} 条结果未显示，如需查看更多请调整预览数量限制")
        
    finally:
        session.close()

def preview_data_packages():
    """预览数据包"""
    st.write("**数据包预览**")
    
    import os
    import glob
    
    output_dir = "output"
    if not os.path.exists(output_dir):
        st.warning("没有找到数据包文件")
        return
    
    package_files = glob.glob(os.path.join(output_dir, "reddit_data_*.json"))
    
    if package_files:
        st.info(f"找到 {len(package_files)} 个数据包文件")
        
        selected_packages = []
        for i, file_path in enumerate(package_files):
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) / 1024  # KB
            
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{file_name}** ({file_size:.1f} KB)")
            with col2:
                if st.checkbox("选择", key=f"package_{i}"):
                    selected_packages.append(file_path)
        
        if selected_packages:
            if st.button(f"📥 下载选中的 {len(selected_packages)} 个数据包", key="download_selected_packages"):
                export_selected_packages(selected_packages)
    else:
        st.warning("没有找到数据包文件")

def get_raw_data_content(date_range, selected_subreddits, export_format):
    """获取原始数据内容"""
    session = st.session_state.db.get_session()
    try:
        query = session.query(st.session_state.db.RedditPost)
        
        if date_range[0]:
            query = query.filter(st.session_state.db.RedditPost.scraped_at >= date_range[0])
        if date_range[1]:
            query = query.filter(st.session_state.db.RedditPost.scraped_at <= date_range[1])
        if selected_subreddits:
            query = query.filter(st.session_state.db.RedditPost.subreddit.in_(selected_subreddits))
        
        posts = query.all()
        
        if not posts:
            return None, None
        
        data = []
        for post in posts:
            data.append({
                'id': post.id,
                'title': post.title,
                'author': post.author,
                'score': post.score,
                'num_comments': post.num_comments,
                'created_utc': post.created_utc.isoformat() if post.created_utc else None,
                'subreddit': post.subreddit,
                'selftext': post.selftext,
                'url': post.url,
                'scraped_at': post.scraped_at.isoformat() if post.scraped_at else None
            })
        
        if export_format == "JSON":
            import json
            file_content = json.dumps(data, ensure_ascii=False, indent=2)
            file_extension = "json"
        else:  # CSV
            import pandas as pd
            df = pd.DataFrame(data)
            file_content = df.to_csv(index=False, encoding='utf-8-sig')
            file_extension = "csv"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reddit_raw_data_{timestamp}.{file_extension}"
        
        return file_content, filename
        
    finally:
        session.close()

def get_analysis_results_content(date_range, selected_subreddits, export_format):
    """获取分析结果内容 - 借鉴Excel导出逻辑"""
    try:
        # 借鉴Excel导出逻辑：直接使用get_analysis_results()获取所有数据
        results = st.session_state.db.get_analysis_results()
        
        if not results:
            return None, None
        
        data = []
        session = st.session_state.db.get_session()
        try:
            for result in results:
                post = session.query(st.session_state.db.RedditPost).filter(
                    st.session_state.db.RedditPost.id == result.content_id
                ).first()
                
                # 日期筛选
                if date_range[0] and result.created_at and result.created_at.date() < date_range[0]:
                    continue
                if date_range[1] and result.created_at and result.created_at.date() > date_range[1]:
                    continue
                
                # 子版块筛选
                if selected_subreddits and post and post.subreddit not in selected_subreddits:
                    continue
                
                data.append({
                    'analysis_id': result.id,
                    'content_id': result.content_id,
                    'content_type': result.content_type,
                    'analysis_type': result.analysis_type,
                    'model_used': result.model_used,
                    'created_at': result.created_at.isoformat() if result.created_at else None,
                    'result': result.result,
                    'post_title': post.title if post else None,
                    'post_subreddit': post.subreddit if post else None,
                    'post_author': post.author if post else None
                })
        finally:
            session.close()
        
        if not data:
            return None, None
        
        if export_format == "JSON":
            import json
            file_content = json.dumps(data, ensure_ascii=False, indent=2)
            file_extension = "json"
        else:  # CSV
            import pandas as pd
            df = pd.DataFrame(data)
            file_content = df.to_csv(index=False, encoding='utf-8-sig')
            file_extension = "csv"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_results_{timestamp}.{file_extension}"
        
        return file_content, filename
        
    finally:
        session.close()

def export_selected_posts(selected_posts, export_format):
    """导出选中的帖子"""
    data = []
    for post in selected_posts:
        data.append({
            'id': post.id,
            'title': post.title,
            'author': post.author,
            'score': post.score,
            'num_comments': post.num_comments,
            'created_utc': post.created_utc.isoformat() if post.created_utc else None,
            'subreddit': post.subreddit,
            'selftext': post.selftext,
            'url': post.url,
            'scraped_at': post.scraped_at.isoformat() if post.scraped_at else None
        })
    
    if export_format == "JSON":
        import json
        file_content = json.dumps(data, ensure_ascii=False, indent=2)
        file_extension = "json"
        mime_type = "application/json"
    else:  # CSV
        import pandas as pd
        df = pd.DataFrame(data)
        file_content = df.to_csv(index=False, encoding='utf-8-sig')
        file_extension = "csv"
        mime_type = "text/csv"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"selected_posts_{timestamp}.{file_extension}"
    
    st.download_button(
        label=f"📥 下载选中的帖子 ({len(data)} 条)",
        data=file_content,
        file_name=filename,
        mime=mime_type
    )

def export_selected_results(selected_results, export_format):
    """导出选中的分析结果"""
    session = st.session_state.db.get_session()
    try:
        data = []
        for result in selected_results:
            post = session.query(st.session_state.db.RedditPost).filter(
                st.session_state.db.RedditPost.id == result.content_id
            ).first()
            
            data.append({
                'analysis_id': result.id,
                'content_id': result.content_id,
                'content_type': result.content_type,
                'analysis_type': result.analysis_type,
                'model_used': result.model_used,
                'created_at': result.created_at.isoformat() if result.created_at else None,
                'result': result.result,
                'post_title': post.title if post else None,
                'post_subreddit': post.subreddit if post else None,
                'post_author': post.author if post else None
            })
        
        if export_format == "JSON":
            import json
            file_content = json.dumps(data, ensure_ascii=False, indent=2)
            file_extension = "json"
            mime_type = "application/json"
        else:  # CSV
            import pandas as pd
            df = pd.DataFrame(data)
            file_content = df.to_csv(index=False, encoding='utf-8-sig')
            file_extension = "csv"
            mime_type = "text/csv"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"selected_results_{timestamp}.{file_extension}"
        
        st.download_button(
            label=f"📥 下载选中的分析结果 ({len(data)} 条)",
            data=file_content,
            file_name=filename,
            mime=mime_type
        )
        
    finally:
        session.close()

def export_selected_packages(selected_packages):
    """导出选中的数据包"""
    import zipfile
    import io
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in selected_packages:
            file_name = os.path.basename(file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                zip_file.writestr(file_name, f.read())
    
    zip_buffer.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"selected_packages_{timestamp}.zip"
    
    st.download_button(
        label=f"📥 下载选中的数据包 ({len(selected_packages)} 个)",
        data=zip_buffer.getvalue(),
        file_name=zip_filename,
        mime="application/zip"
    )

def export_excel_report(date_range, selected_subreddits):
    """导出Excel分析报告"""
    st.write("**正在生成Excel分析报告...**")
    
    try:
        # 检查是否有分析结果数据
        results = st.session_state.db.get_analysis_results()
        if not results:
            st.warning("⚠️ 没有找到分析结果数据，请先进行大模型分析")
            return
        
        # 准备日期参数
        start_date = None
        end_date = None
        if date_range and len(date_range) == 2:
            start_date = date_range[0].strftime('%Y-%m-%d') if date_range[0] else None
            end_date = date_range[1].strftime('%Y-%m-%d') if date_range[1] else None
        
        # 准备子版块参数
        subreddits = selected_subreddits if selected_subreddits else None
        
        # 初始化数据整理器
        from data_organizer import DataOrganizer
        organizer = DataOrganizer(st.session_state.db, st.session_state.analyzer)
        
        # 生成Excel报告
        with st.spinner("正在生成Excel报告，请稍候..."):
            excel_file_path = organizer.generate_excel_report(
                start_date=start_date,
                end_date=end_date,
                subreddits=subreddits,
                output_dir="output"
            )
        
        # 读取生成的Excel文件
        with open(excel_file_path, 'rb') as f:
            excel_data = f.read()
        
        # 生成下载文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reddit_analysis_report_{timestamp}.xlsx"
        
        # 显示成功信息
        st.success("✅ Excel分析报告生成成功！")
        
        # 显示报告预览信息
        st.info(f"""
        📊 **报告包含以下工作表：**
        - **综合分析结果**：包含所有帖子的详细分析结果
        - **统计概览**：数据统计和分析次数统计
        - **子版块分析**：按子版块分组的统计数据
        - **情感分析**：情感分析结果统计
        - **主题分析**：主题关键词统计
        
        📅 **数据范围：** {start_date or '不限'} 至 {end_date or '不限'}
        🏷️ **子版块：** {', '.join(subreddits) if subreddits else '全部'}
        """)
        
        # 提供下载按钮
        st.download_button(
            label="📊 下载Excel分析报告",
            data=excel_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="点击下载包含所有分析结果的Excel报告"
        )
        
    except Exception as e:
        st.error(f"❌ Excel报告生成失败: {str(e)}")
        st.exception(e)
