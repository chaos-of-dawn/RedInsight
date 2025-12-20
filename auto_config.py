"""
自动化配置管理器 - 精简版
使用数据库存储配置，简化配置管理
"""
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, time
from database import DatabaseManager

logger = logging.getLogger(__name__)

class AutoConfig:
    """自动化配置管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        初始化配置管理器
        
        Args:
            db_manager: DatabaseManager实例
        """
        self.db = db_manager
    
    def save_rpta_config(self, config: Dict[str, Any]) -> bool:
        """
        保存RPTA配置
        
        Args:
            config: 配置字典，包含：
                - weights: 权重字典
                - thresholds: 阈值字典
                - scan_time: 扫描时间
                - daily_quota: 每日配额
                - keywords: 关键词列表
        """
        try:
            session = self.db.SessionLocal()
            try:
                # 查找或创建配置
                existing = session.query(self.db.AutoInteractionConfig).filter_by(
                    config_key='rpta_config'
                ).first()
                
                config_value = json.dumps(config, default=str)
                
                if existing:
                    existing.config_value = config_value
                    existing.updated_at = datetime.utcnow()
                else:
                    new_config = self.db.AutoInteractionConfig(
                        config_key='rpta_config',
                        config_value=config_value,
                        description='RPTA评分系统配置'
                    )
                    session.add(new_config)
                
                session.commit()
                logger.info("RPTA配置已保存")
                return True
            finally:
                session.close()
        except Exception as e:
            logger.error(f"保存RPTA配置失败: {str(e)}")
            return False
    
    def get_rpta_config(self) -> Optional[Dict[str, Any]]:
        """获取RPTA配置"""
        try:
            session = self.db.SessionLocal()
            try:
                config_record = session.query(self.db.AutoInteractionConfig).filter_by(
                    config_key='rpta_config'
                ).first()
                
                if config_record and config_record.config_value:
                    return json.loads(config_record.config_value)
                return None
            finally:
                session.close()
        except Exception as e:
            logger.error(f"获取RPTA配置失败: {str(e)}")
            return None
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'weights': {'r': 0.3, 'p': 0.4, 't': 0.2, 'a': 0.1},
            'thresholds': {
                's_min': 0.5,
                'deep': 0.85,
                'standard': 0.65,
                'light': 0.50
            },
            'scan_time': {
                'start': '08:00',
                'end': '17:00'
            },
            'daily_quota': 7,
            'keywords': ['移动电源', '容量', '快充', '露营', '停电', '品牌对比']
        }
    
    def save_scheduler_config(self, config: Dict[str, Any]) -> bool:
        """保存调度器配置"""
        try:
            session = self.db.SessionLocal()
            try:
                existing = session.query(self.db.AutoInteractionConfig).filter_by(
                    config_key='scheduler_config'
                ).first()
                
                config_value = json.dumps(config, default=str)
                
                if existing:
                    existing.config_value = config_value
                    existing.updated_at = datetime.utcnow()
                else:
                    new_config = self.db.AutoInteractionConfig(
                        config_key='scheduler_config',
                        config_value=config_value,
                        description='自动化调度器配置'
                    )
                    session.add(new_config)
                
                session.commit()
                return True
            finally:
                session.close()
        except Exception as e:
            logger.error(f"保存调度器配置失败: {str(e)}")
            return False
    
    def get_scheduler_config(self) -> Optional[Dict[str, Any]]:
        """获取调度器配置"""
        try:
            session = self.db.SessionLocal()
            try:
                config_record = session.query(self.db.AutoInteractionConfig).filter_by(
                    config_key='scheduler_config'
                ).first()
                
                if config_record and config_record.config_value:
                    return json.loads(config_record.config_value)
                return None
            finally:
                session.close()
        except Exception as e:
            logger.error(f"获取调度器配置失败: {str(e)}")
            return None
    
    def get_default_scheduler_config(self) -> Dict[str, Any]:
        """获取默认调度器配置"""
        return {
            'execution_time': {
                'start': '08:00',
                'end': '20:00'
            },
            'execution_limits': {
                'deep': 3,      # 深度互动每日次数
                'standard': 5,  # 中度互动每日次数
                'light': 10     # 轻度互动每日次数
            },
            'auto_resume': True  # 是否自动延续未完成任务
        }
