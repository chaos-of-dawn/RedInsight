# Python应用激活码生成系统

一个用于Python应用分发的激活码生成和验证系统，支持机器码绑定和用户邮箱验证。

## 功能特点

- ✅ **机器码绑定**：激活码与特定机器硬件绑定，更换硬件需重新激活
- ✅ **邮箱验证**：激活码包含用户邮箱信息，确保一对一使用
- ✅ **简洁可读格式**：激活码格式为 `LICENSE-XXXX-XXXX-XXXX-XXXX-XXXX`
- ✅ **可选过期时间**：支持设置激活码过期日期
- ✅ **离线验证**：无需服务器，完全离线验证
- ✅ **安全加密**：使用HMAC-SHA256确保激活码不被伪造

## 文件说明

- `machine_fingerprint.py` - 获取机器硬件信息并生成唯一机器码
- `license_generator.py` - 激活码生成器
- `license_validator.py` - 激活码验证器（供应用使用）
- `config.py` - 配置文件（存储密钥）

## 工作流程

1. **用户获取机器码**：用户在自己的机器上运行 `machine_fingerprint.py` 获取机器码
2. **用户提供信息**：用户将机器码和邮箱提供给开发者
3. **开发者生成激活码**：开发者使用用户的机器码和邮箱运行 `license_generator.py` 生成激活码
4. **用户激活应用**：用户在自己的应用中使用激活码和邮箱进行激活验证

## 快速开始

### 1. 配置密钥

编辑 `config.py`，修改 `SECRET_KEY` 为你的密钥：

```python
SECRET_KEY = "your-secret-key-here-change-this-to-a-random-string"
```

**重要**：密钥应该是一个随机字符串，建议使用以下命令生成：

```python
import secrets
print(secrets.token_urlsafe(32))
```

### 2. 获取用户机器码

**用户需要先在自己的机器上获取机器码：**

用户运行：
```bash
python machine_fingerprint.py
```

这会显示用户的机器码（32位十六进制字符串）。用户需要将这个机器码提供给开发者。

### 3. 生成激活码

开发者运行生成器：

```bash
python license_generator.py
```

按提示输入：
- **用户邮箱**（用户提供的邮箱地址）
- **用户机器码**（用户提供的机器码，不是本机机器码）
- 可选择设置过期时间（可选）

### 4. 在应用中使用验证器

在你的应用中导入验证模块：

```python
from license_validator import check_license

# 获取用户输入的激活码和邮箱
license_code = input("请输入激活码: ")
email = input("请输入邮箱: ")

# 验证激活码
if check_license(license_code, email):
    print("激活成功！")
    # 继续运行应用
else:
    print("激活失败！")
    # 退出应用
    exit()
```

## 使用示例

### 生成单个激活码

```python
from license_generator import generate_license_code

# 用户提供的邮箱和机器码
email = "user@example.com"
machine_code = "USER_PROVIDED_MACHINE_CODE_32_CHARS_HEX"  # 用户提供的机器码

# 生成永不过期的激活码
license_code = generate_license_code(email, machine_code)
print(f"激活码: {license_code}")

# 生成30天后过期的激活码
license_code = generate_license_code(email, machine_code, expire_days=30)
print(f"激活码: {license_code}")
```

**注意**：机器码是用户提供的，不是使用 `get_machine_code()` 获取本机机器码。

### 批量生成激活码

```python
from license_generator import generate_license_batch, save_licenses_to_file

# 准备邮箱和机器码列表
email_machine_list = [
    ("user1@example.com", "MACHINE_CODE_1"),
    ("user2@example.com", "MACHINE_CODE_2"),
]

# 批量生成（30天过期）
results = generate_license_batch(email_machine_list, expire_days=30)

# 保存到文件
save_licenses_to_file(results, "licenses.txt")
```

### 验证激活码

```python
from license_validator import validate_license_code
from machine_fingerprint import get_machine_code

license_code = "LICENSE-XXXX-XXXX-XXXX-XXXX-XXXX"
email = "user@example.com"
machine_code = get_machine_code()

is_valid, message = validate_license_code(license_code, email, machine_code)
if is_valid:
    print("激活成功！")
else:
    print(f"激活失败: {message}")
```

## 激活码格式

激活码格式：`LICENSE-XXXX-XXXX-XXXX-XXXX-XXXX`

其中包含：
- 用户邮箱（小写，去除空格）
- 机器码（32位十六进制）
- 过期时间（可选）
- HMAC-SHA256签名（防伪造）

## 机器码说明

机器码基于以下硬件信息生成：
- **Windows**: CPU序列号、主板序列号、MAC地址
- **Linux**: CPU序列号、主板序列号、MAC地址
- **macOS**: 硬件UUID

如果无法获取硬件信息，将使用系统信息作为备选。

## 安全注意事项

1. **保护密钥**：`config.py` 中的 `SECRET_KEY` 必须保密，不要泄露
2. **密钥唯一性**：每个应用应该使用不同的密钥
3. **机器码获取**：确保 `machine_fingerprint.py` 能正确获取机器信息
4. **验证时机**：建议在应用启动时验证激活码

## 常见问题

### Q: 更换硬件后激活码失效怎么办？
A: 这是设计特性。更换硬件需要用户提供新机器码，重新生成激活码。

### Q: 如何允许用户在多台机器使用？
A: 可以为同一用户生成多个激活码，每个激活码绑定不同的机器码。

### Q: 激活码可以离线验证吗？
A: 是的，完全支持离线验证，无需连接服务器。

### Q: 如何防止激活码被复制到其他机器？
A: 激活码包含机器码信息，如果机器码不匹配，验证会失败。

## 许可证

MIT License

