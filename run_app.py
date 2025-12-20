"""
RedInsight 启动脚本
用于压缩包部署，一键启动Streamlit Web界面
支持自动恢复，遇到错误自动重启，无需手动操作
"""
import subprocess
import sys
import os
import time

def check_and_activate():
    """检查激活状态，如果未激活则自动启动激活流程"""
    try:
        # 添加当前目录到路径
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # 检查激活文件是否存在
        activation_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "activation.json")
        if not os.path.exists(activation_file):
            print("\n" + "=" * 60)
            print("⚠️  激活要求")
            print("=" * 60)
            print()
            print("应用需要激活后才能使用。")
            print("正在启动激活流程...")
            print()
            print("=" * 60)
            
            # 自动运行激活脚本
            try:
                from activation import check_and_activate as activate
                if activate():
                    print("\n✅ 激活成功，继续启动应用...")
                    print()
                    return True
                else:
                    print("\n❌ 激活失败或取消")
                    return False
            except Exception as e:
                print(f"\n❌ 激活过程出错: {str(e)}")
                return False
        
        # 验证激活状态
        try:
            from activation import check_activation_status, verify_existing_activation
            if not check_activation_status():
                print("\n⚠️  未激活，正在启动激活流程...")
                try:
                    from activation import check_and_activate as activate
                    if activate():
                        print("\n✅ 激活成功，继续启动应用...")
                        print()
                        return True
                    else:
                        print("\n❌ 激活失败或取消")
                        return False
                except Exception as e:
                    print(f"\n❌ 激活过程出错: {str(e)}")
                    return False
            
            if not verify_existing_activation():
                print("\n⚠️  激活验证失败，需要重新激活...")
                # 删除旧的激活文件
                try:
                    if os.path.exists(activation_file):
                        os.remove(activation_file)
                except:
                    pass
                # 启动激活流程
                try:
                    from activation import check_and_activate as activate
                    if activate():
                        print("\n✅ 重新激活成功，继续启动应用...")
                        print()
                        return True
                    else:
                        print("\n❌ 激活失败或取消")
                        return False
                except Exception as e:
                    print(f"\n❌ 激活过程出错: {str(e)}")
                    return False
            
            return True
        except Exception as e:
            print(f"\n⚠️  激活检查失败: {str(e)}")
            print("正在尝试启动激活流程...")
            try:
                from activation import check_and_activate as activate
                if activate():
                    print("\n✅ 激活成功，继续启动应用...")
                    print()
                    return True
                else:
                    return False
            except:
                return False
            
    except Exception as e:
        print(f"\n⚠️  激活检查出错: {str(e)}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 RedInsight - Reddit自动化、数据分析工具")
    print("=" * 60)
    print()
    
    # 设置工作目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 检查激活状态，如果未激活则自动启动激活流程
    print("🔐 检查激活状态...")
    if not check_and_activate():
        print("\n❌ 激活失败，应用无法启动")
        input("\n按回车键退出...")
        sys.exit(1)
    
    print("✅ 激活验证通过")
    print()
    print("🚀 正在启动应用，请稍候...")
    print("📊 Streamlit会自动打开浏览器")
    print("💡 提示：遇到错误会自动重启，无需手动操作")
    print("⏹️  关闭此窗口将停止应用")
    print()
    
    max_restarts = 10  # 最大重启次数
    restart_count = 0
    
    while restart_count < max_restarts:
        try:
            # 启动Streamlit
            process = subprocess.run([
                sys.executable, "-m", "streamlit", "run", "streamlit_app.py"
            ])
            
            # 如果正常退出（退出码为0）
            if process.returncode == 0:
                print("\n✅ 应用正常退出")
                break
            else:
                # 非正常退出，尝试重启
                restart_count += 1
                if restart_count < max_restarts:
                    print(f"\n⚠️  应用退出（代码: {process.returncode}）")
                    print(f"🔄 自动重启中... ({restart_count}/{max_restarts})")
                    print("💡 提示：按 Ctrl+C 可停止自动重启")
                    time.sleep(2)  # 等待2秒后重启
                else:
                    print(f"\n❌ 达到最大重启次数 ({max_restarts})")
                    input("按回车键退出...")
                    break
        
        except KeyboardInterrupt:
            print("\n⏹️  收到停止信号，正在退出...")
            break
        except Exception as e:
            restart_count += 1
            if restart_count < max_restarts:
                print(f"\n❌ 发生错误: {str(e)}")
                print(f"🔄 自动重启中... ({restart_count}/{max_restarts})")
                print("💡 提示：按 Ctrl+C 可停止自动重启")
                time.sleep(2)
            else:
                print(f"\n❌ 达到最大重启次数 ({max_restarts})")
                print(f"错误信息: {str(e)}")
                input("按回车键退出...")
                break

if __name__ == "__main__":
    main()
