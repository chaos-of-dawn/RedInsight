"""
RPTA评分引擎 - 精简版（已优化）
复用LLMAnalyzer进行AI评分，直接计算T和A维度
支持缓存机制、Prompt优化、两阶段评分、批量评分等优化
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re
import json

logger = logging.getLogger(__name__)

class RPTAScorer:
    """RPTA综合评分器"""
    
    def __init__(self, llm_analyzer, keywords: List[str] = None, db_manager=None):
        """
        初始化评分器
        
        Args:
            llm_analyzer: LLMAnalyzer实例
            keywords: 核心关键词列表
            db_manager: DatabaseManager实例（用于缓存评分结果）
        """
        self.llm_analyzer = llm_analyzer
        self.keywords = keywords or []
        self.db_manager = db_manager
        # 默认权重
        self.weights = {'r': 0.3, 'p': 0.4, 't': 0.2, 'a': 0.1}
        # 缓存配置
        self.cache_enabled = db_manager is not None
        self.r_cache_hours = 7 * 24  # R维度缓存7天
        self.p_cache_hours = 3 * 24  # P维度缓存3天
        # 批量评分配置（方案3）
        self.batch_size = 5  # 每批处理的帖子数量
        # 批量评分配置
        self.batch_size = 5  # 每批处理的帖子数量（方案3）
    
    def set_weights(self, r: float, p: float, t: float, a: float):
        """设置权重"""
        self.weights = {'r': r, 'p': p, 't': t, 'a': a}
    
    def set_keywords(self, keywords: List[str]):
        """设置核心关键词"""
        self.keywords = keywords
    
    def calculate_r_score(self, post_text: str, provider: str = "deepseek", post_id: str = None) -> float:
        """
        计算相关性评分 (R) - 使用AI大模型分析相关性（支持缓存）
        
        Args:
            post_text: 帖子文本（标题+正文）
            provider: LLM提供商
            post_id: 帖子ID（用于缓存）
            
        Returns:
            相关性评分 0-1
        """
        if not post_text:
            return 0.0
        
        # 尝试从缓存获取
        if self.cache_enabled and post_id:
            cached_score = self._get_cached_r_score(post_id)
            if cached_score is not None:
                logger.debug(f"使用缓存的R评分: post_id={post_id}, score={cached_score}")
                return cached_score
        
        try:
            # 构建关键词上下文
            keywords_context = ""
            if self.keywords:
                keywords_context = f"\n关键词: {', '.join(self.keywords)}"
            
            # 精简版prompt（优化方案4）
            prompt = f"""评分帖子与关键词的相关性（0-1）：
帖子：{post_text}
{keywords_context}
标准：0.9+高度相关，0.7+明显相关，0.5+有一定相关，0.3+相关性低，0.0+不相关
只返回浮点数。"""
            result = self.llm_analyzer._call_llm(prompt, provider, "rpta_r_score")
            
            # 提取数字
            content = result.get('content', '') if isinstance(result, dict) else str(result)
            numbers = re.findall(r'0?\.\d+|1\.0|0\.\d+', content)
            
            if numbers:
                score = float(numbers[0])
                score = max(0.0, min(1.0, score))  # 限制在0-1范围
                
                # 保存到缓存
                if self.cache_enabled and post_id:
                    self._save_cached_r_score(post_id, score)
                
                return score
            
            # 如果无法提取，使用关键词匹配作为fallback
            if self.keywords:
                text_lower = post_text.lower()
                matches = sum(1 for keyword in self.keywords if keyword.lower() in text_lower)
                score = min(matches / len(self.keywords), 1.0)
                
                # 保存fallback结果到缓存
                if self.cache_enabled and post_id:
                    self._save_cached_r_score(post_id, score)
                
                return score
            
            return 0.5  # 默认值
            
        except Exception as e:
            logger.error(f"计算R评分失败: {str(e)}")
            # 如果AI调用失败，使用关键词匹配作为fallback
            if self.keywords:
                text_lower = post_text.lower()
                matches = sum(1 for keyword in self.keywords if keyword.lower() in text_lower)
                score = min(matches / len(self.keywords), 1.0)
                
                # 保存fallback结果到缓存
                if self.cache_enabled and post_id:
                    self._save_cached_r_score(post_id, score)
                
                return score
            return 0.5
    
    def calculate_p_score(self, post_text: str, provider: str = "deepseek", post_id: str = None) -> float:
        """
        计算痛点/情绪评分 (P) - 使用AI分析（支持缓存）
        
        Args:
            post_text: 帖子文本
            provider: LLM提供商
            post_id: 帖子ID（用于缓存）
            
        Returns:
            痛点/情绪评分 0-1
        """
        # 尝试从缓存获取
        if self.cache_enabled and post_id:
            cached_score = self._get_cached_p_score(post_id)
            if cached_score is not None:
                logger.debug(f"使用缓存的P评分: post_id={post_id}, score={cached_score}")
                return cached_score
        
        try:
            # 精简版prompt（优化方案4）
            prompt = f"""评分帖子的情绪和痛点强度（0-1）：
