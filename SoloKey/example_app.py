"""
示例应用：展示如何在应用中使用激活码验证系统
"""

from license_validator import check_license, validate_license_code
from machine_fingerprint import get_machine_code


def main():
    """示例应用主函数"""
    print("=" * 80)
    print("欢迎使用示例应用")
    print("=" * 80)
    
    # 检查激活码
    print("\n请激活您的应用：")
    license_code = input("请输入激活码: ").strip()
    email = input("请输入邮箱: ").strip()
    
    # 获取当前机器码
    machine_code = get_machine_code()
    
    # 验证激活码
    print("\n正在验证激活码...")
    is_valid, message = validate_license_code(license_code, email, machine_code)
    
    if is_valid:
        print("\n" + "=" * 80)
        print("✓ 激活成功！")
        print("=" * 80)
        print(f"\n邮箱: {email}")
        print(f"机器码: {machine_code}")
        print(f"\n应用已激活，可以正常使用。")
        
        # 这里可以保存激活信息到文件或配置中
        # 例如：保存到 config.json 或注册表
        
        # 继续运行应用
        run_application()
    else:
        print("\n" + "=" * 80)
        print("✗ 激活失败！")
        print("=" * 80)
        print(f"\n错误信息: {message}")
        print("\n请检查：")
        print("1. 激活码是否正确")
        print("2. 邮箱是否匹配")
        print("3. 是否在正确的机器上激活")
        print("\n如需更换硬件，请联系开发者重新生成激活码。")
        exit(1)


def run_application():
    """运行应用主逻辑（激活成功后的代码）"""
    print("\n" + "=" * 80)
    print("应用功能演示")
    print("=" * 80)
    print("\n这是应用的主要功能区域...")
    print("激活码验证成功，应用可以正常运行。")
    
    # 在实际应用中，这里应该是你的应用主逻辑
    # 例如：
    # - 启动GUI界面
    # - 运行主程序循环
    # - 加载应用功能模块等


# 简化版验证（使用便捷函数）
def simple_check():
    """使用便捷函数进行验证"""
    license_code = input("请输入激活码: ").strip()
    email = input("请输入邮箱: ").strip()
    
    if check_license(license_code, email):
        print("激活成功！")
        return True
    else:
        print("激活失败！")
        return False


if __name__ == "__main__":
    main()


