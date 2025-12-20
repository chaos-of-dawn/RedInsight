"""
Tab6: 智能筛选模块 - AI数据分析
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import re
import logging

logger = logging.getLogger(__name__)

def render_smart_filter_tab():
    """渲染智能筛选页面 - AI数据分析"""
    try:
        st.header("🔍 智能筛选 - AI数据分析")
        st.markdown("💡 通过AI大模型对本地数据库中的帖子进行深度分析")
        
        if not st.session_state.initialized:
            st.warning("⚠️ 请先配置API密钥并初始化系统")
            st.info("💡 请在左侧边栏配置Reddit API密钥和AI模型API密钥，然后点击'初始化系统'按钮")
            return
        
        if not st.session_state.get('analyzer'):
            st.warning("⚠️ AI分析器未初始化，请先配置AI模型API密钥（OpenAI/Anthropic/DeepSeek）")
            return
        
        # === 第一步：数据筛选（可选） ===
        st.subheader("📊 第一步：数据筛选（可选）")
        st.info("💡 提示：如果不设置筛选条件，将分析数据库中的所有帖子")
        
        use_filter = st.checkbox("使用筛选条件", value=False, help="勾选后可以设置筛选条件")
        
        selected_subreddits = []
        keywords = ""
        date_range = None
        min_score = 0
        max_score = 0
        
        if use_filter:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### 📍 子版块筛选")
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
                        st.info("💡 请先在'📥 数据抓取'页面抓取数据")
                except Exception as e:
                    st.error(f"❌ 获取子版块列表失败: {str(e)}")
                    selected_subreddits = []
                
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
                st.markdown("#### 📅 时间范围")
                date_range = st.date_input(
                    "选择日期范围",
                    value=(datetime.now() - timedelta(days=30), datetime.now()),
                    key="filter_date_range"
                )
                
                st.markdown("#### 🔍 关键词筛选")
                keywords = st.text_area(
                    "关键词（每行一个）",
                    placeholder="keyword1\nkeyword2\nkeyword3",
                    help="在标题或内容中搜索关键词",
                    key="filter_keywords"
                )
                
                keyword_search_mode = st.selectbox(
                    "搜索模式",
                    ["全部匹配", "任一匹配"],
                    help="全部匹配：帖子必须包含所有关键词；任一匹配：包含任一关键词即可",
                    key="filter_keyword_mode"
                )
            
            with col3:
                st.markdown("#### 📊 数据限制")
                result_limit = st.number_input(
                    "分析数量限制",
                    min_value=1,
                    max_value=5000,
                    value=500,
                    help="最多分析的帖子数量（建议100-1000）",
                    key="filter_limit"
                )
            
            # 显示符合筛选条件的帖子数量
            st.markdown("---")
            st.markdown("#### 📊 筛选结果预览")
            
            col_preview1, col_preview2 = st.columns([3, 1])
            with col_preview1:
                if st.button("🔍 查询符合筛选条件的帖子数量", key="preview_filter_count"):
                    try:
                        # 保存关键词到历史记录
                        if keywords and keywords.strip():
                            try:
                                if st.session_state.get('db'):
                                    st.session_state.db.save_keywords_to_history(keywords, source="smart_filter")
                            except Exception:
                                pass  # 静默失败，不影响查询流程
                        
                        with st.spinner("正在查询..."):
                            # 解析关键词
                            keyword_list = [k.strip() for k in keywords.split('\n') if k.strip()] if keywords else []
                            
                            # 构建筛选条件
                            filters = {
                                'subreddits': selected_subreddits if selected_subreddits else None,
                                'min_score': min_score if min_score > 0 else None,
                                'max_score': max_score if max_score > 0 else None,
                                'keywords': keyword_list if keyword_list else None,
                                'start_date': date_range[0] if date_range else None,
                                'end_date': date_range[1] if date_range else None,
                                'limit': 10000  # 使用较大的限制来获取准确数量
                            }
                            
                            # 使用数据库的筛选方法
                            posts = st.session_state.db.get_posts_with_filters(
                                subreddits=filters['subreddits'],
                                min_score=filters['min_score'],
                                max_score=filters['max_score'],
                                keywords=filters['keywords'],
                                limit=filters['limit']
                            )
                            
                            # 进一步筛选（日期、关键词匹配模式）
                            if filters['start_date'] or filters['end_date']:
                                filtered_posts = []
                                for post in posts:
                                    post_date = post.created_utc if hasattr(post, 'created_utc') else None
                                    if post_date:
                                        if filters['start_date'] and post_date.date() < filters['start_date']:
                                            continue
                                        if filters['end_date'] and post_date.date() > filters['end_date']:
                                            continue
                                    filtered_posts.append(post)
                                posts = filtered_posts
                            
                            # 关键词匹配模式筛选
                            if keyword_list and keyword_search_mode == "全部匹配":
                                filtered_posts = []
                                for post in posts:
                                    title = post.title.lower() if hasattr(post, 'title') else ''
                                    content = post.selftext.lower() if hasattr(post, 'selftext') else ''
                                    text = title + ' ' + content
                                    if all(kw.lower() in text for kw in keyword_list):
                                        filtered_posts.append(post)
                                posts = filtered_posts
                            
                            # 显示结果
                            count = len(posts)
                            if count > 0:
                                # 统计信息
                                unique_subreddits = len(set(p.subreddit for p in posts if hasattr(p, 'subreddit')))
                                avg_score = sum(p.score for p in posts if hasattr(p, 'score')) / count if count > 0 else 0
                                total_comments = sum(p.num_comments for p in posts if hasattr(p, 'num_comments'))
                                
                                st.success(f"✅ 找到 **{count}** 条符合条件的帖子")
                                
                                # 显示详细统计
                                col_stat1, col_stat2, col_stat3 = st.columns(3)
                                with col_stat1:
                                    st.metric("涉及子版块", unique_subreddits)
                                with col_stat2:
                                    st.metric("平均分数", f"{avg_score:.1f}")
                                with col_stat3:
                                    st.metric("总评论数", total_comments)
                            else:
                                st.warning("⚠️ 没有找到符合条件的帖子，请调整筛选条件")
                    
                    except Exception as e:
                        st.error(f"❌ 查询失败: {str(e)}")
                        import traceback
                        with st.expander("查看错误详情"):
                            st.code(traceback.format_exc())
            
            with col_preview2:
                st.markdown("<br>", unsafe_allow_html=True)  # 添加间距
                st.caption("💡 点击按钮查询符合当前筛选条件的帖子数量")
        
        # === 第二步：AI分析选项 ===
        st.markdown("---")
        st.subheader("🤖 第二步：选择AI分析类型")
        
        analysis_type = st.radio(
            "选择分析类型",
            ["痛点提取", "情绪分析", "需求分析", "综合分析", "自定义分析"],
            help="选择要执行的AI分析类型",
            key="analysis_type"
        )
        
        # 根据分析类型显示额外选项
        custom_prompt = None
        if analysis_type == "自定义分析":
            custom_prompt = st.text_area(
                "自定义分析提示词",
                placeholder="例如：分析这些帖子中的用户偏好和购买意向...",
                help="输入您想要AI执行的具体分析任务",
                key="custom_prompt"
            )
            if not custom_prompt.strip():
                st.warning("⚠️ 请输入自定义分析提示词")
        
        # AI模型选择
        col_model1, col_model2 = st.columns(2)
        with col_model1:
            provider = st.selectbox(
                "选择AI模型",
                ["deepseek", "openai", "anthropic"],
                index=0,
                help="选择用于分析的AI模型",
                key="analysis_provider"
            )
        with col_model2:
            batch_size = st.number_input(
                "批量分析大小",
                min_value=1,
                max_value=100,
                value=10,
                help="每次批量分析的帖子数量（建议5-20）",
                key="batch_size"
            )
        
        # === 第三步：执行分析 ===
        st.markdown("---")
        st.subheader("🚀 第三步：执行AI分析")
        
        if st.button("🚀 开始AI分析", type="primary"):
            try:
                # 1. 获取筛选后的数据
                with st.spinner("正在筛选数据..."):
                    if use_filter:
                        # 解析关键词
                        keyword_list = [k.strip() for k in keywords.split('\n') if k.strip()] if keywords else []
                        
                        # 构建筛选条件
                        filters = {
                            'subreddits': selected_subreddits if selected_subreddits else None,
                            'min_score': min_score if min_score > 0 else None,
                            'max_score': max_score if max_score > 0 else None,
                            'keywords': keyword_list if keyword_list else None,
                            'start_date': date_range[0] if date_range else None,
                            'end_date': date_range[1] if date_range else None,
                            'limit': result_limit if use_filter else 500
                        }
                        
                        # 使用数据库的筛选方法
                        posts = st.session_state.db.get_posts_with_filters(
                            subreddits=filters['subreddits'],
                            min_score=filters['min_score'],
                            max_score=filters['max_score'],
                            keywords=filters['keywords'],
                            limit=filters['limit']
                        )
                        
                        # 进一步筛选（日期、关键词匹配模式）
                        if filters['start_date'] or filters['end_date']:
                            filtered_posts = []
                            for post in posts:
                                post_date = post.created_utc if hasattr(post, 'created_utc') else None
                                if post_date:
                                    if filters['start_date'] and post_date.date() < filters['start_date']:
                                        continue
                                    if filters['end_date'] and post_date.date() > filters['end_date']:
                                        continue
                                filtered_posts.append(post)
                            posts = filtered_posts
                        
                        # 关键词匹配模式筛选
                        if keyword_list and keyword_search_mode == "全部匹配":
                            filtered_posts = []
                            for post in posts:
                                title = post.title.lower() if hasattr(post, 'title') else ''
                                content = post.selftext.lower() if hasattr(post, 'selftext') else ''
                                text = title + ' ' + content
                                if all(kw.lower() in text for kw in keyword_list):
                                    filtered_posts.append(post)
                            posts = filtered_posts
                    else:
                        # 不使用筛选条件，获取所有帖子（限制数量）
                        posts = st.session_state.db.get_posts(limit=1000)
                
                if not posts:
                    st.warning("⚠️ 没有找到符合条件的帖子，请调整筛选条件")
                    return
                
                st.success(f"✅ 筛选完成，找到 {len(posts)} 条帖子")
                
                # 2. 准备分析数据（包含帖子和评论）
                with st.spinner("正在准备分析数据（包含帖子和评论）..."):
                    posts_data = []
                    total_comments_count = 0
                    
                    for post in posts:
                        post_id = post.id if hasattr(post, 'id') else ''
                        
                        # 获取该帖子的评论
                        comments = st.session_state.db.get_comments_by_post_id(post_id)
                        comments_data = []
                        for comment in comments:
                            comment_dict = {
                                'id': comment.id if hasattr(comment, 'id') else '',
                                'body': comment.body if hasattr(comment, 'body') else '',
                                'author': comment.author if hasattr(comment, 'author') else '',
                                'score': comment.score if hasattr(comment, 'score') else 0,
                                'created_utc': comment.created_utc.strftime('%Y-%m-%d %H:%M:%S') if hasattr(comment, 'created_utc') and comment.created_utc else '',
                                'is_submitter': comment.is_submitter if hasattr(comment, 'is_submitter') else False
                            }
                            comments_data.append(comment_dict)
                        
                        total_comments_count += len(comments_data)
                        
                        # 构建包含帖子和评论的数据结构
                        post_dict = {
                            'id': post_id,
                            'title': post.title if hasattr(post, 'title') else '',
                            'selftext': post.selftext if hasattr(post, 'selftext') else '',
                            'subreddit': post.subreddit if hasattr(post, 'subreddit') else '',
                            'score': post.score if hasattr(post, 'score') else 0,
                            'num_comments': post.num_comments if hasattr(post, 'num_comments') else 0,
                            'created_utc': post.created_utc.strftime('%Y-%m-%d %H:%M:%S') if hasattr(post, 'created_utc') and post.created_utc else '',
                            'author': post.author if hasattr(post, 'author') else '',
                            'comments': comments_data  # 添加评论数据
                        }
                        posts_data.append(post_dict)
                    
                    st.info(f"📊 数据准备完成：{len(posts_data)} 个帖子，{total_comments_count} 条评论")
                
                # 3. 执行AI分析
                st.markdown("---")
                st.subheader("📊 AI分析结果")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 获取筛选关键词（在循环外获取，避免重复）
                keyword_context = ""
                keyword_list_for_analysis = []
                if use_filter and keywords:
                    keyword_list_for_analysis = [k.strip() for k in keywords.split('\n') if k.strip()]
                    if keyword_list_for_analysis:
                        keyword_context = f"\n\n**重要提示：** 以下数据是根据关键词筛选出来的，关键词包括：{', '.join(keyword_list_for_analysis)}。请重点关注与这些关键词相关的内容，分析用户在这些关键词相关话题中的观点、问题、需求和情绪。"
                
                # 分批分析
                total_batches = (len(posts_data) + batch_size - 1) // batch_size
                all_results = []
                
                for batch_idx in range(total_batches):
                    start_idx = batch_idx * batch_size
                    end_idx = min(start_idx + batch_size, len(posts_data))
                    batch_posts = posts_data[start_idx:end_idx]
                    
                    status_text.text(f"正在分析第 {batch_idx + 1}/{total_batches} 批数据... ({len(batch_posts)} 个帖子)")
                    progress_bar.progress((batch_idx + 1) / total_batches)
                    
                    try:
                        
                        # 根据分析类型调用不同的分析方法
                        if analysis_type == "痛点提取":
                            # 构建痛点提取提示词（包含子版块、帖子和评论）
                            # 格式化数据，突出显示评论中的痛点
                            formatted_data = []
                            for p in batch_posts:
                                post_info = {
                                    '子版块': p.get('subreddit', ''),
                                    '帖子标题': p['title'],
                                    '帖子内容': p['selftext'],
                                    '评论': [c['body'] for c in p.get('comments', [])[:20]]  # 最多取20条评论
                                }
                                formatted_data.append(post_info)
                            
                            prompt = f"""
