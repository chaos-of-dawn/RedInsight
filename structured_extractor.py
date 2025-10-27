"""
结构化抽取模块
用于从Reddit数据中提取结构化的关键信息
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class StructuredExtraction:
    """结构化抽取结果"""
    post_id: str
    title: str
    content: str
    author: str
    subreddit: str
    created_utc: float
    score: int
    upvote_ratio: float
    
    # 结构化字段
    main_topic: str
    pain_points: List[str]
    user_needs: List[str]
    sentiment: str
    sentiment_score: float
    key_phrases: List[str]
    mentioned_tools: List[str]
    evidence_sentences: List[str]
    confidence_score: float
    long_tail_keywords: List[str]  # 长尾关键词
    
    # 元数据
    extraction_timestamp: datetime
    extraction_model: str

class StructuredExtractor:
    """结构化抽取器"""
    
    def __init__(self, llm_analyzer):
        self.llm_analyzer = llm_analyzer
        self.extraction_schema = {
            "type": "object",
            "properties": {
                "main_topic": {
                    "type": "string",
                    "description": "帖子的主要讨论主题，1-2个词概括"
                },
                "pain_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "用户提到的痛点或问题，最多3个"
                },
                "user_needs": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "用户表达的需求或期望，最多3个"
                },
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral", "mixed"],
                    "description": "整体情感倾向"
                },
                "sentiment_score": {
                    "type": "number",
                    "minimum": -1,
                    "maximum": 1,
                    "description": "情感强度分数，-1到1"
                },
                "key_phrases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "关键短语或术语，最多5个"
                },
                "mentioned_tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "提到的工具、产品或品牌，最多5个"
                },
                "evidence_sentences": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "支持上述分析的证据句子，最多3个"
                },
                "confidence_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "抽取结果的可信度，0到1"
                },
                "long_tail_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "长尾关键词，如'iPhone battery replacement'、'home renovation cost'等多词短语，最多10个"
                }
            },
            "required": ["main_topic", "pain_points", "user_needs", "sentiment", 
                        "sentiment_score", "key_phrases", "mentioned_tools", 
                        "evidence_sentences", "confidence_score", "long_tail_keywords"]
        }
    
    def extract_from_post(self, post_data: Dict[str, Any], provider: str = "openai") -> Optional[StructuredExtraction]:
        """从单个帖子提取结构化信息"""
        try:
            # 准备文本内容
            title = post_data.get('title', '')
            content = post_data.get('selftext', '')
            full_text = f"{title}\n\n{content}".strip()
            
            if not full_text:
                logger.warning(f"帖子 {post_data.get('id', 'unknown')} 内容为空，跳过")
                return None
            
            # 构建抽取提示词
            prompt = self._build_extraction_prompt(full_text)
            
            # 调用LLM进行结构化抽取
            logger.info(f"调用LLM进行结构化抽取，provider: {provider}")
            result = self.llm_analyzer._call_llm(
                prompt=prompt,
                provider=provider,
                analysis_type="structured_extraction"
            )
            
            # 详细的调试信息
            logger.info(f"LLM调用结果: {result}")
            
            if "error" in result:
                logger.error(f"LLM调用失败: {result['error']}")
                return None
            
            # 处理不同的返回格式
            content = result.get('content', '')
            if not content:
                # 如果LLM返回的是原始响应，尝试提取内容
                raw_response = result.get('raw_response', '')
                if raw_response:
                    content = raw_response
                    logger.info("使用原始响应作为内容")
                else:
                    logger.error("LLM返回空内容")
                    return None
            
            logger.info(f"LLM返回内容长度: {len(content)}")
            
            if not content or len(content.strip()) == 0:
                logger.error("LLM返回空内容")
                return None
            
            # 解析JSON结果
            extracted_data = self._parse_extraction_result(content)
            if not extracted_data:
                logger.error("JSON解析失败")
                return None
            
            # 创建结构化抽取对象
            extraction = StructuredExtraction(
                post_id=post_data.get('id', ''),
                title=title,
                content=content,
                author=post_data.get('author', ''),
                subreddit=post_data.get('subreddit', ''),
                created_utc=post_data.get('created_utc', 0),
                score=post_data.get('score', 0),
                upvote_ratio=post_data.get('upvote_ratio', 0),
                
                main_topic=extracted_data.get('main_topic', ''),
                pain_points=extracted_data.get('pain_points', []),
                user_needs=extracted_data.get('user_needs', []),
                sentiment=extracted_data.get('sentiment', 'neutral'),
                sentiment_score=extracted_data.get('sentiment_score', 0.0),
                key_phrases=extracted_data.get('key_phrases', []),
                mentioned_tools=extracted_data.get('mentioned_tools', []),
                evidence_sentences=extracted_data.get('evidence_sentences', []),
                confidence_score=extracted_data.get('confidence_score', 0.0),
                long_tail_keywords=extracted_data.get('long_tail_keywords', []),
                
                extraction_timestamp=datetime.now(),
                extraction_model=provider
            )
            
            return extraction
            
        except Exception as e:
            logger.error(f"结构化抽取失败: {str(e)}")
            return None
    
    def extract_batch(self, posts_data: List[Dict[str, Any]], provider: str = "openai", 
                     batch_size: int = 5) -> List[StructuredExtraction]:
        """批量提取结构化信息"""
        extractions = []
        
        for i in range(0, len(posts_data), batch_size):
            batch = posts_data[i:i + batch_size]
            logger.info(f"处理批次 {i//batch_size + 1}/{(len(posts_data)-1)//batch_size + 1}")
            
            for post in batch:
                extraction = self.extract_from_post(post, provider)
                if extraction:
                    extractions.append(extraction)
        
        logger.info(f"批量抽取完成，成功 {len(extractions)}/{len(posts_data)} 条")
        return extractions
    
    def _build_extraction_prompt(self, text: str) -> str:
        """构建抽取提示词"""
        # 转义文本中的花括号，避免f-string格式化错误
        escaped_text = text.replace('{', '{{').replace('}', '}}')
        
        return f"""分析以下Reddit帖子，提取关键信息。

