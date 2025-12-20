"""
智能发帖模块
基于深度分析结果和子版块规则，生成并发布高质量内容
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from database import DatabaseManager
from llm_analyzer import LLMAnalyzer
from reddit_scraper import RedditScraper

logger = logging.getLogger(__name__)

class RedditPublisher:
    """智能发帖器"""
    
    def __init__(self, db_manager: DatabaseManager, llm_analyzer: LLMAnalyzer, reddit_scraper: RedditScraper):
        self.db_manager = db_manager
        self.llm_analyzer = llm_analyzer
        self.reddit_scraper = reddit_scraper
    
    def generate_post_content(self, insights: Dict[str, Any], keywords: List[Dict[str, Any]], 
                             subreddit_name: str, target_audience: str = None, 
                             user_input: str = None, auto_translate: bool = True) -> Dict[str, str]:
        """
        基于洞察和关键词生成帖子内容
        
        Args:
            insights: 深度分析洞察
            keywords: 关键词列表（包含长尾关键词）
            subreddit_name: 目标子版块
            target_audience: 目标受众
            user_input: 用户输入的需求描述（可选）
            auto_translate: 是否自动翻译为英文
            
        Returns:
            {'title': str, 'content': str, 'suggested_flair': str, 'translation_info': dict}
        """
        warnings = []
        
        try:
            logger.info(f"开始生成帖子内容，目标子版块: r/{subreddit_name}")
            
            # 检查缺失的数据并添加警告
            if not insights or (not insights.get('dominant_themes') and not insights.get('top_pain_points') and not insights.get('key_opportunities')):
                warnings.append("⚠️ 洞察数据缺失或为空，将主要基于用户输入生成")
                logger.warning("洞察数据缺失")
            
            if not user_input:
                warnings.append("⚠️ 用户需求描述为空，将主要基于可用数据生成")
                logger.warning("用户需求描述为空")
            
            # 即使有缺失，也继续生成
            logger.info(f"生成配置：insights={'有' if insights else '无'}, user_input={'有' if user_input else '无'}")
            
            # 1. 语言检测和翻译
            translation_info = None
            if user_input and auto_translate:
                translation_info = self._handle_language_translation(user_input, subreddit_name)
            
            # 2. 获取子版块规则
            rules = self._get_subreddit_rules(subreddit_name)
            
            # 3. 构建提示词
            prompt = self._build_content_prompt(insights, keywords, subreddit_name, rules, target_audience, user_input, translation_info)
            
            # 4. 调用LLM生成内容
            # 使用_call_llm方法，自动故障转移
            provider = "deepseek"  # 默认使用DeepSeek，如果有其他配置可以调整
            if hasattr(self.llm_analyzer, 'deepseek_api_key') and self.llm_analyzer.deepseek_api_key:
                provider = "deepseek"
            elif hasattr(self.llm_analyzer, 'openai_client') and self.llm_analyzer.openai_client:
                provider = "openai"
            elif hasattr(self.llm_analyzer, 'anthropic_client') and self.llm_analyzer.anthropic_client:
                provider = "anthropic"
            
            response_dict = self.llm_analyzer._call_llm(prompt, provider, "post_generation")
            
            # 检查是否有错误
            if "error" in response_dict:
                raise Exception(f"LLM调用失败: {response_dict.get('error', '未知错误')}")
            
            # 提取响应内容
            # _call_llm返回的格式: {'content': 'JSON文本', 'parsed': {...}, ...}
            if 'parsed' in response_dict:
                # 如果有解析后的对象，直接使用
                parsed = response_dict['parsed']
                content = {
                    'title': parsed.get('title', '未生成'),
                    'content': parsed.get('content', '未生成'),
                    'suggested_flair': parsed.get('suggested_flair')
                }
            elif 'content' in response_dict:
                # 如果只有JSON文本，需要解析
                response = response_dict['content']
                content = self._parse_content_response(response)
            else:
                # 降级处理：尝试直接解析整个响应
                response = str(response_dict)
                content = self._parse_content_response(response)
            
            # 6. 添加翻译信息和警告
            if translation_info:
                content['translation_info'] = translation_info
            
            # 添加警告信息
            if warnings:
                content['warnings'] = warnings
            
            logger.info("✅ 帖子内容生成成功")
            return content
            
        except Exception as e:
            logger.error(f"生成帖子内容失败: {str(e)}", exc_info=True)
            return {'title': '生成失败', 'content': str(e), 'suggested_flair': None}
    
    def _handle_language_translation(self, user_input: str, subreddit_name: str) -> Dict[str, Any]:
        """
        处理语言检测和翻译
        
        Args:
            user_input: 用户输入
            subreddit_name: 目标子版块
            
        Returns:
            翻译信息
        """
        try:
            # 1. 检测语言
            lang_result = self.llm_analyzer.detect_language(user_input)
            
            if not lang_result.get('success', False):
                logger.warning("语言检测失败，跳过翻译")
                return None
            
            # 2. 如果是中文，进行翻译
            if lang_result.get('is_chinese', False):
                logger.info(f"检测到中文输入，开始翻译为英文")
                
                # 使用Reddit专用翻译
                translation_result = self.llm_analyzer.translate_for_reddit(
                    user_input, 
                    subreddit_name, 
                    "讨论"
                )
                
                if translation_result.get('success', False):
                    logger.info("✅ 翻译成功")
                    return {
                        'original_language': lang_result.get('language', '中文'),
                        'original_text': user_input,
                        'translated_text': translation_result.get('translated_text', ''),
                        'reddit_style': translation_result.get('reddit_style', ''),
                        'community_fit': translation_result.get('community_fit', ''),
                        'suggestions': translation_result.get('suggestions', ''),
                        'hashtags': translation_result.get('hashtags', ''),
                        'confidence': lang_result.get('confidence', 0.0)
                    }
                else:
                    logger.warning(f"翻译失败: {translation_result.get('error', '未知错误')}")
                    return None
            else:
                logger.info("输入为英文，无需翻译")
                return None
                
        except Exception as e:
            logger.error(f"语言翻译处理失败: {str(e)}")
            return None
    
    def _get_subreddit_rules(self, subreddit_name: str) -> Dict[str, Any]:
        """获取子版块规则"""
        try:
            # 从数据库获取缓存规则
            index = self.db_manager.get_subreddit_index(subreddit_name)
            if index and index.get('rules'):
                return index['rules']
            
            # 如果没有缓存，从Reddit获取
            subreddit = self.reddit_scraper.reddit.subreddit(subreddit_name)
            rules = []
            
            for rule in subreddit.rules:
                rules.append({
                    'short_name': rule.short_name,
                    'description': rule.description,
                    'kind': rule.kind
                })
            
            result = {
                'rules': rules,
                'subreddit_name': subreddit_name
            }
            
            # 缓存到数据库（可选）
            # self.db_manager.cache_subreddit_rules(subreddit_name, result)
            
            return result
            
        except Exception as e:
            logger.error(f"获取子版块规则失败: {str(e)}")
            return {'rules': []}
    
    def _build_content_prompt(self, insights: Dict[str, Any], keywords: List[Dict[str, Any]], 
                             subreddit_name: str, rules: Dict[str, Any], target_audience: str = None,
                             user_input: str = None, translation_info: Dict[str, Any] = None) -> str:
        """构建内容生成提示词"""
        
        prompt = f"""
