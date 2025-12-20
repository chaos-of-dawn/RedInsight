"""
大模型分析模块 - 接入OpenAI和Anthropic API进行数据分析
"""
import openai
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
import logging
from typing import List, Dict, Any, Optional
import json
import time
import re
import requests
from app_config import Config

class LLMAnalyzer:
    """大模型分析器"""
    
    def __init__(self, api_keys: dict = None):
        """初始化大模型客户端"""
        self.logger = logging.getLogger(__name__)
        
        # 使用传入的API密钥或默认配置
        openai_key = (api_keys.get('openai_api_key') if api_keys else None) or Config.OPENAI_API_KEY
        anthropic_key = (api_keys.get('anthropic_api_key') if api_keys else None) or Config.ANTHROPIC_API_KEY
        deepseek_key = (api_keys.get('deepseek_api_key') if api_keys else None) or Config.DEEPSEEK_API_KEY
        
        # 初始化OpenAI客户端
        if openai_key:
            try:
                self.openai_client = openai.OpenAI(
                    api_key=openai_key
                )
            except Exception as e:
                self.logger.warning(f"OpenAI客户端初始化失败: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            
        # 初始化Anthropic客户端
        if anthropic_key and ANTHROPIC_AVAILABLE:
            try:
                self.anthropic_client = anthropic.Anthropic(
                    api_key=anthropic_key
                )
            except Exception as e:
                self.logger.warning(f"Anthropic客户端初始化失败: {e}")
                self.anthropic_client = None
        else:
            if anthropic_key and not ANTHROPIC_AVAILABLE:
                self.logger.warning("Anthropic模块未安装，跳过Anthropic客户端初始化")
            self.anthropic_client = None
        
        # DeepSeek API配置
        self.deepseek_api_key = deepseek_key
        # DeepSeek API端点 - 使用正确的URL格式
        self.deepseek_base_url = "https://api.deepseek.com"
        
        # 调试信息
        self.logger.info(f"LLMAnalyzer初始化完成:")
        self.logger.info(f"  OpenAI客户端: {'已配置' if self.openai_client else '未配置'}")
        self.logger.info(f"  Anthropic客户端: {'已配置' if self.anthropic_client else '未配置'}")
        self.logger.info(f"  DeepSeek API密钥: {'已配置' if self.deepseek_api_key else '未配置'}")
    
    def analyze_sentiment(self, text: str, provider: str = "openai", custom_prompt: str = None) -> Dict[str, Any]:
        """
        分析文本情感
        
        Args:
            text: 要分析的文本
            provider: API提供商 ("openai" 或 "anthropic")
            custom_prompt: 自定义提示词模板
            
        Returns:
            情感分析结果
        """
        if custom_prompt:
            prompt = custom_prompt.format(text=text)
        else:
            prompt = f"""
            请分析以下文本的情感倾向，并给出详细的分析结果：
            
            文本内容：{text}
            
            请按以下格式返回JSON结果：
            {{
                "sentiment": "positive/negative/neutral",
                "confidence": 0.0-1.0,
                "emotions": ["emotion1", "emotion2"],
                "summary": "简要总结",
                "key_phrases": ["phrase1", "phrase2"]
            }}
            """
        
        return self._call_llm(prompt, provider, "sentiment_analysis")
    
    def analyze_topic(self, text: str, provider: str = "openai", custom_prompt: str = None) -> Dict[str, Any]:
        """
        分析文本主题
        
        Args:
            text: 要分析的文本
            provider: API提供商
            custom_prompt: 自定义提示词模板
            
        Returns:
            主题分析结果
        """
        if custom_prompt:
            prompt = custom_prompt.format(text=text)
        else:
            prompt = f"""
            请分析以下文本的主要主题和关键词：
            
            文本内容：{text}
            
            请按以下格式返回JSON结果：
            {{
                "main_topics": ["topic1", "topic2"],
                "keywords": ["keyword1", "keyword2"],
                "category": "技术/生活/娱乐/其他",
                "summary": "主题总结",
                "relevance_score": 0.0-1.0
            }}
            """
        
        return self._call_llm(prompt, provider, "topic_analysis")
    
    def analyze_quality(self, text: str, provider: str = "openai", custom_prompt: str = None) -> Dict[str, Any]:
        """
        分析文本质量
        
        Args:
            text: 要分析的文本
            provider: API提供商
            custom_prompt: 自定义提示词模板
            
        Returns:
            质量分析结果
        """
        if custom_prompt:
            prompt = custom_prompt.format(text=text)
        else:
            prompt = f"""
            请评估以下文本的质量，包括内容的深度、逻辑性和价值：
            
            文本内容：{text}
            
            请按以下格式返回JSON结果：
            {{
                "quality_score": 0.0-1.0,
                "depth": "浅层/中等/深层",
                "logic_quality": "好/一般/差",
                "value": "高/中/低",
                "suggestions": ["建议1", "建议2"],
                "summary": "质量评估总结"
            }}
            """
        
        return self._call_llm(prompt, provider, "quality_analysis")
    
    def generate_summary(self, posts: List[Dict], provider: str = "openai") -> Dict[str, Any]:
        """
        生成多个帖子的汇总分析
        
        Args:
            posts: 帖子列表
            provider: API提供商
            
        Returns:
            汇总分析结果
        """
        posts_text = ""
        for i, post in enumerate(posts[:10], 1):  # 限制前10个帖子
            posts_text += f"帖子{i}：{post.get('title', '')}\n内容：{post.get('selftext', '')}\n\n"
        
        prompt = f"""
        请分析以下Reddit帖子，生成一个综合性的汇总报告：
        
        {posts_text}
        
        请按以下格式返回JSON结果：
        {{
            "overall_trends": ["趋势1", "趋势2"],
            "common_themes": ["主题1", "主题2"],
            "sentiment_overview": "整体情感倾向",
            "key_insights": ["洞察1", "洞察2"],
            "recommendations": ["建议1", "建议2"],
            "summary": "综合总结"
        }}
        """
        
        return self._call_llm(prompt, provider, "summary_analysis")
    
    def analyze_community_engagement(self, posts: List[Dict], comments: List[Dict], 
                                   provider: str = "openai") -> Dict[str, Any]:
        """
        分析社区参与度
        
        Args:
            posts: 帖子列表
            comments: 评论列表
            provider: API提供商
            
        Returns:
            社区参与度分析结果
        """
        engagement_data = {
            "total_posts": len(posts),
            "total_comments": len(comments),
            "avg_score": sum(p.get('score', 0) for p in posts) / len(posts) if posts else 0,
            "avg_comments": sum(p.get('num_comments', 0) for p in posts) / len(posts) if posts else 0
        }
        
        prompt = f"""
        基于以下社区数据，分析用户参与度和互动模式：
        
        数据统计：
        - 帖子总数：{engagement_data['total_posts']}
        - 评论总数：{engagement_data['total_comments']}
        - 平均得分：{engagement_data['avg_score']:.2f}
        - 平均评论数：{engagement_data['avg_comments']:.2f}
        
        请按以下格式返回JSON结果：
        {{
            "engagement_level": "高/中/低",
            "interaction_patterns": ["模式1", "模式2"],
            "community_health": "健康/一般/需要关注",
            "growth_indicators": ["指标1", "指标2"],
            "recommendations": ["建议1", "建议2"],
            "summary": "参与度分析总结"
        }}
        """
        
        return self._call_llm(prompt, provider, "engagement_analysis")
    
    def analyze_posts_batch(self, posts_data: List[Dict], analysis_type: str, provider: str = "openai") -> Dict[str, Any]:
        """
        批量分析多个帖子
        
        Args:
            posts_data: 帖子数据列表
            analysis_type: 分析类型 ("sentiment", "topic", "quality")
            provider: API提供商
            
        Returns:
            批量分析结果
        """
        if not posts_data:
            return {"error": "没有提供帖子数据"}
        
        # 构建批量分析的提示词
        posts_text = ""
        for i, post in enumerate(posts_data, 1):
            posts_text += f"帖子{i}:\n"
            posts_text += f"标题: {post.get('title', '')}\n"
            posts_text += f"内容: {post.get('content', '')}\n"
            posts_text += f"作者: {post.get('author', '')}\n"
            posts_text += f"子版块: {post.get('subreddit', '')}\n"
            posts_text += f"分数: {post.get('score', 0)}\n"
            posts_text += f"时间: {post.get('created_time', '')}\n\n"
        
        if analysis_type == "sentiment":
            prompt = f"""
            请对以下多个Reddit帖子进行批量情感分析：
            
            {posts_text}
            
            请按以下格式返回JSON结果：
            {{
                "batch_analysis": {{
                    "overall_sentiment": "positive/negative/neutral",
                    "sentiment_distribution": {{
                        "positive": 0,
                        "negative": 0,
                        "neutral": 0
                    }},
                    "average_confidence": 0.0,
                    "common_emotions": ["emotion1", "emotion2"],
                    "summary": "批量情感分析总结"
                }},
                "individual_results": [
                    {{
                        "post_id": "帖子ID",
                        "sentiment": "positive/negative/neutral",
                        "confidence": 0.0,
                        "key_emotions": ["emotion1", "emotion2"]
                    }}
                ]
            }}
            """
        elif analysis_type == "topic":
            prompt = f"""
            请对以下多个Reddit帖子进行批量主题分析：
            
            {posts_text}
            
            请按以下格式返回JSON结果：
            {{
                "batch_analysis": {{
                    "main_topics": ["topic1", "topic2", "topic3"],
                    "topic_frequency": {{
                        "topic1": 0,
                        "topic2": 0
                    }},
                    "common_keywords": ["keyword1", "keyword2"],
                    "category_distribution": {{
                        "技术": 0,
                        "生活": 0,
                        "娱乐": 0
                    }},
                    "summary": "批量主题分析总结"
                }},
                "individual_results": [
                    {{
                        "post_id": "帖子ID",
                        "main_topics": ["topic1", "topic2"],
                        "keywords": ["keyword1", "keyword2"],
                        "category": "技术/生活/娱乐/其他"
                    }}
                ]
            }}
            """
        elif analysis_type == "quality":
            prompt = f"""
            请对以下多个Reddit帖子进行批量质量评估：
            
            {posts_text}
            
            请按以下格式返回JSON结果：
            {{
                "batch_analysis": {{
                    "average_quality_score": 0.0,
                    "quality_distribution": {{
                        "high": 0,
                        "medium": 0,
                        "low": 0
                    }},
                    "common_issues": ["issue1", "issue2"],
                    "improvement_suggestions": ["suggestion1", "suggestion2"],
                    "summary": "批量质量评估总结"
                }},
                "individual_results": [
                    {{
                        "post_id": "帖子ID",
                        "quality_score": 0.0,
                        "depth": "浅层/中等/深层",
                        "logic_quality": "好/一般/差",
                        "value": "高/中/低"
                    }}
                ]
            }}
            """
        else:
            return {"error": f"不支持的分析类型: {analysis_type}"}
        
        return self._call_llm(prompt, provider, f"batch_{analysis_type}_analysis")
    
    def analyze_comprehensive(self, text: str, provider: str = "openai", custom_prompt: str = None) -> Dict[str, Any]:
        """
        综合分析文本（包含主题、情感、洞察和结构化分析）
        
        Args:
            text: 要分析的文本
            provider: API提供商
            custom_prompt: 自定义综合提示词模板（可以是包含{text}占位符的模板，也可以是完整的提示词）
            
        Returns:
            综合分析结果
        """
        if custom_prompt:
            # 检查custom_prompt是否包含{text}占位符
            # 如果包含，说明是模板，需要格式化
            # 如果不包含，说明已经是完整的提示词，直接使用
            if "{text}" in custom_prompt:
                prompt = custom_prompt.format(text=text)
            else:
                # 已经是完整的提示词（可能已经在其他地方包含了数据），直接使用
                prompt = custom_prompt
        else:
            prompt = f"""
            你是一位专业的社交媒体数据分析师。你的任务是深度分析Reddit社区中关于指定主题的讨论。

            请根据下面提供的原始Reddit帖子和评论数据，完成以下四个部分的结构化分析和总结。

            ---
            ### 原始数据：{text}
            ---

            ### **任务一：情感与立场分析 (Sentiment & Stance)**

            1. **整体情绪：** 总结这段数据流中用户讨论的整体情绪倾向（例如：70% 积极，20% 负面，10% 中立）。
            2. **核心情感识别：** 识别讨论中最突出的三种情感（例如：沮丧、希望、感激、焦虑）。
            3. **争议点（如果存在）：** 如果用户在讨论某个特定方法或产品时存在显著争议，请明确指出该争议的核心焦点。

            ### **任务二：主题与痛点提取 (Topic & Pain Points)**

            1. **主要讨论主题：** 将这段数据内容归纳为 2 到 3 个最集中的讨论主题或焦点。
            2. **提取核心痛点：** 总结用户遇到的最常见、最迫切的问题或挑战（即用户主要在抱怨什么或寻求什么帮助）。

            ### **任务三：实用建议和技巧归纳 (Actionable Advice)**

            1. **Top 5 实用建议：** 从评论和回复中提取并整理出五条最具操作性、最实用的建议、技巧或步骤。请以简洁的列表形式呈现。
            2. **工具/品牌提及：** 提取数据中被提及最频繁的工具、产品或品牌名称，并指出用户对它们的态度。

            ### **任务四：结构化摘要与总结 (Structured Output)**

            请用一段简洁的文字总结上述分析结果，然后以JSON格式输出最关键的洞察，以便后续导入数据库。

            **JSON输出格式：**

            ```json
            {{
                "overall_sentiment": "整体情绪百分比",
                "main_emotions": ["情感1", "情感2", "情感3"],
                "controversy_points": ["争议点1", "争议点2"],
                "main_topics": ["主题1", "主题2", "主题3"],
                "top_pain_points": ["痛点1", "痛点2", "痛点3"],
                "top_advice": ["建议1", "建议2", "建议3", "建议4", "建议5"],
                "mentioned_tools": ["工具1", "工具2"],
                "summary": "综合分析总结"
            }}
            ```
            """
        
        return self._call_llm(prompt, provider, "comprehensive_analysis")
    
    def analyze_posts_batch(self, posts_data: list, provider: str = "openai", analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        批量分析帖子数据
        
        Args:
            posts_data: 帖子数据列表
            provider: API提供商
            analysis_type: 分析类型 (comprehensive, sentiment, topic, quality)
            
        Returns:
            批量分析结果
        """
        try:
            # 将帖子数据组合成文本
            combined_text = ""
            for post in posts_data:
                combined_text += f"标题: {post.get('title', '')}\n"
                combined_text += f"内容: {post.get('content', '')}\n"
                combined_text += f"作者: {post.get('author', '')}\n"
                combined_text += f"分数: {post.get('score', 0)}\n"
                combined_text += f"子版块: {post.get('subreddit', '')}\n"
                combined_text += "-" * 50 + "\n"
            
            # 根据分析类型调用相应方法
            if analysis_type == "comprehensive":
                return self.analyze_comprehensive(combined_text, provider)
            elif analysis_type == "sentiment":
                return self.analyze_sentiment(combined_text, provider)
            elif analysis_type == "topic":
                return self.analyze_topic(combined_text, provider)
            elif analysis_type == "quality":
                return self.analyze_quality(combined_text, provider)
            else:
                return {"error": f"不支持的分析类型: {analysis_type}"}
                
        except Exception as e:
            self.logger.error(f"批量分析失败: {str(e)}")
            return {"error": str(e)}
    
    def _call_llm(self, prompt: str, provider: str, analysis_type: str) -> Dict[str, Any]:
        """
        调用大模型API，带自动故障转移
        
        Args:
            prompt: 提示词
            provider: API提供商
            analysis_type: 分析类型
            
        Returns:
            API响应结果
        """
        # 定义可用的提供商优先级列表
        provider_priority = ["deepseek", "openai", "anthropic"]
        
        # 如果指定了provider，将其放在优先级列表首位
        if provider in provider_priority:
            provider_priority.remove(provider)
            provider_priority.insert(0, provider)
        
        last_error = None
        
        for current_provider in provider_priority:
            try:
                self.logger.info(f"尝试使用 {current_provider} API...")
                
                if current_provider == "openai" and self.openai_client:
                    result = self._call_openai(prompt, analysis_type)
                    if "error" not in result:
                        self.logger.info(f"OpenAI API调用成功")
                        return result
                    else:
                        last_error = result.get("error", "未知错误")
                        self.logger.warning(f"OpenAI API调用失败: {last_error}")
                        
                elif current_provider == "anthropic" and self.anthropic_client:
                    result = self._call_anthropic(prompt, analysis_type)
                    if "error" not in result:
                        self.logger.info(f"Anthropic API调用成功")
                        return result
                    else:
                        last_error = result.get("error", "未知错误")
                        self.logger.warning(f"Anthropic API调用失败: {last_error}")
                        
                elif current_provider == "deepseek" and self.deepseek_api_key:
                    result = self._call_deepseek(prompt, analysis_type)
                    if "error" not in result:
                        self.logger.info(f"DeepSeek API调用成功")
                        return result
                    else:
                        last_error = result.get("error", "未知错误")
                        self.logger.warning(f"DeepSeek API调用失败: {last_error}")
                else:
                    self.logger.warning(f"{current_provider} API未配置或不可用")
                    continue
                    
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"{current_provider} API调用异常: {last_error}")
                continue
        
        # 所有提供商都失败了
        self.logger.error("所有API提供商都不可用")
        return {
            "error": "所有API提供商都不可用",
            "last_error": last_error,
            "available_providers": [p for p in provider_priority if self._is_provider_available(p)]
        }
    
    def _is_provider_available(self, provider: str) -> bool:
        """检查提供商是否可用"""
        if provider == "openai":
            return self.openai_client is not None
        elif provider == "anthropic":
            return self.anthropic_client is not None
        elif provider == "deepseek":
            return self.deepseek_api_key is not None
        return False
    
    def _call_openai(self, prompt: str, analysis_type: str) -> Dict[str, Any]:
        """调用OpenAI API"""
        try:
            response = self.openai_client.chat.completions.create(
                model=Config.ANALYSIS_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个专业的数据分析师，擅长分析社交媒体内容。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content
            return self._parse_json_response(result_text, analysis_type)
            
        except Exception as e:
            self.logger.error(f"OpenAI API调用失败: {str(e)}")
            return {"error": str(e)}
    
    def _call_anthropic(self, prompt: str, analysis_type: str) -> Dict[str, Any]:
        """调用Anthropic API"""
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            result_text = response.content[0].text
            return self._parse_json_response(result_text, analysis_type)
            
        except Exception as e:
            self.logger.error(f"Anthropic API调用失败: {str(e)}")
            return {"error": str(e)}
    
    def _parse_json_response(self, response_text: str, analysis_type: str) -> Dict[str, Any]:
        """解析JSON响应，带容错机制"""
        try:
            # 尝试提取JSON部分
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                # 查找下一个```，但需要确保不是开始标记
                json_end = response_text.find("```", json_start)
                if json_end == -1:
                    # 如果没有找到结束标记，尝试找到最后一个}
                    json_end = response_text.rfind("}")
                    if json_end > json_start:
                        json_end += 1
                    else:
                        json_end = len(response_text)
                json_text = response_text[json_start:json_end].strip()
                # 如果提取的文本仍然包含```，移除它们
                json_text = json_text.replace("```", "").strip()
            elif "```" in response_text and "{" in response_text:
                # 可能有代码块但没有json标记
                json_start = response_text.find("{")
                if json_start > 0:
                    json_end = response_text.rfind("}") + 1
                    if json_end > json_start:
                        json_text = response_text[json_start:json_end]
                    else:
                        json_text = response_text[json_start:]
                else:
                    json_text = response_text
            elif "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_end > json_start:
                    json_text = response_text[json_start:json_end]
                else:
                    # 如果找不到闭合的}，尝试修复
                    json_text = response_text[json_start:]
            else:
                # 尝试更宽松的检测：查找可能的JSON结构
                # 检查是否有类似JSON的键值对模式
                has_json_like_pattern = bool(re.search(r'["\']\w+["\']\s*:\s*["\']', response_text) or 
                                             re.search(r'["\']\w+["\']\s*:\s*\[', response_text) or
                                             re.search(r'["\']\w+["\']\s*:\s*\{', response_text))
                
                if has_json_like_pattern:
                    # 可能有JSON结构但格式不标准，尝试提取
                    self.logger.debug("检测到类似JSON的结构，尝试提取")
                    # 尝试找到第一个{和最后一个}
                    json_start = response_text.find("{")
                    if json_start >= 0:
                        json_end = response_text.rfind("}")
                        if json_end > json_start:
                            json_text = response_text[json_start:json_end+1]
                        else:
                            json_text = response_text[json_start:]
                    else:
                        # 没有找到JSON结构，可能是纯文本响应
                        self.logger.info("响应中没有找到标准JSON结构，尝试将纯文本转换为JSON")
                        json_text = self._convert_text_to_json(response_text, analysis_type)
                else:
                    # 没有找到JSON结构，可能是纯文本响应
                    self.logger.info("响应中没有找到JSON结构，尝试将纯文本转换为JSON")
                    json_text = self._convert_text_to_json(response_text, analysis_type)
            
            # 清理JSON文本
            json_text = self._clean_json_text(json_text)
            
            result = json.loads(json_text)
            return {
                "content": json_text,  # 原始JSON文本
                "parsed": result,       # 解析后的对象
                "analysis_type": analysis_type,
                "timestamp": time.time()
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {str(e)}")
            self.logger.error(f"错误位置: 行 {e.lineno}, 列 {e.colno}")
            self.logger.error(f"尝试解析的JSON文本（前500字符）: {json_text[:500] if 'json_text' in locals() else response_text[:500]}")
            self.logger.error(f"原始响应（前1000字符）: {response_text[:1000]}")
            
            # 尝试修复常见的JSON错误
            try:
                if 'json_text' in locals():
                    fixed_json = self._fix_json_errors(json_text)
                else:
                    fixed_json = self._fix_json_errors(response_text)
                result = json.loads(fixed_json)
                self.logger.info("JSON自动修复成功")
                return {
                    "content": fixed_json,  # 修复后的JSON文本
                    "parsed": result,       # 解析后的对象
                    "analysis_type": analysis_type,
                    "timestamp": time.time(),
                    "warning": "JSON已自动修复"
                }
            except Exception as fix_error:
                self.logger.error(f"JSON修复也失败: {str(fix_error)}")
                # 尝试更激进的修复：直接截断未闭合的字符串
                try:
                    if 'json_text' in locals():
                        aggressive_fixed = self._aggressive_fix_json(json_text)
                    else:
                        aggressive_fixed = self._aggressive_fix_json(response_text)
                    result = json.loads(aggressive_fixed)
                    self.logger.info("使用激进修复策略成功")
                    return {
                        "content": aggressive_fixed,
                        "parsed": result,
                        "analysis_type": analysis_type,
                        "timestamp": time.time(),
                        "warning": "JSON已使用激进修复策略修复（可能丢失部分内容）"
                    }
                except Exception as aggressive_error:
                    self.logger.error(f"激进修复也失败: {str(aggressive_error)}")
                    # 最后尝试：直接提取translated_text字段（如果是翻译响应）
                    if analysis_type == "translation":
                        try:
                            # 尝试从原始响应中提取translated_text
                            translated_match = re.search(r'"translated_text"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', response_text, re.DOTALL)
                            if not translated_match:
                                # 尝试更宽松的匹配，包括未闭合的字符串
                                translated_match = re.search(r'"translated_text"\s*:\s*"([^"]*)"', response_text[:5000])  # 只匹配前5000字符
                            
                            if translated_match:
                                translated_text = translated_match.group(1)
                                # 转义未转义的换行符等
                                translated_text = translated_text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                                result = {
                                    "translated_text": translated_text,
                                    "original_text": "",
                                    "source_language": "未知",
                                    "target_language": "未知",
                                    "translation_quality": "一般",
                                    "notes": "JSON解析失败，已从响应中提取部分翻译内容"
                                }
                                self.logger.info("从响应中提取部分翻译内容成功")
                                return {
                                    "content": json.dumps(result, ensure_ascii=False),
                                    "parsed": result,
                                    "analysis_type": analysis_type,
                                    "timestamp": time.time(),
                                    "warning": "JSON解析失败，已从响应中提取部分内容"
                                }
                        except Exception as extract_error:
                            self.logger.error(f"提取部分内容也失败: {str(extract_error)}")
            
            # 如果JSON修复也失败，尝试将纯文本转换为JSON
            try:
                self.logger.info("尝试将纯文本响应转换为JSON格式")
                converted_json = self._convert_text_to_json(response_text, analysis_type)
                result = json.loads(converted_json)
                self.logger.info("纯文本转换为JSON成功")
                return {
                    "content": converted_json,  # 转换后的JSON文本
                    "parsed": result,           # 解析后的对象
                    "analysis_type": analysis_type,
                    "timestamp": time.time(),
                    "warning": "原始响应为纯文本格式，已自动转换为JSON"
                }
            except Exception as convert_error:
                self.logger.error(f"纯文本转换JSON也失败: {str(convert_error)}")
            
            return {
                "error": "JSON解析失败",
                "error_details": f"{str(e)} (行 {e.lineno}, 列 {e.colno})",
                "raw_response": response_text,
                "json_text_attempted": json_text if 'json_text' in locals() else None,
                "analysis_type": analysis_type,
                "suggestion": "请检查大模型返回的JSON格式是否正确。可能是JSON被截断或不完整。已尝试将纯文本转换为JSON但失败。"
            }
        except Exception as e:
            self.logger.error(f"响应处理失败: {str(e)}")
            self.logger.error(f"异常类型: {type(e).__name__}")
            import traceback
            self.logger.error(f"异常堆栈: {traceback.format_exc()}")
            return {
                "error": f"响应处理失败: {str(e)}",
                "error_type": type(e).__name__,
                "raw_response": response_text[:2000] if response_text else None,
                "analysis_type": analysis_type
            }
    
    def _clean_json_text(self, json_text: str) -> str:
        """清理JSON文本"""
        # 移除可能的BOM标记
        if json_text.startswith('\ufeff'):
            json_text = json_text[1:]
        
        # 移除多余的空白字符
        json_text = json_text.strip()
        
        # 确保以{开始，以}结束
        if not json_text.startswith('{'):
            json_text = '{' + json_text
        if not json_text.endswith('}'):
            json_text = json_text + '}'
        
        return json_text
    
    def _fix_json_errors(self, json_text: str) -> str:
        """尝试修复常见的JSON错误"""
        import re
        
        if not json_text or not json_text.strip():
            return '{}'
        
        # 移除可能的截断标记
        json_text = json_text.replace('...', '').replace('…', '')
        
        # 首先尝试修复未转义的换行符和特殊字符（在字符串值中）
        # 这是一个更复杂的问题：需要在字符串值内部转义换行符，但不能破坏JSON结构
        # 使用状态机方法：跟踪是否在字符串内部
        fixed_chars = []
        in_string = False
        escape_next = False
        i = 0
        while i < len(json_text):
            char = json_text[i]
            
            if escape_next:
                # 当前字符是转义字符后的字符，直接添加
                fixed_chars.append(char)
                escape_next = False
            elif char == '\\':
                # 转义字符
                fixed_chars.append(char)
                escape_next = True
            elif char == '"':
                # 检查是否是转义的引号
                # 计算前面连续的反斜杠数量
                backslash_count = 0
                j = i - 1
                while j >= 0 and json_text[j] == '\\':
                    backslash_count += 1
                    j -= 1
                # 如果反斜杠数量是偶数，说明这个引号没有被转义
                if backslash_count % 2 == 0:
                    # 字符串的开始或结束（未转义的引号）
                    in_string = not in_string
                fixed_chars.append(char)
            elif in_string:
                # 在字符串内部
                if char == '\n':
                    # 未转义的换行符，需要转义
                    fixed_chars.append('\\n')
                elif char == '\r':
                    # 未转义的回车符，需要转义
                    fixed_chars.append('\\r')
                elif char == '\t':
                    # 未转义的制表符，需要转义
                    fixed_chars.append('\\t')
                elif char == '\x00':
                    # 空字符，移除或转义
                    fixed_chars.append('\\u0000')
                else:
                    fixed_chars.append(char)
            else:
                # 不在字符串内部
                fixed_chars.append(char)
            
            i += 1
        
        json_text = ''.join(fixed_chars)
        
        # 如果JSON文本看起来不完整（没有以{开头），尝试找到第一个{
        # 移除开头可能的换行符和空格
        json_text = json_text.lstrip()
        if not json_text.startswith('{'):
            brace_start = json_text.find('{')
            if brace_start >= 0:
                json_text = json_text[brace_start:]
            else:
                # 如果没有找到{，可能是格式完全错误，尝试添加
                if json_text.strip():
                    json_text = '{' + json_text
        
        # 修复缺少逗号的问题
        # 在}后面跟{的情况添加逗号
        json_text = re.sub(r'}\s*{', '},{', json_text)
        
        # 修复缺少逗号的问题
        # 在"后面跟"的情况添加逗号（但排除转义的引号）
        json_text = re.sub(r'(?<!\\)"\s*"', '","', json_text)
        
        # 修复缺少逗号的问题
        # 在数字后面跟"的情况添加逗号
        json_text = re.sub(r'(\d+)\s*"', r'\1,"', json_text)
        
        # 修复缺少逗号的问题
        # 在true/false/null后面跟"的情况添加逗号
        json_text = re.sub(r'(true|false|null)\s*"', r'\1,"', json_text)
        
        # 修复截断的JSON - 如果JSON不完整，尝试补全
        if not json_text.strip().endswith('}'):
            # 计算未闭合的大括号（考虑嵌套）
            open_braces = json_text.count('{')
            close_braces = json_text.count('}')
            missing_braces = open_braces - close_braces
            
            if missing_braces > 0:
                # 检查最后一个未闭合的值，如果是字符串、数组等，先闭合它们
                # 找到最后一个未闭合的键值对
                last_colon = json_text.rfind(':')
                if last_colon > 0:
                    after_colon = json_text[last_colon+1:].strip()
                    # 如果是未闭合的字符串
                    if after_colon.startswith('"') and not after_colon.endswith('"'):
                        json_text += '"'
                    # 如果是未闭合的数组
                    elif after_colon.startswith('['):
                        open_brackets = after_colon.count('[')
                        close_brackets = after_colon.count(']')
                        if open_brackets > close_brackets:
                            json_text += ']' * (open_brackets - close_brackets)
                
                # 补全缺失的大括号
                json_text += '}' * missing_braces
        
        # 修复截断的字符串值（更安全的方式）
        # 使用状态机检查是否有未闭合的字符串
        in_string_check = False
        escape_next_check = False
        for i, char in enumerate(json_text):
            if escape_next_check:
                escape_next_check = False
                continue
            elif char == '\\':
                escape_next_check = True
            elif char == '"':
                # 检查是否是转义的引号
                backslash_count = 0
                j = i - 1
                while j >= 0 and json_text[j] == '\\':
                    backslash_count += 1
                    j -= 1
                if backslash_count % 2 == 0:
                    in_string_check = not in_string_check
        
        # 如果最后还在字符串内部，说明字符串未闭合
        if in_string_check:
            # 找到最后一个未转义的引号位置（字符串开始位置）
            last_quote_pos = -1
            for i in range(len(json_text) - 1, -1, -1):
                if json_text[i] == '"':
                    # 检查是否是转义的引号
                    backslash_count = 0
                    j = i - 1
                    while j >= 0 and json_text[j] == '\\':
                        backslash_count += 1
                        j -= 1
                    if backslash_count % 2 == 0:
                        last_quote_pos = i
                        break
            
            # 如果找到了未闭合的字符串，需要修复
            if last_quote_pos >= 0:
                # 检查字符串内容，如果包含未转义的特殊字符，先转义它们
                string_content = json_text[last_quote_pos + 1:]
                # 转义字符串中的特殊字符（如果还没有转义）
                # 但要注意不要重复转义已经转义的字符
                fixed_content = ""
                idx = 0
                while idx < len(string_content):
                    char = string_content[idx]
                    if char == '\\' and idx + 1 < len(string_content):
                        # 已经是转义字符，保留
                        fixed_content += char + string_content[idx + 1]
                        idx += 2
                    elif char in ['\n', '\r', '\t', '\x00']:
                        # 未转义的特殊字符，需要转义
                        if char == '\n':
                            fixed_content += '\\n'
                        elif char == '\r':
                            fixed_content += '\\r'
                        elif char == '\t':
                            fixed_content += '\\t'
                        elif char == '\x00':
                            fixed_content += '\\u0000'
                        idx += 1
                    else:
                        fixed_content += char
                        idx += 1
                
                # 替换字符串内容并添加结束引号
                json_text = json_text[:last_quote_pos + 1] + fixed_content + '"'
        
        # 修复缺少引号的字符串值
        # 检测 ": " 后面跟着的不是引号、数字、布尔值、null、数组或对象的情况
        # 这种情况通常出现在AI返回的JSON中，值直接是文本但没有引号
        i = 0
        result_chars = []
        while i < len(json_text):
            # 检查是否是 ": " 模式（键值分隔符）
            if i < len(json_text) - 2 and json_text[i:i+2] == '":':
                result_chars.append('":')
                i += 2
                # 跳过空白字符
                whitespace_start = i
                while i < len(json_text) and json_text[i] in [' ', '\t']:
                    result_chars.append(json_text[i])
                    i += 1
                
                if i >= len(json_text):
                    break
                
                # 检查值是否已经有引号、是数字、布尔值、null、数组或对象
                next_char = json_text[i]
                if next_char in ['"', '[', '{']:
                    # 已经有引号、数组或对象，不需要修复
                    result_chars.append(next_char)
                    i += 1
                    continue
                elif next_char.isdigit() or next_char == '-':
                    # 是数字，不需要修复
                    result_chars.append(next_char)
                    i += 1
                    continue
                elif json_text[i:i+4] == 'true' or json_text[i:i+5] == 'false' or json_text[i:i+4] == 'null':
                    # 是布尔值或null，不需要修复
                    while i < len(json_text) and json_text[i] not in [',', '}', '\n']:
                        result_chars.append(json_text[i])
                        i += 1
                    continue
                
                # 值没有引号，需要添加
                # 找到值的结束位置（下一个逗号、}，但需要处理嵌套）
                value_start = i
                value_end = i
                brace_count = 0
                bracket_count = 0
                
                while value_end < len(json_text):
                    c = json_text[value_end]
                    
                    # 不在字符串内（因为值本身没有引号）
                    if c == '{':
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count < 0:
                            # 找到了对象的结束
                            break
                    elif c == '[':
                        bracket_count += 1
                    elif c == ']':
                        bracket_count -= 1
                    elif c == ',' and brace_count == 0 and bracket_count == 0:
                        # 找到了下一个键值对的开始
                        break
                    elif c == '\n' and brace_count == 0 and bracket_count == 0:
                        # 检查下一行是否开始新的键（以"开头）
                        next_line_start = value_end + 1
                        while next_line_start < len(json_text) and json_text[next_line_start] in [' ', '\t']:
                            next_line_start += 1
                        if next_line_start < len(json_text) and json_text[next_line_start] == '"':
                            # 下一行开始新的键，当前值结束
                            break
                    
                    value_end += 1
                
                # 提取值
                value = json_text[value_start:value_end].rstrip()
                # 移除末尾可能的逗号
                trailing_comma = ''
                if value.endswith(','):
                    trailing_comma = ','
                    value = value[:-1].rstrip()
                
                # 如果值到达了文本末尾，说明JSON可能被截断了
                # 在这种情况下，我们需要确保值被正确闭合
                if value_end >= len(json_text):
                    # JSON被截断，值需要被闭合
                    # 转义值中的特殊字符
                    escaped_value = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                    
                    # 添加引号
                    result_chars.append('"')
                    result_chars.append(escaped_value)
                    result_chars.append('"')
                    # 不添加逗号，因为这是最后一个值
                    
                    # 更新i到文本末尾
                    i = len(json_text)
                else:
                    # 正常情况，值有明确的结束位置
                    # 转义值中的特殊字符
                    escaped_value = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                    
                    # 添加引号
                    result_chars.append('"')
                    result_chars.append(escaped_value)
                    result_chars.append('"')
                    result_chars.append(trailing_comma)
                    
                    i = value_end
            else:
                result_chars.append(json_text[i])
                i += 1
        
        json_text = ''.join(result_chars)
        
        # 再次检查并修复未闭合的字符串（在修复缺少引号的字符串值之后）
        # 使用状态机检查是否有未闭合的字符串
        in_string_check = False
        escape_next_check = False
        last_quote_pos = -1
        
        for idx, char in enumerate(json_text):
            if escape_next_check:
                escape_next_check = False
                continue
            elif char == '\\':
                escape_next_check = True
            elif char == '"':
                # 检查是否是转义的引号
                backslash_count = 0
                j = idx - 1
                while j >= 0 and json_text[j] == '\\':
                    backslash_count += 1
                    j -= 1
                if backslash_count % 2 == 0:
                    in_string_check = not in_string_check
                    if in_string_check:
                        # 记录字符串开始位置
                        last_quote_pos = idx
        
        # 如果最后还在字符串内部，说明字符串未闭合（JSON被截断）
        if in_string_check and last_quote_pos >= 0:
            # 找到未闭合的字符串，需要修复
            string_content = json_text[last_quote_pos + 1:]
            # 转义字符串中的特殊字符
            fixed_content = ""
            idx = 0
            while idx < len(string_content):
                char = string_content[idx]
                if char == '\\' and idx + 1 < len(string_content):
                    # 已经是转义字符，保留
                    fixed_content += char + string_content[idx + 1]
                    idx += 2
                elif char in ['\n', '\r', '\t', '\x00']:
                    # 未转义的特殊字符，需要转义
                    if char == '\n':
                        fixed_content += '\\n'
                    elif char == '\r':
                        fixed_content += '\\r'
                    elif char == '\t':
                        fixed_content += '\\t'
                    elif char == '\x00':
                        fixed_content += '\\u0000'
                    idx += 1
                else:
                    fixed_content += char
                    idx += 1
            
            # 替换字符串内容并添加结束引号
            json_text = json_text[:last_quote_pos + 1] + fixed_content + '"'
        
        # 修复截断的数组
        open_brackets = json_text.count('[')
        close_brackets = json_text.count(']')
        if open_brackets > close_brackets:
            json_text += ']' * (open_brackets - close_brackets)
        
        # 修复截断的对象
        if json_text.count('{') > json_text.count('}'):
            json_text += '}'
        
        # 修复缺少逗号的问题
        # 在null后面跟"的情况添加逗号
        json_text = re.sub(r'null\s*"', r'null,"', json_text)
        
        # 修复多余的逗号
        json_text = re.sub(r',\s*}', '}', json_text)
        json_text = re.sub(r',\s*]', ']', json_text)
        
        # 修复中文引号问题
        json_text = json_text.replace('"', '"').replace('"', '"')
        json_text = json_text.replace(''', "'").replace(''', "'")
        
        # 修复数组元素之间缺少逗号的问题
        # 在]后面跟[的情况添加逗号
        json_text = re.sub(r']\s*\[', '],[', json_text)
        
        # 修复字符串后面跟[的情况添加逗号
        json_text = re.sub(r'"\s*\[', '",[', json_text)
        
        # 修复字符串后面跟{的情况添加逗号
        json_text = re.sub(r'"\s*\{', '",{', json_text)
        
        # 修复数字后面跟[的情况添加逗号
        json_text = re.sub(r'(\d+)\s*\[', r'\1,[', json_text)
        
        # 修复数字后面跟{的情况添加逗号
        json_text = re.sub(r'(\d+)\s*\{', r'\1,{', json_text)
        
        # 检测和修复截断的JSON
        if self._is_json_truncated(json_text):
            json_text = self._fix_truncated_json(json_text)
        
        # 修复截断的JSON，尝试补全
        if json_text.count('{') > json_text.count('}'):
            json_text += '}' * (json_text.count('{') - json_text.count('}'))
        if json_text.count('[') > json_text.count(']'):
            json_text += ']' * (json_text.count('[') - json_text.count(']'))
        
        return json_text
    
    def _aggressive_fix_json(self, json_text: str) -> str:
        """
        激进修复JSON：直接截断未闭合的字符串，确保JSON可以解析
        这可能会丢失部分内容，但至少能返回部分结果
        """
        import re
        
        if not json_text or not json_text.strip():
            return '{}'
        
        # 找到第一个{的位置
        start_pos = json_text.find('{')
        if start_pos == -1:
            return '{}'
        
        json_text = json_text[start_pos:]
        
        # 策略1：尝试找到最后一个完整的键值对
        # 从后往前查找，找到最后一个完整的 "key": "value" 结构
        last_complete_key_value = -1
        in_string = False
        escape_next = False
        brace_count = 0
        last_colon_pos = -1
        last_comma_pos = -1
        
        # 从后往前扫描，找到最后一个完整的键值对
        for i in range(len(json_text) - 1, -1, -1):
            char = json_text[i]
            
            if escape_next:
                escape_next = False
                continue
            elif char == '\\':
                escape_next = True
            elif char == '"':
                # 检查是否是转义的引号
                backslash_count = 0
                j = i - 1
                while j >= 0 and json_text[j] == '\\':
                    backslash_count += 1
                    j -= 1
                if backslash_count % 2 == 0:
                    in_string = not in_string
            elif not in_string:
                if char == ':':
                    if last_colon_pos == -1:
                        last_colon_pos = i
                elif char == ',':
                    if last_comma_pos == -1 and last_colon_pos > i:
                        # 找到了一个完整的键值对（在冒号之后有逗号）
                        last_complete_key_value = i + 1
                        break
                elif char == '}':
                    brace_count += 1
                elif char == '{':
                    brace_count -= 1
                    if brace_count < 0:
                        # 找到了根对象的开始，但前面还有内容
                        break
        
        # 如果找到了最后一个完整的键值对，截断到那里
        if last_complete_key_value > 0:
            json_text = json_text[:last_complete_key_value].rstrip()
            # 移除末尾可能的逗号
            if json_text.endswith(','):
                json_text = json_text[:-1].rstrip()
            # 补全闭合括号
            open_braces = json_text.count('{')
            close_braces = json_text.count('}')
            if open_braces > close_braces:
                json_text += '}' * (open_braces - close_braces)
            return json_text
        
        # 策略2：如果策略1失败，尝试找到最后一个完整的字符串值并截断
        in_string_check = False
        escape_next_check = False
        last_quote_pos = -1
        last_colon_before_string = -1
        
        for i, char in enumerate(json_text):
            if escape_next_check:
                escape_next_check = False
                continue
            elif char == '\\':
                escape_next_check = True
            elif char == '"':
                backslash_count = 0
                j = i - 1
                while j >= 0 and json_text[j] == '\\':
                    backslash_count += 1
                    j -= 1
                if backslash_count % 2 == 0:
                    if not in_string_check:
                        # 字符串开始，检查前面是否有冒号
                        # 向前查找最近的冒号
                        for k in range(i - 1, -1, -1):
                            if json_text[k] == ':':
                                last_colon_before_string = k
                                break
                    in_string_check = not in_string_check
                    if not in_string_check:
                        last_quote_pos = i
        
        # 如果最后还在字符串内部，尝试截断
        if in_string_check:
            # 找到最后一个完整的键值对（在未闭合字符串之前）
            # 向前查找最后一个逗号或冒号
            truncate_pos = -1
            for i in range(len(json_text) - 1, last_colon_before_string, -1):
                if json_text[i] == ',':
                    truncate_pos = i
                    break
            
            if truncate_pos > 0:
                # 截断到最后一个逗号
                json_text = json_text[:truncate_pos].rstrip()
                # 补全闭合括号
                open_braces = json_text.count('{')
                close_braces = json_text.count('}')
                if open_braces > close_braces:
                    json_text += '}' * (open_braces - close_braces)
                return json_text
            else:
                # 如果找不到逗号，直接截断到冒号位置并添加空字符串
                if last_colon_before_string > 0:
                    json_text = json_text[:last_colon_before_string + 1] + ' ""'
                    # 补全闭合括号
                    open_braces = json_text.count('{')
                    close_braces = json_text.count('}')
                    if open_braces > close_braces:
                        json_text += '}' * (open_braces - close_braces)
                    return json_text
        
        # 策略3：如果都失败了，尝试最简单的修复：补全括号
        open_braces = json_text.count('{')
        close_braces = json_text.count('}')
        if open_braces > close_braces:
            # 移除末尾可能的未闭合字符串
            if json_text.rstrip().endswith('"'):
                # 已经是完整的字符串，直接补全括号
                json_text = json_text.rstrip() + '}' * (open_braces - close_braces)
            else:
                # 可能有未闭合的字符串，尝试修复
                # 找到最后一个冒号
                last_colon = json_text.rfind(':')
                if last_colon > 0:
                    after_colon = json_text[last_colon + 1:].strip()
                    if after_colon.startswith('"') and not after_colon.endswith('"'):
                        # 未闭合的字符串，添加结束引号
                        json_text = json_text.rstrip() + '"'
                json_text += '}' * (open_braces - close_braces)
        
        return json_text
    
    def _convert_text_to_json(self, text: str, analysis_type: str) -> str:
        """
        将纯文本响应转换为JSON格式
        
        Args:
            text: 纯文本响应
            analysis_type: 分析类型
            
        Returns:
            JSON格式的字符串
        """
        import re
        
        # 尝试提取结构化内容
        result_dict = {}
        
        # 特殊处理：识别结构化分析报告（如"匹配度评估"、"讨论热度评估"、"推荐建议"、"趋势洞察"等）
        if analysis_type in ["keyword_match_analysis", "keyword_recommendation"] or \
           any(keyword in text for keyword in ["匹配度评估", "讨论热度评估", "推荐建议", "趋势洞察", "热度分析", "推荐策略", "注意事项"]):
            
            # 提取结构化章节
            structured_sections = {}
            
            # 匹配带编号的章节：1. **匹配度评估**: 内容
            section_pattern1 = r'(\d+)\.\s*\*\*([^*]+?)\*\*\s*[:：]\s*(.+?)(?=\n\d+\.\s*\*\*|\n\*\*|\n\n|$)'
            matches1 = re.findall(section_pattern1, text, re.MULTILINE | re.DOTALL)
            
            # 匹配带**的章节标题：**匹配度评估** 或 **匹配度评估**:
            section_pattern2 = r'\*\*([^*]+?)\*\*\s*[:：]?\s*\n(.+?)(?=\n\*\*|\n\d+\.|\n\n|$)'
            matches2 = re.findall(section_pattern2, text, re.MULTILINE | re.DOTALL)
            
            # 匹配不带**的章节标题（如"热度分析"、"推荐策略"、"注意事项"）
            section_pattern3 = r'(热度分析|推荐策略|注意事项|匹配度评估|讨论热度评估|推荐建议|趋势洞察)[:：]?\s*\n(.+?)(?=\n(?:热度分析|推荐策略|注意事项|匹配度评估|讨论热度评估|推荐建议|趋势洞察)[:：]|\n\n|$)'
            matches3 = re.findall(section_pattern3, text, re.MULTILINE | re.DOTALL)
            
            if matches1:
                # 格式：1. **标题**: 内容
                for num, title, content in matches1:
                    cleaned_title = title.strip()
                    cleaned_content = content.strip().replace('\n\n', '\n').strip()
                    structured_sections[cleaned_title] = cleaned_content
            elif matches2:
                # 格式：**标题**: 内容
                for title, content in matches2:
                    cleaned_title = title.strip()
                    cleaned_content = content.strip().replace('\n\n', '\n').strip()
                    structured_sections[cleaned_title] = cleaned_content
            elif matches3:
                # 格式：标题: 内容
                for title, content in matches3:
                    cleaned_title = title.strip()
                    cleaned_content = content.strip().replace('\n\n', '\n').strip()
                    structured_sections[cleaned_title] = cleaned_content
            
            if structured_sections:
                # 构建结构化的JSON
                result_dict = {
                    "analysis": structured_sections,
                    "sections": list(structured_sections.keys()),
                    "total_sections": len(structured_sections),
                    "note": "从纯文本响应中提取的结构化分析内容"
                }
                # 转换为JSON字符串
                return json.dumps(result_dict, ensure_ascii=False, indent=2)
        
        # 检测是否是列表格式（如 "1. **项目** - 描述" 或 "**项目** - 描述"）
        # 提取所有列表项
        list_items = []
        
        # 匹配数字开头的列表项：1. **关键词** - 描述 或 1. **关键词** - 翻译
        # 更宽松的匹配，允许各种分隔符和换行
        # 格式：1. **Blundstone** - 布伦斯通
        pattern1 = r'(\d+)\.\s*\*\*(.+?)\*\*\s*[-–—~～]\s*(.+?)(?=\n\d+\.|\n\*\*|\n\n|$)'
        matches1 = re.findall(pattern1, text, re.MULTILINE)
        
        # 匹配**关键词** - 描述的格式（没有数字）
        pattern2 = r'\*\*(.+?)\*\*\s*[-–—]\s*(.+?)(?=\n|$)'
        matches2 = re.findall(pattern2, text, re.MULTILINE | re.DOTALL)
        
        # 匹配简单的编号列表：1. 内容
        pattern3 = r'(\d+)\.\s*(.+?)(?=\n\d+\.|\n\n|$)'
        matches3 = re.findall(pattern3, text, re.MULTILINE | re.DOTALL)
        
        if matches1:
            # 格式：1. **品牌** - 翻译
            for num, key, value in matches1:
                cleaned_key = key.strip()
                cleaned_value = value.strip().replace('\n', ' ').replace('  ', ' ')
                # 判断是品牌-翻译格式还是其他格式
                if len(cleaned_value) < 50:  # 如果是翻译，通常较短
                    list_items.append({
                        "name": cleaned_key,
                        "translation": cleaned_value
                    })
                else:
                    list_items.append({
                        "name": cleaned_key,
                        "description": cleaned_value
                    })
        elif matches2:
            # 格式：**品牌** - 翻译
            for key, value in matches2:
                cleaned_key = key.strip()
                cleaned_value = value.strip().replace('\n', ' ').replace('  ', ' ')
                list_items.append({
                    "name": cleaned_key,
                    "description": cleaned_value
                })
        elif matches3:
            # 格式：1. 内容
            for num, content in matches3:
                cleaned_content = content.strip().replace('\n', ' ').replace('  ', ' ')
                list_items.append(cleaned_content)
        
        # 如果有提取到列表项，构建JSON
        # 根据分析类型选择合适的JSON结构
        if list_items:
            if "品牌" in text or "brand" in text.lower() or "product" in text.lower():
                result_dict = {
                    "brands": list_items if isinstance(list_items[0], dict) else [{"name": item} for item in list_items],
                    "total_count": len(list_items),
                    "note": "从纯文本响应中提取的品牌信息"
                }
            elif "需求" in text or "need" in text.lower():
                result_dict = {
                    "user_needs": list_items if isinstance(list_items[0], str) else [item.get("name", item) for item in list_items],
                    "total_count": len(list_items),
                    "note": "从纯文本响应中提取的用户需求"
                }
            elif "痛点" in text or "pain" in text.lower():
                result_dict = {
                    "pain_points": list_items if isinstance(list_items[0], str) else [item.get("name", item) for item in list_items],
                    "total_count": len(list_items),
                    "note": "从纯文本响应中提取的痛点"
                }
            else:
                # 通用格式
                result_dict = {
                    "items": list_items,
                    "total_count": len(list_items),
                    "raw_content": text[:1000],  # 保留原始内容的前1000字符
                    "note": "原始响应为纯文本格式，已转换为JSON结构"
                }
        else:
            # 如果没有识别到特定格式，将整个文本作为内容
            result_dict = {
                "content": text,
                "note": "原始响应为纯文本格式，已转换为JSON结构"
            }
        
        # 转换为JSON字符串
        return json.dumps(result_dict, ensure_ascii=False, indent=2)
    
    def _is_json_truncated(self, json_text: str) -> bool:
        """检测JSON是否被截断"""
        # 检查是否以不完整的结构结尾
        json_text = json_text.strip()
        
        # 如果以不完整的字符串结尾
        if json_text.endswith('"') and json_text.count('"') % 2 == 1:
            return True
        
        # 如果以不完整的数组或对象结尾
        if json_text.endswith(('"', ',', ':', '[', '{')):
            return True
        
        # 如果以省略号结尾
        if json_text.endswith('...'):
            return True
        
        return False
    
    def _fix_truncated_json(self, json_text: str) -> str:
        """修复被截断的JSON"""
        json_text = json_text.strip()
        
        # 如果以不完整的字符串结尾，补全字符串
        if json_text.endswith('"') and json_text.count('"') % 2 == 1:
            # 找到最后一个未闭合的字符串
            last_quote = json_text.rfind('"')
            if last_quote > 0:
                # 在最后一个引号后添加内容
                json_text = json_text[:last_quote] + '"'
        
        # 如果以逗号结尾，移除逗号
        if json_text.endswith(','):
            json_text = json_text[:-1]
        
        # 如果以冒号结尾，添加null值
        if json_text.endswith(':'):
            json_text += ' null'
        
        # 如果以不完整的数组结尾
        if json_text.endswith('['):
            json_text += ']'
        
        # 如果以不完整的对象结尾
        if json_text.endswith('{'):
            json_text += '}'
        
        # 如果以省略号结尾，移除省略号并补全
        if json_text.endswith('...'):
            json_text = json_text[:-3]
            # 尝试补全最后一个不完整的结构
            if json_text.endswith('"'):
                json_text += '"'
            elif json_text.endswith(','):
                json_text = json_text[:-1]
        
        return json_text
    
    def _call_deepseek(self, prompt: str, analysis_type: str) -> Dict[str, Any]:
        """调用DeepSeek API，带重试机制和指数退避"""
        max_retries = 3  # 减少重试次数，避免过度调用
        base_delay = 5   # 增加基础延迟
        max_delay = 30   # 最大延迟30秒
        
        for attempt in range(max_retries):
            try:
                # 添加API调用间隔，避免频率过高
                if attempt > 0:
                    time.sleep(2)
                headers = {
                    "Authorization": f"Bearer {self.deepseek_api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "RedInsight/1.0"
                }
                
                data = {
                    "model": "deepseek-chat",  # 尝试使用正确的模型名称
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个专业的数据分析师，擅长分析社交媒体内容。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4000,
                    "stream": False
                }
                
                # 使用更长的超时时间，并添加连接超时
                # DeepSeek API端点：https://api.deepseek.com/v1/chat/completions
                # 确保URL格式正确
                if not self.deepseek_base_url.endswith('/'):
                    api_url = f"{self.deepseek_base_url}/v1/chat/completions"
                else:
                    api_url = f"{self.deepseek_base_url}v1/chat/completions"
                self.logger.debug(f"DeepSeek API请求: URL={api_url}, Model={data['model']}")
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=data,
                    timeout=(60, 300),  # (连接超时, 读取超时) - 增加到5分钟
                    verify=True
                )
                
                self.logger.debug(f"DeepSeek API响应: Status={response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    result_text = result['choices'][0]['message']['content']
                    self.logger.info(f"DeepSeek API调用成功 (尝试 {attempt + 1})")
                    return self._parse_json_response(result_text, analysis_type)
                else:
                    error_text = response.text[:500] if response.text else "无响应内容"
                    self.logger.error(f"DeepSeek API调用失败: {response.status_code} - {error_text}")
                    if response.status_code == 404:
                        self.logger.error(f"API端点不存在 (404): URL={api_url}, Model={data['model']}")
                        self.logger.error("请检查：1) API URL是否正确 2) 模型名称是否正确 3) API密钥是否有效")
                    elif response.status_code == 401:
                        self.logger.error("API密钥无效 (401)，请检查api_keys.json中的deepseek_api_key配置")
                    elif response.status_code == 400:
                        self.logger.error(f"请求参数错误 (400): {error_text}")
                    if attempt < max_retries - 1:
                        # 指数退避策略
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        self.logger.info(f"第{attempt + 1}次尝试失败，{delay}秒后重试...")
                        time.sleep(delay)
                        continue
                    return {"error": f"API调用失败: {response.status_code} - {response.text}"}
                
            except requests.exceptions.Timeout as e:
                self.logger.error(f"DeepSeek API超时 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    # 指数退避策略
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    self.logger.info(f"超时，{delay}秒后重试...")
                    time.sleep(delay)
                    continue
                return {"error": f"请求超时: {str(e)}"}
            except requests.exceptions.ConnectionError as e:
                self.logger.error(f"DeepSeek API连接错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    self.logger.info(f"连接错误，{delay}秒后重试...")
                    time.sleep(delay)
                    continue
                return {"error": f"连接错误: {str(e)}"}
            except Exception as e:
                self.logger.error(f"DeepSeek API调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    self.logger.info(f"错误，{delay}秒后重试...")
                    time.sleep(delay)
                    continue
                return {"error": str(e)}
        
        return {"error": "所有重试尝试都失败了"}
    
    # ==================== 语言检测和翻译功能 ====================
    
    def detect_language(self, text: str, provider: str = "deepseek") -> Dict[str, Any]:
        """
        检测文本语言
        
        Args:
            text: 要检测的文本
            provider: 使用的LLM提供商
            
        Returns:
            语言检测结果
        """
        try:
            prompt = f"""
请检测以下文本的语言：

文本：{text}

请以JSON格式返回结果：
{{
    "language": "检测到的语言名称（如：中文、英文、日文等）",
    "language_code": "语言代码（如：zh、en、ja等）",
    "confidence": "置信度（0-1之间的数字）",
    "is_chinese": true/false,
    "is_english": true/false
}}

要求：
1. 准确识别文本的主要语言
2. 提供标准化的语言代码
3. 给出合理的置信度评估
4. 明确标识是否为中文或英文
"""
            
            response = self._call_llm(prompt, provider, "language_detection")
            
            if isinstance(response, dict) and 'content' in response:
                result = self._parse_json_response(response['content'], "language_detection")
                if result and 'language' in result:
                    return {
                        'success': True,
                        'language': result.get('language', '未知'),
                        'language_code': result.get('language_code', 'unknown'),
                        'confidence': result.get('confidence', 0.0),
                        'is_chinese': result.get('is_chinese', False),
                        'is_english': result.get('is_english', False)
                    }
            
            # 如果解析失败，使用简单的规则检测
            return self._simple_language_detection(text)
            
        except Exception as e:
            self.logger.error(f"语言检测失败: {str(e)}")
            return self._simple_language_detection(text)
    
    def translate_text(self, text: str, target_language: str = "英文", 
                      provider: str = "deepseek", context: str = None) -> Dict[str, Any]:
        """
        翻译文本
        
        Args:
            text: 要翻译的文本
            target_language: 目标语言
            provider: 使用的LLM提供商
            context: 上下文信息（可选）
            
        Returns:
            翻译结果
        """
        try:
            # 检查内容长度（估算token数，1个中文字符约等于1-2个token，1个英文单词约等于1.3个token）
            # 保守估计：8000字符约等于10000-12000 tokens
            # 考虑到prompt本身会占用一些token，以及需要返回的JSON，限制原文长度为6000字符
            MAX_TEXT_LENGTH = 6000
            original_length = len(text)
            truncated = False
            truncation_note = ""
            
            if original_length > MAX_TEXT_LENGTH:
                # 截断文本
                text = text[:MAX_TEXT_LENGTH]
                truncated = True
                truncation_note = f"注意：原文长度({original_length}字符)超过最大输入限制({MAX_TEXT_LENGTH}字符)，已截断至前{MAX_TEXT_LENGTH}字符进行翻译。"
                self.logger.warning(f"翻译内容过长({original_length}字符)，已截断至{MAX_TEXT_LENGTH}字符")
            
            # 构建翻译提示
            context_info = ""
            if context:
                context_info = f"\n上下文信息：{context}"
            
            if truncated:
                context_info += f"\n\n{truncation_note}"
            
            prompt = f"""
请将以下文本翻译为{target_language}：

原文：{text}{context_info}

请以JSON格式返回结果：
{{
    "translated_text": "翻译后的文本",
    "original_text": "原始文本",
    "source_language": "源语言",
    "target_language": "目标语言",
    "translation_quality": "翻译质量评估（优秀/良好/一般）",
    "notes": "翻译说明或注意事项（如果有）"
}}

要求：
1. 保持原文的语调和风格
2. 确保翻译准确、自然
3. 如果是Reddit帖子，要符合Reddit社区的用语习惯
4. 保持专业术语的准确性
5. 如果涉及技术内容，保持技术准确性
"""
            
            response = self._call_llm(prompt, provider, "translation")
            
            # 首先处理包含已解析内容的情况
            if isinstance(response, dict) and 'parsed' in response:
                parsed = response['parsed']
                notes = parsed.get('notes', '')
                if truncated:
                    notes = f"{truncation_note}\n{notes}" if notes else truncation_note
                return {
                    'success': True,
                    'translated_text': parsed.get('translated_text', parsed if isinstance(parsed, str) else ''),
                    'original_text': parsed.get('original_text', text[:MAX_TEXT_LENGTH] if truncated else text),
                    'source_language': parsed.get('source_language', '未知'),
                    'target_language': parsed.get('target_language', target_language),
                    'translation_quality': parsed.get('translation_quality', '良好'),
                    'notes': notes,
                    'truncated': truncated,
                    'original_length': original_length if truncated else None
                }
            
            # 其次尝试解析content中的JSON
            if isinstance(response, dict) and 'content' in response:
                result = self._parse_json_response(response['content'], "translation")
                if isinstance(result, dict) and 'parsed' in result:
                    parsed = result['parsed']
                    if isinstance(parsed, dict) and 'translated_text' in parsed:
                        notes = parsed.get('notes', '')
                        if truncated:
                            notes = f"{truncation_note}\n{notes}" if notes else truncation_note
                    return {
                        'success': True,
                            'translated_text': parsed.get('translated_text', ''),
                            'original_text': parsed.get('original_text', text[:MAX_TEXT_LENGTH] if truncated else text),
                            'source_language': parsed.get('source_language', '未知'),
                            'target_language': parsed.get('target_language', target_language),
                            'translation_quality': parsed.get('translation_quality', '良好'),
                            'notes': notes,
                            'truncated': truncated,
                            'original_length': original_length if truncated else None
                    }
                
                # 解析失败则降级为将纯文本作为译文返回
                raw = response.get('content') or ''
                cleaned = raw.replace('```json', '').replace('```', '').strip()
                notes = '已使用纯文本降级解析'
                if truncated:
                    notes = f"{truncation_note}\n{notes}"
                return {
                    'success': True,
                    'translated_text': cleaned if cleaned else (text[:MAX_TEXT_LENGTH] if truncated else text),
                    'original_text': text[:MAX_TEXT_LENGTH] if truncated else text,
                    'source_language': '未知',
                    'target_language': target_language,
                    'translation_quality': '一般',
                    'notes': notes,
                    'truncated': truncated,
                    'original_length': original_length if truncated else None
                }
            
            # 无法识别响应结构，直接返回原文作为译文
            notes = '无法解析模型响应，已使用原文'
            if truncated:
                notes = f"{truncation_note}\n{notes}"
            return {
                'success': True,
                'translated_text': text[:MAX_TEXT_LENGTH] if truncated else text,
                'original_text': text[:MAX_TEXT_LENGTH] if truncated else text,
                'source_language': '未知',
                'target_language': target_language,
                'translation_quality': '一般',
                'notes': notes,
                'truncated': truncated,
                'original_length': original_length if truncated else None
            }
            
        except Exception as e:
            self.logger.error(f"翻译失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'original_text': text
            }
    
    def translate_for_reddit(self, text: str, subreddit_name: str = None, 
                           post_type: str = "讨论", provider: str = "deepseek") -> Dict[str, Any]:
        """
        专门为Reddit翻译文本
        
        Args:
            text: 要翻译的文本
            subreddit_name: 目标子版块名称
            post_type: 帖子类型
            provider: 使用的LLM提供商
            
        Returns:
            Reddit专用翻译结果
        """
        try:
            # 构建Reddit专用翻译提示
            subreddit_info = f"目标子版块：r/{subreddit_name}" if subreddit_name else ""
            
            prompt = f"""
请将以下文本翻译为英文，用于Reddit社区发帖：

原文：{text}

{subreddit_info}
帖子类型：{post_type}

请以JSON格式返回结果：
{{
    "translated_text": "翻译后的英文文本",
    "original_text": "原始文本",
    "reddit_style": "Reddit风格调整说明",
    "community_fit": "社区适配说明",
    "suggestions": "发帖建议",
    "hashtags": "建议的标签（如果有）"
}}

要求：
1. 使用自然、地道的英文
2. 符合Reddit社区的用语习惯
3. 保持原文的核心信息和情感
4. 使用适当的Reddit术语和表达方式
5. 如果是技术内容，使用标准的技术英语
6. 保持帖子的吸引力和可读性
7. 考虑目标子版块的特点和规则
"""
            
            response = self._call_llm(prompt, provider, "reddit_translation")
            
            # 优先使用已解析内容
            if isinstance(response, dict) and 'parsed' in response:
                parsed = response['parsed']
                return {
                    'success': True,
                    'translated_text': parsed.get('translated_text', parsed if isinstance(parsed, str) else ''),
                    'original_text': parsed.get('original_text', text),
                    'reddit_style': parsed.get('reddit_style', ''),
                    'community_fit': parsed.get('community_fit', ''),
                    'suggestions': parsed.get('suggestions', ''),
                    'hashtags': parsed.get('hashtags', '')
                }
            
            # 其次尝试解析content中的JSON
            if isinstance(response, dict) and 'content' in response:
                result = self._parse_json_response(response['content'], "reddit_translation")
                if isinstance(result, dict) and 'error' not in result and 'translated_text' in result:
                    return {
                        'success': True,
                        'translated_text': result.get('translated_text', ''),
                        'original_text': result.get('original_text', text),
                        'reddit_style': result.get('reddit_style', ''),
                        'community_fit': result.get('community_fit', ''),
                        'suggestions': result.get('suggestions', ''),
                        'hashtags': result.get('hashtags', '')
                    }
                
                # 解析失败则降级为将纯文本作为译文返回
                raw = response.get('content') or ''
                cleaned = raw.replace('```json', '').replace('```', '').strip()
                return {
                    'success': True,
                    'translated_text': cleaned if cleaned else text,
                    'original_text': text,
                    'reddit_style': '',
                    'community_fit': '',
                    'suggestions': '',
                    'hashtags': ''
                }
            
            # 最后降级到通用翻译
            return self.translate_text(text, "英文", provider, f"Reddit {post_type} 帖子")
            
        except Exception as e:
            self.logger.error(f"Reddit翻译失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'original_text': text
            }
    
    def _simple_language_detection(self, text: str) -> Dict[str, Any]:
        """
        简单的语言检测（备用方法）
        
        Args:
            text: 要检测的文本
            
        Returns:
            语言检测结果
        """
        try:
            # 统计中文字符
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
            # 统计英文字符
            english_chars = len([c for c in text if c.isalpha() and ord(c) < 128])
            # 总字符数
            total_chars = len([c for c in text if c.isalpha()])
            
            if total_chars == 0:
                return {
                    'success': True,
                    'language': '未知',
                    'language_code': 'unknown',
                    'confidence': 0.0,
                    'is_chinese': False,
                    'is_english': False
                }
            
            chinese_ratio = chinese_chars / total_chars
            english_ratio = english_chars / total_chars
            
            if chinese_ratio > 0.3:
                return {
                    'success': True,
                    'language': '中文',
                    'language_code': 'zh',
                    'confidence': min(chinese_ratio, 1.0),
                    'is_chinese': True,
                    'is_english': False
                }
            elif english_ratio > 0.5:
                return {
                    'success': True,
                    'language': '英文',
                    'language_code': 'en',
                    'confidence': min(english_ratio, 1.0),
                    'is_chinese': False,
                    'is_english': True
                }
            else:
                return {
                    'success': True,
                    'language': '混合语言',
                    'language_code': 'mixed',
                    'confidence': 0.5,
                    'is_chinese': chinese_ratio > 0.1,
                    'is_english': english_ratio > 0.1
                }
                
        except Exception as e:
            self.logger.error(f"简单语言检测失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'language': '未知',
                'language_code': 'unknown',
                'confidence': 0.0,
                'is_chinese': False,
                'is_english': False
            }