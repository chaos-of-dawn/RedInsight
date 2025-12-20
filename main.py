"""
RedInsight 简化版主程序
只保留必要的功能，为压缩包做准备
"""
import logging
from app_config import Config

def setup_logging():
    """设置日志系统"""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def main():
    """主函数 - 启动Streamlit Web界面"""
    print("🚀 启动 RedInsight Web界面...")
    print("📊 请使用 Streamlit Web界面进行操作")
    print("🌐 访问地址: http://localhost:8501")
    print("⏹️  按 Ctrl+C 停止服务")

if __name__ == "__main__":
    main()