请分析以下Reddit帖子和评论，提取用户的核心痛点。特别注意评论中用户表达的问题和困扰。{keyword_context}

{json.dumps(formatted_data, ensure_ascii=False, indent=2)}

请按以下格式返回JSON结果：
{{
    "pain_points": ["痛点1", "痛点2", "痛点3"],
    "pain_details": {{
        "痛点1": "详细描述（包括在哪些帖子/评论中出现，以及与关键词的关联）",
        "痛点2": "详细描述"
    }},
    "frequency": {{
        "痛点1": 出现次数,
        "痛点2": 出现次数
    }},
    "sources": {{
        "痛点1": ["来源帖子/评论示例"],
        "痛点2": ["来源帖子/评论示例"]
    }},
    "keyword_relation": {{
        "痛点1": "与关键词的关联说明",
        "痛点2": "与关键词的关联说明"
    }},
    "summary": "痛点总结（重点说明与关键词相关的痛点）"
}}
"""
                            result = st.session_state.analyzer._call_llm(prompt, provider, "pain_point_analysis")
                        
                        elif analysis_type == "情绪分析":
                            # 使用批量情绪分析（包含子版块、帖子和评论）
                            combined_text = "\n\n".join([
                                f"子版块: {p.get('subreddit', '')}\n帖子标题: {p['title']}\n帖子内容: {p['selftext']}\n" +
                                (f"评论:\n" + "\n".join([f"- {c['body']}" for c in p.get('comments', [])[:10]]) if p.get('comments') else "无评论")
                                for p in batch_posts
                            ])
                            
                            # 如果有关键词，添加自定义提示词
                            if keyword_context:
                                custom_prompt = f"""
