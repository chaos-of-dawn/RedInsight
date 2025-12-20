# 🔍 RedInsight - Reddit智能分析、自动运营平台

> 集数据抓取、智能分析、内容生成、养号管理于一体的Reddit数据分析与养号平台

![GitHub stars](https://img.shields.io/github/stars/chaos-of-dawn/RedInsight?style=social)
![GitHub forks](https://img.shields.io/github/forks/chaos-of-dawn/RedInsight?style=social)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

## 📋 项目功能

RedInsight 是一个基于大模型AI技术的Reddit数据分析平台，提供以下核心功能：

### 🎯 核心功能模块

| 功能模块 | 主要功能 |
| 📥 **数据抓取** | 多维度筛选、批量抓取Reddit数据、本地存储、关键词历史记录 |
| 📊 **本地数据管理** | 数据管理、数据整理打包、分析结果展示、关键词历史管理 |
| 🎯 **子版块推荐** | 智能需求分析、三层漏斗式筛选、精准推荐、批量索引 |
| 🔧 **自动点赞回帖控制台** | 账号状态监控、发帖资格检测、养号计划、自动化运营、快速互动、任务管理 |
| 🔍 **智能筛选** | 多维度筛选、条件组合、统计分析、数据导出 |
| 📝 **智能发帖** | 帖子库管理、AI内容生成、定时发布、规则检查、发布计划管理 |

### ✨ 主要特性

- 🤖 **AI智能发帖**：基于深度分析结果，AI自动生成高质量帖子内容，支持增强模式
- 🎯 **智能推荐**：支持中文输入，AI自动翻译并推荐目标子版块
- 📊 **数据分析**：六阶段深度分析，提取关键词和业务洞察
- 🔧 **养号管理**：账号状态监控、发帖资格检测、7天养号计划
- 🤖 **自动化运营**：定时发帖、自动互动、任务调度、后台服务
- ⚡ **快速互动**：帖子互动、评论管理、热帖追踪
- 🔍 **智能筛选**：多维度数据筛选和统计分析
- 📅 **定时发布**：灵活的发布计划管理，支持1-3个子版块批量发布
- ✅ **规则检查**：AI自动检查帖子内容是否符合子版块规则
- 🔑 **关键词历史**：自动记录所有输入的关键词，支持按来源筛选和管理
- ⚡ **性能优化**：智能缓存、减少重新渲染、提升UI流畅度

---

## ⚠️ 重要提示

### 📘 Reddit API申请指南

**在下载部署本项目前，请先用Reddit账号向官方申请Reddit的官方API。**

#### 为什么需要Reddit API？

本项目需要Reddit API密钥才能正常使用以下核心功能：
- 数据抓取：从Reddit子版块获取帖子和评论数据
- 智能发帖：在Reddit上发布帖子
- 账号管理：查看账号状态、Karma等信息
- 互动功能：点赞、评论、回复等操作

#### 申请条件

- 拥有一个有效的Reddit账号
- Reddit账号需要满足一定的使用时长和活跃度要求
- 建议账号有一定Karma值，提高申请成功率

#### 申请步骤

1. **访问Reddit应用管理页面**
   - 打开浏览器，访问：https://www.reddit.com/prefs/apps
   - 确保已登录您的Reddit账号

2. **创建新应用**
   - 滚动到页面底部，点击 **"create another app"** 或 **"create app"** 按钮

3. **填写应用信息**
   - **应用名称（name）**：填写任意名称，例如 "RedInsight" 或 "我的Reddit应用"
   - **应用类型（type）**：选择 **"script"**
   - **描述（description）**：可选，填写应用描述
   - **关于链接（about url）**：留空
   - **重定向URI（redirect uri）**：填写 `http://localhost:8080`（必须填写此值）

4. **提交并获取密钥**
   - 点击 **"create app"** 按钮提交
   - 创建成功后，您会看到应用信息页面

5. **记录密钥信息**
   - **客户端ID（client_id）**：在应用名称下方，显示为一段字符串（通常在应用名称下方，格式类似：`xxxxxxxxxxxxxx`）
   - **客户端密钥（client_secret）**：在应用信息中标记为 "secret" 的字段，点击 "reveal" 按钮可查看完整密钥

#### 注意事项

- ⚠️ **请妥善保管您的API密钥**，不要泄露给他人
- ⚠️ **客户端密钥（client_secret）** 只显示一次，请立即保存
- ⚠️ **重定向URI（redirect uri）** 必须填写 `http://localhost:8080`，否则OAuth认证会失败
- ⚠️ 如果申请被拒绝，请检查账号是否符合Reddit的使用政策

#### 常见问题

**Q: 申请被拒绝怎么办？**  
A: 确保您的Reddit账号活跃，有一定Karma值，并且遵守Reddit社区规则。

**Q: 找不到客户端ID和客户端密钥？**  
A: 客户端ID在应用名称下方，客户端密钥需要点击 "reveal" 按钮才能查看。

**Q: 重定向URI可以填写其他地址吗？**  
A: 建议使用 `http://localhost:8080`，这是本项目默认配置的重定向地址。



## 📖 本地部署详细步骤

### 1. 环境要求

#### 系统要求
- **操作系统**：Windows 10/11、Linux、macOS
- **Python版本**：Python 3.8 或更高版本

#### 必需软件
- Python 3.8+（需添加到系统PATH）
- 网络连接（用于安装依赖和API调用）

### 2. 安装步骤

#### 步骤 1：克隆项目

```bash
# 克隆项目
git clone https://github.com/chaos-of-dawn/RedInsight.git
cd RedInsight
```

#### 步骤 2：创建虚拟环境

**Windows:**
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate
```

**Linux/macOS:**
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

#### 步骤 3：安装PyTorch（CPU版本）

```bash
# 安装PyTorch CPU版本
pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu
pip install torchvision==0.16.0+cpu --index-url https://download.pytorch.org/whl/cpu
```

> **注意**：PyTorch安装可能需要几分钟时间，请耐心等待

#### 步骤 4：安装sentence-transformers依赖（按顺序）

```bash
# 必须按顺序安装，避免依赖冲突
pip install tokenizers==0.13.2
pip install huggingface-hub==0.11.1
pip install transformers==4.21.0
pip install sentence-transformers==2.2.2
```

> **重要**：这些包必须按顺序安装，否则可能出现依赖冲突

#### 步骤 5：安装其他依赖

```bash
# 安装项目依赖
pip install -r requirements.txt
```

> **提示**：如果安装过程中遇到网络问题，可以使用国内镜像源

**使用国内镜像源（可选）：**
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 启动应用

#### 方法一：使用一键启动脚本（推荐）

**Windows:**
```bash
# 双击运行
一键启动.bat
```

脚本会自动：
- 检查Python环境
- 创建/激活虚拟环境
- 安装缺失的依赖
- 处理激活流程
- 启动应用

#### 方法二：手动启动

```bash
# 确保虚拟环境已激活
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# 启动应用
streamlit run streamlit_app.py
```

应用将在浏览器中自动打开，默认地址：http://localhost:8501



### 4. 配置API密钥

> **重要提示**：所有API密钥配置都通过Web界面完成，无需手动编辑配置文件

#### 获取Reddit API密钥

> **提示**：详细的Reddit API申请指南请参考上方的 [📘 Reddit API申请指南](#-reddit-api申请指南) 部分

在配置之前，您需要先获取Reddit API密钥。简要步骤：

1. 访问 https://www.reddit.com/prefs/apps
2. 点击页面上的 "create another app" 或 "create app" 按钮
3. 填写应用信息（应用类型选择"script"，重定向URI填写`http://localhost:8080`）
4. 创建后记录 **客户端ID（client_id）** 和 **客户端密钥（client_secret）**

#### 获取大模型API密钥

- **OpenAI**: 访问 https://platform.openai.com/api-keys
- **Anthropic**: 访问 https://console.anthropic.com/
- **DeepSeek**: 访问 https://platform.deepseek.com/

#### 在Web界面中配置

启动应用后，在左侧边栏的 **"🔧 API配置"** 部分配置API密钥：

1. **Reddit API配置**（必需）
   - 输入客户端ID
   - 输入客户端密钥
   - 设置重定向URI（默认：`http://localhost:8080`）
   - 点击 "开始Reddit认证" 完成OAuth2认证

2. **AI API配置**（至少配置一个）
   - OpenAI API密钥（可选）
   - Anthropic API密钥（可选）
   - DeepSeek API密钥（可选）

3. **保存配置**
   - 点击 "💾 保存配置" 按钮
   - 配置会自动保存到 `api_keys.json` 文件

4. **初始化系统**
   - 配置完成后，点击 "🚀 初始化系统" 按钮
   - 系统会自动验证配置并初始化组件

### 5. 首次使用

#### 激活项目

1. 首次运行需要激活
2. 按照提示输入邮箱
3. 联系项目管理员获取激活码
4. 输入激活码完成激活

**项目管理员联系方式：**
- **微信**：`whj7087824`
- **加好友时请注明**：`RedInsight激活`
邮箱：whj20190815@163.com


## 🛠️ 技术栈

- **前端框架**：Streamlit (Web界面)
- **后端语言**：Python 3.8+
- **数据抓取**：PRAW (Reddit API)
- **AI模型**：OpenAI GPT、Anthropic Claude、DeepSeek
- **向量化**：sentence-transformers
- **数据库**：SQLAlchemy + SQLite
- **关键词提取**：TF-IDF + 大模型混合策略
- **性能优化**：智能缓存、局部更新、减少重新渲染
- **激活系统**：基于机器指纹的激活码验证


## 🎯 适用场景

- **Reddit养号**：新账号养号、账号状态监控、养号计划生成
- **Reddit数据分析**：子版块分析、用户需求挖掘、趋势洞察
- **AI大模型发帖**：基于数据分析生成高质量内容，自动适配子版块规则
- **Reddit热帖追踪**：实时追踪热门帖子，获取最新社区动态
- **自动化运营**：设置自动化任务，提高运营效率

## 📖 使用流程

### 完整工作流程

1. **需求分析** → 输入中文需求，AI分析并推荐目标子版块
2. **批量索引** → 选择推荐子版块进行批量数据抓取
3. **深度分析** → 运行六阶段深度分析，提取关键词和业务洞察
4. **账号检测** → 检测账号发帖资格，生成养号计划（如需要）
5. **智能发帖** → 基于分析结果生成高质量帖子内容
   - **方式一**：使用AI生成模块（标准/增强模式）生成帖子
   - **方式二**：在帖子库中手动创建帖子
6. **规则检查** → 自动检查帖子内容是否符合子版块规则
7. **定时发布** → 设置发布计划，支持1-3个子版块批量发布
8. **互动管理** → 进行帖子互动，追踪热帖，管理账号
9. **自动化运营** → 设置自动化任务，提高运营效率
10. **关键词管理** → 在本地数据管理中查看和管理关键词历史



## 🤝 贡献

欢迎提交问题反馈和代码贡献来改进这个项目！

### 贡献方向
- 功能增强
- Bug修复
- 文档完善
- 性能优化

## 📝 许可证

MIT License

## 📮 联系方式

**微信**：`whj7087824`  
**加好友时请注明**：`RedInsight激活` 或 `github`
**邮箱地址：whj20190815@163.com

如有问题或建议，欢迎通过微信或者电子邮件联系！

---

## 🏷️ 标签

`reddit养号` `reddit数据分析` `AI大模型发帖` `reddit热帖追踪` `Reddit API` `Python` `Streamlit` `AI` `机器学习` `数据分析` `自然语言处理` `自动化运营` `智能筛选` `定时发布` `规则检查` `关键词管理` `性能优化` `激活系统`

---

<div align="center">

**⭐ 如果这个项目对您有帮助，请给个Star支持一下！⭐**

由 RedInsight 团队用 ❤️ 制作

</div>
