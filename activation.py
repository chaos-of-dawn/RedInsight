"""
RedInsight 激活模块
整合 client 和 SoloKey 功能，实现完整的激活流程
"""

import sys
import os
import json
from datetime import datetime
from typing import Tuple, Optional, Dict, Any
import io
from contextlib import redirect_stdout

# 添加 SoloKey 和 client 到路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOLOKEY_PATH = os.path.join(BASE_DIR, 'SoloKey')
CLIENT_PATH = os.path.join(BASE_DIR, 'client')

if SOLOKEY_PATH not in sys.path:
    sys.path.insert(0, SOLOKEY_PATH)
if CLIENT_PATH not in sys.path:
    sys.path.insert(0, CLIENT_PATH)

# 配置常量
ACTIVATION_FILE = "activation.json"
APP_ID = "redinsight"
SERVER_URL = "http://101.43.119.148:5000"


def get_machine_code_silently() -> Optional[str]:
    """
    静默获取机器码，不输出任何信息
    
    Returns:
        32位十六进制机器码字符串，失败返回None
    """
    try:
        # 重定向stdout以静默执行
        f = io.StringIO()
        with redirect_stdout(f):
            # 直接导入模块文件
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "machine_fingerprint",
                os.path.join(SOLOKEY_PATH, "machine_fingerprint.py")
            )
            machine_fp = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(machine_fp)
            code = machine_fp.get_machine_code()
        return code
    except Exception as e:
        print(f"[错误] 获取机器码失败: {str(e)}")
        return None


def validate_email_format(email: str) -> bool:
    """
    验证邮箱格式
    
    Args:
        email: 邮箱地址
        
    Returns:
        True表示格式正确
    """
    if not email or '@' not in email:
        return False
    parts = email.split('@')
    if len(parts) != 2:
        return False
    if not parts[0] or not parts[1] or '.' not in parts[1]:
        return False
    return True


def collect_user_email() -> Optional[str]:
    """
    收集用户输入的邮箱地址
    
    Returns:
        邮箱地址字符串，取消返回None
    """
    while True:
        try:
            email = input("\n请输入您的邮箱地址: ").strip()
            
            if not email:
                print("邮箱不能为空，请重新输入")
                continue
            
            if not validate_email_format(email):
                print("邮箱格式不正确，请重新输入（例如: user@example.com）")
                continue
            
            # 确认邮箱
            confirm = input(f"确认邮箱地址: {email} [Y/N]: ").strip().upper()
            if confirm == 'Y':
                return email
            elif confirm == 'N':
                continue
            else:
                print("请输入 Y 或 N")
        except KeyboardInterrupt:
            print("\n\n操作已取消")
            return None
        except Exception as e:
            print(f"输入错误: {str(e)}")
            continue


def validate_activation_code_format(code: str) -> bool:
    """
    验证激活码格式
    
    Args:
        code: 激活码字符串
        
    Returns:
        True表示格式正确
    """
    if not code:
        return False
    
    code = code.strip()
    
    # 检查是否以LICENSE开头（不区分大小写检查前缀）
    if not code.upper().startswith('LICENSE-'):
        return False
    
    # 检查基本格式：LICENSE-XXXX-XXXX-XXXX-...
    parts = code.split('-')
    if len(parts) < 2:  # 至少要有LICENSE和一组数据
        return False
    
    # 检查前缀
    if parts[0].upper() != 'LICENSE':
        return False
    
    # 检查数据组：每组应该是1-4个字符（最后一组可能不足4个）
    for i in range(1, len(parts)):
        if len(parts[i]) == 0 or len(parts[i]) > 4:
            return False
    
    return True


def collect_activation_code() -> Optional[str]:
    """
    收集用户输入的激活码
    
    Returns:
        激活码字符串，取消返回None
    """
    while True:
        try:
            code = input("\n请输入激活码: ").strip()
            
            if not code:
                print("激活码不能为空，请重新输入")
                continue
            
            # 自动处理常见输入错误（移除空格，但保持原始大小写，因为Base64是大小写敏感的）
            code = code.replace(' ', '')
            
            if not validate_activation_code_format(code):
                print("激活码格式不正确")
                print("格式应为: LICENSE-XXXX-XXXX-XXXX-... (每组4个字符，可能有多个组)")
                retry = input("是否重新输入？(y/n): ").strip().lower()
                if retry != 'y':
                    return None
                continue
            
            return code
            
        except KeyboardInterrupt:
            print("\n\n操作已取消")
            return None
        except Exception as e:
            print(f"输入错误: {str(e)}")
            continue


def send_registration_to_server(machine_code: str, email: str) -> Tuple[bool, str]:
    """
    发送机器码和邮箱到服务器
    
    Args:
        machine_code: 机器码
        email: 用户邮箱
        
    Returns:
        (success, message) 元组
    """
    try:
        from client.mailhook_client import submit
        
        # 静默发送，不显示服务器地址
        result = submit(
            machine_code=machine_code,
            user_email=email,
            server_url=SERVER_URL,
            app_id=APP_ID
        )
        
        if result.get('success'):
            return True, result.get('message', '发送成功')
        else:
            return False, result.get('message', '发送失败')
            
    except ImportError as e:
        return False, f"无法导入client模块: {str(e)}"
    except Exception as e:
        return False, f"发送失败: {str(e)}"