请分析以下Reddit帖子和评论的情感倾向。{keyword_context}

数据内容：
{combined_text}

请重点关注与关键词相关内容的情绪，分析用户对这些关键词相关话题的情感态度。

请按以下格式返回JSON结果：
{{
    "sentiment": "positive/negative/neutral",
    "confidence": 0.0-1.0,
    "emotions": ["emotion1", "emotion2"],
    "summary": "简要总结（重点说明与关键词相关的情绪）",
    "key_phrases": ["phrase1", "phrase2"],
    "keyword_sentiment": {{
        "关键词相关内容的整体情绪": "positive/negative/neutral",
        "情绪强度": "描述"
    }}
}}
"""
                                result = st.session_state.analyzer._call_llm(custom_prompt, provider, "sentiment_analysis")
                            else:
                                result = st.session_state.analyzer.analyze_sentiment(combined_text, provider)
                        
                        elif analysis_type == "需求分析":
                            # 构建需求分析提示词（包含子版块、帖子和评论）
                            formatted_data = []
                            for p in batch_posts:
                                post_info = {
                                    '子版块': p.get('subreddit', ''),
                                    '帖子标题': p['title'],
                                    '帖子内容': p['selftext'],
                                    '评论': [c['body'] for c in p.get('comments', [])[:20]]  # 最多取20条评论
                                }
                                formatted_data.append(post_info)
                            
                            prompt = f"""
