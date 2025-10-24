# RedInsight 高级分析功能使用指南

## 概述

RedInsight 的高级分析功能集成了AI技术，能够从Reddit数据中挖掘深层的业务价值。该功能包括结构化抽取、智能聚类和业务洞察生成。

## 大模型API使用说明

### 必需的API配置

高级分析功能**确实需要使用大模型API**，主要在以下两个阶段：

1. **结构化抽取阶段**：使用LLM从原始文本中提取结构化信息
2. **洞察生成阶段**：使用LLM基于聚类结果生成业务洞察

### 支持的API提供商

- **OpenAI** (推荐)
- **Anthropic** 
- **DeepSeek**

### API配置方法

#### 方法1：通过Web界面配置
1. 启动Streamlit应用：`streamlit run streamlit_app.py`
2. 在侧边栏配置大模型API密钥
3. 完成认证后即可使用高级分析功能

#### 方法2：通过环境变量配置
```bash
# OpenAI
export OPENAI_API_KEY="your_openai_api_key"

# Anthropic
export ANTHROPIC_API_KEY="your_anthropic_api_key"

# DeepSeek
export DEEPSEEK_API_KEY="your_deepseek_api_key"
```

## 使用方法

### 1. Web界面使用（推荐）

```bash
# 启动Web界面
streamlit run streamlit_app.py
```

然后在浏览器中：
1. 配置Reddit API密钥
2. 完成Reddit认证
3. 配置大模型API密钥
4. 进入"🚀 高级分析"标签页
5. 配置分析参数
6. 点击"开始高级分析"

### 2. 命令行使用

```bash
# 快速分析（50个帖子）
python main.py --action advanced --analysis-type quick --subreddits MachineLearning programming

# 全面分析（500个帖子）
python main.py --action advanced --analysis-type comprehensive --subreddits MachineLearning programming --limit 500

# 自定义分析
python main.py --action advanced --subreddits MachineLearning --limit 200
```

### 3. 编程使用

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

## 分析流程

### 1. 结构化抽取
- 使用LLM从Reddit帖子中提取结构化信息
- 提取字段：主题、痛点、需求、情感、关键词、工具提及等
- 支持批量处理和JSON Schema验证

### 2. 向量化
- 使用sentence-transformers将文本转换为向量表示
- 支持本地模型（all-MiniLM-L6-v2）
- 自动缓存机制，避免重复计算

### 3. 聚类分析
- 使用KMeans算法对向量进行聚类
- 自动确定最优聚类数量
- 分析每个簇的特征和代表样本

### 4. 洞察生成
- 基于聚类结果生成业务洞察
- 识别主导主题、痛点和机会
- 提供战略建议和行动优先级矩阵

## 数据要求

### 最小数据量
- **快速分析**: ≥50条有效帖子
- **全面分析**: ≥300条帖子
- **精细分析**: ≥800条帖子

### 数据质量要求
- 多样性：覆盖多个时间段和主题
- 去重：避免重复内容
- 筛选：保留高质量、有信息量的帖子

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

## 成本估算

### API调用成本
- **结构化抽取**: 每条帖子约1-2次API调用
- **洞察生成**: 每个分析批次约5-10次API调用

### 示例成本（OpenAI GPT-4）
- 50条帖子快速分析：约$2-5
- 500条帖子全面分析：约$20-50

### 优化建议
1. 使用GPT-3.5-turbo降低成本
2. 合理设置数据限制
3. 利用缓存机制避免重复计算

## 故障排除

### 常见问题

1. **API密钥错误**
   - 检查API密钥是否正确配置
   - 确认API配额是否充足

2. **数据量不足**
   - 确保有足够的数据进行分析
   - 建议至少50条帖子

3. **内存不足**
   - 减少分析的数据量
   - 增加系统内存

4. **网络问题**
   - 检查网络连接
   - 确认API服务可用性

### 调试方法

1. **查看日志**
   ```bash
   # 启用详细日志
   export LOG_LEVEL=DEBUG
   python main.py --action advanced
   ```

2. **检查数据**
   ```python
   from database import DatabaseManager
   db = DatabaseManager()
   posts = db.get_posts(limit=10)
   print(f"可用帖子数: {len(posts)}")
   ```

3. **测试API连接**
   ```python
   from llm_analyzer import LLMAnalyzer
   analyzer = LLMAnalyzer()
   result = analyzer.analyze_sentiment("测试文本", "openai")
   print(result)
   ```

## 最佳实践

### 1. 数据准备
- 确保数据质量和多样性
- 定期更新数据
- 避免重复分析相同数据

### 2. 参数调优
- 根据数据量选择合适的分析类型
- 调整聚类参数以获得更好的结果
- 监控API使用量和成本

### 3. 结果解读
- 结合业务背景理解洞察结果
- 关注高优先级的行动建议
- 定期回顾和更新分析结果

## 扩展功能

未来版本将支持：
- 更多聚类算法（UMAP + HDBSCAN）
- 实时分析更新
- 可视化图表
- 自定义分析模板
- 多语言支持
- 成本优化功能