帖子内容：
{escaped_text}

请输出JSON格式的分析结果，格式如下：

{{
  "main_topic": "主题",
  "pain_points": ["问题1", "问题2"],
  "user_needs": ["需求1", "需求2"],
  "sentiment": "positive",
  "sentiment_score": 0.5,
  "key_phrases": ["关键词1", "关键词2"],
  "mentioned_tools": ["工具1", "工具2"],
  "evidence_sentences": ["证据1", "证据2"],
  "confidence_score": 0.8,
  "long_tail_keywords": ["多词短语1", "多词短语2"]
}}

要求：
- 只输出JSON，不要其他文字
- 使用双引号
- 不要markdown标记
- 确保JSON格式正确
- long_tail_keywords是2-5个词的关键词短语，例如"iPhone battery replacement"、"home renovation cost"等"""
    
    def _parse_extraction_result(self, content: str) -> Optional[Dict[str, Any]]:
        """解析抽取结果"""
        try:
            import re
            
            # 清理内容
            content = content.strip()
            
            # 尝试直接解析JSON
            if content.startswith('{'):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass
            
            # 尝试从代码块中提取JSON
            json_patterns = [
                r'```(?:json)?\s*(\{.*?\})\s*```',
                r'```json\s*(\{.*?\})\s*```',
                r'```\s*(\{.*?\})\s*```'
            ]
            
            for pattern in json_patterns:
                json_match = re.search(pattern, content, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        continue
            
            # 尝试查找JSON对象（更宽松的匹配）
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            # 尝试修复常见的JSON问题
            fixed_content = self._fix_json_format(content)
            if fixed_content:
                try:
                    return json.loads(fixed_content)
                except json.JSONDecodeError:
                    pass
            
            # 最后的尝试：使用更宽松的解析
            try:
                # 尝试提取所有可能的JSON片段
                json_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                for json_obj in json_objects:
                    try:
                        parsed = json.loads(json_obj)
                        if isinstance(parsed, dict) and 'main_topic' in parsed:
                            logger.info("使用宽松解析成功")
                            return parsed
                    except:
                        continue
            except:
                pass
            
            # 记录详细的调试信息
            logger.warning(f"无法解析JSON结果，原始内容长度: {len(content)}")
            logger.warning(f"内容前200字符: {content[:200]}")
            logger.warning(f"内容后200字符: {content[-200:]}")
            
            # 尝试返回默认结构，避免完全失败
            logger.info("尝试返回默认结构...")
            return {
                "main_topic": "未识别",
                "pain_points": [],
                "user_needs": [],
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "key_phrases": [],
                "mentioned_tools": [],
                "evidence_sentences": [],
                "confidence_score": 0.1
            }
            
        except Exception as e:
            logger.error(f"解析结果失败: {str(e)}")
            return None
    
    def _fix_json_format(self, content: str) -> Optional[str]:
        """尝试修复JSON格式问题"""
        try:
            import re
            
            # 移除可能的markdown标记
            content = re.sub(r'^```.*?\n', '', content)
            content = re.sub(r'\n```.*?$', '', content)
            
            # 查找JSON对象
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                return None
            
            json_str = json_match.group(0)
            
            # 修复常见的JSON问题
            # 1. 修复单引号为双引号
            json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
            json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)
            
            # 2. 修复尾随逗号
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            # 3. 修复布尔值
            json_str = re.sub(r'\bTrue\b', 'true', json_str)
            json_str = re.sub(r'\bFalse\b', 'false', json_str)
            json_str = re.sub(r'\bNone\b', 'null', json_str)
            
            return json_str
            
        except Exception as e:
            logger.error(f"修复JSON格式失败: {str(e)}")
            return None