帖子：{post_text}
标准：0.9+强烈负面情绪/需求，0.7+明显负面情绪/需求，0.5+中等情绪/需求，0.3+轻微情绪/需求，0.0+无明显情绪
只返回浮点数。"""
            result = self.llm_analyzer._call_llm(prompt, provider, "rpta_p_score")
            
            # 提取数字
            content = result.get('content', '') if isinstance(result, dict) else str(result)
            numbers = re.findall(r'0?\.\d+|1\.0|0\.\d+', content)
            
            if numbers:
                score = float(numbers[0])
                score = max(0.0, min(1.0, score))  # 限制在0-1范围
                
                # 保存到缓存
                if self.cache_enabled and post_id:
                    self._save_cached_p_score(post_id, score)
                
                return score
            
            # 如果无法提取，使用情感分析作为fallback
            sentiment_result = self.llm_analyzer.analyze_sentiment(post_text, provider)
            if isinstance(sentiment_result, dict):
                sentiment = sentiment_result.get('sentiment', 'neutral')
                confidence = sentiment_result.get('confidence', 0.5)
                
                # 负面情绪得分更高
                if sentiment == 'negative':
                    score = min(0.8 + confidence * 0.2, 1.0)
                elif sentiment == 'positive':
                    score = 0.3 + confidence * 0.2
                else:
                    score = 0.3
                
                # 保存fallback结果到缓存
                if self.cache_enabled and post_id:
                    self._save_cached_p_score(post_id, score)
                
                return score
            
            return 0.5  # 默认值
            
        except Exception as e:
            logger.error(f"计算P评分失败: {str(e)}")
            return 0.5
    
    def calculate_t_score(self, created_utc: datetime, hours_threshold: int = 12) -> float:
        """
        计算及时性评分 (T) - 直接计算
        
        Args:
            created_utc: 帖子创建时间
            hours_threshold: 时间阈值（小时），默认12小时
            
        Returns:
            及时性评分 0-1
        """
        if not created_utc:
            return 0.0
        
        now = datetime.utcnow()
        if isinstance(created_utc, (int, float)):
            # 如果是Unix时间戳
            created_utc = datetime.utcfromtimestamp(created_utc)
        
        age_hours = (now - created_utc).total_seconds() / 3600
        
        # 12小时内：1.0，之后线性递减
        if age_hours <= hours_threshold:
            return 1.0
        elif age_hours <= hours_threshold * 2:
            return 1.0 - (age_hours - hours_threshold) / hours_threshold
        else:
            return 0.0
    
    def calculate_a_score(self, num_comments: int, score: int) -> float:
        """
        计算活跃度评分 (A) - 直接计算
        
        Args:
            num_comments: 评论数
            score: 帖子得分
            
        Returns:
            活跃度评分 0-1（适中为佳）
        """
        # 理想范围：评论数5-50，得分10-200
        comment_score = 1.0 if 5 <= num_comments <= 50 else max(0.0, 1.0 - abs(num_comments - 27.5) / 27.5)
        score_norm = min(score / 100.0, 1.0) if score > 0 else 0.0
        
        # 综合评分
        return (comment_score * 0.6 + score_norm * 0.4)
    
    def calculate_total_score(self, post_data: Dict[str, Any], provider: str = "deepseek", use_cache: bool = True) -> Dict[str, Any]:
        """
        计算综合RPTA评分（支持缓存和两阶段评分优化）
        
        Args:
            post_data: 帖子数据字典，包含：
                - id: 帖子ID（用于缓存）
                - title: 标题
                - selftext: 正文
                - created_utc: 创建时间
                - num_comments: 评论数
                - score: 帖子得分
            provider: LLM提供商
            use_cache: 是否使用缓存
            
        Returns:
            评分结果字典
        """
        try:
            post_id = post_data.get('id')
            
            # 优化方案2：两阶段评分策略
            # 先计算T和A维度（无需AI，快速）
            t_score = self.calculate_t_score(post_data.get('created_utc'))
            a_score = self.calculate_a_score(
                post_data.get('num_comments', 0),
                post_data.get('score', 0)
            )
            
            # 计算最小可能总分（只考虑T和A）
            min_possible_score = (
                self.weights['t'] * t_score +
                self.weights['a'] * a_score
            )
            
            # 如果最小可能总分已经低于阈值，可以提前返回（但需要配置阈值）
            # 这里先不实现提前返回，因为需要知道阈值
            
            # 准备文本
            title = post_data.get('title', '')
            selftext = post_data.get('selftext', '') or ''
            post_text = f"{title}\n\n{selftext}".strip()
            
            # 计算R和P维度（需要AI，支持缓存）
            r_score = self.calculate_r_score(post_text, provider, post_id if use_cache else None)
            p_score = self.calculate_p_score(post_text, provider, post_id if use_cache else None)
            
            # 综合评分
            total_score = (
                self.weights['r'] * r_score +
                self.weights['p'] * p_score +
                self.weights['t'] * t_score +
                self.weights['a'] * a_score
            )
            
            result = {
                'total_score': total_score,
                'r_score': r_score,
                'p_score': p_score,
                't_score': t_score,
                'a_score': a_score,
                'weights': self.weights.copy()
            }
            
            # 保存完整评分到数据库（用于缓存和统计）
            if self.cache_enabled and post_id:
                try:
                    subreddit = post_data.get('subreddit', 'unknown')
                    self.db_manager.save_post_scoring(
                        post_id=post_id,
                        subreddit=subreddit,
                        title=title[:500] if title else '',  # 限制长度
                        relevance_score=r_score,
                        pain_emotion_score=p_score,
                        timeliness_score=t_score,
                        activity_score=a_score,
                        final_score=total_score
                    )
                except Exception as e:
                    logger.warning(f"保存评分到数据库失败: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"计算RPTA评分失败: {str(e)}")
            return {
                'total_score': 0.0,
                'r_score': 0.0,
                'p_score': 0.0,
                't_score': 0.0,
                'a_score': 0.0,
                'error': str(e)
            }
    
    def _get_cached_r_score(self, post_id: str) -> Optional[float]:
        """从数据库获取缓存的R评分（方案7：时效性管理）"""
        if not self.cache_enabled or not self.db_manager:
            return None
        
        try:
            session = self.db_manager.get_session()
            try:
                scoring = session.query(self.db_manager.PostScoring).filter(
                    self.db_manager.PostScoring.post_id == post_id
                ).first()
                
                if scoring and scoring.relevance_score is not None:
                    # 检查缓存是否过期（7天）
                    cache_age = (datetime.utcnow() - scoring.scored_at).total_seconds() / 3600
                    if cache_age <= self.r_cache_hours:
                        return float(scoring.relevance_score)
                    else:
                        logger.debug(f"R评分缓存已过期: post_id={post_id}, age={cache_age:.1f}小时")
                
                return None
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"获取R评分缓存失败: {str(e)}")
            return None
    
    def _get_cached_p_score(self, post_id: str) -> Optional[float]:
        """从数据库获取缓存的P评分（方案7：时效性管理）"""
        if not self.cache_enabled or not self.db_manager:
            return None
        
        try:
            session = self.db_manager.get_session()
            try:
                scoring = session.query(self.db_manager.PostScoring).filter(
                    self.db_manager.PostScoring.post_id == post_id
                ).first()
                
                if scoring and scoring.pain_emotion_score is not None:
                    # 检查缓存是否过期（3天）
                    cache_age = (datetime.utcnow() - scoring.scored_at).total_seconds() / 3600
                    if cache_age <= self.p_cache_hours:
                        return float(scoring.pain_emotion_score)
                    else:
                        logger.debug(f"P评分缓存已过期: post_id={post_id}, age={cache_age:.1f}小时")
                
                return None
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"获取P评分缓存失败: {str(e)}")
            return None
    
    def calculate_batch_scores(self, posts_data: List[Dict[str, Any]], provider: str = "deepseek") -> List[Dict[str, Any]]:
        """
        批量计算RPTA评分（方案3：批量AI评分）
        
        将多个帖子的R和P评分合并为一次API调用，减少token消耗
        
        Args:
            posts_data: 帖子数据列表，每个元素包含：
                - id: 帖子ID
                - title: 标题
                - selftext: 正文
                - created_utc: 创建时间
                - num_comments: 评论数
                - score: 帖子得分
                - subreddit: 子版块
            provider: LLM提供商
            
        Returns:
            评分结果列表，每个元素对应一个帖子的评分结果
        """
        if not posts_data:
            return []
        
        results = []
        
        # 分批处理
        for i in range(0, len(posts_data), self.batch_size):
            batch = posts_data[i:i + self.batch_size]
            batch_results = self._calculate_batch_scores_internal(batch, provider)
            results.extend(batch_results)
        
        return results
    
    def _calculate_batch_scores_internal(self, posts_data: List[Dict[str, Any]], provider: str = "deepseek") -> List[Dict[str, Any]]:
        """内部方法：处理一批帖子的评分"""
        if not posts_data:
            return []
        
        # 分离需要AI评分和不需要AI评分的帖子
        need_ai_posts = []
        cached_results = {}
        
        for post in posts_data:
            post_id = post.get('id')
            title = post.get('title', '')
            selftext = post.get('selftext', '') or ''
            post_text = f"{title}\n\n{selftext}".strip()
            
            # 检查缓存
            r_score = None
            p_score = None
            
            if self.cache_enabled and post_id:
                r_score = self._get_cached_r_score(post_id)
                p_score = self._get_cached_p_score(post_id)
            
            # 如果R和P都有缓存，直接使用
            if r_score is not None and p_score is not None:
                t_score = self.calculate_t_score(post.get('created_utc'))
                a_score = self.calculate_a_score(
                    post.get('num_comments', 0),
                    post.get('score', 0)
                )
                total_score = (
                    self.weights['r'] * r_score +
                    self.weights['p'] * p_score +
                    self.weights['t'] * t_score +
                    self.weights['a'] * a_score
                )
                cached_results[post_id] = {
                    'total_score': total_score,
                    'r_score': r_score,
                    'p_score': p_score,
                    't_score': t_score,
                    'a_score': a_score,
                    'weights': self.weights.copy(),
                    'from_cache': True
                }
            else:
                # 需要AI评分
                need_ai_posts.append({
                    'post': post,
                    'post_id': post_id,
                    'post_text': post_text,
                    'cached_r': r_score,
                    'cached_p': p_score
                })
        
        # 批量AI评分
        if need_ai_posts:
            batch_scores = self._batch_ai_score(need_ai_posts, provider)
            logger.info(f"批量评分返回结果: {len(batch_scores)}/{len(need_ai_posts)} 个帖子有评分结果")
            
            # 合并结果
            for item in need_ai_posts:
                post = item['post']
                post_id = item['post_id']
                post_text = item['post_text']
                
                # 获取批量评分结果
                batch_result = batch_scores.get(post_id, {})
                # 修复：使用 'in' 检查而不是 None 检查，因为 0.0 也是有效值
                r_score = batch_result.get('r_score') if 'r_score' in batch_result else item['cached_r']
                p_score = batch_result.get('p_score') if 'p_score' in batch_result else item['cached_p']
                
                # 如果批量评分失败，回退到单独评分
                if r_score is None or p_score is None:
                    logger.debug(f"帖子 {post_id} 批量评分不完整，回退到单独评分 (r={r_score}, p={p_score})")
                    if r_score is None:
                        r_score = self.calculate_r_score(post_text, provider, post_id)
                        logger.debug(f"单独评分R: {r_score}")
                    if p_score is None:
                        p_score = self.calculate_p_score(post_text, provider, post_id)
                        logger.debug(f"单独评分P: {p_score}")
                
                # 验证评分值是否合理
                if r_score is None or p_score is None:
                    logger.warning(f"帖子 {post_id} 评分失败，使用默认值 (r={r_score}, p={p_score})")
                    r_score = r_score if r_score is not None else 0.5
                    p_score = p_score if p_score is not None else 0.5
                
                # 计算T和A
                t_score = self.calculate_t_score(post.get('created_utc'))
                a_score = self.calculate_a_score(
                    post.get('num_comments', 0),
                    post.get('score', 0)
                )
                
                # 综合评分
                total_score = (
                    self.weights['r'] * r_score +
                    self.weights['p'] * p_score +
                    self.weights['t'] * t_score +
                    self.weights['a'] * a_score
                )
                
                result = {
                    'total_score': total_score,
                    'r_score': r_score,
                    'p_score': p_score,
                    't_score': t_score,
                    'a_score': a_score,
                    'weights': self.weights.copy(),
                    'from_cache': False
                }
                
                # 保存到数据库
                if self.cache_enabled and post_id:
                    try:
                        subreddit = post.get('subreddit', 'unknown')
                        self.db_manager.save_post_scoring(
                            post_id=post_id,
                            subreddit=subreddit,
                            title=title[:500] if title else '',
                            relevance_score=r_score,
                            pain_emotion_score=p_score,
                            timeliness_score=t_score,
                            activity_score=a_score,
                            final_score=total_score
                        )
                    except Exception as e:
                        logger.warning(f"保存批量评分到数据库失败: {str(e)}")
                
                cached_results[post_id] = result
        
        # 按原始顺序返回结果
        results = []
        for post in posts_data:
            post_id = post.get('id')
            if post_id in cached_results:
                results.append(cached_results[post_id])
            else:
                # 如果出错，返回默认值
                results.append({
                    'total_score': 0.0,
                    'r_score': 0.0,
                    'p_score': 0.0,
                    't_score': 0.0,
                    'a_score': 0.0,
                    'weights': self.weights.copy(),
                    'error': '评分失败'
                })
        
        return results
    
    def _batch_ai_score(self, need_ai_posts: List[Dict[str, Any]], provider: str = "deepseek") -> Dict[str, Dict[str, float]]:
        """
        批量AI评分：一次API调用处理多个帖子的R和P评分
        
        Returns:
            Dict[post_id, {'r_score': float, 'p_score': float}]
        """
        if not need_ai_posts:
            return {}
        
        try:
            # 构建批量prompt
            keywords_context = ""
            if self.keywords:
                keywords_context = f"\n核心关键词: {', '.join(self.keywords)}"
            
            # 准备帖子列表
            posts_list = []
            post_id_map = {}  # 用于映射结果
            
            for idx, item in enumerate(need_ai_posts):
                post_id = item['post_id']
                post_text = item['post_text']
                # 截断过长的文本（避免token超限）
                if len(post_text) > 500:
                    post_text = post_text[:500] + "..."
                
                posts_list.append({
                    'index': idx + 1,
                    'post_id': post_id,
                    'text': post_text
                })
                post_id_map[idx + 1] = post_id
            
            # 构建批量prompt
            posts_text = "\n\n".join([
                f"帖子{p['index']}:\n{p['text']}"
                for p in posts_list
            ])
            
            batch_prompt = f"""批量评分以下{len(posts_list)}个Reddit帖子：
{keywords_context}

