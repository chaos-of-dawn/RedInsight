"""
AI内容生成模块
"""
import streamlit as st
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
import uuid
import json
from modules.posting.shared.post_manager import PostManager
from modules.posting.shared.state_manager import PostingStateManager
from modules.posting.shared.ui_components import render_post_card
from modules.posting.ai_generator_enhanced import EnhancedAIGenerator

logger = logging.getLogger(__name__)

def serialize_for_json(obj: Any) -> Any:
    """
    将对象中的datetime对象转换为字符串，以便JSON序列化
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(serialize_for_json(item) for item in obj)
    else:
        return obj

def render_ai_generator():
    """渲染AI内容生成页面"""
    try:
        if not st.session_state.get('initialized'):
            st.warning("⚠️ 请先初始化系统")
            return
        
        if not st.session_state.get('analyzer'):
            st.warning("⚠️ AI分析器未初始化，请先配置AI模型API密钥")
            return
        
        db = st.session_state.db
        post_manager = PostManager(db)
        analyzer = st.session_state.analyzer
        
        # 布局：左侧配置，右侧结果
        col_config, col_result = st.columns([1, 2])
        
        with col_config:
            render_generation_config(analyzer)
        
        with col_result:
            render_generation_results(post_manager)
    
    except Exception as e:
        st.error(f"❌ AI生成页面加载失败: {str(e)}")
        logger.error(f"AI生成页面错误: {str(e)}", exc_info=True)

def render_generation_config(analyzer):
    """渲染生成配置区域"""
    st.subheader("🤖 AI生成配置")
    
    # 关键词组设置
    st.markdown("#### 📝 关键词组设置")
    
    if 'keyword_groups' not in st.session_state:
        st.session_state.keyword_groups = [""]
    
    keyword_groups = []
    for i, group in enumerate(st.session_state.keyword_groups):
        keywords_input = st.text_input(
            f"关键词组 {i+1}",
            value=group,
            key=f"keyword_group_{i}",
            placeholder="多个关键词用逗号分隔，例如: keyword1, keyword2"
        )
        keyword_groups.append(keywords_input)
    
    col_add, col_remove = st.columns(2)
    with col_add:
        if st.button("➕ 添加关键词组", key="add_keyword_group"):
            keyword_groups.append("")
            st.session_state.keyword_groups = keyword_groups
            st.rerun()
    
    with col_remove:
        if len(keyword_groups) > 1 and st.button("➖ 删除最后一组", key="remove_keyword_group"):
            keyword_groups.pop()
            st.session_state.keyword_groups = keyword_groups
            st.rerun()
    
    st.session_state.keyword_groups = keyword_groups
    
    # 生成模式选择
    st.markdown("#### 📊 生成设置")
    generation_mode = st.radio(
        "生成模式",
        ["标准模式", "增强模式（推荐）"],
        index=1,
        help="标准模式：基于本地数据生成；增强模式：全站抓取+子版块分析+主题一致性检查+规则检查",
        key="generation_mode"
    )
    
    # 生成数量
    generation_count = st.number_input(
        "生成数量",
        min_value=1,
        max_value=20,
        value=3 if generation_mode == "增强模式（推荐）" else 5,
        help="每次生成的帖子数量",
        key="generation_count"
    )
    
    # 分析类型选择（仅标准模式）
    if generation_mode == "标准模式":
        analysis_types = st.multiselect(
            "分析类型",
            ["痛点提取", "需求分析", "情绪分析", "综合分析"],
            default=["痛点提取", "需求分析"],
            help="选择AI分析的类型，用于生成帖子内容",
            key="analysis_types"
        )
    else:
        analysis_types = []  # 增强模式不需要这个
    
    # AI模型选择
    provider = st.selectbox(
        "AI模型",
        ["deepseek", "openai", "anthropic"],
        index=0,
        key="ai_provider"
    )
    
    # 生成按钮
    if st.button("🚀 开始生成", type="primary", key="start_generation"):
        if not keyword_groups or not any(kg.strip() for kg in keyword_groups):
            st.warning("⚠️ 请至少输入一个关键词组")
            return
        
        if generation_mode == "标准模式" and not analysis_types:
            st.warning("⚠️ 请至少选择一个分析类型")
            return
        
        # 保存关键词到历史记录
        try:
            if st.session_state.get('db'):
                for keyword_group in keyword_groups:
                    if keyword_group.strip():
                        st.session_state.db.save_keywords_to_history(keyword_group, source="ai_generator")
        except Exception as e:
            logger.warning(f"保存关键词到历史记录失败: {str(e)}")
        
        # 执行生成
        if generation_mode == "增强模式（推荐）":
            # 使用增强模式
            generated_posts, analysis_summary = generate_enhanced_posts_from_keywords(
                analyzer,
                keyword_groups,
                generation_count,
                provider
            )
            
            if generated_posts:
                # 保存到session_state
                PostingStateManager.set_ai_generated_posts(generated_posts)
                # 保存分析摘要
                st.session_state['last_enhanced_analysis'] = analysis_summary
                st.success(f"✅ 成功生成 {len(generated_posts)} 篇帖子")
                st.rerun()
            else:
                st.error("❌ 生成失败")
        else:
            # 使用标准模式
            with st.spinner("🤖 AI正在生成内容，请稍候..."):
                generated_posts = generate_posts_from_keywords(
                    analyzer,
                    keyword_groups,
                    generation_count,
                    analysis_types,
                    provider
                )
                
                if generated_posts:
                    # 保存到session_state
                    PostingStateManager.set_ai_generated_posts(generated_posts)
                    st.success(f"✅ 成功生成 {len(generated_posts)} 篇帖子")
                    st.rerun()
                else:
                    # 显示更详细的错误信息
                    st.error("❌ 生成失败")
                    with st.expander("查看可能的原因和解决方案"):
                        st.markdown("""
                        **可能的原因：**
                        1. **AI API调用失败**
                           - 请检查API密钥是否正确配置
                           - 检查网络连接是否正常
                           - 查看控制台日志获取详细错误信息
                        
                        2. **未找到相关帖子数据**
                           - 请检查关键词是否正确
                           - 尝试使用更通用的关键词
                           - 确保本地数据库中有相关数据
                        
                        3. **AI返回的数据格式不正确**
                           - 可能是AI模型响应异常
                           - 可以尝试更换AI提供商
                           - 查看控制台日志了解详情
                        
                        4. **Token限制**
                           - 如果数据量过大，系统会自动精简
                           - 可以尝试减少关键词数量
                        
                        **建议操作：**
                        - 查看浏览器控制台（F12）的详细错误信息
                        - 检查系统日志文件
                        - 尝试使用更少的关键词重新生成
                        """)

def generate_posts_from_keywords(analyzer,
                                keyword_groups: List[str],
                                count: int,
                                analysis_types: List[str],
                                provider: str) -> List[Dict[str, Any]]:
    """
    根据关键词生成帖子
    
    流程：
    1. 先从本地数据库搜索匹配关键词的帖子
    2. 如果本地数据不够，再执行全站抓取（复用数据抓取功能的方式）
    3. 将新抓取的数据保存到本地数据库
    4. 用AI分析生成与关键词、子版块高度相关的帖子内容
    
    Args:
        analyzer: AI分析器
        keyword_groups: 关键词组列表（每个组是逗号分隔的字符串）
        count: 生成数量
        analysis_types: 分析类型列表
        provider: AI提供商
    
    Returns:
        生成的帖子列表
    """
    try:
        # 清理关键词组
        cleaned_groups = []
        for group in keyword_groups:
            if group.strip():
                keywords = [k.strip() for k in group.split(',') if k.strip()]
                if keywords:
                    cleaned_groups.append(keywords)
        
        if not cleaned_groups:
            return []
        
        db = st.session_state.db
        scraper = st.session_state.get('scraper')
        
        if not db:
            logger.error("数据库未初始化")
            return []
        
        if not scraper:
            logger.error("Reddit抓取器未初始化")
            return []
        
        # 步骤1: 先从本地数据库搜索匹配关键词的帖子
        all_posts_data = []
        all_subreddits = set()  # 收集所有子版块
        
        for keyword_list in cleaned_groups:
            try:
                # 从本地数据库搜索
                db_posts = db.get_posts_with_filters(
                    keywords=keyword_list,
                    limit=100  # 每个关键词组最多100条
                )
                
                logger.info(f"从本地数据库找到 {len(db_posts)} 条匹配关键词 {keyword_list} 的帖子")
                
                # 转换为字典格式并获取评论
                for post in db_posts:
                    post_dict = {
                        'id': post.id,  # RedditPost的主键是id
                        'title': post.title,
                        'author': post.author,
                        'score': post.score,
                        'upvote_ratio': getattr(post, 'upvote_ratio', 0.0),
                        'num_comments': post.num_comments,
                        'created_utc': post.created_utc,
                        'url': post.url,
                        'selftext': post.selftext,
                        'subreddit': post.subreddit,
                        'flair': getattr(post, 'flair', None),
                        'search_query': ', '.join(keyword_list)
                    }
                    
                    # 获取评论
                    comments = db.get_comments_by_post_id(post.id)
                    post_dict['comments'] = [
                        {
                            'id': c.id,  # RedditComment的主键是id
                            'body': c.body,
                            'author': c.author,
                            'score': c.score,
                            'created_utc': c.created_utc,
                            'parent_id': getattr(c, 'parent_id', None)
                        }
                        for c in comments[:50]  # 限制评论数量
                    ]
                    
                    all_posts_data.append(post_dict)
                    all_subreddits.add(post.subreddit)
                    
            except Exception as e:
                logger.error(f"从本地数据库搜索关键词 {keyword_list} 失败: {str(e)}")
                continue
        
        # 步骤2: 如果本地数据不够（少于50条），执行全站抓取
        min_required_posts = 50
        if len(all_posts_data) < min_required_posts:
            st.info(f"📡 本地数据不足（{len(all_posts_data)}条），开始全站抓取...")
            
            # 计算需要抓取的数量（注意API限制）
            need_more = min_required_posts - len(all_posts_data)
            # 每个关键词组抓取数量，限制在300-500之间
            posts_per_keyword = min(max(need_more // len(cleaned_groups), 100), 500)
            
            seen_post_ids = {p.get('id') for p in all_posts_data}  # 去重
            
            for keyword_list in cleaned_groups:
                try:
                    # 使用关键词组中的第一个关键词进行全站搜索（避免过多API请求）
                    search_query = keyword_list[0] if keyword_list else ''
                    if not search_query:
                        continue
                    
                    st.info(f"🔍 正在全站搜索: '{search_query}'...")
                    
                    # 全站搜索（复用数据抓取的方式）
                    posts = scraper.search_all_posts(
                        query=search_query,
                        limit=posts_per_keyword,
                        sort='relevance',
                        months_back=6  # 限制在最近6个月内
                    )
                    
                    # 去重和筛选
                    new_posts = []
                    for post in posts:
                        post_id = post.get('id')
                        if post_id and post_id not in seen_post_ids:
                            seen_post_ids.add(post_id)
                            new_posts.append(post)
                    
                    # 保存新抓取的帖子到数据库
                    if new_posts:
                        db.save_posts(new_posts)
                        logger.info(f"已保存 {len(new_posts)} 条新帖子到数据库")
                        
                        # 抓取部分评论（避免过多请求）
                        posts_for_comments = new_posts[:20]  # 只抓取前20个帖子的评论
                        for post in posts_for_comments:
                            try:
                                post_id = post.get('id')
                                if post_id:
                                    comments = scraper.get_post_comments(
                                        post_id=post_id,
                                        limit=50
                                    )
                                    if comments:
                                        db.save_comments(comments)
                                        post['comments'] = comments
                                    else:
                                        post['comments'] = []
                            except Exception as e:
                                logger.warning(f"抓取评论失败: {str(e)}")
                                post['comments'] = []
                        
                        # 添加新抓取的帖子到分析数据
                        for post in new_posts:
                            post['search_query'] = ', '.join(keyword_list)
                            all_posts_data.append(post)
                            all_subreddits.add(post.get('subreddit', ''))
                    
                    logger.info(f"关键词 '{search_query}': 抓取到 {len(new_posts)} 个新帖子")
                    
                except Exception as e:
                    logger.error(f"全站抓取关键词 {keyword_list} 失败: {str(e)}")
                    continue
        
        if not all_posts_data:
            logger.warning("未找到相关帖子，无法生成内容")
            return []
        
        # AI分析并生成帖子
        generated_posts = []
        batch_id = str(uuid.uuid4())
        
        # 精简数据以减少token使用
        def simplify_post_data(posts_data, max_posts=15, max_comments_per_post=5, max_text_length=500):
            """
            精简帖子数据以减少token使用
            - 限制帖子数量
            - 限制每个帖子的评论数量
            - 截断过长的文本
            """
            simplified = []
            for post in posts_data[:max_posts]:
                # 只保留必要字段
                simple_post = {
                    'title': post.get('title', '')[:max_text_length],
                    'selftext': post.get('selftext', '')[:max_text_length],
                    'subreddit': post.get('subreddit', ''),
                    'score': post.get('score', 0),
                    'num_comments': post.get('num_comments', 0),
                    'search_query': post.get('search_query', '')
                }
                
                # 精简评论（只保留前几个高赞评论的摘要）
                comments = post.get('comments', [])[:max_comments_per_post]
                simple_comments = []
                for comment in comments:
                    body = comment.get('body', '')
                    if body:
                        # 截断过长的评论
                        if len(body) > max_text_length:
                            body = body[:max_text_length] + '...'
                        simple_comments.append({
                            'body': body,
                            'score': comment.get('score', 0)
                        })
                
                simple_post['top_comments'] = simple_comments
                simplified.append(simple_post)
            
            return simplified
        
        # 收集所有关键词
        all_keywords = []
        for kg in cleaned_groups:
            all_keywords.extend(kg)
        unique_keywords = list(set(all_keywords))
        
        # 收集子版块信息
        subreddit_list = sorted(list(all_subreddits))
        
        # 精简数据（减少到15个帖子，每个帖子最多5条评论）
        simplified_data = simplify_post_data(all_posts_data, max_posts=15, max_comments_per_post=5, max_text_length=500)
        
        # 序列化数据（处理datetime对象）
        serialized_data = serialize_for_json(simplified_data)
        
        # 估算token数（粗略估算：1个中文字符≈1.5 tokens，1个英文单词≈1.3 tokens）
        # 保守估算：使用字符数 * 1.5
        prompt_text = json.dumps(serialized_data, ensure_ascii=False, indent=2)
        estimated_tokens = len(prompt_text) * 1.5
        
        # 如果数据仍然太大，进一步精简
        # DeepSeek最大上下文：131072 tokens，留出30000给输出，10000给prompt，所以输入最多约90000
        MAX_INPUT_TOKENS = 90000
        if estimated_tokens > MAX_INPUT_TOKENS:
            # 动态调整：减少帖子数量和文本长度
            reduction_ratio = MAX_INPUT_TOKENS / estimated_tokens
            target_posts = max(5, int(15 * reduction_ratio))
            target_comments = max(2, int(5 * reduction_ratio))
            target_text_length = max(200, int(500 * reduction_ratio))
            
            simplified_data = simplify_post_data(
                all_posts_data, 
                max_posts=target_posts, 
                max_comments_per_post=target_comments, 
                max_text_length=target_text_length
            )
            serialized_data = serialize_for_json(simplified_data)
            logger.warning(f"数据过大（估算{estimated_tokens:.0f} tokens），已精简至 {target_posts} 个帖子，每个帖子最多 {target_comments} 条评论")
        
        analysis_prompt = f"""
