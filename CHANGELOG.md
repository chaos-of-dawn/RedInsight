# 更新日志

所有重要的项目变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且此项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- 添加数据导出功能，支持JSON和CSV格式
- 实现分页和高级筛选功能
- 添加数据包管理和LLM处理规则设定
- 支持多种AI提供商（OpenAI、Anthropic、DeepSeek）

### 改进
- 优化数据库查询性能
- 改进Streamlit界面响应速度
- 增强错误处理和用户反馈

### 修复
- 修复筛选条件状态管理问题
- 解决分页显示异常
- 修复LLM处理规则选择问题

## [1.0.0] - 2025-01-07

### 新增
- 🎉 首次发布
- 🔍 Reddit数据抓取功能
- 💾 本地SQLite数据库存储
- 🤖 大模型分析集成（OpenAI、Anthropic、DeepSeek）
- 📊 多维度数据分析（情感、主题、质量）
- 🖥️ 多种界面支持（GUI、Web、命令行）
- ⚙️ 灵活的配置系统
- 📈 社区报告生成
- 🔐 OAuth2认证支持
- 📝 提示词管理系统
- 📦 数据整理和打包功能
- 🎯 批量处理和分析
- 📥 数据导出和下载功能

### 功能特性
- **数据抓取**: 支持抓取帖子、评论和子版块信息
- **数据分析**: 情感分析、主题分析、质量评估
- **界面支持**: 桌面GUI、Web界面、命令行界面
- **AI集成**: 支持多个大模型API
- **数据管理**: 本地数据库存储和管理
- **导出功能**: 支持多种格式的数据导出

### 技术栈
- Python 3.8+
- PRAW (Reddit API)
- SQLAlchemy (数据库)
- Streamlit (Web界面)
- Tkinter (GUI界面)
- OpenAI/Anthropic/DeepSeek APIs

## [0.9.0] - 2024-12-XX

### 新增
- 基础Reddit数据抓取功能
- 简单的数据分析功能
- 基础GUI界面

### 改进
- 优化数据抓取性能
- 改进错误处理

## [0.8.0] - 2024-11-XX

### 新增
- 项目初始版本
- 基础架构搭建
- 核心模块开发

---

## 版本说明

### 版本号格式
我们使用 [语义化版本](https://semver.org/lang/zh-CN/) 进行版本管理：

- **主版本号**：不兼容的API修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

### 更新类型
- **新增**: 新功能
- **改进**: 对现有功能的改进
- **修复**: 问题修复
- **移除**: 移除的功能
- **安全**: 安全相关的修复

### 如何查看更新
- 查看 [Releases](https://github.com/chaos-of-dawn/RedInsight/releases) 页面
- 关注 [Issues](https://github.com/chaos-of-dawn/RedInsight/issues) 中的功能请求
- 查看 [Pull Requests](https://github.com/chaos-of-dawn/RedInsight/pulls) 了解开发进度
