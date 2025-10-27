"""
向量化模块
使用sentence-transformers将文本转换为向量表示
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import pickle
import os

logger = logging.getLogger(__name__)

@dataclass
class VectorizedText:
    """向量化文本结果"""
    text_id: str
    text: str
    vector: np.ndarray
    model_name: str
    vectorization_timestamp: Any

class TextVectorizer:
    """文本向量化器"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_dir: str = "./vector_cache"):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.model = None
        self.vector_cache = {}
        
        # 设置Hugging Face镜像源（解决网络连接问题）
        import os
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
        # 加载缓存
        self._load_cache()
    
    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                import time
                
                # 添加重试机制
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        logger.info(f"加载向量化模型: {self.model_name} (尝试 {attempt + 1}/{max_retries})")
                        self.model = SentenceTransformer(self.model_name)
                        logger.info("模型加载完成")
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"模型加载失败，重试 {attempt + 1}/{max_retries}: {str(e)}")
                            time.sleep(2)  # 等待2秒后重试
                        else:
                            logger.error(f"模型加载失败: {str(e)}")
                            raise
            except ImportError:
                logger.error("sentence-transformers未安装，请运行: pip install sentence-transformers")
                raise
            except Exception as e:
                logger.error(f"模型加载失败: {str(e)}")
                raise
    
    def _load_cache(self):
        """加载向量缓存"""
        try:
            # 确保缓存目录存在
            os.makedirs(self.cache_dir, exist_ok=True)
            
            cache_file = os.path.join(self.cache_dir, f"{self.model_name}_cache.pkl")
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    self.vector_cache = pickle.load(f)
                logger.info(f"加载向量缓存: {len(self.vector_cache)} 条记录")
            else:
                self.vector_cache = {}
        except Exception as e:
            logger.warning(f"缓存加载失败: {str(e)}")
            self.vector_cache = {}
    
    def _save_cache(self):
        """保存向量缓存"""
        try:
            # 确保缓存目录存在
            os.makedirs(self.cache_dir, exist_ok=True)
            
            cache_file = os.path.join(self.cache_dir, f"{self.model_name}_cache.pkl")
            with open(cache_file, 'wb') as f:
                pickle.dump(self.vector_cache, f)
            logger.info(f"保存向量缓存: {len(self.vector_cache)} 条记录")
        except Exception as e:
            logger.warning(f"缓存保存失败: {str(e)}")
    
    def vectorize_text(self, text: str, text_id: str = None) -> Optional[VectorizedText]:
        """向量化单个文本"""
        try:
            # 检查缓存
            if text_id and text_id in self.vector_cache:
                cached_data = self.vector_cache[text_id]
                # 确保缓存中的时间戳是 datetime 对象
                timestamp = cached_data['timestamp']
                if isinstance(timestamp, str):
                    from datetime import datetime
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        timestamp = datetime.utcnow()
                
                return VectorizedText(
                    text_id=text_id,
                    text=text,
                    vector=cached_data['vector'],
                    model_name=self.model_name,
                    vectorization_timestamp=timestamp
                )
            
            # 加载模型
            self._load_model()
            
            # 向量化
            vector = self.model.encode(text, convert_to_numpy=True)
            
            # 创建结果
            from datetime import datetime
            result = VectorizedText(
                text_id=text_id or str(hash(text)),
                text=text,
                vector=vector,
                model_name=self.model_name,
                vectorization_timestamp=datetime.utcnow()
            )
            
            # 更新缓存
            if text_id:
                self.vector_cache[text_id] = {
                    'vector': vector,
                    'timestamp': result.vectorization_timestamp
                }
                self._save_cache()
            
            return result
            
        except Exception as e:
            logger.error(f"文本向量化失败: {str(e)}")
            return None
    
    def vectorize_batch(self, texts: List[str], text_ids: List[str] = None) -> List[VectorizedText]:
        """批量向量化文本"""
        try:
            # 加载模型
            self._load_model()
            
            # 检查哪些需要重新计算
            texts_to_process = []
            text_ids_to_process = []
            results = []
            
            for i, text in enumerate(texts):
                text_id = text_ids[i] if text_ids and i < len(text_ids) else str(hash(text))
                
                # 检查缓存
                if text_id in self.vector_cache:
                    cached_data = self.vector_cache[text_id]
                    results.append(VectorizedText(
                        text_id=text_id,
                        text=text,
                        vector=cached_data['vector'],
                        model_name=self.model_name,
                        vectorization_timestamp=cached_data['timestamp']
                    ))
                else:
                    texts_to_process.append(text)
                    text_ids_to_process.append(text_id)
            
            # 批量处理未缓存的文本
            if texts_to_process:
                logger.info(f"批量向量化 {len(texts_to_process)} 条文本")
                vectors = self.model.encode(texts_to_process, convert_to_numpy=True)
                
                for i, (text, text_id, vector) in enumerate(zip(texts_to_process, text_ids_to_process, vectors)):
                    result = VectorizedText(
                        text_id=text_id,
                        text=text,
                        vector=vector,
                        model_name=self.model_name,
                        vectorization_timestamp=str(np.datetime64('now'))
                    )
                    results.append(result)
                    
                    # 更新缓存
                    self.vector_cache[text_id] = {
                        'vector': vector,
                        'timestamp': result.vectorization_timestamp
                    }
                
                # 保存缓存
                self._save_cache()
            
            logger.info(f"批量向量化完成: {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"批量向量化失败: {str(e)}")
            return []
    
    def vectorize_extractions(self, extractions: List[Any]) -> List[VectorizedText]:
        """向量化结构化抽取结果"""
        try:
            texts = []
            text_ids = []
            
            for extraction in extractions:
                # 组合多个字段作为向量化文本
                combined_text = self._combine_extraction_fields(extraction)
                texts.append(combined_text)
                text_ids.append(extraction.post_id)
            
            return self.vectorize_batch(texts, text_ids)
            
        except Exception as e:
            logger.error(f"抽取结果向量化失败: {str(e)}")
            return []
    
    def _combine_extraction_fields(self, extraction: Any) -> str:
        """组合抽取字段为向量化文本"""
        parts = []
        
        # 主要信息
        if hasattr(extraction, 'main_topic') and extraction.main_topic:
            parts.append(f"主题: {extraction.main_topic}")
        
        if hasattr(extraction, 'title') and extraction.title:
            parts.append(f"标题: {extraction.title}")
        
        if hasattr(extraction, 'content') and extraction.content:
            parts.append(f"内容: {extraction.content}")
        
        # 痛点和需求
        if hasattr(extraction, 'pain_points') and extraction.pain_points:
            parts.append(f"痛点: {' '.join(extraction.pain_points)}")
        
        if hasattr(extraction, 'user_needs') and extraction.user_needs:
            parts.append(f"需求: {' '.join(extraction.user_needs)}")
        
        # 关键短语
        if hasattr(extraction, 'key_phrases') and extraction.key_phrases:
            parts.append(f"关键词: {' '.join(extraction.key_phrases)}")
        
        # 工具提及
        if hasattr(extraction, 'mentioned_tools') and extraction.mentioned_tools:
            parts.append(f"工具: {' '.join(extraction.mentioned_tools)}")
        
        return " | ".join(parts)
    
    def get_similarity(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """计算两个向量的余弦相似度"""
        try:
            # 计算余弦相似度
            dot_product = np.dot(vector1, vector2)
            norm1 = np.linalg.norm(vector1)
            norm2 = np.linalg.norm(vector2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"相似度计算失败: {str(e)}")
            return 0.0
    
    def find_similar_texts(self, query_vector: np.ndarray, candidate_vectors: List[VectorizedText], 
                          top_k: int = 5) -> List[tuple]:
        """查找最相似的文本"""
        similarities = []
        
        for candidate in candidate_vectors:
            similarity = self.get_similarity(query_vector, candidate.vector)
            similarities.append((candidate, similarity))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
