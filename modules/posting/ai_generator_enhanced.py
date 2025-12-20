"""
增强AI内容生成模块
实现全站抓取、子版块分析、主题一致性检查和规则检查的完整流程
"""
import streamlit as st
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import uuid
from collections import defaultdict

from modules.posting.shared.post_manager import PostManager
from modules.posting.shared.rule_checker import SubredditRuleChecker

logger = logging.getLogger(__name__)


class EnhancedAIGenerator:
    """增强的AI生成器"""
    
    def __init__(self, db_manager, scraper, analyzer):
        """
        初始化增强生成器
        
        Args:
            db_manager: 数据库管理器
            scraper: RedditScraper实例
            analyzer: LLMAnalyzer实例
        """
        self.db = db_manager
        self.scraper = scraper
        self.analyzer = analyzer
        self.rule_checker = SubredditRuleChecker(db_manager, analyzer, scraper)
    
    def fetch_posts_by_keywords(self, keywords: List[str], limit_per_keyword: int = 300) -> Dict[str, List[Dict[str, Any]]]:
        """
        全站抓取与关键词相关的帖子，按子版块分组
        
        Args:
            keywords: 关键词列表
            limit_per_keyword: 每个关键词抓取的数量
        
        Returns:
            按子版块分组的帖子字典 {subreddit: [posts]}
        """
        all_posts_by_subreddit = defaultdict(list)
        seen_post_ids = set()
        
        for keyword in keywords:
            try:
                logger.info(f"开始全站搜索关键词: {keyword}")
                
                # 使用全站搜索
                posts = self.scraper.search_all_posts(
                    query=keyword,
                    limit=limit_per_keyword,
                    sort='relevance',
                    months_back=6
                )
                
                # 按子版块分组并去重
                for post in posts:
                    post_id = post.get('id')
                    if not post_id or post_id in seen_post_ids:
                        continue
                    
                    seen_post_ids.add(post_id)
                    subreddit = post.get('subreddit', '').lower()
                    if subreddit:
                        all_posts_by_subreddit[subreddit].append(post)
                
                logger.info(f"关键词 '{keyword}': 抓取到 {len(posts)} 条帖子")
                
            except Exception as e:
                logger.error(f"抓取关键词 '{keyword}' 失败: {str(e)}")
                continue
        
        # 保存到数据库
        all_posts = []
        for subreddit, posts in all_posts_by_subreddit.items():
            all_posts.extend(posts)
        
        if all_posts:
            try:
                self.db.save_posts(all_posts)
                logger.info(f"已保存 {len(all_posts)} 条帖子到数据库")
            except Exception as e:
                logger.error(f"保存帖子到数据库失败: {str(e)}")
        
        return dict(all_posts_by_subreddit)
    
    def calculate_subreddit_statistics(self, posts_by_subreddit: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
        """
        计算每个子版块的统计信息
        
        Args:
            posts_by_subreddit: 按子版块分组的帖子
        
        Returns:
            子版块统计信息字典
        """
        stats = {}
        
        for subreddit, posts in posts_by_subreddit.items():
            if not posts:
                continue
            
            total_posts = len(posts)
            total_score = sum(p.get('score', 0) for p in posts)
            total_comments = sum(p.get('num_comments', 0) for p in posts)
            
            avg_score = total_score / total_posts if total_posts > 0 else 0
            avg_comments = total_comments / total_posts if total_posts > 0 else 0
            
            # 计算热度评分（综合指标）
            # 热度 = 平均分数 * 0.4 + 平均评论数 * 0.3 + 帖子总数 * 0.3（归一化）
            # 归一化：将分数和评论数缩放到0-100范围
            normalized_score = min(avg_score / 100.0 * 100, 100)  # 假设100分为满分
            normalized_comments = min(avg_comments / 50.0 * 100, 100)  # 假设50条评论为满分
            normalized_count = min(total_posts / 200.0 * 100, 100)  # 假设200条帖子为满分
            
            heat_score = (normalized_score * 0.4 + normalized_comments * 0.3 + normalized_count * 0.3)
            
            stats[subreddit] = {
                'subreddit': subreddit,
                'post_count': total_posts,
                'avg_score': round(avg_score, 2),
                'avg_comments': round(avg_comments, 2),
                'total_comments': total_comments,
                'heat_score': round(heat_score, 2),
                'sample_posts': posts[:10]  # 保留前10个帖子作为样本
            }
        
        return stats
    
    def analyze_subreddit_match(self, keywords: List[str], subreddit_stats: Dict[str, Dict[str, Any]], 
                                provider: str = "deepseek") -> Dict[str, float]:
        """
        使用AI分析子版块与关键词的匹配度
        
        Args:
            keywords: 关键词列表
            subreddit_stats: 子版块统计信息
            provider: AI提供商
        
        Returns:
            子版块匹配度评分字典 {subreddit: match_score}
        """
        match_scores = {}
        
        # 为每个子版块准备样本数据
        for subreddit, stats in subreddit_stats.items():
            sample_posts = stats.get('sample_posts', [])
            if not sample_posts:
                match_scores[subreddit] = 0.0
                continue
            
            # 准备样本文本（标题+内容摘要）
            sample_texts = []
            for post in sample_posts[:5]:  # 只取前5个作为样本
                title = post.get('title', '')
                selftext = post.get('selftext', '')[:200]  # 限制长度
                sample_texts.append(f"标题: {title}\n内容: {selftext}")
            
            sample_text = "\n\n".join(sample_texts)
            
            # 构建AI分析提示词
            prompt = f"""
请分析以下Reddit子版块 r/{subreddit} 与关键词的匹配度。

**关键词：** {', '.join(keywords)}

**子版块样本帖子（前5条）：**
{sample_text}

**子版块统计：**
- 帖子总数: {stats['post_count']}
- 平均分数: {stats['avg_score']}
- 平均评论数: {stats['avg_comments']}

**分析要求：**
1. 评估关键词与子版块主题的相关性（0-100分）
2. 考虑子版块讨论的内容是否围绕这些关键词
3. 考虑关键词是否是该子版块的核心话题

**请返回JSON格式：**
{{
    "match_score": 85,
    "reasoning": "分析原因（为什么是这个分数）"
}}
"""
            
            try:
                result = self.analyzer._call_llm(prompt, provider, "subreddit_match_analysis")
                
                # 解析结果
                match_score = 0.0
                if isinstance(result, dict):
                    if 'parsed' in result:
                        parsed = result['parsed']
                        match_score = parsed.get('match_score', 0.0)
                    elif 'match_score' in result:
                        match_score = result.get('match_score', 0.0)
                    elif 'content' in result:
                        # 尝试从字符串中提取JSON
                        import re
                        json_match = re.search(r'\{.*\}', result['content'], re.DOTALL)
                        if json_match:
                            try:
                                parsed = json.loads(json_match.group())
                                match_score = parsed.get('match_score', 0.0)
                            except:
                                pass
                elif isinstance(result, str):
                    import re
                    json_match = re.search(r'\{.*\}', result, re.DOTALL)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                            match_score = parsed.get('match_score', 0.0)
                        except:
                            pass
                
                match_scores[subreddit] = float(match_score)
                logger.info(f"子版块 r/{subreddit} 匹配度: {match_score}")
                
            except Exception as e:
                logger.error(f"分析子版块 r/{subreddit} 匹配度失败: {str(e)}")
                match_scores[subreddit] = 0.0
        
        return match_scores
    
    def filter_best_subreddits(self, subreddit_stats: Dict[str, Dict[str, Any]], 
                               match_scores: Dict[str, float],
                               min_match_score: float = 70.0,
                               min_heat_score: float = 50.0,
                               top_n: int = 5) -> List[Dict[str, Any]]:
        """
        筛选最佳子版块
        
        Args:
            subreddit_stats: 子版块统计信息
            match_scores: 匹配度评分
            min_match_score: 最低匹配度要求
            min_heat_score: 最低热度要求
            top_n: 返回前N个
        
        Returns:
            最佳子版块列表（包含综合评分）
        """
        candidates = []
        
        for subreddit, stats in subreddit_stats.items():
            match_score = match_scores.get(subreddit, 0.0)
            heat_score = stats.get('heat_score', 0.0)
            
            # 过滤不符合最低要求的
            if match_score < min_match_score or heat_score < min_heat_score:
                continue
            
            # 计算综合评分
            combined_score = match_score * 0.6 + heat_score * 0.4
            
            candidates.append({
                'subreddit': subreddit,
                'match_score': match_score,
                'heat_score': heat_score,
                'combined_score': combined_score,
                'stats': stats
            })
        
        # 按综合评分排序
        candidates.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return candidates[:top_n]
    
    def check_topic_consistency(self, keywords: List[str], subreddit: str, 
                                provider: str = "deepseek") -> Dict[str, Any]:
        """
        检查关键词与子版块主题的一致性
        
        Args:
            keywords: 关键词列表
            subreddit: 子版块名称
            provider: AI提供商
        
        Returns:
            一致性检查结果
        """
        try:
            # 获取子版块规则和描述
            rules_text = self.rule_checker.get_subreddit_rules(subreddit)
            
            # 获取子版块描述（如果有）
            try:
                subreddit_obj = self.scraper.reddit.subreddit(subreddit)
                description = subreddit_obj.public_description or subreddit_obj.description or ""
            except:
                description = ""
            
            prompt = f"""
请分析关键词与Reddit子版块 r/{subreddit} 的主题一致性。

**关键词：** {', '.join(keywords)}

**子版块信息：**
- 名称: r/{subreddit}
- 描述: {description[:500] if description else '无描述'}

**子版块规则：**
{rules_text[:1000] if rules_text else '无规则信息'}

**分析要求：**
1. 识别子版块的核心主题是什么
2. 评估关键词是否与子版块核心主题一致
3. 注意：仅仅包含关键词不等于主题相关
   - 例如：如果子版块只讨论"烹饪技术"，而关键词用于描述"家庭矛盾"，则不一致
4. 给出一致性评分（0-100分）

**请返回JSON格式：**
{{
    "core_topic": "子版块的核心主题",
    "topic_match": true/false,
    "consistency_score": 85,
    "reasoning": "分析原因"
}}
"""
            
            result = self.analyzer._call_llm(prompt, provider, "topic_consistency_check")
            
            # 解析结果
            consistency_result = {
                'core_topic': '',
                'topic_match': True,
                'consistency_score': 100.0,
                'reasoning': ''
            }
            
            if isinstance(result, dict):
                if 'parsed' in result:
                    parsed = result['parsed']
                    consistency_result.update({
                        'core_topic': parsed.get('core_topic', ''),
                        'topic_match': parsed.get('topic_match', True),
                        'consistency_score': float(parsed.get('consistency_score', 100.0)),
                        'reasoning': parsed.get('reasoning', '')
                    })
                elif 'consistency_score' in result:
                    consistency_result.update({
                        'core_topic': result.get('core_topic', ''),
                        'topic_match': result.get('topic_match', True),
                        'consistency_score': float(result.get('consistency_score', 100.0)),
                        'reasoning': result.get('reasoning', '')
                    })
                elif 'content' in result:
                    import re
                    json_match = re.search(r'\{.*\}', result['content'], re.DOTALL)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                            consistency_result.update({
                                'core_topic': parsed.get('core_topic', ''),
                                'topic_match': parsed.get('topic_match', True),
                                'consistency_score': float(parsed.get('consistency_score', 100.0)),
                                'reasoning': parsed.get('reasoning', '')
                            })
                        except:
                            pass
            elif isinstance(result, str):
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        consistency_result.update({
                            'core_topic': parsed.get('core_topic', ''),
                            'topic_match': parsed.get('topic_match', True),
                            'consistency_score': float(parsed.get('consistency_score', 100.0)),
                            'reasoning': parsed.get('reasoning', '')
                        })
                    except:
                        pass
            
            return consistency_result
            
        except Exception as e:
            logger.error(f"检查主题一致性失败: {str(e)}")
            return {
                'core_topic': '',
                'topic_match': True,
                'consistency_score': 100.0,
                'reasoning': f'检查失败: {str(e)}'
            }
    
    def generate_enhanced_posts(self, keywords: List[str], best_subreddits: List[Dict[str, Any]],
                               subreddit_stats: Dict[str, Dict[str, Any]],
                               topic_consistency_results: Dict[str, Dict[str, Any]],
                               rule_check_results: Dict[str, Dict[str, Any]],
                               count: int = 3,
                               provider: str = "deepseek") -> List[Dict[str, Any]]:
        """
        生成增强的帖子内容
        
        Args:
            keywords: 关键词列表
            best_subreddits: 最佳子版块列表
            subreddit_stats: 子版块统计信息
            topic_consistency_results: 主题一致性检查结果
            rule_check_results: 规则检查结果
            count: 生成数量
            provider: AI提供商
        
        Returns:
            生成的帖子列表
        """
        # 准备参考数据
        reference_data = []
        for subreddit_info in best_subreddits[:3]:  # 只取前3个
            subreddit = subreddit_info['subreddit']
            stats = subreddit_info['stats']
            sample_posts = stats.get('sample_posts', [])[:5]
            
            for post in sample_posts:
                reference_data.append({
                    'title': post.get('title', ''),
                    'content': post.get('selftext', '')[:300],
                    'subreddit': subreddit,
                    'score': post.get('score', 0),
                    'comments': post.get('num_comments', 0)
                })
        
        # 构建生成提示词
        subreddit_summary = []
        for subreddit_info in best_subreddits:
            subreddit = subreddit_info['subreddit']
            match_score = subreddit_info['match_score']
            heat_score = subreddit_info['heat_score']
            consistency = topic_consistency_results.get(subreddit, {})
            rule_check = rule_check_results.get(subreddit, {})
            
            subreddit_summary.append(f"""
- r/{subreddit}:
  * 匹配度: {match_score:.1f}/100
  * 热度: {heat_score:.1f}/100
  * 主题一致性: {consistency.get('consistency_score', 100):.1f}/100
  * 规则符合度: {rule_check.get('compliance_score', 100):.1f}/100
  * 核心主题: {consistency.get('core_topic', '未知')}
            """)
        
        prompt = f"""
基于以下分析结果，生成 {count} 篇高质量的Reddit帖子。

**关键词：** {', '.join(keywords)}

**最佳子版块分析：**
{''.join(subreddit_summary)}

**参考数据（来自最佳子版块的样本帖子）：**
{json.dumps(reference_data[:10], ensure_ascii=False, indent=2)}

**重要要求：**
1. 每篇帖子必须与关键词高度相关，内容要围绕这些关键词展开
2. 每篇帖子针对一个最佳子版块，确保符合该子版块的主题和规则
3. 内容要原创，基于真实讨论但要有独特性
4. 长度200-500字，要有价值，能引发讨论
5. 标题吸引人，包含关键词暗示
6. 确保主题一致性：帖子核心主题必须与目标子版块主题一致
7. 确保规则符合：遵守目标子版块的所有规则

**生成策略：**
- 为不同的最佳子版块生成帖子（确保3篇帖子覆盖不同子版块）
- 结合子版块的讨论风格和规则要求
- 分析用户痛点、需求、情绪，生成能引起共鸣的内容

请返回JSON格式：
{{
    "posts": [
        {{
            "title": "帖子标题（必须与关键词相关）",
            "content": "帖子内容（200-500字，与关键词和子版块高度相关）",
            "target_subreddit": "目标子版块名称",
            "reasoning": "为什么选择这个子版块，如何确保主题一致性和规则符合"
        }},
        ...
    ]
}}
"""
        
        try:
            result = self.analyzer._call_llm(prompt, provider, "enhanced_post_generation")
            
            # 解析结果
            posts_data = []
            if isinstance(result, dict):
                if 'parsed' in result:
                    parsed = result['parsed']
                    posts_data = parsed.get('posts', [])
                elif 'posts' in result:
                    posts_data = result.get('posts', [])
                elif 'content' in result:
                    import re
                    json_match = re.search(r'\{.*\}', result['content'], re.DOTALL)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                            posts_data = parsed.get('posts', [])
                        except:
                            pass
            elif isinstance(result, str):
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        posts_data = parsed.get('posts', [])
                    except:
                        pass
            
            # 转换为标准格式
            generated_posts = []
            for i, post_data in enumerate(posts_data[:count]):
                if isinstance(post_data, dict):
                    target_subreddit = post_data.get('target_subreddit', '')
                    if not target_subreddit and best_subreddits:
                        # 如果没有指定，循环分配
                        target_subreddit = best_subreddits[i % len(best_subreddits)]['subreddit']
                    
                    # 获取该子版块的相关评分
                    subreddit_info = next((s for s in best_subreddits if s['subreddit'] == target_subreddit), None)
                    match_score = subreddit_info['match_score'] if subreddit_info else 0.0
                    heat_score = subreddit_info['heat_score'] if subreddit_info else 0.0
                    consistency = topic_consistency_results.get(target_subreddit, {})
                    rule_check = rule_check_results.get(target_subreddit, {})
                    
                    generated_posts.append({
                        'temp_id': str(uuid.uuid4()),
                        'title': post_data.get('title', f'生成的帖子 {i+1}'),
                        'content': post_data.get('content', ''),
                        'content_type': 'text',
                        'status': 'draft',
                        'source': 'ai_generated_enhanced',
                        'is_ai_generated': True,
                        'keywords': ', '.join(keywords),
                        'target_subreddit': target_subreddit,
                        'match_score': match_score,
                        'heat_score': heat_score,
                        'topic_consistency_score': consistency.get('consistency_score', 100.0),
                        'rule_compliance_score': rule_check.get('compliance_score', 100.0),
                        'generation_metadata': {
                            'reasoning': post_data.get('reasoning', ''),
                            'core_topic': consistency.get('core_topic', ''),
                            'selected_subreddits': [s['subreddit'] for s in best_subreddits]
                        },
                        'created_at': datetime.utcnow()
                    })
            
            return generated_posts
            
        except Exception as e:
            logger.error(f"生成增强帖子失败: {str(e)}", exc_info=True)
            return []
    
    def generate_enhanced_posts_from_keywords(self, keywords: List[str], count: int = 3,
                                               provider: str = "deepseek",
                                               progress_callback=None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        完整的增强生成流程
        
        Args:
            keywords: 关键词列表
            count: 生成数量
            provider: AI提供商
            progress_callback: 进度回调函数（可选）
        
        Returns:
            (生成的帖子列表, 分析结果摘要)
        """
        analysis_summary = {
            'keywords': keywords,
            'subreddits_analyzed': 0,
            'best_subreddits': [],
            'generated_count': 0
        }
        
        try:
            # 步骤1: 全站抓取
            if progress_callback:
                progress_callback("步骤1/8: 全站抓取相关帖子...")
            posts_by_subreddit = self.fetch_posts_by_keywords(keywords, limit_per_keyword=300)
            
            if not posts_by_subreddit:
                logger.warning("未抓取到任何帖子")
                return [], analysis_summary
            
            # 步骤2: 计算统计信息
            if progress_callback:
                progress_callback("步骤2/8: 计算子版块统计信息...")
            subreddit_stats = self.calculate_subreddit_statistics(posts_by_subreddit)
            analysis_summary['subreddits_analyzed'] = len(subreddit_stats)
            
            if not subreddit_stats:
                logger.warning("未计算出任何子版块统计信息")
                return [], analysis_summary
            
            # 步骤3: AI匹配度分析
            if progress_callback:
                progress_callback("步骤3/8: AI分析子版块匹配度...")
            match_scores = self.analyze_subreddit_match(keywords, subreddit_stats, provider)
            
            # 步骤4: 筛选最佳子版块
            if progress_callback:
                progress_callback("步骤4/8: 筛选最佳子版块...")
            best_subreddits = self.filter_best_subreddits(
                subreddit_stats, match_scores,
                min_match_score=70.0,
                min_heat_score=50.0,
                top_n=5
            )
            analysis_summary['best_subreddits'] = [
                {
                    'subreddit': s['subreddit'],
                    'match_score': s['match_score'],
                    'heat_score': s['heat_score'],
                    'combined_score': s['combined_score']
                }
                for s in best_subreddits
            ]
            
            if not best_subreddits:
                logger.warning("未筛选出任何最佳子版块")
                return [], analysis_summary
            
            # 步骤5: 主题一致性检查
            if progress_callback:
                progress_callback("步骤5/8: 检查主题一致性...")
            topic_consistency_results = {}
            for subreddit_info in best_subreddits:
                subreddit = subreddit_info['subreddit']
                consistency = self.check_topic_consistency(keywords, subreddit, provider)
                topic_consistency_results[subreddit] = consistency
            
            # 步骤6: 规则检查
            if progress_callback:
                progress_callback("步骤6/8: 检查规则符合度...")
            rule_check_results = {}
            for subreddit_info in best_subreddits:
                subreddit = subreddit_info['subreddit']
                # 使用一个示例标题和内容进行预检查
                sample_title = f"关于 {', '.join(keywords)} 的讨论"
                sample_content = f"这是一个关于 {', '.join(keywords)} 的帖子。"
                rule_check = self.rule_checker.check_post_compliance(
                    subreddit, sample_title, sample_content, provider
                )
                rule_check_results[subreddit] = rule_check
            
            # 步骤7: 生成帖子
            if progress_callback:
                progress_callback("步骤7/8: AI生成帖子内容...")
            generated_posts = self.generate_enhanced_posts(
                keywords, best_subreddits, subreddit_stats,
                topic_consistency_results, rule_check_results,
                count, provider
            )
            analysis_summary['generated_count'] = len(generated_posts)
            
            # 步骤8: 保存到数据库
            if progress_callback:
                progress_callback("步骤8/8: 保存到数据库...")
            post_manager = PostManager(self.db)
            for post in generated_posts:
                try:
                    saved_id = post_manager.create_post(
                        title=post['title'],
                        content=post['content'],
                        source=post['source'],
                        is_ai_generated=True,
                        keywords=post['keywords'],
                        status='ready',
                        generation_metadata=post.get('generation_metadata', {})
                    )
                    # 将数据库ID回写到返回对象，便于在AI生成界面“一键发布/定时发布”
                    if saved_id:
                        post['id'] = saved_id
                except Exception as e:
                    logger.error(f"保存帖子失败: {str(e)}")
            
            if progress_callback:
                progress_callback("✅ 完成！")
            
            return generated_posts, analysis_summary
            
        except Exception as e:
            logger.error(f"增强生成流程失败: {str(e)}", exc_info=True)
            return [], analysis_summary

