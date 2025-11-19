"""
MailHook 客户端
用于向邮件中转服务发送机器码和用户邮箱
"""
import requests
from typing import Optional, Dict, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MailHookClient:
    """MailHook客户端类"""
    
    def __init__(self, server_url: str = "http://101.43.119.148:5000", app_id: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            server_url: 服务器地址（不含路径），默认: http://101.43.119.148:5000
            app_id: 应用标识（可选），如果不提供，提交时使用 "unknown"
        """
        self.server_url = server_url.rstrip('/')
        self.app_id = app_id or "unknown"
        self.api_path = "/api/submit"
        self.timeout = 10  # 请求超时时间（秒）
    
    def submit(self, machine_code: str, user_email: str, app_id: Optional[str] = None) -> Dict[str, Any]:
        """
        提交机器码和用户邮箱
        
        Args:
            machine_code: 机器码
            user_email: 用户邮箱地址
            app_id: 应用标识（可选），如果不提供，使用初始化时的app_id
            
        Returns:
            dict: 包含 success, message, timestamp 的字典
            
        Raises:
            requests.RequestException: 网络请求异常
        """
        # 使用传入的app_id或默认值
        current_app_id = app_id or self.app_id
        
        # 构建完整URL
        url = f"{self.server_url}{self.api_path}"
        
        # 构建请求数据
        data = {
            "app_id": current_app_id,
            "machine_code": str(machine_code).strip(),
            "user_email": str(user_email).strip()
        }
        
        # 请求头
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            # 隐藏服务器URL，只显示基本信息
            logger.info(f"提交数据: app_id={current_app_id}, machine_code={data['machine_code'][:10]}...")
            
            # 发送POST请求
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            
            # 检查HTTP状态码
            response.raise_for_status()
            
            # 解析JSON响应
            result = response.json()
            
            if result.get('success'):
                logger.info(f"提交成功: {result.get('message')}")
            else:
                logger.warning(f"提交失败: {result.get('message')}")
            
            return result
            
        except requests.exceptions.Timeout:
            error_msg = f"请求超时（{self.timeout}秒）"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "timestamp": None
            }
            
        except requests.exceptions.ConnectionError:
            error_msg = "无法连接到服务器"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "timestamp": None
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP错误: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "timestamp": None
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"请求异常: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "timestamp": None
            }
            
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "timestamp": None
            }


def submit(machine_code: str, user_email: str, server_url: str = "http://101.43.119.148:5000", app_id: Optional[str] = None) -> Dict[str, Any]:
    """
    便捷函数：快速提交机器码和邮箱
    
    Args:
        machine_code: 机器码
        user_email: 用户邮箱地址
        server_url: 服务器地址（可选），默认: http://101.43.119.148:5000
        app_id: 应用标识（可选）
        
    Returns:
        dict: 包含 success, message, timestamp 的字典
        
    Example:
        >>> result = submit("ABC123", "user@example.com", app_id="my_app")
        >>> if result['success']:
        ...     print("提交成功")
    """
    client = MailHookClient(server_url=server_url, app_id=app_id)
    return client.submit(machine_code, user_email)


# 使用示例
if __name__ == "__main__":
    # 示例1: 使用便捷函数
    print("示例1: 使用便捷函数")
    result = submit(
        machine_code="TEST123456",
        user_email="test@example.com",
        app_id="test_app"
    )
    print(f"结果: {result}\n")
    
    # 示例2: 使用客户端类
    print("示例2: 使用客户端类")
    client = MailHookClient(
        server_url="http://101.43.119.148:5000",
        app_id="my_app"
    )
    result = client.submit(
        machine_code="TEST789012",
        user_email="user@example.com"
    )
    print(f"结果: {result}\n")

