# 贡献指南

感谢您对 RedInsight 项目的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 1. 报告问题 (Bug Reports)

如果您发现了 bug，请通过以下方式报告：

- 使用 GitHub Issues 创建新的 issue
- 提供详细的错误描述和复现步骤
- 包含您的系统环境信息（Python 版本、操作系统等）
- 如果可能，提供错误日志或截图

### 2. 功能请求 (Feature Requests)

如果您有新的功能想法：

- 在 GitHub Issues 中创建 feature request
- 详细描述功能需求和预期效果
- 说明为什么这个功能对项目有价值

### 3. 代码贡献

#### 开发环境设置

1. Fork 本仓库
2. 克隆您的 fork：
   ```bash
   git clone https://github.com/chaos-of-dawn/RedInsight.git
   cd RedInsight
   ```

3. 创建虚拟环境：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate     # Windows
   ```

4. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

5. 创建开发分支：
   ```bash
   git checkout -b feature/your-feature-name
   ```

#### 代码规范

- 遵循 PEP 8 Python 代码规范
- 使用有意义的变量和函数名
- 添加适当的注释和文档字符串
- 确保代码通过基本的语法检查

#### 提交规范

使用清晰的提交信息：

```
feat: 添加新功能
fix: 修复 bug
docs: 更新文档
style: 代码格式调整
refactor: 代码重构
test: 添加测试
chore: 构建过程或辅助工具的变动
```

#### 测试

在提交代码前，请确保：

- 代码能够正常运行
- 没有破坏现有功能
- 添加了适当的错误处理

### 4. 文档贡献

- 改进 README.md
- 添加代码注释
- 创建使用教程
- 翻译文档

## 开发指南

### 项目结构

```
RedInsight/
├── launcher.py              # 启动器
├── main.py                  # 命令行入口
├── ui_app.py                # GUI 应用
├── streamlit_app.py         # Web 应用
├── reddit_scraper.py        # Reddit 数据抓取
├── database.py              # 数据库管理
├── llm_analyzer.py          # LLM 分析
├── merged_analysis_page.py  # 合并分析页面
├── data_organizer.py        # 数据整理
├── config.py                # 配置管理
└── requirements.txt         # 依赖列表
```

### 核心模块说明

- **reddit_scraper.py**: 负责从 Reddit 抓取数据
- **database.py**: 数据库操作和模型定义
- **llm_analyzer.py**: 大模型 API 调用和分析
- **streamlit_app.py**: Streamlit Web 界面
- **merged_analysis_page.py**: 数据分析页面逻辑

### 添加新功能

1. 在相应的模块中添加功能
2. 更新配置文件（如需要）
3. 更新文档
4. 测试新功能

## 行为准则

请遵循以下行为准则：

- 尊重所有贡献者
- 保持友好和专业的态度
- 接受建设性的批评
- 专注于对社区最有利的事情
- 对其他社区成员表示同理心

## 许可证

通过贡献代码，您同意您的贡献将在 MIT 许可证下发布。

## 联系方式

如果您有任何问题，请通过以下方式联系：

- 创建 GitHub Issue
- 发送邮件到项目维护者

感谢您的贡献！
