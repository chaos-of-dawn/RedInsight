# RedInsight - Reddit数据分析工具

RedInsight是一个用于抓取Reddit数据、存储到本地数据库，并使用大模型API进行数据分析的Python工具。

## 功能特性

- 🔍 **Reddit数据抓取**: 使用PRAW抓取帖子、评论和子版块信息
- 💾 **本地数据存储**: 使用SQLAlchemy和SQLite存储结构化数据
- 🤖 **大模型分析**: 集成OpenAI、Anthropic和DeepSeek API进行内容分析
- 📊 **多维度分析**: 支持情感分析、主题分析、质量评估等
- 📈 **社区报告**: 生成社区参与度和趋势分析报告
- ⚙️ **灵活配置**: 支持多种配置选项和自定义参数

## 安装说明

### 1. 克隆项目
```bash
git clone https://github.com/chaos-of-dawn/RedInsight.git
cd RedInsight
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
复制 `env_example.txt` 为 `.env` 并填写您的API密钥：

```bash
cp env_example.txt .env
```

编辑 `.env` 文件，填入以下信息：
- Reddit API密钥（从 https://www.reddit.com/prefs/apps 获取）
- OpenAI API密钥
- Anthropic API密钥（可选）
- DeepSeek API密钥（可选）

**重要提示**：Reddit现在使用OAuth2认证，不再支持用户名/密码认证。

## 使用方法

### 🚀 快速启动

#### 使用启动器（推荐）
```bash
python launcher.py
```
启动器提供了三种界面选择：
- 🖥️ **桌面GUI界面** (Tkinter) - 传统桌面应用
- 🌐 **Web界面** (Streamlit) - 现代化Web应用
- 💻 **命令行界面** - 纯命令行操作

### 界面使用说明

#### 1. 桌面GUI界面
```bash
python ui_app.py
```
- 多标签页界面设计
- OAuth2认证流程
- API密钥安全存储
- 实时进度显示
- 完整的日志记录

#### 2. Web界面
```bash
streamlit run streamlit_app.py
```
- 现代化Web界面
- 响应式设计
- 实时数据更新
- 美观的图表展示

#### 3. 命令行界面

##### 完整工作流程
```bash
python main.py --action full --subreddits MachineLearning programming
```

##### 仅抓取数据
```bash
python main.py --action scrape --subreddits MachineLearning --limit 50
```

##### 仅分析现有数据
```bash
python main.py --action analyze --provider openai
```

##### 生成社区报告
```bash
python main.py --action report --subreddits MachineLearning
```

### 高级用法

#### 搜索特定内容
```bash
python main.py --action scrape --subreddits MachineLearning --search "machine learning" "deep learning"
```

#### 使用不同的AI提供商
```bash
python main.py --action analyze --provider anthropic
python main.py --action analyze --provider deepseek
```

#### 不抓取评论（加快速度）
```bash
python main.py --action scrape --subreddits MachineLearning --no-comments
```

## 项目结构

```
RedInsight/
├── launcher.py          # 启动器（推荐使用）
├── main.py              # 命令行主程序入口
├── ui_app.py            # 桌面GUI应用程序
├── streamlit_app.py     # Web界面应用程序
├── reddit_scraper.py    # Reddit数据抓取模块
├── database.py          # 数据库管理模块
├── llm_analyzer.py      # 大模型分析模块
├── config.py            # 配置文件
├── requirements.txt     # 依赖包列表
├── env_example.txt      # 环境变量示例
└── README.md           # 项目说明
```

## 数据库结构

### RedditPost 表
- 存储Reddit帖子信息
- 包含标题、内容、作者、得分等字段

### RedditComment 表
- 存储Reddit评论信息
- 关联到对应的帖子

### AnalysisResult 表
- 存储大模型分析结果
- 支持多种分析类型（情感、主题、质量等）

### SubredditInfo 表
- 存储子版块基本信息

## 分析功能

### 1. 情感分析
- 分析文本的情感倾向（正面/负面/中性）
- 识别具体情绪类型
- 提取关键短语

### 2. 主题分析
- 识别主要话题和关键词
- 内容分类
- 相关性评分

### 3. 质量评估
- 评估内容深度和逻辑性
- 提供改进建议
- 价值评估

### 4. 社区分析
- 整体趋势分析
- 参与度评估
- 社区健康度指标

## 配置选项

在 `config.py` 中可以调整以下参数：

- `DEFAULT_SUBREDDITS`: 默认分析的子版块
- `MAX_POSTS_PER_SUBREDDIT`: 每个子版块最大帖子数
- `MAX_COMMENTS_PER_POST`: 每个帖子最大评论数
- `ANALYSIS_MODEL`: 使用的AI模型
- `BATCH_SIZE`: 批处理大小

## 注意事项

1. **API限制**: Reddit API和AI API都有调用限制，程序已内置延迟机制
2. **数据隐私**: 请遵守Reddit的使用条款和数据处理规范
3. **API密钥安全**: 不要将包含真实API密钥的 `.env` 文件提交到版本控制
4. **存储空间**: 大量数据会占用本地存储空间，请定期清理

## 故障排除

### 常见问题

1. **Reddit API认证失败**
   - 检查Reddit API密钥是否正确
   - 确认用户代理字符串格式正确

2. **AI API调用失败**
   - 验证API密钥是否有效
   - 检查网络连接
   - 确认API配额是否充足

3. **数据库错误**
   - 检查数据库文件权限
   - 确认SQLite版本兼容性

## 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

## 许可证

MIT License

## 联系方式

如有问题或建议，请通过Issue联系。