请分析以下Reddit帖子和评论，提取用户的核心需求。特别注意评论中用户表达的需求和期望。{keyword_context}

{json.dumps(formatted_data, ensure_ascii=False, indent=2)}

请按以下格式返回JSON结果：
{{
    "user_needs": ["需求1", "需求2", "需求3"],
    "need_details": {{
        "需求1": "详细描述（包括在哪些帖子/评论中出现，以及与关键词的关联）",
        "需求2": "详细描述"
    }},
    "priority": {{
        "需求1": "高/中/低",
        "需求2": "高/中/低"
    }},
    "sources": {{
        "需求1": ["来源帖子/评论示例"],
        "需求2": ["来源帖子/评论示例"]
    }},
    "keyword_relation": {{
        "需求1": "与关键词的关联说明",
        "需求2": "与关键词的关联说明"
    }},
    "summary": "需求总结（重点说明与关键词相关的需求）"
}}
"""
                            result = st.session_state.analyzer._call_llm(prompt, provider, "need_analysis")
                        
                        elif analysis_type == "综合分析":
                            # 使用综合分析（包含子版块、帖子和评论）
                            combined_text = "\n\n".join([
                                f"子版块: {p.get('subreddit', '')}\n帖子标题: {p['title']}\n帖子内容: {p['selftext']}\n" +
                                (f"评论:\n" + "\n".join([f"- {c['body']}" for c in p.get('comments', [])[:15]]) if p.get('comments') else "无评论")
                                for p in batch_posts
                            ])
                            
                            # 如果有关键词，添加自定义提示词
                            if keyword_context:
                                custom_prompt = f"""