def validate_activation_code(license_code: str, email: str, machine_code: str) -> Tuple[bool, str]:
    """
    验证激活码
    
    Args:
        license_code: 激活码
        email: 用户邮箱
        machine_code: 机器码
        
    Returns:
        (is_valid, message) 元组
    """
    try:
        # 确保SoloKey路径在sys.path的最前面，以便config模块能被正确导入
        if SOLOKEY_PATH not in sys.path:
            sys.path.insert(0, SOLOKEY_PATH)
        elif sys.path[0] != SOLOKEY_PATH:
            # 如果SoloKey路径不在最前面，移到最前面
            sys.path.remove(SOLOKEY_PATH)
            sys.path.insert(0, SOLOKEY_PATH)
        
        # 先导入config模块，确保它被加载并添加到sys.modules
        try:
            # 如果config已经在sys.modules中，先删除它以确保重新加载
            if 'config' in sys.modules:
                del sys.modules['config']
            import config
            # 验证SECRET_KEY是否存在（即使使用默认值也允许，只要与生成激活码时一致即可）
            if not hasattr(config, 'SECRET_KEY'):
                return False, "错误：config模块中未找到SECRET_KEY，请检查SoloKey/config.py"
        except ImportError as config_import_error:
            # 如果直接导入失败，使用importlib加载
            import importlib.util
            config_spec = importlib.util.spec_from_file_location(
                "config",
                os.path.join(SOLOKEY_PATH, "config.py")
            )
            if config_spec is None or config_spec.loader is None:
                return False, f"无法加载config模块：无法创建spec"
            config_module = importlib.util.module_from_spec(config_spec)
            config_spec.loader.exec_module(config_module)
            # 将config添加到sys.modules，以便license_validator可以导入
            sys.modules['config'] = config_module
            # 验证SECRET_KEY是否存在（即使使用默认值也允许，只要与生成激活码时一致即可）
            if not hasattr(config_module, 'SECRET_KEY'):
                return False, "错误：config模块中未找到SECRET_KEY，请检查SoloKey/config.py"
        except Exception as config_e:
            return False, f"无法加载config模块: {str(config_e)}"
        
        # 现在导入license_validator，它应该能够找到config模块
        try:
            from license_validator import validate_license_code
            is_valid, message = validate_license_code(license_code, email, machine_code)
        except ImportError:
            # 如果直接导入失败，使用importlib
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "license_validator",
                os.path.join(SOLOKEY_PATH, "license_validator.py")
            )
            if spec is None or spec.loader is None:
                return False, f"无法加载license_validator模块：无法创建spec"
            license_validator = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(license_validator)
            is_valid, message = license_validator.validate_license_code(license_code, email, machine_code)
        
        # 如果验证失败，提供更详细的错误信息
        if not is_valid and "激活码格式无效" in message:
            # 尝试解析激活码看看问题在哪里
            try:
                from license_validator import parse_license_code
                parsed = parse_license_code(license_code)
                import base64
                padding = 4 - (len(parsed) % 4)
                if padding != 4:
                    parsed += '=' * padding
                decoded = base64.b64decode(parsed)
                if b'|' not in decoded:
                    return False, f"激活码格式无效：Base64解码成功但未找到数据分隔符。\n" \
                                 f"这可能是因为：\n" \
                                 f"1. 激活码生成时使用的SECRET_KEY与验证时不同\n" \
                                 f"2. 激活码本身有问题\n" \
                                 f"请确认SoloKey/config.py中的SECRET_KEY与生成激活码的脚本完全一致"
            except Exception as debug_e:
                pass  # 如果调试失败，返回原始错误信息
        
        return is_valid, message
        
    except ImportError as e:
        return False, f"无法导入SoloKey模块: {str(e)}"
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return False, f"验证过程出错: {str(e)}\n详细信息: {error_detail}"