基于以下Reddit帖子和评论数据，生成 {count} 篇高质量的帖子内容。

**关键词：** {', '.join(unique_keywords)}
**相关子版块：** {', '.join(subreddit_list[:15])}
**分析类型：** {', '.join(analysis_types)}

**帖子数据摘要（已精简，包含帖子和高赞评论）：**
{json.dumps(serialized_data, ensure_ascii=False, indent=2)}

**重要要求：**
1. 每篇帖子必须与关键词高度相关，内容要围绕这些关键词展开
2. 帖子内容要适合相关的子版块（{', '.join(subreddit_list[:10])}等），符合各子版块的讨论风格
3. 每篇帖子都要有吸引人的标题，标题要包含或暗示关键词
4. 内容要基于真实用户讨论和评论，但要有原创性和独特性
5. 内容要符合Reddit社区规范和各个子版块的规则
6. 每篇帖子长度适中（200-500字），要有价值，能引发讨论
7. 分析用户痛点、需求、情绪等，生成能引起共鸣的内容
8. 内容要自然、真实，避免明显的营销或推广痕迹

**生成策略：**
- 分析数据中的用户痛点、需求、情绪
- 提取高频讨论话题和关注点
- 结合关键词和子版块特点生成内容
- 确保内容与关键词、子版块高度相关

