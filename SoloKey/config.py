"""
配置文件
存储激活码生成和验证的密钥
"""

# 激活码加密密钥（请修改为你的密钥，建议使用随机生成的字符串）
# 生成密钥建议：使用 secrets.token_urlsafe(32) 生成
SECRET_KEY = "your-secret-key-here-change-this-to-a-random-string"

# 激活码格式配置
LICENSE_PREFIX = "LICENSE"  # 激活码前缀
LICENSE_FORMAT = "XXXX-XXXX-XXXX-XXXX-XXXX"  # 激活码格式


