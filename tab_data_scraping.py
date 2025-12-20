"""
Tab2: 数据抓取模块
"""
import streamlit as st
from datetime import datetime, timedelta

def render_data_scraping_tab():
    """渲染数据抓取页面"""
    try:
        st.header("📥 数据抓取")
        
        if not st.session_state.initialized:
            st.warning("⚠️ 请先配置API密钥并初始化系统")
            
            # 显示初始化提示和按钮
            col1, col2 = st.columns([2, 1])
            with col1:
                st.info("""
                💡 **初始化步骤：**
                1. 在左侧边栏配置 Reddit API 密钥（Client ID、Client Secret）
                2. 完成 Reddit 认证（使用用户名/密码或 OAuth2）
                3. 点击下方"🚀 初始化系统"按钮
                """)
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)  # 添加一些间距
            
            # 尝试初始化系统
            if st.button("🚀 初始化系统", type="primary", key="init_system_from_scraping"):
                try:
                    from app_init import init_components
                    with st.spinner("正在初始化系统..."):
                        if init_components():
                            st.success("✅ 系统初始化成功！")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ 系统初始化失败，请检查配置")
                except Exception as e:
                    st.error(f"❌ 初始化失败: {str(e)}")
                    import traceback
                    with st.expander("查看错误详情"):
                        st.code(traceback.format_exc())
                    st.info("💡 如果问题持续，请检查左侧边栏的配置是否正确")
            
            return
        
        if not st.session_state.scraper:
            st.warning("⚠️ Reddit API未初始化，请先完成认证并初始化系统")
            return
        
        # 抓取模式选择
        st.subheader("🎯 抓取模式")
        scrape_mode = st.radio(
            "选择抓取方式",
            ["按子版块抓取", "按关键词全站搜索"],
            help="选择按子版块抓取或使用关键词进行全站搜索"
        )
        
        subreddit_input = ""
        keywords_input = ""
        
        if scrape_mode == "按子版块抓取":
            # 子版块输入
            st.subheader("📌 选择子版块")
            subreddit_input = st.text_area(
                "输入子版块名称（每行一个，不带r/前缀）",
                placeholder="MachineLearning\nprogramming\nselfhosted",
                help="每行输入一个子版块名称，例如：MachineLearning",
                key="subreddit_input"
            )
        else:
            # 关键词输入（全站搜索）
            st.subheader("🔍 关键词搜索")
            keywords_input = st.text_area(
                "输入关键词（每行一个或逗号分隔，支持多关键词）",
                placeholder="portable charger\npower bank\ncamping gear",
                help="每行输入一个关键词，或使用逗号分隔多个关键词。系统将在全站搜索这些关键词",
                key="keywords_input"
            )
            st.info("💡 提示：全站搜索将搜索所有公开子版块，抓取数量限制在300-500之间以避免API限制")
        
        # 抓取参数
        col1, col2 = st.columns(2)
        with col1:
            if scrape_mode == "按关键词全站搜索":
                limit = st.number_input(
                    "帖子数量", 
                    min_value=300, 
                    max_value=500, 
                    value=400, 
                    help="全站搜索建议300-500个帖子，避免API请求次数超限"
                )
            else:
                limit = st.number_input(
                    "帖子数量", 
                    min_value=1, 
                    max_value=1000, 
                    value=100, 
                    help="建议50-500个帖子"
                )
            
            time_filter = st.selectbox(
                "时间范围",
                ["all", "year", "month", "week", "day", "hour"],
                index=3,
                format_func=lambda x: {
                    "all": "全部时间",
                    "year": "过去一年",
                    "month": "过去一月",
                    "week": "过去一周",
                    "day": "过去一天",
                    "hour": "过去一小时"
                }[x]
            )
        
        with col2:
            min_score = st.number_input("最低分数", min_value=0, value=0, help="只抓取分数大于等于此值的帖子")
            max_score = st.number_input("最高分数", min_value=0, value=0, help="0表示不限制")
            
            if scrape_mode == "按子版块抓取":
                search_query = st.text_input("搜索关键词（可选）", placeholder="输入关键词进行筛选", key="subreddit_search_query")
            else:
                search_query = None
        
        # 日期范围筛选
        use_date_filter = st.checkbox("使用日期范围筛选", value=False)
        date_range = None
        if use_date_filter:
            date_range = st.date_input(
                "选择日期范围",
                value=(datetime.now() - timedelta(days=7), datetime.now())
            )
        
        # 开始抓取按钮
        if st.button("🚀 开始抓取", type="primary"):
            # 保存关键词到历史记录
            if scrape_mode == "按关键词全站搜索" and keywords_input and keywords_input.strip():
                try:
                    if st.session_state.get('db'):
                        st.session_state.db.save_keywords_to_history(keywords_input, source="data_scraping")
                except Exception as e:
                    pass  # 静默失败，不影响抓取流程
            
            if scrape_mode == "按子版块抓取":
                # 按子版块抓取模式
                if not subreddit_input.strip():
                    st.error("❌ 请输入至少一个子版块名称")
                else:
                    subreddits = [s.strip() for s in subreddit_input.strip().split('\n') if s.strip()]
                    subreddits = [s.replace('r/', '').replace('/', '') for s in subreddits]  # 移除r/前缀
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    total_posts = 0
                    total_comments = 0
                    
                    for idx, subreddit in enumerate(subreddits):
                        status_text.text(f"正在抓取 r/{subreddit}... ({idx+1}/{len(subreddits)})")
                        progress_bar.progress((idx) / len(subreddits))
                        
                        try:
                            start_date = date_range[0] if date_range else None
                            end_date = date_range[1] if date_range else None
                            
                            posts = st.session_state.scraper.get_hot_posts(
                                subreddit_name=subreddit,
                                limit=limit,
                                time_filter=time_filter,
                                start_date=start_date,
                                end_date=end_date,
                                min_score=min_score,
                                max_score=max_score if max_score > 0 else None
                            )
                            
                            # 关键词筛选
                            if search_query:
                                filtered_posts = []
                                for post in posts:
                                    if (search_query.lower() in post.get('title', '').lower() or 
                                        search_query.lower() in post.get('selftext', '').lower()):
                                        filtered_posts.append(post)
                                posts = filtered_posts
                            
                            # 保存到数据库
                            if posts and st.session_state.db:
                                st.session_state.db.save_posts(posts)
                                
                                # 抓取评论
                                comments_count = 0
                                for post in posts[:10]:  # 只抓取前10个帖子的评论
                                    try:
                                        comments = st.session_state.scraper.get_post_comments(
                                            post_id=post.get('id'),
                                            limit=50
                                        )
                                        if comments:
                                            st.session_state.db.save_comments(comments)
                                            comments_count += len(comments)
                                    except Exception as e:
                                        st.warning(f"抓取评论失败: {str(e)}")
                                
                                total_posts += len(posts)
                                total_comments += comments_count
                                st.success(f"✅ r/{subreddit}: 成功抓取 {len(posts)} 个帖子, {comments_count} 条评论")
                            else:
                                st.warning(f"⚠️ r/{subreddit}: 未找到符合条件的帖子")
                        
                        except Exception as e:
                            st.error(f"❌ 抓取 r/{subreddit} 失败: {str(e)}")
                    
                    progress_bar.progress(1.0)
                    status_text.text("")
                    st.success(f"🎉 抓取完成！共抓取 {total_posts} 个帖子, {total_comments} 条评论")
            
            else:
                # 按关键词全站搜索模式
                if not keywords_input.strip():
                    st.error("❌ 请输入至少一个关键词")
                else:
                    # 解析关键词（支持换行和逗号分隔）
                    keywords_list = []
                    for line in keywords_input.strip().split('\n'):
                        line = line.strip()
                        if line:
                            # 支持逗号分隔
                            if ',' in line:
                                keywords_list.extend([k.strip() for k in line.split(',') if k.strip()])
                            else:
                                keywords_list.append(line)
                    
                    if not keywords_list:
                        st.error("❌ 请输入至少一个有效的关键词")
                    else:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        total_posts = 0
                        total_comments = 0
                        all_posts = []  # 用于去重
                        seen_post_ids = set()  # 用于去重
                        
                        # 计算每个关键词的抓取数量（平均分配）
                        posts_per_keyword = limit // len(keywords_list)
                        if posts_per_keyword < 100:
                            posts_per_keyword = 100  # 每个关键词至少100条
                        posts_per_keyword = min(posts_per_keyword, 500)  # 最多500条
                        
                        for idx, keyword in enumerate(keywords_list):
                            status_text.text(f"正在全站搜索关键词: '{keyword}'... ({idx+1}/{len(keywords_list)})")
                            progress_bar.progress((idx) / len(keywords_list))
                            
                            try:
                                # 使用全站搜索
                                posts = st.session_state.scraper.search_all_posts(
                                    query=keyword,
                                    limit=posts_per_keyword,
                                    sort='relevance',
                                    months_back=6  # 限制在最近6个月内
                                )
                                
                                # 去重（基于post_id）
                                new_posts = []
                                for post in posts:
                                    post_id = post.get('id')
                                    if post_id and post_id not in seen_post_ids:
                                        seen_post_ids.add(post_id)
                                        new_posts.append(post)
                                
                                # 分数筛选
                                if min_score > 0 or (max_score > 0):
                                    filtered_posts = []
                                    for post in new_posts:
                                        score = post.get('score', 0)
                                        if score >= min_score:
                                            if max_score > 0:
                                                if score <= max_score:
                                                    filtered_posts.append(post)
                                            else:
                                                filtered_posts.append(post)
                                    new_posts = filtered_posts
                                
                                # 日期筛选
                                if date_range:
                                    start_date = date_range[0] if isinstance(date_range, tuple) else None
                                    end_date = date_range[1] if isinstance(date_range, tuple) else None
                                    if start_date or end_date:
                                        filtered_posts = []
                                        for post in new_posts:
                                            post_date = post.get('created_utc')
                                            if post_date:
                                                if isinstance(post_date, datetime):
                                                    post_date_only = post_date.date()
                                                else:
                                                    post_date_only = post_date
                                                
                                                if start_date and post_date_only < start_date:
                                                    continue
                                                if end_date and post_date_only > end_date:
                                                    continue
                                                filtered_posts.append(post)
                                        new_posts = filtered_posts
                                
                                all_posts.extend(new_posts)
                                
                                if new_posts:
                                    st.success(f"✅ 关键词 '{keyword}': 找到 {len(new_posts)} 个帖子（去重后）")
                                else:
                                    st.warning(f"⚠️ 关键词 '{keyword}': 未找到符合条件的帖子")
                            
                            except Exception as e:
                                st.error(f"❌ 搜索关键词 '{keyword}' 失败: {str(e)}")
                        
                        # 保存所有帖子到数据库
                        if all_posts and st.session_state.db:
                            # 限制总数量在300-500之间
                            if len(all_posts) > limit:
                                all_posts = all_posts[:limit]
                            
                            st.session_state.db.save_posts(all_posts)
                            
                            # 抓取部分评论（避免过多请求）
                            comments_count = 0
                            posts_for_comments = all_posts[:20]  # 只抓取前20个帖子的评论
                            for post in posts_for_comments:
                                try:
                                    post_id = post.get('id')
                                    if post_id:
                                        comments = st.session_state.scraper.get_post_comments(
                                            post_id=post_id,
                                            limit=50
                                        )
                                        if comments:
                                            st.session_state.db.save_comments(comments)
                                            comments_count += len(comments)
                                except Exception as e:
                                    st.warning(f"抓取评论失败: {str(e)}")
                            
                            total_posts = len(all_posts)
                            st.success(f"🎉 全站搜索完成！共抓取 {total_posts} 个帖子（来自 {len(set(p.get('subreddit', '') for p in all_posts))} 个子版块）, {comments_count} 条评论")
                        else:
                            st.warning("⚠️ 未找到符合条件的帖子")
                        
                        progress_bar.progress(1.0)
                        status_text.text("")
    except Exception as e:
        st.error(f"❌ 数据抓取页面加载失败: {str(e)}")
        import traceback
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())

