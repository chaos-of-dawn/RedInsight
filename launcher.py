"""
RedInsight 启动器
提供选择不同UI界面的选项
"""
import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os

class RedInsightLauncher:
    """RedInsight启动器"""
    
    def __init__(self):
        """初始化启动器"""
        self.root = tk.Tk()
        self.root.title("RedInsight 启动器")
        self.root.geometry("500x400")
        self.root.configure(bg='#f0f0f0')
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置用户界面"""
        # 标题
        title_frame = tk.Frame(self.root, bg='#f0f0f0')
        title_frame.pack(pady=20)
        
        title_label = tk.Label(
            title_frame, 
            text="🔍 RedInsight", 
            font=("Arial", 24, "bold"),
            fg='#FF4500',
            bg='#f0f0f0'
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="Reddit数据分析工具",
            font=("Arial", 12),
            fg='#666666',
            bg='#f0f0f0'
        )
        subtitle_label.pack()
        
        # 界面选择
        choice_frame = tk.Frame(self.root, bg='#f0f0f0')
        choice_frame.pack(pady=30, padx=50, fill='x')
        
        tk.Label(
            choice_frame,
            text="选择界面类型：",
            font=("Arial", 14, "bold"),
            bg='#f0f0f0'
        ).pack(pady=(0, 20))
        
        # 桌面GUI按钮
        desktop_btn = tk.Button(
            choice_frame,
            text="🖥️  桌面GUI界面 (Tkinter)",
            font=("Arial", 12),
            bg='#4CAF50',
            fg='white',
            height=2,
            command=self.launch_desktop_gui
        )
        desktop_btn.pack(fill='x', pady=5)
        
        # Web界面按钮
        web_btn = tk.Button(
            choice_frame,
            text="🌐 Web界面 (Streamlit)",
            font=("Arial", 12),
            bg='#2196F3',
            fg='white',
            height=2,
            command=self.launch_web_gui
        )
        web_btn.pack(fill='x', pady=5)
        
        # 命令行界面按钮
        cli_btn = tk.Button(
            choice_frame,
            text="💻 命令行界面",
            font=("Arial", 12),
            bg='#FF9800',
            fg='white',
            height=2,
            command=self.launch_cli
        )
        cli_btn.pack(fill='x', pady=5)
        
        # 帮助按钮
        help_btn = tk.Button(
            choice_frame,
            text="❓ 帮助",
            font=("Arial", 12),
            bg='#9E9E9E',
            fg='white',
            height=2,
            command=self.show_help
        )
        help_btn.pack(fill='x', pady=5)
        
        # 退出按钮
        exit_btn = tk.Button(
            choice_frame,
            text="❌ 退出",
            font=("Arial", 12),
            bg='#F44336',
            fg='white',
            height=2,
            command=self.root.quit
        )
        exit_btn.pack(fill='x', pady=5)
        
        # 状态信息
        status_frame = tk.Frame(self.root, bg='#f0f0f0')
        status_frame.pack(pady=20)
        
        self.status_label = tk.Label(
            status_frame,
            text="请选择要使用的界面类型",
            font=("Arial", 10),
            fg='#666666',
            bg='#f0f0f0'
        )
        self.status_label.pack()
    
    def launch_desktop_gui(self):
        """启动桌面GUI界面"""
        try:
            self.status_label.config(text="正在启动桌面GUI界面...")
            self.root.update()
            
            # 检查ui_app.py是否存在
            if not os.path.exists('ui_app.py'):
                messagebox.showerror("错误", "找不到 ui_app.py 文件")
                return
            
            # 检查依赖包
            try:
                import praw
                import sqlalchemy
                import streamlit
            except ImportError as e:
                messagebox.showerror("缺少依赖", f"缺少必要的依赖包: {str(e)}\n请运行: pip install -r requirements.txt")
                return
            
            # 启动桌面GUI
            subprocess.Popen([sys.executable, 'ui_app.py'])
            self.status_label.config(text="桌面GUI界面已启动")
            
        except Exception as e:
            messagebox.showerror("启动失败", f"启动桌面GUI失败: {str(e)}")
            self.status_label.config(text="启动失败")
    
    def launch_web_gui(self):
        """启动Web界面"""
        try:
            self.status_label.config(text="正在启动Web界面...")
            self.root.update()
            
            # 检查streamlit_app.py是否存在
            if not os.path.exists('streamlit_app.py'):
                messagebox.showerror("错误", "找不到 streamlit_app.py 文件")
                return
            
            # 检查streamlit是否安装
            try:
                import streamlit
            except ImportError:
                messagebox.showerror(
                    "缺少依赖", 
                    "Streamlit未安装。请运行：\npip install streamlit"
                )
                return
            
            # 启动Streamlit应用
            subprocess.Popen([
                sys.executable, '-m', 'streamlit', 'run', 'streamlit_app.py'
            ])
            self.status_label.config(text="Web界面已启动，请在浏览器中打开")
            
        except Exception as e:
            messagebox.showerror("启动失败", f"启动Web界面失败: {str(e)}")
            self.status_label.config(text="启动失败")
    
    def launch_cli(self):
        """启动命令行界面"""
        try:
            self.status_label.config(text="正在启动命令行界面...")
            self.root.update()
            
            # 检查main.py是否存在
            if not os.path.exists('main.py'):
                messagebox.showerror("错误", "找不到 main.py 文件")
                return
            
            # 启动命令行界面
            subprocess.Popen([sys.executable, 'main.py', '--help'])
            self.status_label.config(text="命令行界面已启动")
            
        except Exception as e:
            messagebox.showerror("启动失败", f"启动命令行界面失败: {str(e)}")
            self.status_label.config(text="启动失败")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
🔍 RedInsight - Reddit数据分析工具

界面说明：

🖥️ 桌面GUI界面 (Tkinter)
- 传统的桌面应用程序界面
- 适合本地使用，功能完整
- 需要安装tkinter（通常随Python自带）

🌐 Web界面 (Streamlit)
- 现代化的Web应用程序界面
- 支持多标签页，界面美观
- 需要安装streamlit：pip install streamlit

💻 命令行界面
- 纯命令行操作
- 适合脚本化和自动化
- 支持批处理和定时任务

使用步骤：
1. 选择界面类型
2. 配置API密钥（Reddit API和AI API）
3. 设置抓取参数
4. 开始数据抓取和分析
5. 查看分析结果

注意事项：
- 首次使用需要配置API密钥
- 请遵守Reddit使用条款
- 注意API调用限制
        """
        
        # 创建帮助窗口
        help_window = tk.Toplevel(self.root)
        help_window.title("帮助")
        help_window.geometry("600x500")
        help_window.configure(bg='#f0f0f0')
        
        # 添加滚动文本框
        text_frame = tk.Frame(help_window, bg='#f0f0f0')
        text_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        text_widget = tk.Text(
            text_frame,
            wrap='word',
            font=("Arial", 10),
            bg='white',
            fg='black'
        )
        text_widget.pack(fill='both', expand=True)
        
        # 插入帮助文本
        text_widget.insert('1.0', help_text)
        text_widget.config(state='disabled')
        
        # 添加关闭按钮
        close_btn = tk.Button(
            help_window,
            text="关闭",
            command=help_window.destroy,
            bg='#2196F3',
            fg='white',
            font=("Arial", 10)
        )
        close_btn.pack(pady=10)
    
    def run(self):
        """运行启动器"""
        self.root.mainloop()

def main():
    """主函数"""
    launcher = RedInsightLauncher()
    launcher.run()

if __name__ == "__main__":
    main()
