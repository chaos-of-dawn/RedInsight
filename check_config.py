#!/usr/bin/env python3
"""
检查RedInsight配置脚本
"""
import os
import sys
from config import Config

def check_reddit_config():
    """检查Reddit API配置"""
    print("🔍 检查Reddit API配置...")
    
    required_configs = {
        'REDDIT_CLIENT_ID': Config.REDDIT_CLIENT_ID,
        'REDDIT_CLIENT_SECRET': Config.REDDIT_CLIENT_SECRET,
        'REDDIT_USERNAME': Config.REDDIT_USERNAME,
        'REDDIT_PASSWORD': Config.REDDIT_PASSWORD
    }
    
    missing_configs = []
    for key, value in required_configs.items():
        if not value:
            missing_configs.append(key)
            print(f"❌ {key}: 未配置")
        else:
            # 只显示前几位，保护隐私
            masked_value = value[:4] + "*" * (len(value) - 4) if len(value) > 4 else "***"
            print(f"✅ {key}: {masked_value}")
    
    if missing_configs:
        print(f"\n⚠️ 缺少配置项: {', '.join(missing_configs)}")
        print("请通过以下方式配置:")
        print("1. 运行UI界面: python ui_app.py")
        print("2. 运行Web界面: streamlit run streamlit_app.py")
        print("3. 设置环境变量或创建.env文件")
        return False
    else:
        print("\n✅ Reddit API配置完整!")
        return True

def check_ai_config():
    """检查AI API配置"""
    print("\n🤖 检查AI API配置...")
    
    ai_configs = {
        'OPENAI_API_KEY': Config.OPENAI_API_KEY,
        'ANTHROPIC_API_KEY': Config.ANTHROPIC_API_KEY,
        'DEEPSEEK_API_KEY': Config.DEEPSEEK_API_KEY
    }
    
    configured_apis = []
    for key, value in ai_configs.items():
        if value:
            configured_apis.append(key)
            masked_value = value[:4] + "*" * (len(value) - 4) if len(value) > 4 else "***"
            print(f"✅ {key}: {masked_value}")
        else:
            print(f"⚪ {key}: 未配置")
    
    if configured_apis:
        print(f"\n✅ 已配置AI API: {', '.join(configured_apis)}")
        return True
    else:
        print("\n⚠️ 未配置任何AI API，将无法进行数据分析")
        print("建议至少配置一个AI API:")
        print("- OpenAI API Key")
        print("- Anthropic API Key") 
        print("- DeepSeek API Key")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 RedInsight 配置检查工具")
    print("=" * 60)
    
    # 检查环境变量加载
    print("📁 检查配置文件...")
    if os.path.exists('.env'):
        print("✅ 找到.env文件")
    else:
        print("⚪ 未找到.env文件，将使用系统环境变量")
    
    # 检查配置
    reddit_ok = check_reddit_config()
    ai_ok = check_ai_config()
    
    print("\n" + "=" * 60)
    print("📊 检查结果总结")
    print("=" * 60)
    
    if reddit_ok and ai_ok:
        print("🎉 配置完整！可以开始使用RedInsight")
        print("\n🚀 启动方式:")
        print("- 桌面GUI: python ui_app.py")
        print("- Web界面: streamlit run streamlit_app.py")
        print("- 启动器: python launcher.py")
    elif reddit_ok:
        print("⚠️ Reddit配置完整，但缺少AI API配置")
        print("可以抓取数据，但无法进行AI分析")
    elif ai_ok:
        print("⚠️ AI API配置完整，但缺少Reddit配置")
        print("无法抓取Reddit数据")
    else:
        print("❌ 配置不完整，请先配置必要的API密钥")
    
    print("\n💡 配置提示:")
    print("- Reddit API密钥获取: https://www.reddit.com/prefs/apps")
    print("- OpenAI API密钥获取: https://platform.openai.com/")
    print("- Anthropic API密钥获取: https://console.anthropic.com/")
    print("- DeepSeek API密钥获取: https://platform.deepseek.com/")

if __name__ == "__main__":
    main()

