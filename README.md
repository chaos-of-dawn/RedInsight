# 🔍 RedInsight - Reddit智能分析平台

> 集数据抓取、智能分析、内容生成、养号管理于一体的Reddit数据分析与养号平台

![GitHub stars](https://img.shields.io/github/stars/chaos-of-dawn/RedInsight?style=social)
![GitHub forks](https://img.shields.io/github/forks/chaos-of-dawn/RedInsight?style=social)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

## ⚠️ 重要提示 / Important Notice

### 📦 版本说明 / Version Description


**🔗 夸克网盘下载链接 / Quark Cloud Drive Download Link：** [https://pan.quark.cn/s/2cbfb4c18c47](https://pan.quark.cn/s/2cbfb4c18c47)

**使用说明 / Usage Instructions：**
- 下载后解压文件 / Extract the downloaded file
- 双击运行 `一键启动.bat` 即可使用 / Double-click `一键启动.bat` to start
- 项目需要激活码才能使用 / Activation code required

**🔑 获取激活码 / Get Activation Code：**  
请联系项目管理员获取激活码 / Please contact the project administrator for activation code  
**管理员微信号 / Administrator WeChat：`whj7087824`**  
加好友时请注明：`RedInsight激活` / Please note `RedInsight激活` when adding friend

---

## 📖 本地部署详细步骤 / Detailed Local Deployment Steps

### 1. 环境要求 / Requirements

#### 系统要求 / System Requirements
- **操作系统**：Windows 10/11、Linux、macOS
- **Operating System**: Windows 10/11, Linux, macOS
- **Python版本**：Python 3.8 或更高版本
- **Python Version**: Python 3.8 or higher

#### 必需软件 / Required Software
- Python 3.8+（需添加到系统PATH）
- Python 3.8+ (must be added to system PATH)
- 网络连接（用于安装依赖和API调用）
- Network connection (for installing dependencies and API calls)

### 2. 安装步骤 / Installation Steps

#### 步骤 1：克隆项目 / Step 1: Clone the Project

```bash
# 克隆项目 / Clone the project
git clone https://github.com/chaos-of-dawn/RedInsight.git
cd RedInsight
```

#### 步骤 2：创建虚拟环境 / Step 2: Create Virtual Environment

**Windows:**
```bash
# 创建虚拟环境 / Create virtual environment
python -m venv venv

# 激活虚拟环境 / Activate virtual environment
venv\Scripts\activate
```

**Linux/macOS:**
```bash
# 创建虚拟环境 / Create virtual environment
python3 -m venv venv

# 激活虚拟环境 / Activate virtual environment
source venv/bin/activate
```

#### 步骤 3：安装PyTorch（CPU版本）/ Step 3: Install PyTorch (CPU Version)

```bash
# 安装PyTorch CPU版本 / Install PyTorch CPU version
pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu
pip install torchvision==0.16.0+cpu --index-url https://download.pytorch.org/whl/cpu
```

> **注意**：PyTorch安装可能需要几分钟时间，请耐心等待  
> **Note**: PyTorch installation may take several minutes, please be patient

#### 步骤 4：安装sentence-transformers依赖（按顺序）/ Step 4: Install sentence-transformers Dependencies (In Order)

```bash
# 必须按顺序安装，避免依赖冲突 / Must install in order to avoid dependency conflicts
pip install tokenizers==0.13.2
pip install huggingface-hub==0.11.1
pip install transformers==4.21.0
pip install sentence-transformers==2.2.2
```

> **重要**：这些包必须按顺序安装，否则可能出现依赖冲突  
> **Important**: These packages must be installed in order, otherwise dependency conflicts may occur

#### 步骤 5：安装其他依赖 / Step 5: Install Other Dependencies

```bash
# 安装项目依赖 / Install project dependencies
pip install -r requirements.txt
```

> **提示**：如果安装过程中遇到网络问题，可以使用国内镜像源  
> **Tip**: If you encounter network issues, you can use domestic mirror sources

**使用国内镜像源（可选）/ Using Domestic Mirror Sources (Optional):**
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 启动应用 / Start the Application

#### 方法一：使用一键启动脚本（推荐）/ Method 1: Use One-Click Launch Script (Recommended)

**Windows:**
```bash
# 双击运行 / Double-click to run
一键启动.bat
```

脚本会自动：
- 检查Python环境
- 创建/激活虚拟环境
- 安装缺失的依赖
- 处理激活流程
- 启动应用

The script will automatically:
- Check Python environment
- Create/activate virtual environment
- Install missing dependencies
- Handle activation process
- Start the application

#### 方法二：手动启动 / Method 2: Manual Start

```bash
# 确保虚拟环境已激活 / Ensure virtual environment is activated
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# 启动应用 / Start the application
streamlit run streamlit_app.py
```

应用将在浏览器中自动打开，默认地址：http://localhost:8501

The application will automatically open in your browser at: http://localhost:8501

### 4. 配置API密钥 / Configure API Keys

> **重要提示**：所有API密钥配置都通过Web界面完成，无需手动编辑配置文件  
> **Important**: All API key configuration is done through the Web interface, no need to manually edit configuration files

#### 获取Reddit API密钥 / Get Reddit API Keys

在配置之前，您需要先获取Reddit API密钥：

Before configuration, you need to get Reddit API keys first:

1. 访问 https://www.reddit.com/prefs/apps
   Visit https://www.reddit.com/prefs/apps
2. 点击 "create another app" 或 "create app"
   Click "create another app" or "create app"
3. 填写应用信息：
   Fill in application information:
   - **name**: 应用名称（任意）
     Application name (any)
   - **type**: 选择 "script"
     Select "script"
   - **description**: 应用描述（可选）
     Application description (optional)
   - **about url**: 留空
     Leave blank
   - **redirect uri**: 填写 `http://localhost:8080`
     Fill in `http://localhost:8080`
4. 创建后，记录以下信息：
   After creation, record the following information:
   - **client_id**: 应用ID（在应用名称下方）
     Application ID (below application name)
   - **client_secret**: 密钥（secret字段）
     Secret key (secret field)

#### 获取大模型API密钥 / Get LLM API Keys

- **OpenAI**: 访问 https://platform.openai.com/api-keys
  Visit https://platform.openai.com/api-keys
- **Anthropic**: 访问 https://console.anthropic.com/
  Visit https://console.anthropic.com/
- **DeepSeek**: 访问 https://platform.deepseek.com/
  Visit https://platform.deepseek.com/

#### 在Web界面中配置 / Configure in Web Interface

启动应用后，在左侧边栏的 **"🔧 API配置"** 部分配置API密钥：

After starting the application, configure API keys in the **"🔧 API配置"** section in the left sidebar:

1. **Reddit API配置**（必需）
   **Reddit API Configuration** (Required)
   - 输入 Client ID
     Enter Client ID
   - 输入 Client Secret
     Enter Client Secret
   - 设置重定向URI（默认：`http://localhost:8080`）
     Set redirect URI (default: `http://localhost:8080`)
   - 点击 "开始Reddit认证" 完成OAuth2认证
     Click "开始Reddit认证" to complete OAuth2 authentication

2. **AI API配置**（至少配置一个）
   **AI API Configuration** (At least one required)
   - OpenAI API Key（可选）
     OpenAI API Key (Optional)
   - Anthropic API Key（可选）
     Anthropic API Key (Optional)
   - DeepSeek API Key（可选）
     DeepSeek API Key (Optional)

3. **保存配置**
   **Save Configuration**
   - 点击 "💾 保存配置" 按钮
     Click "💾 保存配置" button
   - 配置会自动保存到 `api_keys.json` 文件
     Configuration will be automatically saved to `api_keys.json` file

4. **初始化系统**
   **Initialize System**
   - 配置完成后，点击 "🚀 初始化系统" 按钮
     After configuration, click "🚀 初始化系统" button
   - 系统会自动验证配置并初始化组件
     System will automatically verify configuration and initialize components

### 5. 首次使用 / First Time Use

#### 激活项目 / Activate the Project

1. 首次运行需要激活 / Activation required on first run
2. 按照提示输入邮箱 / Enter your email as prompted
3. 联系项目管理员获取激活码 / Contact project administrator for activation code
4. 输入激活码完成激活 / Enter activation code to complete activation

**项目管理员联系方式 / Project Administrator Contact:**
- **微信 / WeChat**: `whj7087824`
- **加好友时请注明 / Please note when adding friend**: `RedInsight激活`

---

**RedInsight** 是一个基于大模型AI技术的Reddit数据分析平台，帮助用户从Reddit数据中挖掘商业价值，生成高质量内容，并智能管理Reddit账号。通过AI技术实现从需求分析到内容发布到互动反馈的完整闭环。

**RedInsight** is a Reddit data analysis platform based on large language model AI technology, helping users extract business value from Reddit data, generate high-quality content, and intelligently manage Reddit accounts. It achieves a complete closed loop from demand analysis to content publishing to interaction feedback through AI technology.

## ✨ 核心特性 / Core Features

### 🎯 智能子版块推荐 / Intelligent Subreddit Recommendation
- **需求分析**：支持中文输入，AI自动翻译并分析用户意图
- **Demand Analysis**: Supports Chinese input, AI automatically translates and analyzes user intent
- **三层漏斗式筛选**：高度匹配(85-100分) → 中度匹配(70-84分) → 低度匹配(60-69分)
- **Three-Tier Funnel Filtering**: High match (85-100) → Medium match (70-84) → Low match (60-69)
- **精准推荐**：基于向量相似度匹配，精准定位目标子版块
- **Precise Recommendation**: Based on vector similarity matching, precisely locate target subreddits
- **批量索引**：一键索引多个推荐子版块，快速建立数据基础
- **Batch Indexing**: One-click indexing of multiple recommended subreddits, quickly establish data foundation

### 🔧 Reddit养号控制台 / Reddit Account Management Console
- **账号状态监控**：实时显示账号Karma、账号年龄、今日任务等关键指标
- **Account Status Monitoring**: Real-time display of account Karma, account age, daily tasks and other key metrics
- **发帖资格检测**：智能评估账号在目标子版块的发帖资格，生成个性化养号建议
- **Posting Eligibility Detection**: Intelligently evaluate account posting eligibility in target subreddits, generate personalized account nurturing suggestions
- **7天养号计划**：自动生成科学的养号计划，包括点赞、评论、发帖任务
- **7-Day Account Nurturing Plan**: Automatically generate scientific account nurturing plans, including likes, comments, and posting tasks
- **互动历史统计**：记录所有互动操作，统计成功率和互动趋势
- **Interaction History Statistics**: Record all interaction operations, statistics on success rate and interaction trends

### 📝 AI智能发帖系统 / AI Intelligent Posting System
- **五步骤智能流程**：
  1. **子版块选择** - 从推荐/手动/已索引/数据库中选择
  2. **详情查看** - 查看订阅数、描述、关键词、热门帖子
  3. **规则提示** - 自动获取并翻译子版块规则为中文
  4. **内容生成** - AI基于深度分析结果、关键词、长尾词和规则生成内容
  5. **预览发布** - 预览、验证、保存草稿或直接发布
- **Five-Step Intelligent Process**:
  1. **Subreddit Selection** - Select from recommendations/manual/indexed/database
  2. **Details View** - View subscribers, description, keywords, hot posts
  3. **Rules Prompt** - Automatically fetch and translate subreddit rules to Chinese
  4. **Content Generation** - AI generates content based on deep analysis results, keywords, long-tail keywords and rules
  5. **Preview & Publish** - Preview, verify, save draft or publish directly
  
- **AI内容生成**：基于深度分析结果、长尾关键词和子版块规则生成高质量帖子
- **AI Content Generation**: Generate high-quality posts based on deep analysis results, long-tail keywords and subreddit rules
- **规则智能适配**：自动获取并翻译子版块规则，确保内容合规
- **Intelligent Rule Adaptation**: Automatically fetch and translate subreddit rules to ensure content compliance
- **多语言支持**：中文输入自动翻译为英文，支持本地化内容
- **Multi-language Support**: Chinese input automatically translated to English, supports localized content
- **重新生成功能**：支持不满意内容一键重新生成
- **Regeneration Function**: Supports one-click regeneration of unsatisfactory content

### 🔬 深度数据分析 / Deep Data Analysis
- **六阶段分析流程**：结构化抽取 → 向量化 → 聚类 → 洞察生成 → 关键词提取 → 报告导出
- **Six-Stage Analysis Process**: Structured extraction → Vectorization → Clustering → Insight generation → Keyword extraction → Report export
- **长尾关键词提取**：TF-IDF + 大模型混合策略，提取精准短语（如"iPhone battery replacement"）
- **Long-tail Keyword Extraction**: TF-IDF + LLM hybrid strategy, extract precise phrases (e.g., "iPhone battery replacement")
- **业务洞察生成**：从海量数据中提取主导主题、主要痛点、关键机会
- **Business Insight Generation**: Extract dominant themes, main pain points, and key opportunities from massive data
- **自动报告生成**：导出包含高频词、长尾词、主题分析的完整JSON/TXT报告
- **Automatic Report Generation**: Export complete JSON/TXT reports including high-frequency words, long-tail keywords, and theme analysis

### 📚 快速互动管理 / Quick Interaction Management
- **帖子互动**：快速点赞、点踩、保存、回复、查看评论
- **Post Interaction**: Quick like, dislike, save, reply, view comments
- **子版块浏览与翻译**：浏览热门帖子，一键翻译为中文，查看评论并进行互动
- **Subreddit Browsing & Translation**: Browse hot posts, one-click translation to Chinese, view comments and interact
- **评论管理**：查看帖子评论，点赞/点踩评论，快速回复
- **Comment Management**: View post comments, like/dislike comments, quick reply
- **热帖追踪**：实时追踪热门帖子，获取最新社区动态
- **Hot Post Tracking**: Real-time tracking of hot posts, get latest community trends

### 🔍 数据抓取与存储 / Data Scraping & Storage
- **灵活抓取**：支持按时间、分数、关键词等多维度筛选
- **Flexible Scraping**: Supports multi-dimensional filtering by time, score, keywords, etc.
- **本地存储**：使用SQLAlchemy和SQLite存储结构化数据
- **Local Storage**: Use SQLAlchemy and SQLite to store structured data
- **数据管理**：完整的本地数据管理和查询功能
- **Data Management**: Complete local data management and query functions

## 🛠️ 技术栈 / Tech Stack

- **前端框架 / Frontend Framework**: Streamlit (Web界面 / Web Interface)
- **后端语言 / Backend Language**: Python 3.8+
- **数据抓取 / Data Scraping**: PRAW (Reddit API)
- **AI模型 / AI Models**: OpenAI GPT、Anthropic Claude、DeepSeek
- **向量化 / Vectorization**: sentence-transformers
- **数据库 / Database**: SQLAlchemy + SQLite
- **关键词提取 / Keyword Extraction**: TF-IDF + 大模型混合策略 / TF-IDF + LLM Hybrid Strategy

## 📊 功能模块 / Feature Modules

| 模块 / Module | 功能 / Features |
|------|------|
| 🎯 **子版块推荐 / Subreddit Recommendation** | 智能需求分析、三层漏斗式筛选、精准推荐、批量索引 / Intelligent demand analysis, three-tier funnel filtering, precise recommendation, batch indexing |
| 🔧 **养号控制台 / Account Management Console** | 账号状态监控、发帖资格检测、养号计划、互动管理 / Account status monitoring, posting eligibility detection, account nurturing plan, interaction management |
| 📝 **智能发帖 / Intelligent Posting** | 5步智能流程、AI内容生成、规则适配、多语言支持 / 5-step intelligent process, AI content generation, rule adaptation, multi-language support |
| 🔬 **深度分析 / Deep Analysis** | 六阶段分析、长尾关键词提取、业务洞察、自动报告 / Six-stage analysis, long-tail keyword extraction, business insights, automatic reports |
| 📚 **互动管理 / Interaction Management** | 帖子互动、浏览翻译、评论管理、热帖追踪 / Post interaction, browse translation, comment management, hot post tracking |
| 🔍 **数据抓取 / Data Scraping** | 多维度筛选、批量抓取、本地存储、数据管理 / Multi-dimensional filtering, batch scraping, local storage, data management |

## 🎯 适用场景 / Use Cases

- **Reddit养号**：新账号养号、账号状态监控、养号计划生成
- **Reddit Account Nurturing**: New account nurturing, account status monitoring, account nurturing plan generation
- **Reddit数据分析**：子版块分析、用户需求挖掘、趋势洞察
- **Reddit Data Analysis**: Subreddit analysis, user demand mining, trend insights
- **AI大模型发帖**：基于数据分析生成高质量内容，自动适配子版块规则
- **AI LLM Posting**: Generate high-quality content based on data analysis, automatically adapt to subreddit rules
- **Reddit热帖追踪**：实时追踪热门帖子，获取最新社区动态
- **Reddit Hot Post Tracking**: Real-time tracking of hot posts, get latest community trends

## 🚀 快速开始 / Quick Start

### 使用步骤 / Usage Steps

1. **下载完整版 / Download Full Version**  
   从夸克网盘下载完整版项目压缩包：[下载链接](https://pan.quark.cn/s/2cbfb4c18c47)  
   Download the full version project package from Quark Cloud Drive: [Download Link](https://pan.quark.cn/s/2cbfb4c18c47)

2. **解压文件 / Extract Files**  
   将下载的压缩包解压到本地目录  
   Extract the downloaded package to a local directory

3. **启动应用 / Start Application**  
   双击运行 `一键启动.bat` 文件即可启动应用  
   Double-click `一键启动.bat` to start the application

4. **激活项目 / Activate Project**  
   - 首次运行需要激活 / Activation required on first run
   - 按照提示输入邮箱并获取激活码 / Enter email as prompted and get activation code
   - 联系项目管理员获取激活码：**微信号 `whj7087824`** / Contact project administrator for activation code: **WeChat `whj7087824`**

## 📖 使用流程 / Usage Workflow

### 完整工作流程 / Complete Workflow

1. **需求分析** → 输入中文需求，AI分析并推荐目标子版块
   **Demand Analysis** → Enter Chinese demand, AI analyzes and recommends target subreddits
2. **批量索引** → 选择推荐子版块进行批量数据抓取
   **Batch Indexing** → Select recommended subreddits for batch data scraping
3. **深度分析** → 运行六阶段深度分析，提取关键词和业务洞察
   **Deep Analysis** → Run six-stage deep analysis, extract keywords and business insights
4. **账号检测** → 检测账号发帖资格，生成养号计划（如需要）
   **Account Detection** → Detect account posting eligibility, generate account nurturing plan (if needed)
5. **智能发帖** → 基于分析结果生成高质量帖子内容
   **Intelligent Posting** → Generate high-quality post content based on analysis results
6. **互动管理** → 进行帖子互动，追踪热帖，管理账号
   **Interaction Management** → Interact with posts, track hot posts, manage accounts

### 核心功能演示 / Core Feature Demo

#### 🔧 Reddit养号控制台 / Reddit Account Management Console
- 查看账号状态（Karma、账号年龄）
- View account status (Karma, account age)
- 检测目标子版块发帖资格
- Detect target subreddit posting eligibility
- 生成7天养号计划
- Generate 7-day account nurturing plan
- 跟踪养号进度和互动历史
- Track account nurturing progress and interaction history

#### 📝 智能发帖流程 / Intelligent Posting Process
1. 选择子版块 → 2. 查看详情 → 3. 规则提示（自动翻译） → 4. 生成内容 → 5. 预览发布
1. Select subreddit → 2. View details → 3. Rules prompt (auto-translate) → 4. Generate content → 5. Preview & publish

#### 🎯 子版块推荐 / Subreddit Recommendation
- 中文需求输入 → AI翻译分析 → 三层漏斗筛选 → 精准推荐 → 批量索引
- Chinese demand input → AI translation analysis → Three-tier funnel filtering → Precise recommendation → Batch indexing

## 📸 功能截图 / Screenshots

> 注：本项目提供Web界面（Streamlit），界面友好，操作便捷。  
> Note: This project provides a Web interface (Streamlit), user-friendly and easy to operate.

## 🤝 贡献 / Contributing

欢迎提交Issue和Pull Request来改进这个项目！

Welcome to submit Issues and Pull Requests to improve this project!

### 贡献方向 / Contribution Directions
- 功能增强 / Feature Enhancement
- Bug修复 / Bug Fixes
- 文档完善 / Documentation Improvement
- 性能优化 / Performance Optimization

## 📝 许可证 / License

MIT License

## 📮 联系方式 / Contact

**微信 / WeChat**：`whj7087824`  
**加好友时请注明 / Please note when adding friend**：`RedInsight激活` 或 `github`

如有问题或建议，欢迎通过微信联系！

If you have any questions or suggestions, please contact via WeChat!

---

## 🏷️ 标签 / Tags

`reddit养号` `reddit数据分析` `AI大模型发帖` `reddit热帖追踪` `Reddit API` `Python` `Streamlit` `AI` `机器学习` `数据分析` `自然语言处理`

`reddit account nurturing` `reddit data analysis` `AI LLM posting` `reddit hot post tracking` `Reddit API` `Python` `Streamlit` `AI` `Machine Learning` `Data Analysis` `Natural Language Processing`

---

<div align="center">

**⭐ 如果这个项目对您有帮助，请给个Star支持一下！⭐**

**⭐ If this project helps you, please give it a Star! ⭐**

Made with ❤️ by RedInsight Team

</div>
