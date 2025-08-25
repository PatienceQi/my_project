"""
政策法规RAG问答系统 - 输入验证和安全检查模块

提供输入内容验证、清理和安全检查功能
"""

import re
import html
from typing import Tuple, Optional, Dict, Any
from backend.exceptions import ValidationError


class InputValidator:
    """输入验证器"""
    
    # 配置常量
    MAX_QUESTION_LENGTH = 1000
    MIN_QUESTION_LENGTH = 1
    
    # 危险模式匹配
    DANGEROUS_PATTERNS = [
        r'<script.*?>.*?</script>',  # 脚本标签
        r'javascript:',              # JavaScript协议
        r'on\w+\s*=',               # 事件处理器
        r'data:.*?base64',          # Base64数据
        r'vbscript:',               # VBScript协议
        r'expression\s*\(',         # CSS表达式
    ]
    
    # 非法字符模式
    ILLEGAL_CHARS_PATTERN = r'[<>\'";&\\]'
    
    # SQL注入模式
    SQL_INJECTION_PATTERNS = [
        r'union\s+select',
        r'insert\s+into',
        r'delete\s+from', 
        r'drop\s+table',
        r'update\s+set',
        r'exec\s*\(',
        r'script\s*\(',
    ]
    
    @classmethod
    def validate_question(cls, question: str) -> Tuple[bool, Optional[str], str]:
        """
        验证用户问题输入
        
        Args:
            question: 用户输入的问题
            
        Returns:
            Tuple[bool, Optional[str], str]: (是否有效, 错误信息, 清理后的内容)
        """
        if not question:
            return False, "问题不能为空", ""
        
        # 去除首尾空白字符
        question = question.strip()
        
        # 长度检查
        if len(question) < cls.MIN_QUESTION_LENGTH:
            return False, "问题长度不能少于1个字符", ""
        
        if len(question) > cls.MAX_QUESTION_LENGTH:
            return False, f"问题长度不能超过{cls.MAX_QUESTION_LENGTH}个字符", ""
        
        # 危险内容检查
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, question, re.IGNORECASE):
                return False, "问题包含不安全的内容", ""
        
        # SQL注入检查
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, question, re.IGNORECASE):
                return False, "问题包含非法的数据库操作指令", ""
        
        # 非法字符检查
        if re.search(cls.ILLEGAL_CHARS_PATTERN, question):
            return False, "问题包含非法字符，请使用中英文、数字和常用标点符号", ""
        
        # 清理和转义
        cleaned_question = cls.sanitize_input(question)
        
        return True, None, cleaned_question
    
    @classmethod
    def sanitize_input(cls, text: str) -> str:
        """
        清理和转义输入内容
        
        Args:
            text: 原始输入文本
            
        Returns:
            str: 清理后的文本
        """
        # HTML实体转义
        text = html.escape(text)
        
        # 移除控制字符
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # 标准化空白字符
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    @classmethod
    def validate_session_id(cls, session_id: str) -> Tuple[bool, Optional[str]]:
        """
        验证会话ID格式
        
        Args:
            session_id: 会话ID
            
        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误信息)
        """
        if not session_id:
            return False, "会话ID不能为空"
        
        # UUID格式检查 (36字符，包含4个连字符)
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, session_id, re.IGNORECASE):
            return False, "会话ID格式无效"
        
        return True, None


class SecurityChecker:
    """安全检查器"""
    
    @staticmethod
    def check_content_safety(content: str) -> Dict[str, Any]:
        """
        检查内容安全性
        
        Args:
            content: 待检查的内容
            
        Returns:
            Dict[str, Any]: 安全检查结果
        """
        result = {
            "is_safe": True,
            "risk_level": "low",
            "issues": []
        }
        
        # 检查长度异常
        if len(content) > 10000:
            result["issues"].append("内容长度异常")
            result["risk_level"] = "medium"
        
        # 检查重复字符
        if re.search(r'(.)\1{50,}', content):
            result["issues"].append("包含大量重复字符")
            result["risk_level"] = "medium"
        
        # 检查URL
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, content)
        if len(urls) > 5:
            result["issues"].append("包含过多URL链接")
            result["risk_level"] = "high"
        
        # 检查可疑关键词
        suspicious_keywords = ['hack', 'crack', 'exploit', 'vulnerability', 'bypass']
        for keyword in suspicious_keywords:
            if keyword.lower() in content.lower():
                result["issues"].append(f"包含可疑关键词: {keyword}")
                result["risk_level"] = "high"
        
        # 如果有高风险问题，标记为不安全
        if result["risk_level"] == "high":
            result["is_safe"] = False
        
        return result
    
    @staticmethod
    def validate_api_request(request_data: Dict[str, Any]) -> None:
        """
        验证API请求数据
        
        Args:
            request_data: 请求数据字典
            
        Raises:
            ValidationError: 当请求数据无效时
        """
        # 检查请求大小
        import json
        request_size = len(json.dumps(request_data))
        if request_size > 10 * 1024:  # 10KB
            raise ValidationError("请求数据过大", "request_size", str(request_size))
        
        # 检查必需字段
        if 'question' not in request_data:
            raise ValidationError("缺少必需字段", "question", None)
        
        # 验证问题内容
        question = request_data.get('question', '')
        is_valid, error_msg, _ = InputValidator.validate_question(question)
        if not is_valid:
            raise ValidationError(error_msg, "question", question)
        
        # 验证会话ID（如果提供）
        session_id = request_data.get('session_id')
        if session_id:
            is_valid, error_msg = InputValidator.validate_session_id(session_id)
            if not is_valid:
                raise ValidationError(error_msg, "session_id", session_id)


def create_validation_decorator():
    """
    创建输入验证装饰器
    """
    from functools import wraps
    
    def validate_input(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 假设第一个参数是Flask的request对象或包含数据的对象
            if args and hasattr(args[0], 'get_json'):
                try:
                    data = args[0].get_json()
                    SecurityChecker.validate_api_request(data)
                except ValidationError:
                    raise
                except Exception as e:
                    raise ValidationError(f"请求数据格式错误: {str(e)}", "request_format", None)
            
            return func(*args, **kwargs)
        return wrapper
    
    return validate_input


# 导出主要组件
__all__ = [
    'InputValidator',
    'SecurityChecker', 
    'create_validation_decorator',
    'ValidationError'
]