请为Reddit子版块 r/{subreddit_name} 生成一篇高质量的帖子。

## 子版块信息
- 子版块名称: r/{subreddit_name}
- 规则数量: {len(rules.get('rules', []))}

## 业务洞察
主导主题: {', '.join(insights.get('dominant_themes', [])[:5])}
主要痛点: {', '.join(insights.get('top_pain_points', [])[:5])}
关键机会: {', '.join(insights.get('key_opportunities', [])[:5])}

## 子版块规则
{chr(10).join([f"- {rule['short_name']}: {rule['description'][:100]}" for rule in rules.get('rules', [])[:5]])}
"""
        
        # 添加用户输入和翻译信息
        if user_input:
            prompt += f"\n## 用户需求\n{user_input}\n"
            
            if translation_info:
                prompt += f"""
## 翻译信息
- 原文语言: {translation_info.get('original_language', '未知')}
- 翻译文本: {translation_info.get('translated_text', '')}
- Reddit风格调整: {translation_info.get('reddit_style', '')}
- 社区适配建议: {translation_info.get('community_fit', '')}
- 发帖建议: {translation_info.get('suggestions', '')}
"""
        
        if target_audience:
            prompt += f"\n## 目标受众\n{target_audience}\n"
        
        prompt += """
## 要求
1. 标题要吸引人但不过分夸大，符合该子版块的风格
2. 内容要有价值，解决问题或提供见解
3. 使用自然、友好的语调
4. 长度适中（300-800字）
5. **重要：如果用户输入是中文，请使用翻译后的英文内容作为基础**
6. 确保内容符合Reddit社区的用语习惯