请对以下Reddit帖子和评论进行综合分析。{keyword_context}

数据内容：
{combined_text}

请重点关注与关键词相关的内容，包括：
1. 与关键词相关的整体情绪
2. 与关键词相关的主要讨论主题
3. 与关键词相关的核心痛点
4. 与关键词相关的实用建议

请按以下格式返回JSON结果：
{{
    "overall_sentiment": "整体情绪百分比（重点说明关键词相关内容的情绪）",
    "main_emotions": ["情感1", "情感2", "情感3"],
    "controversy_points": ["争议点1", "争议点2"],
    "main_topics": ["主题1（与关键词相关）", "主题2", "主题3"],
    "top_pain_points": ["痛点1（与关键词相关）", "痛点2", "痛点3"],
    "top_advice": ["建议1（与关键词相关）", "建议2", "建议3", "建议4", "建议5"],
    "mentioned_tools": ["工具1", "工具2"],
    "keyword_insights": {{
        "关键词相关讨论的主要特点": "描述",
        "关键词相关话题的热点": "描述",
        "关键词相关内容的趋势": "描述"
    }},
    "summary": "综合分析总结（重点说明与关键词相关的洞察）"
}}
"""
                                result = st.session_state.analyzer._call_llm(custom_prompt, provider, "comprehensive_analysis")
                            else:
                                result = st.session_state.analyzer.analyze_comprehensive(combined_text, provider)
                        
                        else:  # 自定义分析
                            if not custom_prompt:
                                st.error("❌ 请输入自定义分析提示词")
                                return
                            
                            # 使用自定义提示词（包含帖子和评论）
                            # 格式化数据，包含评论
                            formatted_data = []
                            for p in batch_posts:
                                post_info = {
                                    '帖子标题': p['title'],
                                    '帖子内容': p['selftext'],
                                    '子版块': p.get('subreddit', ''),
                                    '分数': p.get('score', 0),
                                    '评论数': p.get('num_comments', 0),
                                    '评论': [{'内容': c['body'], '作者': c.get('author', ''), '分数': c.get('score', 0)} 
                                            for c in p.get('comments', [])[:20]]  # 最多取20条评论
                                }
                                formatted_data.append(post_info)
                            
                            prompt = f"""
{custom_prompt}

数据（包含帖子和评论）：
{json.dumps(formatted_data, ensure_ascii=False, indent=2)}

