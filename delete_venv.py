#!/usr/bin/env python3
"""
删除虚拟环境的脚本
"""
import os
import shutil
import stat

def remove_readonly(func, path, exc):
    """移除只读属性"""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def delete_venv():
    """删除虚拟环境"""
    venv_path = "venv"
    
    if os.path.exists(venv_path):
        try:
            print(f"正在删除虚拟环境: {venv_path}")
            shutil.rmtree(venv_path, onerror=remove_readonly)
            print("✅ 虚拟环境删除成功")
        except Exception as e:
            print(f"❌ 删除失败: {e}")
            print("请尝试以管理员权限运行此脚本")
    else:
        print("虚拟环境不存在")

if __name__ == "__main__":
    delete_venv()


