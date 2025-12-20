"""
Tab4: 子版块推荐模块
"""
import streamlit as st

def render_subreddit_recommendation_tab():
    """渲染子版块推荐页面"""
    try:
        st.header("🎯 子版块推荐")
        
        if not st.session_state.initialized:
            st.warning("⚠️ 请先配置API密钥并初始化系统")
            st.info("💡 请在左侧边栏配置Reddit API密钥，然后点击'初始化系统'按钮")
            return
        
        # 初始化子版块推荐器
        if 'subreddit_recommender' not in st.session_state:
            try:
                from subreddit_recommender import SubredditRecommender
                st.session_state.subreddit_recommender = SubredditRecommender(st.session_state.db)
            except ImportError:
                st.warning("⚠️ 子版块推荐模块未找到")
                return
            except Exception as e:
                st.error(f"❌ 初始化子版块推荐器失败: {str(e)}")
                return
        
        # 推荐方式选择
        recommendation_method = st.radio(
            "选择推荐方式",
            ["智能需求分析", "基于关键词数据推荐"],
            horizontal=True
        )
        
        if recommendation_method == "智能需求分析":
            st.subheader("🧠 智能需求分析")
            
            # 检查是否有LLM分析器
            if not hasattr(st.session_state, 'analyzer') or not st.session_state.analyzer:
                st.warning("⚠️ AI大模型未初始化，无法使用智能需求分析功能")
                st.info("💡 请确保已配置AI大模型API密钥（如DeepSeek、OpenAI等）")
                return
            
            # 初始化需求分析器
            if 'demand_analyzer' not in st.session_state:
                try:
                    from demand_analyzer import DemandAnalyzer
                    st.session_state.demand_analyzer = DemandAnalyzer(st.session_state.analyzer)
                except ImportError:
                    st.warning("⚠️ 需求分析模块未找到")
                    return
                except Exception as e:
                    st.error(f"❌ 初始化需求分析器失败: {str(e)}")
                    return
            
            user_query = st.text_area(
                "输入您的需求（支持中文）",
                placeholder="例如：我想了解iPhone电池更换的相关信息",
                help="用中文描述您的需求，AI大模型会自动翻译、分析意图并推荐相关子版块"
            )
            
            top_k = st.slider("推荐数量", min_value=5, max_value=30, value=10)
            
            if st.button("🔍 开始推荐", type="primary"):
                if not user_query.strip():
                    st.error("❌ 请输入您的需求")
                else:
                    # 步骤1: 使用AI大模型分析需求
                    with st.spinner("🤖 AI正在分析您的需求（翻译、提取关键词、分析意图）..."):
                        try:
                            demand_analysis = st.session_state.demand_analyzer.analyze_demand(user_query)
                            
                            # 显示分析结果
                            with st.expander("📊 AI需求分析结果", expanded=False):
                                st.write(f"**英文翻译**: {demand_analysis.get('translation', 'N/A')}")
                                st.write(f"**提取的关键词**: {', '.join(demand_analysis.get('keywords', []))}")
                                st.write(f"**用户意图**: {demand_analysis.get('intent', 'N/A')}")
                            
                            # 步骤2: 基于AI分析结果进行推荐
                            # 优先使用AI分析结果中的推荐子版块
                            ai_recommendations = []
                            funnel_candidates = demand_analysis.get('funnel_candidates', {})
                            
                            # 收集所有AI推荐的子版块
                            raw_ai_recommendations = []
                            for match_type in ['high_match', 'medium_match', 'low_match']:
                                candidates = funnel_candidates.get(match_type, [])
                                for candidate in candidates[:top_k]:
                                    raw_ai_recommendations.append({
                                        'subreddit': candidate.get('name', ''),
                                        'match_score': candidate.get('match_score', 0),
                                        'reason': candidate.get('reason', ''),
                                        'description': candidate.get('description', ''),
                                        'category': candidate.get('category', ''),
                                        'match_type': match_type
                                    })
                            
                            # 步骤2.5: 验证AI推荐的子版块是否真实存在于Reddit
                            if raw_ai_recommendations:
                                st.info(f"🔍 正在验证 {len(raw_ai_recommendations)} 个AI推荐的子版块是否存在于Reddit...")
                                
                                verified_recommendations = []
                                invalid_subreddits = []
                                
                                # 检查是否有Reddit scraper
                                if not hasattr(st.session_state, 'scraper') or not st.session_state.scraper:
                                    st.warning("⚠️ Reddit API未初始化，无法验证子版块是否存在")
                                    st.info("💡 请先完成Reddit API认证")
                                    ai_recommendations = raw_ai_recommendations  # 使用原始推荐
                                else:
                                    # 创建进度条
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    for idx, rec in enumerate(raw_ai_recommendations):
                                        subreddit_name = rec.get('subreddit', '').strip()
                                        if not subreddit_name:
                                            continue
                                        
                                        # 更新进度
                                        progress = (idx + 1) / len(raw_ai_recommendations)
                                        progress_bar.progress(progress)
                                        status_text.text(f"正在验证 r/{subreddit_name}... ({idx + 1}/{len(raw_ai_recommendations)})")
                                        
                                        try:
                                            # 调用Reddit API验证子版块是否存在
                                            subreddit_info = st.session_state.scraper.get_subreddit_info(subreddit_name)
                                            
                                            if subreddit_info and subreddit_info.get('name'):
                                                # 子版块存在，添加到验证通过的列表
                                                rec['reddit_info'] = subreddit_info  # 保存Reddit API返回的信息
                                                verified_recommendations.append(rec)
                                            else:
                                                # 子版块不存在
                                                invalid_subreddits.append({
                                                    'name': subreddit_name,
                                                    'match_score': rec.get('match_score', 0),
                                                    'reason': rec.get('reason', '')
                                                })
                                        except Exception as e:
                                            # 验证失败，视为不存在
                                            invalid_subreddits.append({
                                                'name': subreddit_name,
                                                'match_score': rec.get('match_score', 0),
                                                'reason': rec.get('reason', ''),
                                                'error': str(e)
                                            })
                                    
                                    # 清除进度条
                                    progress_bar.empty()
                                    status_text.empty()
                                    
                                    # 显示验证结果统计
                                    if invalid_subreddits:
                                        st.warning(f"⚠️ 发现 {len(invalid_subreddits)} 个不存在的子版块，已跳过：")
                                        for invalid in invalid_subreddits:
                                            st.write(f"- r/{invalid['name']} (匹配度: {invalid['match_score']}分) - {invalid.get('reason', 'N/A')}")
                                    
                                    if verified_recommendations:
                                        st.success(f"✅ 验证完成：{len(verified_recommendations)} 个子版块存在，{len(invalid_subreddits)} 个不存在")
                                        ai_recommendations = verified_recommendations
                                    else:
                                        st.error("❌ 所有AI推荐的子版块都不存在于Reddit中")
                                        ai_recommendations = []
                            else:
                                ai_recommendations = []
                            
                            # 如果AI推荐了子版块，优先显示
                            if ai_recommendations:
                                st.success(f"✅ AI分析完成，找到 {len(ai_recommendations)} 个已验证存在的推荐子版块")
                                
                                # 按匹配度排序
                                ai_recommendations.sort(key=lambda x: x.get('match_score', 0), reverse=True)
                                
                                # 保存前5个推荐子版块到历史记录
                                try:
                                    if st.session_state.get('db'):
                                        # 准备保存的数据（前5个）
                                        top_5_recommendations = ai_recommendations[:5]
                                        for rec in top_5_recommendations:
                                            rec['subreddit_name'] = rec.get('subreddit', '')
                                        st.session_state.db.save_subreddits_to_history(
                                            top_5_recommendations, 
                                            source="subreddit_recommendation", 
                                            top_n=5
                                        )
                                except Exception as e:
                                    # 静默失败，不影响推荐功能
                                    pass
                                
                                for i, rec in enumerate(ai_recommendations[:top_k], 1):
                                    match_type_label = {
                                        'high_match': '高度匹配',
                                        'medium_match': '中度匹配',
                                        'low_match': '低度匹配'
                                    }.get(rec.get('match_type', ''), '')
                                    
                                    subreddit_name = rec.get('subreddit', 'N/A')
                                    
                                    with st.expander(f"#{i} r/{subreddit_name} - {match_type_label} ({rec.get('match_score', 0)}分) ✅已验证"):
                                        st.write(f"**匹配度**: {rec.get('match_score', 0)}分")
                                        st.write(f"**匹配类型**: {match_type_label}")
                                        st.write(f"**推荐理由**: {rec.get('reason', 'N/A')}")
                                        
                                        # 显示Reddit API返回的真实信息
                                        if rec.get('reddit_info'):
                                            reddit_info = rec['reddit_info']
                                            st.write("**Reddit子版块信息**:")
                                            st.write(f"- **标题**: {reddit_info.get('title', 'N/A')}")
                                            st.write(f"- **订阅者**: {reddit_info.get('subscribers', 0):,}")
                                            if reddit_info.get('public_description'):
                                                st.write(f"- **描述**: {reddit_info.get('public_description', '')[:200]}...")
                                        
                                        if rec.get('description'):
                                            st.write(f"**AI描述**: {rec.get('description', 'N/A')}")
                                        if rec.get('category'):
                                            st.write(f"**分类**: {rec.get('category', 'N/A')}")
                                        
                                        # 显示子版块详情（如果已索引）
                                        if hasattr(st.session_state, 'subreddit_recommender') and st.session_state.subreddit_recommender:
                                            try:
                                                details = st.session_state.subreddit_recommender.get_subreddit_details(subreddit_name)
                                                if details:
                                                    st.write("**已索引数据**:")
                                                    st.json(details)
                                            except:
                                                pass
                            
                            # 步骤3: 如果已索引了子版块，也使用向量匹配进行补充推荐
                            if hasattr(st.session_state, 'subreddit_recommender') and st.session_state.subreddit_recommender:
                                # 使用AI分析结果中的翻译文本进行向量匹配
                                translation = demand_analysis.get('translation', user_query)
                                keywords_text = ' '.join(demand_analysis.get('keywords', []))
                                search_query = f"{translation} {keywords_text}".strip()
                                
                                with st.spinner("🔍 基于已索引数据补充推荐..."):
                                    try:
                                        vector_recommendations = st.session_state.subreddit_recommender.recommend(search_query, top_k=top_k)
                                        
                                        if vector_recommendations:
                                            # 过滤掉AI已经推荐过的子版块
                                            ai_recommended_names = {r.get('subreddit', '').lower() for r in ai_recommendations}
                                            new_recommendations = [
                                                r for r in vector_recommendations 
                                                if r.get('subreddit_name', '').lower() not in ai_recommended_names
                                            ]
                                            
                                            if new_recommendations:
                                                st.info(f"💡 基于已索引数据补充推荐 {len(new_recommendations)} 个子版块")
                                                
                                                # 保存前5个补充推荐子版块到历史记录
                                                try:
                                                    if st.session_state.get('db'):
                                                        # 准备保存的数据（前5个）
                                                        top_5_supplement = new_recommendations[:5]
                                                        st.session_state.db.save_subreddits_to_history(
                                                            top_5_supplement, 
                                                            source="subreddit_recommendation", 
                                                            top_n=5
                                                        )
                                                except Exception:
                                                    pass
                                                
                                                for i, rec in enumerate(new_recommendations[:5], 1):  # 最多显示5个补充推荐
                                                    with st.expander(f"补充推荐 #{i} r/{rec.get('subreddit_name', 'N/A')} - 匹配度: {rec.get('score', 0):.1%}"):
                                                        st.write(f"**匹配度**: {rec.get('score', 0):.1%}")
                                                        st.write(f"**推荐理由**: {rec.get('reason', 'N/A')}")
                                                        
                                                        # 显示子版块详情
                                                        try:
                                                            details = st.session_state.subreddit_recommender.get_subreddit_details(rec.get('subreddit_name'))
                                                            if details:
                                                                st.json(details)
                                                        except:
                                                            pass
                                    except Exception as e:
                                        # 向量匹配失败不影响AI推荐结果
                                        pass
                            
                            # 如果没有AI推荐，也没有向量推荐，显示提示
                            if not ai_recommendations:
                                st.warning("⚠️ AI未找到匹配的子版块，建议：")
                                st.info("1. 尝试更具体地描述您的需求\n2. 使用英文关键词进行搜索\n3. 使用'基于关键词数据推荐'功能")
                                
                        except Exception as e:
                            st.error(f"❌ AI分析失败: {str(e)}")
                            import traceback
                            with st.expander("查看错误详情"):
                                st.code(traceback.format_exc())
                            
                            # 如果AI分析失败，尝试使用向量匹配作为备选
                            st.info("💡 尝试使用向量匹配进行推荐...")
                            try:
                                if hasattr(st.session_state, 'subreddit_recommender') and st.session_state.subreddit_recommender:
                                    recommendations = st.session_state.subreddit_recommender.recommend(user_query, top_k=top_k)
                                    
                                    if recommendations:
                                        st.success(f"✅ 找到 {len(recommendations)} 个推荐子版块（基于向量匹配）")
                                        
                                        # 保存前5个推荐子版块到历史记录
                                        try:
                                            if st.session_state.get('db'):
                                                st.session_state.db.save_subreddits_to_history(
                                                    recommendations, 
                                                    source="subreddit_recommendation", 
                                                    top_n=5
                                                )
                                        except Exception:
                                            pass
                                        
                                        for i, rec in enumerate(recommendations, 1):
                                            with st.expander(f"#{i} r/{rec.get('subreddit_name', 'N/A')} - 匹配度: {rec.get('score', 0):.1%}"):
                                                st.write(f"**匹配度**: {rec.get('score', 0):.1%}")
                                                st.write(f"**推荐理由**: {rec.get('reason', 'N/A')}")
                                                
                                                # 显示子版块详情
                                                try:
                                                    details = st.session_state.subreddit_recommender.get_subreddit_details(rec.get('subreddit_name'))
                                                    if details:
                                                        st.json(details)
                                                except:
                                                    pass
                                    else:
                                        st.warning("⚠️ 未找到匹配的子版块，请尝试其他关键词")
                            except Exception as e2:
                                st.error(f"❌ 向量匹配也失败: {str(e2)}")
        
        else:  # 基于关键词数据推荐
            st.subheader("📊 基于关键词数据推荐")
            
            try:
                from keyword_based_recommender import KeywordBasedRecommender
                
                if 'keyword_recommender' not in st.session_state:
                    st.session_state.keyword_recommender = KeywordBasedRecommender(st.session_state.db, st.session_state.analyzer)
                
                # 获取数据库中的关键词
                session = st.session_state.db.get_session()
                try:
                    # 从分析结果中获取关键词（这里简化处理，实际应该从数据库查询）
                    search_keyword = st.text_input(
                        "输入关键词",
                        placeholder="例如：iPhone battery replacement",
                        help="输入要搜索的关键词"
                    )
                    
                    top_k = st.slider("推荐数量", min_value=5, max_value=30, value=10, key="keyword_top_k")
                    
                    if st.button("🔍 开始推荐", type="primary", key="keyword_recommend"):
                        if not search_keyword.strip():
                            st.error("❌ 请输入关键词")
                        else:
                            # 保存关键词到历史记录
                            try:
                                if st.session_state.get('db'):
                                    st.session_state.db.save_keywords_to_history(search_keyword, source="subreddit_recommendation")
                            except Exception:
                                pass  # 静默失败，不影响推荐流程
                            
                            with st.spinner("正在分析关键词热度并推荐子版块..."):
                                try:
                                    recommendations = st.session_state.keyword_recommender.analyze_and_recommend(
                                        search_keyword, top_k=top_k
                                    )
                                    
                                    if recommendations:
                                        st.success(f"✅ 找到 {len(recommendations)} 个推荐子版块")
                                        
                                        for rec in recommendations:
                                            with st.expander(f"#{rec.get('rank', 0)} r/{rec.get('subreddit', 'N/A')} - 热度: {rec.get('heat_score', 0):.1f}"):
                                                st.write(f"**热度分数**: {rec.get('heat_score', 0):.1f}")
                                                st.write(f"**帖子数**: {rec.get('post_count', 0)}")
                                                st.write(f"**平均分数**: {rec.get('avg_score', 0):.1f}")
                                                st.write(f"**推荐理由**: {rec.get('reason', 'N/A')}")
                                    else:
                                        st.warning("⚠️ 未找到匹配的子版块，请尝试其他关键词")
                                except Exception as e:
                                    st.error(f"❌ 推荐失败: {str(e)}")
                                    import traceback
                                    with st.expander("查看错误详情"):
                                        st.code(traceback.format_exc())
                finally:
                    session.close()
            except ImportError:
                st.warning("⚠️ 关键词推荐模块未找到")
            except Exception as e:
                st.error(f"❌ 加载关键词推荐模块失败: {str(e)}")
                import traceback
                with st.expander("查看错误详情"):
                    st.code(traceback.format_exc())
    except Exception as e:
        st.error(f"❌ 子版块推荐页面加载失败: {str(e)}")
        import traceback
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())

