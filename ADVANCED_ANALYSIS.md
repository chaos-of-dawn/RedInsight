# RedInsight 深度分析功能

## 概述

RedInsight 现在支持深度数据分析功能，包括结构化抽取、向量化、聚类和业务洞察生成。这些功能可以帮助您从Reddit数据中挖掘更深层的价值。

## 功能特性

### 1. 结构化抽取 (Structured Extraction)
- 使用LLM从Reddit帖子中提取结构化信息
- 提取字段：主题、痛点、需求、情感、关键词、工具提及等
- 支持批量处理和JSON Schema验证

### 2. 向量化 (Vectorization)
- 使用sentence-transformers将文本转换为向量表示
- 支持本地模型（all-MiniLM-L6-v2）
- 自动缓存机制，避免重复计算

### 3. 聚类分析 (Clustering)
- 使用KMeans算法对向量进行聚类
- 自动确定最优聚类数量
- 分析每个簇的特征和代表样本

### 4. 洞察生成 (Insights Generation)
- 基于聚类结果生成业务洞察
- 识别主导主题、痛点和机会
- 提供战略建议和行动优先级矩阵

## 使用方法

### 命令行使用

```bash
# 快速分析（50个帖子）
python main.py --action advanced --analysis-type quick --subreddits MachineLearning programming

# 全面分析（500个帖子）
python main.py --action advanced --analysis-type comprehensive --subreddits MachineLearning programming --limit 500

# 自定义分析
python main.py --action advanced --subreddits MachineLearning --limit 200
```

### 编程使用

```python
from database import DatabaseManager
from llm_analyzer import LLMAnalyzer
from advanced_analyzer import AdvancedAnalyzer

# 初始化
db_manager = DatabaseManager()
llm_analyzer = LLMAnalyzer()
analyzer = AdvancedAnalyzer(db_manager, llm_analyzer)

# 运行分析
result = analyzer.run_quick_analysis(
    subreddits=['MachineLearning', 'programming'], 
    limit=50
)

# 获取摘要
summary = analyzer.get_analysis_summary()
```

## 输出结果

### 1. 数据库存储
- `structured_extractions`: 结构化抽取结果
- `vectorized_texts`: 向量化文本
- `clustering_results`: 聚类结果
- `business_insights`: 业务洞察

### 2. JSON报告
分析完成后会生成JSON格式的洞察报告，包含：
- 整体情感分析
- 主导主题识别
- 主要痛点总结
- 关键机会发现
- 战略建议
- 行动优先级矩阵

## 数据要求

### 最小数据量
- **基础可用**: ≥100-150条有效帖子
- **稳定可靠**: ≥300-500条帖子
- **精细分析**: ≥800-1500条帖子

### 数据质量
- 多样性：覆盖多个时间段和主题
- 去重：避免重复内容
- 筛选：保留高质量、有信息量的帖子

## 依赖安装

```bash
pip install sentence-transformers==2.2.2
pip install scikit-learn==1.3.2
```

## 配置要求

确保在`.env`文件中配置了LLM API密钥：

```env
OPENAI_API_KEY=your_openai_api_key
# 或
ANTHROPIC_API_KEY=your_anthropic_api_key
```

## 示例输出

```json
{
  "analysis_timestamp": "2024-01-15T10:30:00",
  "total_clusters": 5,
  "total_samples": 150,
  "overall_sentiment": "positive",
  "dominant_themes": ["机器学习", "编程技巧", "工具推荐"],
  "top_pain_points": ["调试困难", "性能优化", "文档不足"],
  "key_opportunities": ["自动化工具", "学习资源", "社区建设"],
  "strategic_recommendations": [
    "开发调试工具",
    "创建学习指南",
    "建立开发者社区"
  ]
}
```

## 注意事项

1. **首次运行**：需要下载sentence-transformers模型，可能需要几分钟
2. **内存使用**：向量化过程会占用一定内存，建议至少4GB可用内存
3. **API限制**：LLM调用有频率限制，大量数据可能需要较长时间
4. **数据隐私**：确保遵守Reddit API使用条款和数据隐私规定

## 故障排除

### 常见问题

1. **模型下载失败**
   - 检查网络连接
   - 尝试手动下载模型

2. **内存不足**
   - 减少分析的数据量
   - 增加系统内存

3. **LLM API错误**
   - 检查API密钥配置
   - 确认API配额和限制

4. **聚类结果不理想**
   - 增加数据量
   - 检查数据质量
   - 调整聚类参数

## 扩展功能

未来版本将支持：
- 更多聚类算法（UMAP + HDBSCAN）
- 实时分析更新
- 可视化图表
- 自定义分析模板
- 多语言支持