请返回JSON格式：
{{
    "posts": [
        {{
            "title": "帖子标题（必须与关键词相关）",
            "content": "帖子内容（200-500字，与关键词和子版块高度相关）",
            "suggested_subreddits": ["子版块1", "子版块2"],
            "keywords_used": ["关键词1", "关键词2"]
        }},
        ...
    ]
}}
"""
        
        # 调用AI生成
        result = analyzer._call_llm(analysis_prompt, provider, "post_generation")
        
        # 检查是否有错误
        if isinstance(result, dict) and "error" in result:
            error_msg = result.get("error", "未知错误")
            last_error = result.get("last_error", "")
            logger.error(f"AI生成失败: {error_msg}")
            if last_error:
                logger.error(f"最后错误详情: {last_error}")
            # 不在这里使用st，错误会在UI层显示
            return []
        
        # 解析结果
        posts_data = []
        if isinstance(result, dict):
            # 优先使用parsed字段（如果存在）
            if 'parsed' in result:
                parsed = result['parsed']
                if isinstance(parsed, dict):
                    posts_data = parsed.get('posts', [])
            # 其次使用content字段
            elif 'content' in result:
                content = result['content']
                if isinstance(content, str):
                    # 尝试提取JSON
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                            posts_data = parsed.get('posts', [])
                        except Exception as e:
                            logger.warning(f"解析JSON失败: {str(e)}")
                            posts_data = []
                    else:
                        posts_data = []
            # 直接包含posts字段
            elif 'posts' in result:
                posts_data = result.get('posts', [])
        elif isinstance(result, str):
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    posts_data = parsed.get('posts', [])
                except Exception as e:
                    logger.warning(f"解析JSON失败: {str(e)}")
                    posts_data = []
        
        # 如果仍然没有数据，记录详细信息
        if not posts_data:
            error_detail = f"响应类型: {type(result)}, 响应内容: {str(result)[:500]}"
            logger.warning(f"未能从AI响应中提取帖子数据。{error_detail}")
            # 不在这里使用st，错误会在UI层显示
            return []
        
        # 转换为标准格式
        for i, post_data in enumerate(posts_data[:count]):
            if isinstance(post_data, dict):
                # 提取建议的子版块和关键词
                suggested_subreddits = post_data.get('suggested_subreddits', [])
                keywords_used = post_data.get('keywords_used', [])
                
                # 如果没有提供，使用原始关键词组
                if not keywords_used:
                    keywords_used = unique_keywords
                
                generated_posts.append({
                    'temp_id': str(uuid.uuid4()),
                    'title': post_data.get('title', f'生成的帖子 {i+1}'),
                    'content': post_data.get('content', ''),
                    'content_type': 'text',
                    'status': 'draft',
                    'source': 'ai_generated',
                    'is_ai_generated': True,
                    'keywords': ', '.join(keywords_used) if keywords_used else ', '.join([', '.join(kg) for kg in cleaned_groups]),
                    'suggested_subreddits': suggested_subreddits if suggested_subreddits else list(all_subreddits)[:5],  # 默认使用前5个子版块
                    'generation_batch_id': batch_id,
                    'original_ai_prompt': analysis_prompt[:500],  # 保存部分提示词用于参考
                    'created_at': datetime.utcnow()
                })
        
        return generated_posts
        
    except Exception as e:
        logger.error(f"生成帖子失败: {str(e)}", exc_info=True)
        return []

def generate_enhanced_posts_from_keywords(analyzer, keyword_groups: List[str], 
                                         count: int, provider: str) -> tuple:
    """
    使用增强模式生成帖子
    
    Args:
        analyzer: AI分析器
        keyword_groups: 关键词组列表（每个组是逗号分隔的字符串）
        count: 生成数量
        provider: AI提供商
    
    Returns:
        (生成的帖子列表, 分析结果摘要)
    """
    try:
        # 清理关键词组
        cleaned_groups = []
        for group in keyword_groups:
            if group.strip():
                keywords = [k.strip() for k in group.split(',') if k.strip()]
                if keywords:
                    cleaned_groups.append(keywords)
        
        if not cleaned_groups:
            return [], {}
        
        # 合并所有关键词
        all_keywords = []
        for kg in cleaned_groups:
            all_keywords.extend(kg)
        unique_keywords = list(set(all_keywords))
        
        db = st.session_state.db
        scraper = st.session_state.get('scraper')
        
        if not db or not scraper:
            logger.error("数据库或Reddit抓取器未初始化")
            return [], {}
        
        # 创建增强生成器
        enhanced_generator = EnhancedAIGenerator(db, scraper, analyzer)
        
        # 创建进度显示
        progress_placeholder = st.empty()
        
        def progress_callback(message):
            progress_placeholder.info(f"⏳ {message}")
        
        # 执行增强生成
        generated_posts, analysis_summary = enhanced_generator.generate_enhanced_posts_from_keywords(
            unique_keywords,
            count=count,
            provider=provider,
            progress_callback=progress_callback
        )
        
        # 清除进度显示
        progress_placeholder.empty()
        
        return generated_posts, analysis_summary
        
    except Exception as e:
        logger.error(f"增强生成失败: {str(e)}", exc_info=True)
        return [], {}

def render_generation_results(post_manager: PostManager):
    """渲染生成结果区域"""
    st.subheader("📊 生成结果")
    
    # 获取AI生成的帖子
    generated_posts = PostingStateManager.get_ai_generated_posts()
    
    if not generated_posts:
        st.info("💡 请在左侧配置关键词并点击'开始生成'")
        return
    
    st.success(f"✅ 已生成 {len(generated_posts)} 篇帖子")
    
    # 显示增强模式的分析摘要
    if st.session_state.get('last_enhanced_analysis'):
        analysis_summary = st.session_state.get('last_enhanced_analysis', {})
        with st.expander("📊 分析摘要（增强模式）", expanded=False):
            st.markdown(f"**关键词：** {', '.join(analysis_summary.get('keywords', []))}")
            st.markdown(f"**分析的子版块数量：** {analysis_summary.get('subreddits_analyzed', 0)}")
            
            best_subreddits = analysis_summary.get('best_subreddits', [])
            if best_subreddits:
                # 保存前3个最佳子版块到历史记录
                try:
                    if st.session_state.get('db'):
                        # 准备保存的数据（前3个）
                        top_3_subreddits = best_subreddits[:3]
                        st.session_state.db.save_subreddits_to_history(
                            top_3_subreddits, 
                            source="ai_generator", 
                            top_n=3
                        )
                except Exception:
                    # 静默失败，不影响生成功能
                    pass
                
                st.markdown("**最佳子版块：**")
                for subreddit_info in best_subreddits:
                    st.markdown(f"""
                    - **r/{subreddit_info['subreddit']}**
                      - 匹配度: {subreddit_info['match_score']:.1f}/100
                      - 热度: {subreddit_info['heat_score']:.1f}/100
                      - 综合评分: {subreddit_info['combined_score']:.1f}/100
                    """)
    
    # 批量操作工具栏
    st.markdown("#### 批量操作")
    col_batch1, col_batch2, col_batch3, col_batch4 = st.columns(4)
    
    selected_indices = []
    for i, post in enumerate(generated_posts):
        if st.checkbox(f"选择帖子 {i+1}", key=f"select_post_{i}"):
            selected_indices.append(i)
    
    if selected_indices:
        with col_batch1:
            if st.button("🗑️ 批量删除", key="batch_delete"):
                generated_posts = [p for i, p in enumerate(generated_posts) if i not in selected_indices]
                PostingStateManager.set_ai_generated_posts(generated_posts)
                st.rerun()
        
        with col_batch2:
            if st.button("📋 批量复制", key="batch_copy"):
                st.info("📋 已复制到剪贴板（功能待实现）")
        
        with col_batch3:
            if st.button("💾 批量保存到计划", key="batch_save_schedule"):
                selected_posts = [generated_posts[i] for i in selected_indices]
                PostingStateManager.set_posts_for_schedule(selected_posts)
                st.session_state.posting_active_tab = "发布计划"
                st.success(f"✅ 已选择 {len(selected_posts)} 篇帖子，跳转到发布计划")
                st.rerun()

        with col_batch4:
            if st.button("⏰ 批量定时发布", type="primary", key="batch_schedule_publish"):
                st.session_state['show_batch_schedule_publish'] = True

    # 批量定时发布配置（滚动窗口：任意8小时最多4篇；相邻>=2小时）
    if st.session_state.get('show_batch_schedule_publish'):
        with st.expander("⏰ 批量定时发布（自动排程：2小时/篇；任意8小时最多4篇）", expanded=True):
            analysis_summary = st.session_state.get('last_enhanced_analysis', {}) or {}
            best_subreddits = analysis_summary.get('best_subreddits', []) or []
            default_subs = [s.get('subreddit') for s in best_subreddits[:3] if isinstance(s, dict) and s.get('subreddit')]
            # fallback：从生成帖元数据里拿
            if not default_subs:
                for p in generated_posts:
                    meta = p.get('generation_metadata', {}) if isinstance(p, dict) else {}
                    subs = meta.get('selected_subreddits') if isinstance(meta, dict) else None
                    if subs:
                        default_subs = [str(x) for x in subs[:3]]
                        break

            subreddits_input = st.text_input(
                "目标子版块（最多3个，用逗号分隔）",
                value=", ".join(default_subs) if default_subs else "",
                help="例如: subreddit1, subreddit2, subreddit3（不需要写r/，可选择1-3个子版块）",
                key="batch_publish_subreddits"
            )

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                start_date = st.date_input("开始日期（UTC）", value=datetime.utcnow().date(), key="batch_publish_start_date")
            with col_t2:
                start_time = st.time_input("开始时间（UTC）", value=datetime.utcnow().time().replace(second=0, microsecond=0), key="batch_publish_start_time")

            auto_start_service = st.checkbox(
                "创建计划后启动自动发帖后台服务（推荐）",
                value=True,
                help="只要应用在运行，后台会自动按计划发布，无需停留在页面",
                key="batch_publish_autostart"
            )

            col_do1, col_do2 = st.columns(2)
            with col_do1:
                if st.button("✅ 创建发布计划", type="primary", key="batch_publish_confirm"):
                    try:
                        subs = [s.strip() for s in (subreddits_input or "").split(",") if s.strip()]
                        if len(subs) == 0:
                            st.error("请至少填写1个子版块")
                            return
                        if len(subs) > 3:
                            st.error("最多只能选择3个子版块")
                            return
                            return

                        selected_posts = [generated_posts[i] for i in selected_indices] if selected_indices else []
                        if not selected_posts:
                            st.error("请先勾选要发布的帖子")
                            return

                        # 确保帖子已存在于数据库，并拿到 post_content_id
                        post_ids = []
                        for p in selected_posts:
                            if not isinstance(p, dict):
                                continue
                            pid = p.get('id')
                            if not pid:
                                pid = post_manager.create_post(
                                    title=p.get('title', ''),
                                    content=p.get('content', ''),
                                    source=p.get('source', 'ai_generated'),
                                    is_ai_generated=bool(p.get('is_ai_generated', True)),
                                    keywords=p.get('keywords'),
                                    status='ready',
                                    generation_metadata=p.get('generation_metadata', {})
                                )
                                if pid:
                                    p['id'] = pid
                            if pid:
                                post_ids.append(int(pid))

                        if not post_ids:
                            st.error("无法获取帖子ID，创建计划失败")
                            return

                        scheduled_dt = datetime.combine(start_date, start_time)

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

                        from modules.posting.shared.schedule_manager import ScheduleManager
                        schedule_manager = ScheduleManager(st.session_state.db)
                        created_ids = schedule_manager.create_schedules_for_posts(
                            post_ids=post_ids,
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
                            st.success(f"✅ 已创建 {len(created_ids)} 条发布计划（{len(post_ids)} 篇帖子 × {len(subs)}个子版块）")
                        else:
                            st.warning("未创建任何计划（可能帖子内容缺失）")

                        # 可选：启动后台服务
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

                        st.session_state['show_batch_schedule_publish'] = False
                    except Exception as e:
                        st.error(f"创建计划失败: {str(e)}")

            with col_do2:
                if st.button("取消", key="batch_publish_cancel"):
                    st.session_state['show_batch_schedule_publish'] = False
    
    # 显示帖子列表
    st.markdown("---")
    st.markdown("#### 帖子列表")
    
    for i, post in enumerate(generated_posts):
        if post.get('_deleted', False):
            continue
        
        # 使用post的唯一ID作为key的一部分，避免重复
        post_id = post.get('temp_id', post.get('id', f'post_{i}_{hash(str(post))}'))
        post_key_suffix = str(post_id).replace('-', '_').replace(' ', '_')  # 替换特殊字符
        
        with st.expander(f"📝 {post.get('title', '无标题')[:50]}...", expanded=False):
            # 标题编辑
            title_key = f"edit_title_{post_key_suffix}"
            title = st.text_input("标题", value=post.get('title', ''), key=title_key)
            post['title'] = title
            
            # 内容编辑
            content_key = f"edit_content_{post_key_suffix}"
            content = st.text_area("内容", value=post.get('content', ''), height=200, key=content_key)
            post['content'] = content
            
            # 显示增强模式的评分信息
            if post.get('source') == 'ai_generated_enhanced':
                col_score1, col_score2, col_score3, col_score4 = st.columns(4)
                with col_score1:
                    st.metric("匹配度", f"{post.get('match_score', 0):.1f}")
                with col_score2:
                    st.metric("热度", f"{post.get('heat_score', 0):.1f}")
                with col_score3:
                    st.metric("主题一致性", f"{post.get('topic_consistency_score', 0):.1f}")
                with col_score4:
                    st.metric("规则符合度", f"{post.get('rule_compliance_score', 0):.1f}")
                
                if post.get('target_subreddit'):
                    st.info(f"🎯 目标子版块: r/{post.get('target_subreddit')}")
                
                metadata = post.get('generation_metadata', {})
                if metadata.get('core_topic'):
                    st.caption(f"核心主题: {metadata.get('core_topic')}")
            
            # 操作按钮
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("🗑️ 删除", key=f"delete_{post_key_suffix}"):
                    post['_deleted'] = True
                    st.rerun()
            
            with col2:
                if st.button("📋 复制", key=f"copy_{post_key_suffix}"):
                    st.info("📋 已复制（功能待实现）")
            
            with col3:
                if st.button("🔗 链接", key=f"link_{post_key_suffix}"):
                    st.info("🔗 链接已复制（功能待实现）")
            
            with col4:
                if st.button("💾 保存到库", key=f"save_lib_{post_key_suffix}"):
                    saved_post_id = post_manager.create_post(
                        title=post.get('title', ''),
                        content=post.get('content', ''),
                        source='ai_generated',
                        is_ai_generated=True,
                        keywords=post.get('keywords'),
                        generation_batch_id=post.get('generation_batch_id')
                    )
                    if saved_post_id:
                        st.success(f"✅ 已保存到帖子库（ID: {saved_post_id}）")
            
            with col5:
                if st.button("💾 保存到计划", key=f"save_schedule_{post_key_suffix}"):
                    PostingStateManager.set_posts_for_schedule([post])
                    st.session_state.posting_active_tab = "发布计划"
                    st.success("✅ 已选择，跳转到发布计划")
                    st.rerun()
    
    # 添加新帖子按钮
    st.markdown("---")
    if st.button("➕ 添加新帖子", key="add_new_post"):
        new_post = post_manager.create_temp_post("新帖子标题", "新帖子内容")
        generated_posts.append(new_post)
        PostingStateManager.set_ai_generated_posts(generated_posts)
        st.rerun()
    
    # 更新session_state
    PostingStateManager.set_ai_generated_posts([p for p in generated_posts if not p.get('_deleted', False)])


