"""
MailHook 客户端使用示例
"""
from mailhook_client import submit, MailHookClient


def example1_simple_usage():
    """示例1: 最简单的使用方式"""
    print("=" * 50)
    print("示例1: 使用便捷函数")
    print("=" * 50)
    
    # 获取机器码（示例）
    machine_code = "ABC123XYZ789"
    
    # 获取用户输入的邮箱（示例）
    user_email = "user@example.com"
    
    # 提交到服务器
    result = submit(
        machine_code=machine_code,
        user_email=user_email,
        app_id="my_app"
    )
    
    # 检查结果
    if result['success']:
        print(f"✅ 提交成功: {result['message']}")
        print(f"   时间: {result['timestamp']}")
    else:
        print(f"❌ 提交失败: {result['message']}")


def example2_client_class():
    """示例2: 使用客户端类（适合多次调用）"""
    print("\n" + "=" * 50)
    print("示例2: 使用客户端类")
    print("=" * 50)
    
    # 创建客户端实例
    client = MailHookClient(
        server_url="http://101.43.119.148:5000",
        app_id="my_app"
    )
    
    # 多次提交
    test_cases = [
        ("MACHINE001", "user1@example.com"),
        ("MACHINE002", "user2@example.com"),
    ]
    
    for machine_code, user_email in test_cases:
        result = client.submit(machine_code, user_email)
        if result['success']:
            print(f"✅ {machine_code} - 提交成功")
        else:
            print(f"❌ {machine_code} - 提交失败: {result['message']}")


def example3_custom_server():
    """示例3: 使用自定义服务器地址"""
    print("\n" + "=" * 50)
    print("示例3: 自定义服务器地址")
    print("=" * 50)
    
    # 如果服务器地址改变了，可以这样设置
    result = submit(
        machine_code="TEST123",
        user_email="test@example.com",
        server_url="http://your-server-ip:5000",  # 自定义服务器地址
        app_id="my_app"
    )
    
    print(f"结果: {result}")


def example4_integration():
    """示例4: 集成到你的应用中"""
    print("\n" + "=" * 50)
    print("示例4: 集成示例")
    print("=" * 50)
    
    # 假设这是你的应用代码
    def get_machine_code():
        """获取机器码的函数（示例）"""
        # 这里是你获取机器码的实际代码
        import platform
        import hashlib
        machine_id = platform.node() + platform.processor()
        return hashlib.md5(machine_id.encode()).hexdigest()
    
    def get_user_email():
        """获取用户输入的邮箱（示例）"""
        # 这里是你获取用户输入的实际代码
        return input("请输入您的邮箱: ")
    
    # 主流程
    try:
        machine_code = get_machine_code()
        user_email = get_user_email()
        
        print(f"机器码: {machine_code}")
        print(f"用户邮箱: {user_email}")
        print("正在提交...")
        
        result = submit(
            machine_code=machine_code,
            user_email=user_email,
            app_id="my_python_app"
        )
        
        if result['success']:
            print("✅ 注册成功！邮件已发送到管理员邮箱。")
        else:
            print(f"❌ 注册失败: {result['message']}")
            
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        print(f"❌ 发生错误: {e}")


if __name__ == "__main__":
    # 运行所有示例
    example1_simple_usage()
    example2_client_class()
    example3_custom_server()
    # example4_integration()  # 取消注释以运行集成示例

