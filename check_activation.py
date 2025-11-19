"""
激活检查脚本
用于在启动脚本中检查激活状态
"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from activation import check_and_activate
    
    # 执行激活检查
    result = check_and_activate()
    
    # 返回退出码：0表示成功，1表示失败
    sys.exit(0 if result else 1)
    
except Exception as e:
    print(f"[错误] 激活检查失败: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