## 输出格式
请以JSON格式输出，包含以下字段：
- "title": 帖子标题（英文）
- "content": 帖子正文（英文）
- "suggested_flair": 建议的标签（如果有）
- "language_notes": 语言处理说明（如果有翻译）
"""
        
        return prompt
    
    def _parse_content_response(self, response: str) -> Dict[str, str]:
        """解析LLM响应"""
        try:
            import json
            
            # 尝试解析JSON
            if response.strip().startswith('{'):
                content = json.loads(response)
                return {
                    'title': content.get('title', '未生成'),
                    'content': content.get('content', '未生成'),
                    'suggested_flair': content.get('suggested_flair')
                }
            
            # 如果不是JSON，尝试提取
            lines = response.strip().split('\n')
            title = lines[0] if lines else '未生成'
            content = '\n'.join(lines[1:]) if len(lines) > 1 else '未生成'
            
            return {
                'title': title,
                'content': content,
                'suggested_flair': None
            }
            
        except Exception as e:
            logger.error(f"解析内容响应失败: {str(e)}")
            return {
                'title': '解析失败',
                'content': response,
                'suggested_flair': None
            }
    
    def validate_content(self, content: Dict[str, str], rules: Dict[str, Any]) -> Dict[str, Any]:
        """验证内容是否符合规则"""
        validation_results = {
            'pass': True,
            'warnings': [],
            'errors': []
        }
        
        # 检查标题长度
        if len(content['title']) > 300:
            validation_results['pass'] = False
            validation_results['errors'].append("标题过长（超过300字符）")
        
        # 检查内容长度
        if len(content['content']) < 100:
            validation_results['warnings'].append("内容可能过短")
        elif len(content['content']) > 40000:
            validation_results['pass'] = False
            validation_results['errors'].append("内容过长（超过40000字符）")
        
        # 检查是否有链接（某些子版块不允许）
        # 这里可以根据具体规则扩展
        
        return validation_results
    
    def save_draft(self, content: Dict[str, str], subreddit_name: str, user_id: str = None) -> bool:
        """保存草稿"""
        try:
            # 这里可以保存到数据库或文件
            # 暂时保存到文件
            import json
            
            draft = {
                'title': content['title'],
                'content': content['content'],
                'subreddit_name': subreddit_name,
                'suggested_flair': content.get('suggested_flair'),
                'created_at': datetime.now().isoformat(),
                'user_id': user_id
            }
            
            filename = f"drafts/draft_{subreddit_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            import os
            os.makedirs('drafts', exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(draft, f, ensure_ascii=False, indent=2)
            
            logger.info(f"草稿保存成功: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"保存草稿失败: {str(e)}")
            return False
    
    def publish_post(self, content: Dict[str, str], subreddit_name: str, flair: str = None) -> Dict[str, Any]:
        """
        发布帖子到单个子版块（注意：这需要Reddit API的写权限）
        
        Args:
            content: 帖子内容 {'title': str, 'content': str}
            subreddit_name: 子版块名称
            flair: 标签（可选）
            
        Returns:
            发布结果
        """
        try:
            logger.info(f"准备发布帖子到 r/{subreddit_name}")
            
            # 检查权限
            if not self.reddit_scraper.access_token:
                return {
                    'success': False,
                    'error': '未获得Reddit API写权限'
                }
            
            # 使用RedditScraper的submit_post方法
            result = self.reddit_scraper.submit_post(
                subreddit_name=subreddit_name,
                title=content['title'],
                content=content['content'],
                flair_text=flair,
                kind='self'
            )
            
            if result['success']:
                # 保存发布记录
                self.save_post_record(
                    post_id=result['post_id'],
                    subreddit_name=subreddit_name,
                    title=content['title'],
                    published_at=datetime.now()
                )
                
                logger.info(f"✅ 帖子发布成功: {result['post_id']}")
                return {
                    'success': True,
                    'post_id': result['post_id'],
                    'url': result['url']
                }
            else:
                logger.error(f"发布失败: {result['error']}")
                return {
                    'success': False,
                    'error': result['error']
                }
            
        except Exception as e:
            logger.error(f"发布帖子失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def publish_to_multiple_subreddits(self, content: Dict[str, str], subreddit_names: List[str], 
                                      flair: str = None) -> Dict[str, Any]:
        """
        发布帖子到多个子版块
        
        Args:
            content: 帖子内容 {'title': str, 'content': str}
            subreddit_names: 子版块名称列表
            flair: 标签（可选）
            
        Returns:
            发布结果 {'success': bool, 'results': List[Dict], 'total': int, 'succeeded': int, 'failed': int}
        """
        results = []
        succeeded = 0
        failed = 0
        
        for subreddit_name in subreddit_names:
            result = self.publish_post(content, subreddit_name, flair)
            results.append({
                'subreddit': subreddit_name,
                'result': result
            })
            
            if result.get('success'):
                succeeded += 1
            else:
                failed += 1
        
        return {
            'success': succeeded > 0,
            'results': results,
            'total': len(subreddit_names),
            'succeeded': succeeded,
            'failed': failed
            }
    
    def save_post_record(self, post_id: str, subreddit_name: str, title: str, published_at: datetime) -> bool:
        """保存发布记录"""
        # 这里需要在database.py中添加一个新的表来记录发布历史
        # 暂时跳过
        return True

