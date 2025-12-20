"""
任务执行器 - 精简版
复用InteractionManager执行自动化任务
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from database import DatabaseManager
from interaction_manager import InteractionManager
from llm_analyzer import LLMAnalyzer

logger = logging.getLogger(__name__)

class TaskExecutor:
    """自动化任务执行器"""
    
    def __init__(self, db_manager: DatabaseManager, 
                 interaction_manager: InteractionManager,
                 llm_analyzer: LLMAnalyzer,
                 scraper=None):
        """
        初始化任务执行器
        
        Args:
            db_manager: DatabaseManager实例
            interaction_manager: InteractionManager实例
            llm_analyzer: LLMAnalyzer实例
            scraper: RedditScraper实例（可选，用于发布评论）
        """
        self.db = db_manager
        self.interaction_manager = interaction_manager
        self.llm_analyzer = llm_analyzer
        self.scraper = scraper
    
    def generate_ai_comment(self, post_data: Dict[str, Any], 
                           interaction_type: str, 
                           provider: str = "deepseek") -> Optional[str]:
        """
        生成AI评论内容
        
        Args:
            post_data: 帖子数据
            interaction_type: 互动类型 ('deep', 'standard', 'light')
            provider: LLM提供商
            
        Returns:
            AI生成的评论内容
        """
        try:
            title = post_data.get('title', '')
            selftext = post_data.get('selftext', '') or ''
            post_text = f"{title}\n\n{selftext}".strip()
            
            if interaction_type == 'deep':
                prompt = f"""
Based on the following Reddit post, generate a professional and valuable comment in English:

Post content:
{post_text}

Requirements:
1. Provide solutions or share experiences
2. Show strong personality and authenticity
3. Guide users to think about deeper issues
4. Never mention any product names or brands
5. Moderate length (100-200 words)
6. Use natural, friendly tone
7. Write in English (match the language of the post)

Please return only the comment content, no other explanations.
"""
            elif interaction_type == 'standard':
                prompt = f"""
Based on the following Reddit post, generate a concise empathetic comment in English:

Post content:
{post_text}

Requirements:
1. Express empathy or ask related questions
2. Increase account activity and blend into community discussions
3. Concise text (50-100 words)
4. Natural and friendly
5. Write in English (match the language of the post)

