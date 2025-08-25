"""
Ollama错误处理和回退策略模块
提供连接失败的错误处理、自动重试和回退机制
"""

import os
import logging
import time
import requests
from typing import Dict, List, Optional, Callable, Any
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

class OllamaConnectionError(Exception):
    """Ollama连接错误"""
    pass

class OllamaModelError(Exception):
    """Ollama模型错误"""
    pass

class OllamaErrorHandler:
    """Ollama错误处理器"""
    
    def __init__(self):
        self.primary_host = 'http://120.232.79.82:11434'
        # 关键修复：移除所有本地回退主机，确保只使用远程服务
        self.fallback_hosts = []  # 不再提供本地回退选项
        self.max_retries = 3
        self.retry_delay = 2  # 秒
        self.timeout = 30
        
        # 错误统计
        self.error_counts = {}
        self.last_successful_host = None
        
        # 强制设置远程配置
        self._force_remote_config()
        
        self.logger = logging.getLogger(__name__)
    
    def _force_remote_config(self):
        """强制设置远程配置"""
        config_vars = {
            'LLM_BINDING_HOST': self.primary_host,
            'OLLAMA_HOST': self.primary_host,
            'OLLAMA_BASE_URL': self.primary_host,
            'OLLAMA_NO_SERVE': '1',
            'OLLAMA_ORIGINS': '*'
        }
        
        for key, value in config_vars.items():
            old_value = os.environ.get(key)
            os.environ[key] = value
            if old_value != value:
                self.logger.info(f"OllamaErrorHandler强制配置: {key} = {value}")
    
    def with_retry_and_fallback(self, func: Callable) -> Callable:
        """装饰器：为函数添加重试和回退机制"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.execute_with_fallback(func, *args, **kwargs)
        return wrapper
    
    def execute_with_fallback(self, func: Callable, *args, **kwargs) -> Any:
        """执行函数，但不再支持本地回退，只使用远程服务"""
        # 关键修复：只使用主要远程主机，不再回退到本地
        host = self.primary_host
        
        # 确保使用远程配置
        self._set_ollama_host(host)
        
        # 尝试执行函数，带重试
        success, result, error = self._execute_with_retry(func, *args, **kwargs)
        
        if success:
            self.last_successful_host = host
            self._reset_error_count(host)
            return result
        else:
            self._increment_error_count(host)
            self.logger.error(f"远程主机 {host} 执行失败: {error}")
            
            # 检查是否是本地连接尝试
            if 'localhost' in str(error) or '127.0.0.1' in str(error):
                self.logger.error("❌ 检测到尝试连接本地服务！配置已损坏")
                # 重新强制配置
                self._force_remote_config()
            
            # 直接抛出错误，不再回退
            raise OllamaConnectionError(f"远程Ollama服务不可用: {error}")
    
    def _execute_with_retry(self, func: Callable, *args, **kwargs) -> tuple:
        """执行函数，支持重试"""
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                return True, result, None
                
            except Exception as e:
                self.logger.warning(f"尝试 {attempt + 1}/{self.max_retries} 失败: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # 递增延迟
                else:
                    return False, None, str(e)
        
        return False, None, "重试次数耗尽"
    
    def _set_ollama_host(self, host: str):
        """设置Ollama主机地址"""
        # 更新环境变量
        os.environ['LLM_BINDING_HOST'] = host
        os.environ['OLLAMA_HOST'] = host
        os.environ['OLLAMA_BASE_URL'] = host
        
        self.logger.info(f"切换Ollama主机到: {host}")
    
    def _increment_error_count(self, host: str):
        """增加主机错误计数"""
        self.error_counts[host] = self.error_counts.get(host, 0) + 1
    
    def _reset_error_count(self, host: str):
        """重置主机错误计数"""
        if host in self.error_counts:
            del self.error_counts[host]
    
    def validate_ollama_connection(self, host: str) -> bool:
        """验证Ollama连接"""
        try:
            response = requests.get(f"{host}/api/version", timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def validate_model_availability(self, host: str, model: str) -> bool:
        """验证模型可用性"""
        try:
            response = requests.get(f"{host}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                return any(model in name for name in model_names)
        except Exception:
            pass
        return False
    
    def get_health_status(self) -> Dict:
        """获取健康状态"""
        status = {
            'primary_host': self.primary_host,
            'last_successful_host': self.last_successful_host,
            'error_counts': self.error_counts.copy(),
            'host_status': {}
        }
        
        # 只检查远程主机状态
        is_available = self.validate_ollama_connection(self.primary_host)
        status['host_status'][self.primary_host] = {
            'available': is_available,
            'error_count': self.error_counts.get(self.primary_host, 0)
        }
        
        return status
    
    def force_reset_to_primary(self):
        """强制重置到主要主机"""
        self._set_ollama_host(self.primary_host)
        self.last_successful_host = None
        self.error_counts.clear()
        self.logger.info("强制重置到主要主机")


class OllamaClientWithFallback:
    """支持回退的Ollama客户端"""
    
    def __init__(self):
        self.error_handler = OllamaErrorHandler()
        self.logger = logging.getLogger(__name__)
    
    @property
    def current_host(self) -> str:
        """获取当前主机地址"""
        host = os.getenv('LLM_BINDING_HOST', self.error_handler.primary_host)
        
        # 关键修复：检查并修正本地地址
        if 'localhost' in host or '127.0.0.1' in host:
            host = self.error_handler.primary_host
            os.environ['LLM_BINDING_HOST'] = host
            self.logger.warning(f"检测到本地地址，强制使用远程服务: {host}")
        
        return host
    
    def call_api(self, endpoint: str, payload: Dict, method: str = 'POST') -> Dict:
        """调用API，支持错误处理和回退"""
        def _make_request():
            url = f"{self.current_host}/api/{endpoint}"
            
            if method.upper() == 'POST':
                response = requests.post(url, json=payload, timeout=self.error_handler.timeout)
            else:
                response = requests.get(url, timeout=self.error_handler.timeout)
            
            response.raise_for_status()
            return response.json()
        
        return self.error_handler.execute_with_fallback(_make_request)
    
    def generate_text(self, model: str, prompt: str, **options) -> str:
        """生成文本"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options
        }
        
        result = self.call_api('generate', payload)
        return result.get('response', '')
    
    def get_embeddings(self, model: str, text: str) -> List[float]:
        """获取嵌入向量"""
        payload = {
            "model": model,
            "prompt": text
        }
        
        result = self.call_api('embeddings', payload)
        return result.get('embedding', [])
    
    def list_models(self) -> List[Dict]:
        """列出可用模型"""
        result = self.call_api('tags', {}, method='GET')
        return result.get('models', [])
    
    def health_check(self) -> Dict:
        """健康检查"""
        return self.error_handler.get_health_status()


