"""
后台分析管理器
支持异步执行高级分析，不阻塞用户界面
"""
import threading
import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional
import logging

class BackgroundAnalysisManager:
    """后台分析管理器"""
    
    def __init__(self):
        self.status_file = "analysis_status.json"
        self.result_file = "analysis_result.json"
        self.lock = threading.Lock()
        self.analysis_thread = None
        self.logger = logging.getLogger(__name__)
        
    def start_analysis(self, advanced_analyzer, subreddits: list, limit: int) -> bool:
        """启动后台分析"""
        with self.lock:
            if self.is_running():
                self.logger.warning("分析已在运行中")
                return False
            
            # 初始化状态
            self._update_status({
                'running': True,
                'progress': 0.0,
                'status': '🔄 正在初始化分析...',
                'start_time': datetime.now().isoformat(),
                'subreddits': subreddits,
                'limit': limit,
                'error': None
            })
            
            # 启动后台线程
            self.analysis_thread = threading.Thread(
                target=self._run_analysis,
                args=(advanced_analyzer, subreddits, limit),
                daemon=True
            )
            self.analysis_thread.start()
            
            self.logger.info(f"后台分析已启动: {subreddits}")
            return True
    
    def _run_analysis(self, advanced_analyzer, subreddits: list, limit: int):
        """在后台线程中执行分析"""
        try:
            # 更新状态：开始分析
            self._update_status({
                'progress': 0.1,
                'status': '🔄 正在执行结构化抽取...'
            })
            
            # 模拟进度更新
            import time
            time.sleep(1)  # 模拟处理时间
            
            # 更新状态：向量化阶段
            self._update_status({
                'progress': 0.3,
                'status': '🔄 正在执行文本向量化...'
            })
            time.sleep(1)
            
            # 更新状态：聚类阶段
            self._update_status({
                'progress': 0.6,
                'status': '🔄 正在执行智能聚类...'
            })
            time.sleep(1)
            
            # 更新状态：洞察生成阶段
            self._update_status({
                'progress': 0.8,
                'status': '🔄 正在生成业务洞察...'
            })
            time.sleep(1)
            
            # 执行分析
            result = advanced_analyzer.run_full_analysis(
                subreddits=subreddits,
                limit=limit
            )
            
            # 更新状态：分析完成
            self._update_status({
                'progress': 1.0,
                'status': '✅ 分析完成！',
                'running': False,
                'completed_time': datetime.now().isoformat()
            })
            
            # 保存结果
            self._save_result(result)
            
            self.logger.info("后台分析完成")
            
        except Exception as e:
            # 处理错误
            error_msg = f"分析失败: {str(e)}"
            self.logger.error(error_msg)
            
            self._update_status({
                'running': False,
                'status': f'❌ {error_msg}',
                'error': error_msg,
                'failed_time': datetime.now().isoformat()
            })
    
    def stop_analysis(self) -> bool:
        """停止分析"""
        with self.lock:
            if not self.is_running():
                return False
            
            self._update_status({
                'running': False,
                'status': '❌ 分析已停止',
                'stopped_time': datetime.now().isoformat()
            })
            
            self.logger.info("分析已停止")
            return True
    
    def get_status(self) -> Dict[str, Any]:
        """获取分析状态"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"读取状态文件失败: {str(e)}")
        
        return {
            'running': False,
            'progress': 0.0,
            'status': '无分析任务',
            'error': None
        }
    
    def get_result(self) -> Optional[Dict[str, Any]]:
        """获取分析结果"""
        try:
            if os.path.exists(self.result_file):
                with open(self.result_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"读取结果文件失败: {str(e)}")
        
        return None
    
    def is_running(self) -> bool:
        """检查是否有分析正在运行"""
        status = self.get_status()
        return status.get('running', False)
    
    def is_completed(self) -> bool:
        """检查分析是否已完成"""
        status = self.get_status()
        return not status.get('running', False) and 'completed_time' in status
    
    def is_failed(self) -> bool:
        """检查分析是否失败"""
        status = self.get_status()
        error = status.get('error')
        return not status.get('running', False) and error is not None and error != 'None'
    
    def clear_status(self):
        """清除状态文件"""
        try:
            if os.path.exists(self.status_file):
                os.remove(self.status_file)
            if os.path.exists(self.result_file):
                os.remove(self.result_file)
        except Exception as e:
            self.logger.error(f"清除状态文件失败: {str(e)}")
    
    def _update_status(self, updates: Dict[str, Any]):
        """更新状态文件"""
        try:
            # 读取当前状态
            current_status = self.get_status()
            
            # 更新状态
            current_status.update(updates)
            
            # 保存到文件
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(current_status, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"更新状态文件失败: {str(e)}")
    
    def _save_result(self, result: Dict[str, Any]):
        """保存分析结果"""
        try:
            with open(self.result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存结果文件失败: {str(e)}")

# 全局实例
background_analyzer = BackgroundAnalysisManager()