def save_activation_info(machine_code: str, email: str, activation_code: str) -> bool:
    """
    保存激活信息到本地文件
    
    Args:
        machine_code: 机器码
        email: 用户邮箱
        activation_code: 激活码
        
    Returns:
        True表示保存成功
    """
    try:
        activation_data = {
            "machine_code": machine_code,
            "email": email,
            "activation_code": activation_code,
            "activated_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        with open(ACTIVATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(activation_data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"[错误] 保存激活信息失败: {str(e)}")
        return False


def load_activation_info() -> Optional[Dict[str, Any]]:
    """
    加载激活信息
    
    Returns:
        激活信息字典，文件不存在或损坏返回None
    """
    if not os.path.exists(ACTIVATION_FILE):
        return None
    
    try:
        with open(ACTIVATION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 验证必要字段
        required_fields = ['machine_code', 'email', 'activation_code']
        if not all(field in data for field in required_fields):
            return None
        
        return data
    except Exception as e:
        print(f"[警告] 加载激活信息失败: {str(e)}")
        return None


def check_activation_status() -> bool:
    """
    检查是否已激活
    
    Returns:
        True表示已激活
    """
    return load_activation_info() is not None


def verify_existing_activation() -> bool:
    """
    验证已保存的激活信息
    
    Returns:
        True表示验证通过
    """
    activation_info = load_activation_info()
    if not activation_info:
        return False
    
    # 获取当前机器码
    current_machine_code = get_machine_code_silently()
    if not current_machine_code:
        print("[错误] 无法获取当前机器码")
        return False
    
    # 检查机器码是否匹配
    saved_machine_code = activation_info.get('machine_code', '')
    if current_machine_code != saved_machine_code:
        print("\n[警告] 检测到机器码变化")
        print("可能的原因：硬件更换或系统重装")
        print("需要重新激活")
        return False
    
    # 验证激活码
    email = activation_info.get('email', '')
    activation_code = activation_info.get('activation_code', '')
    
    is_valid, message = validate_activation_code(activation_code, email, current_machine_code)
    
    if not is_valid:
        print(f"\n[错误] 激活码验证失败: {message}")
        return False
    
    return True


def perform_activation() -> bool:
    """
    执行完整激活流程
    
    Returns:
        True表示激活成功
    """
    print("\n" + "="*60)
    print("RedInsight 激活流程")
    print("="*60)
    
    # 步骤1: 获取机器码（静默执行，不显示提示）
    machine_code = get_machine_code_silently()
    if not machine_code:
        print("[错误] 无法获取机器码，激活失败")
        return False
    
    # 步骤1: 收集邮箱
    print("\n[步骤 1/3] 请输入您的邮箱地址")
    email = collect_user_email()
    if not email:
        print("[错误] 未输入邮箱，激活取消")
        return False
    
    # 步骤2: 发送到服务器（静默执行，不显示过程）
    send_success, send_message = send_registration_to_server(machine_code, email)
    
    if not send_success:
        # 静默重试一次
        send_success, send_message = send_registration_to_server(machine_code, email)
        if not send_success:
            print(f"[错误] 发送失败: {send_message}")
            print("请检查网络连接后重试，或联系管理员")
            return False
    
    # 发送成功，静默处理，不显示发送过程
    
    # 显示提示信息
    print("\n" + "-"*60)
    print("下一步操作：")
    print("1. 请通过微信联系项目管理员")
    print("2. 提供以下信息给管理员：")
    print(f"   - 机器码: {machine_code}")
    print(f"   - 邮箱: {email}")
    print("3. 管理员将为您生成激活码")
    print("4. 收到激活码后，请在下方输入")
    print("-"*60)
    
    # 步骤3: 收集并验证激活码
    print("\n[步骤 3/3] 请输入激活码")
    activation_code = collect_activation_code()
    if not activation_code:
        print("[错误] 未输入激活码，激活取消")
        return False
    
    # 验证激活码
    print("\n正在验证激活码...")
    is_valid, message = validate_activation_code(activation_code, email, machine_code)
    
    if not is_valid:
        print(f"\n✗ 激活码验证失败")
        print(f"原因: {message}")
        print("\n请确认：")
        print("1. 激活码是否正确（注意大小写和连字符）")
        print("2. 邮箱是否与提供给管理员的一致")
        print("3. 是否在正确的机器上激活")
        print("\n提示：激活码格式为 LICENSE-XXXX-XXXX-XXXX-... (可能有多个组)")
        
        retry = input("\n是否重新输入激活码？(y/n): ").strip().lower()
        if retry == 'y':
            activation_code = collect_activation_code()
            if activation_code:
                is_valid, message = validate_activation_code(activation_code, email, machine_code)
                if not is_valid:
                    print(f"\n验证仍然失败: {message}")
                    return False
            else:
                return False
        else:
            return False
    
    # 保存激活信息
    print(f"\n✓ {message}")
    print("\n正在保存激活信息...")
    if not save_activation_info(machine_code, email, activation_code):
        print("[错误] 保存激活信息失败")
        return False
    
    print("✓ 激活信息已保存")
    print("\n" + "="*60)
    print("激活成功！")
    print("="*60)
    
    return True


def check_and_activate() -> bool:
    """
    主入口函数：检查激活状态并处理
    
    Returns:
        True表示已激活或激活成功，False表示激活失败
    """
    try:
        # 检查是否已激活
        if check_activation_status():
            # 验证现有激活
            if verify_existing_activation():
                # 验证成功，静默返回（在批处理脚本中不显示，避免干扰）
                return True
            else:
                # 验证失败，需要重新激活（直接执行，不询问）
                # 删除旧激活信息
                if os.path.exists(ACTIVATION_FILE):
                    try:
                        os.remove(ACTIVATION_FILE)
                    except:
                        pass
                # 直接执行激活流程
                return perform_activation()
        else:
            # 未激活，执行激活流程
            return perform_activation()
            
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        return False
    except Exception as e:
        print(f"\n[错误] 激活检查过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 直接执行激活流程，不询问
    check_and_activate()