{posts_text}

请为每个帖子评分：
1. 相关性评分（R）：与关键词的相关性（0-1）
2. 痛点/情绪评分（P）：情绪和痛点强度（0-1）

请返回JSON格式：
{{
    "scores": [
        {{
            "index": 1,
            "r_score": 0.85,
            "p_score": 0.72
        }},
        {{
            "index": 2,
            "r_score": 0.65,
            "p_score": 0.58
        }}
    ]
}}

只返回JSON，不要其他文字。"""
            
            # 调用AI
            result = self.llm_analyzer._call_llm(batch_prompt, provider, "rpta_batch_score")
            
            # 解析结果
            scores_dict = {}
            
            if isinstance(result, dict):
                content = result.get('content', '')
                if not content and 'parsed' in result:
                    parsed = result['parsed']
                    if isinstance(parsed, dict) and 'scores' in parsed:
                        for score_item in parsed['scores']:
                            idx = score_item.get('index')
                            if idx in post_id_map:
                                post_id = post_id_map[idx]
                                scores_dict[post_id] = {
                                    'r_score': max(0.0, min(1.0, float(score_item.get('r_score', 0.5)))),
                                    'p_score': max(0.0, min(1.0, float(score_item.get('p_score', 0.5))))
                                }
                else:
                    # 尝试从content中提取JSON
                    import json
                    try:
                        # 尝试直接解析
                        parsed = json.loads(content)
                        if 'scores' in parsed:
                            for score_item in parsed['scores']:
                                idx = score_item.get('index')
                                if idx in post_id_map:
                                    post_id = post_id_map[idx]
                                    scores_dict[post_id] = {
                                        'r_score': max(0.0, min(1.0, float(score_item.get('r_score', 0.5)))),
                                        'p_score': max(0.0, min(1.0, float(score_item.get('p_score', 0.5))))
                                    }
                    except:
                        # 尝试提取JSON
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            try:
                                parsed = json.loads(json_match.group())
                                if 'scores' in parsed:
                                    for score_item in parsed['scores']:
                                        idx = score_item.get('index')
                                        if idx in post_id_map:
                                            post_id = post_id_map[idx]
                                            scores_dict[post_id] = {
                                                'r_score': max(0.0, min(1.0, float(score_item.get('r_score', 0.5)))),
                                                'p_score': max(0.0, min(1.0, float(score_item.get('p_score', 0.5))))
                                            }
                            except:
                                logger.warning("批量评分JSON解析失败")
            
            logger.info(f"批量评分完成: {len(scores_dict)}/{len(need_ai_posts)} 个帖子成功评分")
            
            # 调试：记录评分分布
            if scores_dict:
                r_scores = [v.get('r_score', 0) for v in scores_dict.values()]
                p_scores = [v.get('p_score', 0) for v in scores_dict.values()]
                logger.debug(f"批量评分统计 - R评分: 平均={sum(r_scores)/len(r_scores):.3f}, 最小={min(r_scores):.3f}, 最大={max(r_scores):.3f}")
                logger.debug(f"批量评分统计 - P评分: 平均={sum(p_scores)/len(p_scores):.3f}, 最小={min(p_scores):.3f}, 最大={max(p_scores):.3f}")
            else:
                logger.warning("批量评分返回空结果，可能是JSON解析失败")
            
            return scores_dict
            
        except Exception as e:
            logger.error(f"批量AI评分失败: {str(e)}", exc_info=True)
            return {}
