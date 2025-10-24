# 网络连接问题解决方案

## 🔧 问题描述

在使用高级分析功能时，可能会遇到以下网络连接问题：

1. **Hugging Face 连接错误** - SSL连接超时
2. **PyTorch 警告** - 无害的警告信息

## ✅ 解决方案

### 1. Hugging Face 连接问题

#### 方法一：使用镜像源（推荐）
```bash
# 设置环境变量
export HF_ENDPOINT=https://hf-mirror.com
```

#### 方法二：手动下载模型
```bash
# 下载模型到本地
git clone https://hf-mirror.com/sentence-transformers/all-MiniLM-L6-v2
```

#### 方法三：使用代理
```bash
# 设置代理（如果有的话）
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=https://your-proxy:port
```

### 2. PyTorch 警告

这个警告是无害的，可以忽略：
```
Examining the path of torch.classes raised: Tried to instantiate class '__path__._path', but it does not exist!
```

### 3. 网络连接优化

#### 增加重试机制
代码已经添加了自动重试机制，最多重试3次，每次间隔2秒。

#### 使用本地缓存
系统会自动缓存向量化结果，避免重复下载模型。

## 🚀 使用建议

1. **首次使用** - 建议在网络状况良好时首次运行
2. **模型缓存** - 模型下载后会缓存在本地，后续使用无需重新下载
3. **网络问题** - 如果遇到网络问题，可以稍后重试

## 📊 功能状态

✅ **洞察报告功能正常** - JSON和TXT格式都能正常生成
✅ **向量化功能正常** - 支持文本向量化
✅ **聚类分析正常** - 支持KMeans聚类
✅ **业务洞察正常** - 支持生成业务洞察报告

## 🔍 故障排除

如果仍然遇到问题，请检查：

1. **网络连接** - 确保能访问 huggingface.co
2. **防火墙设置** - 确保没有阻止HTTPS连接
3. **代理设置** - 如果在公司网络，可能需要配置代理
4. **DNS设置** - 确保DNS解析正常

## 📞 技术支持

如果问题持续存在，请提供以下信息：
- 错误日志
- 网络环境描述
- 操作系统信息
