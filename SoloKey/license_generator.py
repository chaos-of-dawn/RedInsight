"""
激活码生成器
用于生成包含用户邮箱和机器码的激活码
"""

import hashlib
import hmac
import base64
import json
from datetime import datetime, timedelta
from config import SECRET_KEY, LICENSE_PREFIX


def generate_license_code(email, machine_code, expire_days=None):
    """
    生成激活码
    
    参数:
        email: 用户邮箱地址
        machine_code: 机器码（32位十六进制字符串）
        expire_days: 过期天数（可选，None表示永不过期）
    
    返回:
        激活码字符串，格式：LICENSE-XXXX-XXXX-XXXX-XXXX-XXXX
    """
    # 验证输入
    if not email or '@' not in email:
        raise ValueError("无效的邮箱地址")
    
    if not machine_code or len(machine_code) != 32:
        raise ValueError("无效的机器码（应为32位十六进制字符串）")
    
    # 构建许可证数据
    license_data = {
        "email": email.lower().strip(),  # 转换为小写并去除空格
        "machine_code": machine_code.upper(),  # 转换为大写
    }
    
    # 添加过期时间（如果提供）
    if expire_days:
        expire_date = datetime.now() + timedelta(days=expire_days)
        license_data["expire_date"] = expire_date.strftime("%Y-%m-%d")
    
    # 将数据转换为JSON字符串
    data_string = json.dumps(license_data, sort_keys=True)
    
    # 使用HMAC-SHA256生成签名
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        data_string.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    # 组合数据和签名
    combined_data = data_string.encode('utf-8') + b'|' + signature
    
    # Base64编码
    encoded = base64.b64encode(combined_data).decode('utf-8')
    
    # 移除Base64中的填充字符
    encoded = encoded.rstrip('=')
    
    # 格式化为可读格式：LICENSE-XXXX-XXXX-XXXX-...
    # 将编码字符串分成多组，每组4个字符
    # 注意：保持原始大小写，因为Base64是大小写敏感的
    formatted = LICENSE_PREFIX
    for i in range(0, len(encoded), 4):
        if i + 4 <= len(encoded):
            formatted += "-" + encoded[i:i+4]
        else:
            # 最后一组可能不足4个字符
            if encoded[i:]:  # 如果有剩余字符
                formatted += "-" + encoded[i:]
    
    return formatted


def generate_license_batch(email_machine_list, expire_days=None):
    """
    批量生成激活码
    
    参数:
        email_machine_list: 列表，每个元素为 (email, machine_code) 元组
        expire_days: 过期天数（可选）
    
    返回:
        列表，每个元素为 (email, machine_code, license_code) 元组
    """
    results = []
    for email, machine_code in email_machine_list:
        try:
            license_code = generate_license_code(email, machine_code, expire_days)
            results.append((email, machine_code, license_code))
        except Exception as e:
            print(f"生成失败 - 邮箱: {email}, 错误: {str(e)}")
            results.append((email, machine_code, None))
    
    return results


def save_licenses_to_file(results, filename="licenses.txt"):
    """
    将生成的激活码保存到文件
    
    参数:
        results: generate_license_batch 返回的结果列表
        filename: 输出文件名
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("激活码列表\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for email, machine_code, license_code in results:
            if license_code:
                f.write(f"邮箱: {email}\n")
                f.write(f"机器码: {machine_code}\n")
                f.write(f"激活码: {license_code}\n")
                f.write("-" * 80 + "\n")
            else:
                f.write(f"邮箱: {email}\n")
                f.write(f"机器码: {machine_code}\n")
                f.write(f"状态: 生成失败\n")
                f.write("-" * 80 + "\n")
    
    print(f"激活码已保存到: {filename}")


if __name__ == "__main__":
    # 示例使用
    print("=" * 80)
    print("激活码生成器")
    print("=" * 80)
    
    # 获取用户输入
    email = input("\n请输入用户邮箱: ").strip()
    
    # 获取机器码（用户提供）
    print("\n请输入用户的机器码（32位十六进制字符串）")
    print("提示：用户可以在他们的机器上运行 machine_fingerprint.py 获取机器码")
    machine_code = input("机器码: ").strip().upper()
    
    # 提供选项：如果用户想参考本机机器码格式
    if not machine_code:
        reference_input = input("\n是否查看本机机器码作为格式参考？(y/n): ").strip().lower()
        if reference_input == 'y':
            from machine_fingerprint import get_machine_code
            local_machine_code = get_machine_code()
            print(f"\n本机机器码（仅供参考）: {local_machine_code}")
            print("注意：这是本机机器码，不是用户的机器码！")
            machine_code = input("\n请输入用户的机器码: ").strip().upper()
    
    if not machine_code:
        print("错误：机器码不能为空")
        exit(1)
    
    # 验证机器码格式（32位十六进制）
    if len(machine_code) != 32 or not all(c in '0123456789ABCDEF' for c in machine_code):
        print("警告：机器码格式可能不正确（应为32位十六进制字符串）")
        continue_input = input("是否继续？(y/n): ").strip().lower()
        if continue_input != 'y':
            exit(1)
    
    # 询问是否设置过期时间
    expire_input = input("\n是否设置过期时间？(y/n，默认n): ").strip().lower()
    expire_days = None
    if expire_input == 'y':
        try:
            expire_days = int(input("请输入过期天数: ").strip())
        except ValueError:
            print("无效输入，将生成永不过期的激活码")
    
    # 生成激活码
    try:
        license_code = generate_license_code(email, machine_code, expire_days)
        print("\n" + "=" * 80)
        print("激活码生成成功！")
        print("=" * 80)
        print(f"\n邮箱: {email}")
        print(f"机器码: {machine_code}")
        print(f"激活码: {license_code}")
        print("\n" + "=" * 80)
        
        # 询问是否保存到文件
        save_input = input("\n是否保存到文件？(y/n): ").strip().lower()
        if save_input == 'y':
            save_licenses_to_file([(email, machine_code, license_code)])
    except Exception as e:
        print(f"\n错误: {str(e)}")

