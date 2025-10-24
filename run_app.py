"""
RedInsight 启动脚本
用于压缩包部署，一键启动Streamlit Web界面
"""
import subprocess
import sys
import os


def main():
    """主函数"""
    print("=" * 60)
    print("🔍 RedInsight - Reddit数据分析工具")
    print("=" * 60)
    print()
    print("🚀 正在启动应用，请稍候...")
    print("📊 Streamlit会自动打开浏览器")
    print("⏹️  关闭此窗口将停止应用")
    print()
    
    # 设置工作目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # 启动Streamlit (Streamlit会自动打开浏览器)
        process = subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py"
        ])
        
    except KeyboardInterrupt:
        print("\n⏹️ 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {str(e)}")
        input("按回车键退出...")

if __name__ == "__main__":
    main()