def create_resilient_ollama_client() -> OllamaClientWithFallback:
    """创建具有错误恢复能力的Ollama客户端"""
    return OllamaClientWithFallback()


def ensure_remote_ollama_config():
    """确保远程Ollama配置正确"""
    remote_host = 'http://120.232.79.82:11434'
    
    required_vars = {
        'LLM_BINDING_HOST': remote_host,
        'OLLAMA_HOST': remote_host,
        'OLLAMA_BASE_URL': remote_host,
        'OLLAMA_NO_SERVE': '1',
        'OLLAMA_ORIGINS': '*'
    }
    
    updated = False
    for key, expected in required_vars.items():
        current = os.environ.get(key)
        if current != expected:
            os.environ[key] = expected
            updated = True
            logging.info(f"环境变量修正: {key} = {expected}")
    
    if updated:
        logging.info("远程Ollama配置已更新")
    
    return updated


# 装饰器简化版本
def ollama_retry(max_retries: int = 3, delay: float = 2.0):
    """简化的重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries - 1:
                        logging.warning(f"Ollama调用失败，重试 {attempt + 1}/{max_retries}: {e}")
                        time.sleep(delay * (attempt + 1))
                    else:
                        logging.error(f"Ollama调用最终失败: {e}")
                        raise
            return None
        return wrapper
    return decorator


# 示例使用
if __name__ == "__main__":
    # 测试错误处理机制
    logging.basicConfig(level=logging.INFO)
    
    # 确保远程配置
    ensure_remote_ollama_config()
    
    # 创建客户端
    client = create_resilient_ollama_client()
    
    try:
        # 测试健康检查
        health = client.health_check()
        print("健康状态:", health)
        
        # 测试模型列表
        models = client.list_models()
        print("可用模型:", [m.get('name') for m in models])
        
        # 测试文本生成
        response = client.generate_text(
            model="llama3.2:latest",
            prompt="简单回答：什么是人工智能？",
            temperature=0.1,
            max_tokens=100
        )
        print("生成文本:", response)
        
    except Exception as e:
        print(f"测试失败: {e}")