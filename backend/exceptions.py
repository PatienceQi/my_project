"""
政策法规RAG问答系统 - 分层错误处理系统

定义系统中使用的自定义异常类，用于更精确的错误分类和处理
"""

class SystemError(Exception):
    """系统级错误基类"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or "SYSTEM_ERROR"
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self):
        """转换为字典格式，用于API响应"""
        return {
            "error": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class DatabaseError(SystemError):
    """数据库连接和操作错误"""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(
            message, 
            "DATABASE_ERROR",
            {"operation": operation}
        )


class LLMServiceError(SystemError):
    """大语言模型服务错误"""
    
    def __init__(self, message: str, model_name: str = None):
        super().__init__(
            message, 
            "LLM_SERVICE_ERROR",
            {"model": model_name}
        )


class ValidationError(SystemError):
    """输入验证错误"""
    
    def __init__(self, message: str, field: str = None, value: str = None):
        super().__init__(
            message, 
            "VALIDATION_ERROR",
            {"field": field, "value": value}
        )


class SessionError(SystemError):
    """会话管理错误"""
    
    def __init__(self, message: str, session_id: str = None):
        super().__init__(
            message, 
            "SESSION_ERROR",
            {"session_id": session_id}
        )


class RateLimitError(SystemError):
    """请求频率限制错误"""
    
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(
            message, 
            "RATE_LIMIT_ERROR",
            {"retry_after": retry_after}
        )


class ConfigurationError(SystemError):
    """配置错误"""
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(
            message, 
            "CONFIG_ERROR",
            {"config_key": config_key}
        )


def handle_error(error: Exception) -> dict:
    """
    统一错误处理函数
    
    Args:
        error: 异常对象
        
    Returns:
        dict: 标准化的错误响应
    """
    if isinstance(error, SystemError):
        return error.to_dict()
    elif isinstance(error, ValueError):
        return ValidationError(str(error)).to_dict()
    elif isinstance(error, ConnectionError):
        return DatabaseError("连接失败").to_dict()
    else:
        # 对于未知错误，返回通用错误信息，避免暴露系统内部细节
        return SystemError("系统内部错误，请稍后重试").to_dict()


def log_error(error: Exception, context: dict = None):
    """
    记录错误日志
    
    Args:
        error: 异常对象
        context: 错误上下文信息
    """
    import logging
    import json
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {}
    }
    
    if isinstance(error, SystemError):
        log_data.update({
            "error_code": error.error_code,
            "details": error.details
        })
    
    logger.error(json.dumps(log_data, ensure_ascii=False))