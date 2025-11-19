"""
激活验证脚本（只验证，不激活）
用于一键启动脚本中验证激活状态
"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from activation import check_activation_status, verify_existing_activation
    
    # 只检查激活状态，不执行激活流程
    if not check_activation_status():
        # 未激活
        sys.exit(1)
    
    # 验证激活
    if not verify_existing_activation():
        # 验证失败
        sys.exit(1)
    
    # 验证成功
    sys.exit(0)
    
except Exception as e:
    # 静默失败，不输出错误信息（由批处理脚本处理）
    sys.exit(1)

