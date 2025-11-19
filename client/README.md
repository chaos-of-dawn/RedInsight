# MailHook 客户端

用于调用邮件中转服务的Python客户端库。

## 安装依赖

```bash
pip install requests
```

或者使用requirements.txt：

```bash
pip install -r requirements.txt
```

## 快速开始

### 方式1: 使用便捷函数（最简单）

```python
from mailhook_client import submit

# 提交机器码和邮箱
result = submit(
    machine_code="ABC123XYZ",
    user_email="user@example.com",
    app_id="my_app"  # 可选
)

if result['success']:
    print("提交成功！")
else:
    print(f"提交失败: {result['message']}")
```

### 方式2: 使用客户端类（适合多次调用）

```python
from mailhook_client import MailHookClient

# 创建客户端
client = MailHookClient(
    server_url="http://101.43.119.148:5000",
    app_id="my_app"
)

# 提交数据
result = client.submit(
    machine_code="ABC123XYZ",
    user_email="user@example.com"
)

if result['success']:
    print("提交成功！")
```

## API 说明

### submit() 函数

便捷函数，快速提交数据。

**参数**：
- `machine_code` (str, 必需): 机器码
- `user_email` (str, 必需): 用户邮箱地址
- `server_url` (str, 可选): 服务器地址，默认: `http://101.43.119.148:5000`
- `app_id` (str, 可选): 应用标识

**返回**：
```python
{
    "success": True,  # 或 False
    "message": "邮件已发送",  # 或错误信息
    "timestamp": "2025-11-07T20:50:26.083913"  # 或 None
}
```

### MailHookClient 类

客户端类，适合需要多次调用的场景。

**初始化参数**：
- `server_url` (str): 服务器地址，默认: `http://101.43.119.148:5000`
- `app_id` (str, 可选): 默认应用标识

**方法**：
- `submit(machine_code, user_email, app_id=None)`: 提交数据

## 使用示例

### 示例1: 基本使用

```python
from mailhook_client import submit

result = submit("ABC123", "user@example.com", app_id="my_app")
print(result)
```

### 示例2: 集成到应用中

```python
from mailhook_client import submit

# 获取机器码（你的代码）
machine_code = get_machine_code()

# 获取用户邮箱（你的代码）
user_email = input("请输入邮箱: ")

# 提交
result = submit(machine_code, user_email, app_id="my_app")

if result['success']:
    print("注册成功！")
else:
    print(f"注册失败: {result['message']}")
```

### 示例3: 错误处理

```python
from mailhook_client import submit

result = submit("ABC123", "user@example.com")

if result['success']:
    print("✅ 成功")
else:
    print(f"❌ 失败: {result['message']}")
    # 根据错误信息处理
    if "连接" in result['message']:
        print("网络连接问题，请检查服务器地址")
    elif "超时" in result['message']:
        print("请求超时，请稍后重试")
```

## 配置

### 修改服务器地址

如果服务器地址改变了，有两种方式：

**方式1: 在调用时指定**
```python
result = submit(
    "ABC123",
    "user@example.com",
    server_url="http://new-server-ip:5000"
)
```

**方式2: 使用客户端类**
```python
client = MailHookClient(server_url="http://new-server-ip:5000")
result = client.submit("ABC123", "user@example.com")
```

## 错误处理

客户端会自动处理以下错误：
- 网络连接错误
- 请求超时
- HTTP错误
- 服务器返回的错误

所有错误都会返回包含 `success: False` 的字典，不会抛出异常。

## 运行示例

```bash
# 运行示例代码
python example.py
```

## 注意事项

1. **服务器地址**: 默认是 `http://101.43.119.148:5000`，如果服务器IP改变，需要更新
2. **网络连接**: 确保能够访问服务器地址
3. **依赖**: 需要安装 `requests` 库
4. **超时**: 默认超时时间为10秒，可以在 `MailHookClient` 类中修改 `timeout` 属性

