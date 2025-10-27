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
import requests
from config import Config

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
        self.deepseek_base_url = "https://api.deepseek.com/v1"
        
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
            custom_prompt: 自定义综合提示词模板
            
        Returns:
            综合分析结果
        """
        if custom_prompt:
            prompt = custom_prompt.format(text=text)
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
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end]
            else:
                json_text = response_text
            
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
            self.logger.error(f"原始响应: {response_text[:500]}...")
            
            # 尝试修复常见的JSON错误
            try:
                fixed_json = self._fix_json_errors(json_text)
                result = json.loads(fixed_json)
                return {
                    "content": fixed_json,  # 修复后的JSON文本
                    "parsed": result,       # 解析后的对象
                    "analysis_type": analysis_type,
                    "timestamp": time.time(),
                    "warning": "JSON已自动修复"
                }
            except:
                pass
            
            return {
                "error": "JSON解析失败",
                "error_details": str(e),
                "raw_response": response_text,
                "analysis_type": analysis_type,
                "suggestion": "请检查大模型返回的JSON格式是否正确"
            }
        except Exception as e:
            self.logger.error(f"响应处理失败: {str(e)}")
            return {
                "error": str(e),
                "raw_response": response_text,
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
        
        # 移除可能的截断标记
        json_text = json_text.replace('...', '')
        
        # 修复缺少逗号的问题
        # 在}后面跟{的情况添加逗号
        json_text = re.sub(r'}\s*{', '},{', json_text)
        
        # 修复缺少逗号的问题
        # 在"后面跟"的情况添加逗号
        json_text = re.sub(r'"\s*"', '","', json_text)
        
        # 修复缺少逗号的问题
        # 在数字后面跟"的情况添加逗号
        json_text = re.sub(r'(\d+)\s*"', r'\1,"', json_text)
        
        # 修复缺少逗号的问题
        # 在true/false后面跟"的情况添加逗号
        json_text = re.sub(r'(true|false)\s*"', r'\1,"', json_text)
        
        # 修复截断的JSON - 如果JSON不完整，尝试补全
        if not json_text.strip().endswith('}'):
            # 计算未闭合的大括号
            open_braces = json_text.count('{')
            close_braces = json_text.count('}')
            missing_braces = open_braces - close_braces
            
            # 补全缺失的大括号
            json_text += '}' * missing_braces
        
        # 修复截断的字符串值
        json_text = re.sub(r'"([^"]*)$', r'"\1"', json_text)
        
        # 修复截断的数组
        if json_text.count('[') > json_text.count(']'):
            json_text += ']'
        
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
                    "model": "deepseek-chat",
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
                response = requests.post(
                    f"{self.deepseek_base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=(60, 300),  # (连接超时, 读取超时) - 增加到5分钟
                    verify=True
                )
                
                if response.status_code == 200:
                    result = response.json()
                    result_text = result['choices'][0]['message']['content']
                    self.logger.info(f"DeepSeek API调用成功 (尝试 {attempt + 1})")
                    return self._parse_json_response(result_text, analysis_type)
                else:
                    self.logger.error(f"DeepSeek API调用失败: {response.status_code} - {response.text}")
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