Please return only the comment content, no other explanations.
"""
            else:
                return None  # light类型不需要评论

            # 生成 + 清洗 + 校验（英文 & 无元数据）
            # 少量重试：如果模型输出了JSON/说明文字/非英文，要求它重发“纯文本英文评论”
            max_attempts = 3
            extra_guard = (
                "\n\nIMPORTANT OUTPUT RULES:\n"
                "- Output ONLY the raw English comment text.\n"
                "- Do NOT include JSON, markdown, code blocks, labels like 'Comment:'/'Reply:', metadata, or quotes.\n"
                "- No preface, no explanation.\n"
            )
            last_candidate = None
            for attempt in range(max_attempts):
                prompt_to_use = prompt if attempt == 0 else (prompt + extra_guard)
                result = self.llm_analyzer._call_llm(prompt_to_use, provider, "ai_comment_generation")

                # 提取评论内容 - 处理各种返回格式
                content = None
                if isinstance(result, dict):
                    content = result.get('content', '')
                    if not content:
                        for key in ['text', 'comment', 'response', 'output', 'message']:
                            if key in result:
                                content = result[key]
                                break
                else:
                    content = str(result)
                if not content:
                    content = str(result)

                content = self._sanitize_comment_text(content)
                last_candidate = content
                if self._is_valid_english_plain_comment(content):
                    return content

            # 返回最后一次候选（便于上层记录/调试），但不用于直接发布
            if last_candidate:
                logger.warning("AI评论生成未通过英文/纯文本校验，将返回None避免发布异常内容")
            return None
            
        except Exception as e:
            logger.error(f"生成AI评论失败: {str(e)}")
            return None
    
    def _extract_plain_text(self, text: str) -> str:
        """
        从文本中提取纯文本内容，去除 JSON 包装、markdown 代码块等
        
        Args:
            text: 原始文本
            
        Returns:
            纯文本内容
        """
        if not text:
            return ""
        
        import json
        import re
        
        text = str(text).strip()
        
        # 1. 尝试解析 JSON 格式
        if text.startswith('{') or text.startswith('['):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    # 提取 content 字段（去除 note 等元数据）
                    content = parsed.get('content', '')
                    if content:
                        # 递归处理，因为 content 可能也是 JSON 字符串
                        return self._extract_plain_text(content)
                    # 如果没有 content 字段，尝试其他字段
                    for key in ['text', 'comment', 'response', 'output', 'message']:
                        if key in parsed:
                            return self._extract_plain_text(parsed[key])
                    # 如果都没有，返回整个 JSON 的字符串表示（去除元数据字段）
                    filtered = {k: v for k, v in parsed.items() 
                               if k not in ['note', 'warning', 'error', 'metadata', 'info']}
                    if len(filtered) == 1:
                        return str(list(filtered.values())[0])
                elif isinstance(parsed, list) and len(parsed) > 0:
                    # 如果是列表，取第一个元素
                    return self._extract_plain_text(parsed[0])
            except (json.JSONDecodeError, ValueError):
                # 不是有效的 JSON，继续处理
                pass
        
        # 2. 去除 markdown 代码块
        # 匹配 ```json ... ``` 或 ``` ... ```
        code_block_pattern = r'```(?:json|python|text)?\s*\n?(.*?)\n?```'
        matches = re.findall(code_block_pattern, text, re.DOTALL)
        if matches:
            # 如果有代码块，提取代码块内的内容
            text = matches[0].strip()
        
        # 3. 去除 JSON 对象模式（即使不是有效的 JSON）
        # 匹配 { "content": "...", "note": "..." } 模式
        json_pattern = r'\{[^{}]*"content"\s*:\s*"([^"]+)"[^{}]*\}'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            text = match.group(1)
            # 处理转义字符
            text = text.replace('\\n', '\n').replace('\\"', '"').replace('\\t', '\t')
        
        # 4. 去除其他可能的包装
        # 去除 "content": "..." 模式
        content_pattern = r'["\']content["\']\s*:\s*["\']([^"\']+)["\']'
        match = re.search(content_pattern, text, re.IGNORECASE)
        if match:
            text = match.group(1)
        
        # 5. 去除多余的空白和换行
        text = text.strip()
        # 去除开头和结尾的引号
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        
        # 6. 最终清理
        text = text.strip()
        
        return text

    def _sanitize_comment_text(self, text: str) -> str:
        """把模型输出清洗成“像手动输入”的纯文本。"""
        import re
        cleaned = self._extract_plain_text(text)
        cleaned = str(cleaned or "").strip()

        # 去掉可能的前缀标签
        prefix_patterns = [
            r'^\s*(here\s+is|here\'s)\s+(the\s+)?(comment|reply)\s*[:\-]\s*',
            r'^\s*(comment|reply)\s*[:\-]\s*',
            r'^\s*output\s*[:\-]\s*',
        ]
        for p in prefix_patterns:
            cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE).strip()

        # 去掉多余的包裹符号/引号
        cleaned = cleaned.strip().strip('“”"').strip("‘’'")

        # 去掉残留代码围栏
        cleaned = re.sub(r'```[\s\S]*?```', lambda m: m.group(0).strip('`'), cleaned).strip()

        # 压缩过多空行
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
        return cleaned

    def _looks_like_metadata_or_wrapper(self, text: str) -> bool:
        """判断文本是否像带元数据/包装的模型输出。"""
        if not text:
            return True
        t = text.strip()
        if t.startswith('{') or t.startswith('[') or t.startswith('```'):
            return True
        lowered = t.lower()
        bad_markers = [
            '"content"', "'content'", 'content:', 'metadata', 'note:', 'warning:', 'json',
            'model_used', 'analysis', 'explanation', 'reasoning', 'output:',
        ]
        if any(m in lowered for m in bad_markers):
            return True
        # 过多的花括号一般也不是手动输入
        if t.count('{') + t.count('}') >= 2:
            return True
        return False

    def _is_valid_english_plain_comment(self, text: str) -> bool:
        """校验：英文为主 + 不含元数据包装 + 长度/词数合理。"""
        import re
        if not text:
            return False
        t = text.strip()
        if self._looks_like_metadata_or_wrapper(t):
            return False

        # 禁止明显的中日韩字符（避免非英文）
        if re.search(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', t):
            return False

        # 统计英文单词
        words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", t)
        if len(words) < 5:
            return False

        # 英文字母比例（排除URL）
        no_url = re.sub(r'https?://\S+', '', t)
        letters = re.findall(r'[A-Za-z]', no_url)
        total_alpha = re.findall(r'[A-Za-z\u00C0-\u024F]', no_url)  # 包含少量拉丁扩展
        if len(letters) < 15:
            return False
        if total_alpha and (len(letters) / max(1, len(total_alpha))) < 0.85:
            # 主要应为英文
            return False

        return True
    
    def execute_task(self, task_id: int) -> Dict[str, Any]:
        """
        执行单个自动化任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            执行结果
        """
        try:
            session = self.db.SessionLocal()
            try:
                # 获取任务
                task = session.query(self.db.AutoInteractionQueue).filter_by(id=task_id).first()
                if not task:
                    return {'success': False, 'error': '任务不存在'}
                
                if task.status != 'pending':
                    return {'success': False, 'error': f'任务状态不是pending: {task.status}'}
                
                # 更新状态为执行中
                task.status = 'executing'
                session.commit()
                
                # 执行互动
                result = {'success': True, 'actions': []}

                def _is_ratelimit_result(res: Dict[str, Any]) -> bool:
                    err = str(res.get('error', '') or '')
                    return res.get('error_type') == 'ratelimit' or ('RATELIMIT' in err)

                def _defer_task(res: Dict[str, Any]) -> Dict[str, Any]:
                    """遇到限速：把任务回滚为pending，交给上层做暂停/自恢复。"""
                    retry_after = res.get('retry_after')
                    err = str(res.get('error', 'RATELIMIT') or 'RATELIMIT')
                    task.status = 'pending'
                    task.error_message = err
                    session.commit()
                    return {
                        'success': False,
                        'error': err,
                        'error_type': 'ratelimit',
                        'retry_after': retry_after,
                        'task_id': task_id
                    }
                
                # 检查Reddit API认证状态
                if not self.interaction_manager.reddit_scraper or not self.interaction_manager.reddit_scraper.is_authenticated():
                    error_msg = "Reddit API未认证或认证已过期，无法执行任务"
                    logger.error(error_msg)
                    return {'success': False, 'error': error_msg}

                # 1) deep/standard：先评论，再点赞（避免评论被限速时反复点赞）
                if task.interaction_type in ('deep', 'standard'):
                    if task.ai_comment and self.scraper:
                        # 二次清洗+校验：确保发布到Reddit的内容像“手动输入”，且为英文
                        comment_text = self._sanitize_comment_text(task.ai_comment)
                        if not self._is_valid_english_plain_comment(comment_text):
                            # 尝试自动重生成一次（避免历史任务遗留脏数据）
                            try:
                                reddit_post = session.query(self.db.RedditPost).filter_by(id=task.post_id).first()
                                if reddit_post:
                                    post_data = {
                                        'id': task.post_id,
                                        'title': reddit_post.title or '',
                                        'selftext': reddit_post.selftext or '',
                                        'subreddit': task.subreddit
                                    }
                                    regenerated = self.generate_ai_comment(post_data, task.interaction_type)
                                    if regenerated and self._is_valid_english_plain_comment(regenerated):
                                        comment_text = regenerated
                                        task.ai_comment = regenerated
                                        session.commit()
                            except Exception as regen_err:
                                logger.warning(f"评论内容不合规，自动重生成失败: {str(regen_err)}")

                        if not self._is_valid_english_plain_comment(comment_text):
                            err = "AI回帖内容未通过校验（必须为英文纯文本，且不能包含JSON/元数据/标签）"
                            logger.warning(err)
                            task.status = 'failed'
                            task.error_message = err
                            session.commit()
                            return {'success': False, 'error': err}

                        comment_result = self.scraper.reply_to_post(task.post_id, comment_text)
                        if comment_result.get('success'):
                            result['actions'].append('comment')
                            logger.info(f"任务 {task_id} 评论发布成功")
                        else:
                            if _is_ratelimit_result(comment_result):
                                return _defer_task(comment_result)
                            error = comment_result.get('error', '未知错误')
                            logger.warning(f"任务 {task_id} 评论发布失败: {error}")
                            task.status = 'failed'
                            task.error_message = str(error)
                            session.commit()
                            return {'success': False, 'error': str(error)}
                    else:
                        # 需要评论但没有内容/没有scraper，视为失败
                        err = "缺少评论内容或RedditScraper实例，无法发布评论"
                        task.status = 'failed'
                        task.error_message = err
                        session.commit()
                        return {'success': False, 'error': err}

                # 2) 点赞（所有类型都需要）
                upvote_result = self.interaction_manager.upvote_post(task.post_id, task.subreddit)
                if upvote_result.get('success'):
                    result['actions'].append('upvote')
                else:
                    if _is_ratelimit_result(upvote_result):
                        return _defer_task(upvote_result)
                    error = upvote_result.get('error', '未知错误')
                    logger.warning(f"点赞失败: {error}")
                    # 如果是认证错误，直接返回失败
                    if 'USER_REQUIRED' in str(error) or 'Please log in' in str(error) or 'not authenticated' in str(error).lower():
                        return {'success': False, 'error': f'Reddit API认证失败: {error}'}
                    task.status = 'failed'
                    task.error_message = str(error)
                    session.commit()
                    return {'success': False, 'error': str(error)}

                # 更新任务状态为完成
                task.status = 'completed'
                task.executed_at = datetime.utcnow()
                task.error_message = None
                session.commit()

                logger.info(f"任务 {task_id} 执行成功")
                return result
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"执行任务失败: {str(e)}")
            # 更新任务状态为失败
            try:
                session = self.db.SessionLocal()
                try:
                    task = session.query(self.db.AutoInteractionQueue).filter_by(id=task_id).first()
                    if task:
                        task.status = 'failed'
                        task.error_message = str(e)
                        session.commit()
                finally:
                    session.close()
            except:
                pass
            
            return {'success': False, 'error': str(e)}


