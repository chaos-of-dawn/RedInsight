"""
激活码验证器
用于验证激活码是否有效，是否匹配当前机器码和用户邮箱
"""

import json
import hashlib
import hmac
import base64
from datetime import datetime
from config import SECRET_KEY, LICENSE_PREFIX


def parse_license_code(license_code):
    """
    解析激活码格式
    
    参数:
        license_code: 激活码字符串
    
    返回:
        Base64编码的原始数据（去除格式化和前缀）
    """
    # 移除前缀和连字符
    if license_code.startswith(LICENSE_PREFIX):
        license_code = license_code[len(LICENSE_PREFIX):]
    
    # 移除所有连字符和空格，但保持原始大小写（Base64是大小写敏感的）
    encoded = license_code.replace('-', '').replace(' ', '')
    
    # 移除末尾的填充字符X（如果有）
    encoded = encoded.rstrip('X')
    
    return encoded


def validate_license_code(license_code, email, machine_code):
    """
    验证激活码
    
    参数:
        license_code: 激活码字符串
        email: 用户邮箱地址
        machine_code: 当前机器码
    
    返回:
        tuple: (is_valid, message)
        is_valid: bool, 是否有效
        message: str, 验证结果消息
    """
    try:
        # 解析激活码
        encoded = parse_license_code(license_code)
        
        # 尝试恢复Base64填充
        # Base64编码的字符串长度应该是4的倍数
        padding = 4 - (len(encoded) % 4)
        if padding != 4:
            encoded += '=' * padding
        
        # Base64解码
        try:
            decoded = base64.b64decode(encoded)
        except Exception as e:
            return False, f"激活码格式错误: {str(e)}"
        
        # 分离数据和签名
        if b'|' not in decoded:
            return False, "激活码格式无效"
        
        data_bytes, signature = decoded.rsplit(b'|', 1)
        
        # 验证签名
        expected_signature = hmac.new(
            SECRET_KEY.encode('utf-8'),
            data_bytes,
            hashlib.sha256
        ).digest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return False, "激活码签名验证失败，可能是伪造的激活码"
        
        # 解析许可证数据
        try:
            license_data = json.loads(data_bytes.decode('utf-8'))
        except json.JSONDecodeError as e:
            return False, f"激活码数据解析失败: {str(e)}"
        
        # 验证邮箱
        provided_email = email.lower().strip()
        stored_email = license_data.get('email', '').lower().strip()
        if provided_email != stored_email:
            return False, f"邮箱不匹配。期望: {stored_email}, 提供: {provided_email}"
        
        # 验证机器码
        provided_machine_code = machine_code.upper()
        stored_machine_code = license_data.get('machine_code', '').upper()
        if provided_machine_code != stored_machine_code:
            return False, f"机器码不匹配。该激活码绑定到其他机器，需要重新激活"
        
        # 检查过期时间
        expire_date_str = license_data.get('expire_date')
        if expire_date_str:
            try:
                expire_date = datetime.strptime(expire_date_str, "%Y-%m-%d")
                if datetime.now() > expire_date:
                    return False, f"激活码已过期。过期日期: {expire_date_str}"
            except ValueError:
                pass  # 如果日期格式错误，忽略过期检查
        
        return True, "激活码验证成功"
        
    except Exception as e:
        return False, f"验证过程出错: {str(e)}"


def validate_from_user_input():
    """
    从用户输入验证激活码（用于测试）
    """
    print("=" * 80)
    print("激活码验证器")
    print("=" * 80)
    
    license_code = input("\n请输入激活码: ").strip()
    email = input("请输入邮箱: ").strip()
    
    print("\n正在获取当前机器码...")
    from machine_fingerprint import get_machine_code
    machine_code = get_machine_code()
    print(f"当前机器码: {machine_code}")
    
    print("\n正在验证...")
    is_valid, message = validate_license_code(license_code, email, machine_code)
    
    print("\n" + "=" * 80)
    if is_valid:
        print("✓ 验证成功！")
    else:
        print("✗ 验证失败！")
    print(f"结果: {message}")
    print("=" * 80)
    
    return is_valid


# 用于在应用中使用的便捷函数
def check_license(license_code, email):
    """
    检查激活码是否有效（在应用中使用）
    
    参数:
        license_code: 激活码
        email: 用户邮箱
    
    返回:
        bool: True表示激活码有效，False表示无效
    """
    from machine_fingerprint import get_machine_code
    machine_code = get_machine_code()
    is_valid, _ = validate_license_code(license_code, email, machine_code)
    return is_valid


if __name__ == "__main__":
    validate_from_user_input()