请提供详细的分析结果。
"""
                            result = st.session_state.analyzer._call_llm(prompt, provider, "custom_analysis")
                        
                        if result:
                            all_results.append({
                                'batch': batch_idx + 1,
                                'posts_count': len(batch_posts),
                                'result': result
                            })
                    
                    except Exception as e:
                        st.warning(f"⚠️ 第 {batch_idx + 1} 批分析失败: {str(e)}")
                        import traceback
                        if 'logger' in globals():
                            logger.error(traceback.format_exc())
                        else:
                            st.error(traceback.format_exc())
                
                progress_bar.progress(1.0)
                status_text.text("")
                
                # 4. 保存分析结果到数据库
                if all_results:
                    try:
                        session = st.session_state.db.get_session()
                        try:
                            # 为每个批次的分析结果创建数据库记录
                            for batch_result in all_results:
                                result_data = batch_result['result']
                                
                                # 将结果转换为JSON字符串
                                import json
                                if isinstance(result_data, dict):
                                    result_json_str = json.dumps(result_data, ensure_ascii=False)
                                elif isinstance(result_data, str):
                                    result_json_str = result_data
                                else:
                                    result_json_str = str(result_data)
                                
                                # 创建分析结果记录
                                # 使用批次编号作为content_id，content_type为'batch'
                                analysis_record = st.session_state.db.AnalysisResult(
                                    content_id=f"batch_{batch_result['batch']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                    content_type='batch',
                                    analysis_type={
                                        '痛点提取': 'pain_point_analysis',
                                        '情绪分析': 'sentiment_analysis',
                                        '需求分析': 'need_analysis',
                                        '综合分析': 'comprehensive_analysis',
                                        '自定义分析': 'custom_analysis'
                                    }.get(analysis_type, 'custom_analysis'),
                                    result=result_json_str,
                                    model_used=provider
                                )
                                session.add(analysis_record)
                            
                            session.commit()
                            logger.info(f"已保存 {len(all_results)} 条分析结果到数据库")
                        except Exception as e:
                            session.rollback()
                            logger.error(f"保存分析结果到数据库失败: {str(e)}")
                        finally:
                            session.close()
                    except Exception as e:
                        logger.warning(f"保存分析结果失败: {str(e)}")
                
                # 5. 展示分析结果
                if all_results:
                    st.success(f"✅ 分析完成！共分析了 {len(posts_data)} 个帖子，分为 {len(all_results)} 批")
                    
                    # 合并所有批次的结果
                    combined_result = {
                        'total_posts': len(posts_data),
                        'total_batches': len(all_results),
                        'analysis_type': analysis_type,
                        'results': all_results
                    }
                    
                    # 显示结果
                    st.markdown("#### 📋 分析结果详情")
                    
                    for idx, batch_result in enumerate(all_results):
                        with st.expander(f"第 {batch_result['batch']} 批结果 ({batch_result['posts_count']} 个帖子)"):
                            result_data = batch_result['result']
                            
                            # 尝试解析JSON结果
                            if isinstance(result_data, dict):
                                st.json(result_data)
                            elif isinstance(result_data, str):
                                # 尝试提取JSON
                                try:
                                    # 尝试从字符串中提取JSON
                                    json_match = re.search(r'\{.*\}', result_data, re.DOTALL)
                                    if json_match:
                                        parsed = json.loads(json_match.group())
                                        st.json(parsed)
                                    else:
                                        st.markdown(result_data)
                                except:
                                    st.markdown(result_data)
                            else:
                                st.write(result_data)
                    
                    # 导出结果
                    st.markdown("#### 💾 导出分析结果")
                    col_export1, col_export2 = st.columns(2)
                    with col_export1:
                        json_str = json.dumps(combined_result, ensure_ascii=False, indent=2)
                        st.download_button(
                            "📥 下载JSON",
                            json_str,
                            f"ai_analysis_{analysis_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            "application/json",
                            key="download_analysis_json"
                        )
                    with col_export2:
                        # 生成摘要文本
                        summary_text = f"""
AI分析报告
分析类型: {analysis_type}
分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
分析帖子数: {len(posts_data)}
分析批次数: {len(all_results)}

详细结果请查看JSON文件。
"""
                        st.download_button(
                            "📥 下载摘要",
                            summary_text,
                            f"ai_analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            "text/plain",
                            key="download_analysis_summary"
                        )
                else:
                    st.error("❌ 分析失败，没有获得任何结果")
            
            except Exception as e:
                st.error(f"❌ 分析过程失败: {str(e)}")
                import traceback
                with st.expander("查看错误详情"):
                    st.code(traceback.format_exc())
    
    except Exception as e:
        st.error(f"❌ 智能筛选页面加载失败: {str(e)}")
        import traceback
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())
