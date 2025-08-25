"""
政策法规RAG问答系统 - 连接管理模块

提供Neo4j数据库和Ollama服务的连接管理功能
"""

import os
import time
import logging
import threading
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
from datetime import datetime, timedelta

from neo4j import GraphDatabase
import requests

from backend.exceptions import DatabaseError, LLMServiceError, ConfigurationError


class Neo4jConnectionManager:
    """Neo4j连接池管理器"""
    
    def __init__(self, uri: str, auth: tuple, max_pool_size: int = 10, 
                 connection_timeout: int = 30):
        """
        初始化Neo4j连接管理器
        
        Args:
            uri: Neo4j连接URI
            auth: 认证信息 (username, password)
            max_pool_size: 最大连接池大小
            connection_timeout: 连接超时时间(秒)
        """
        self.uri = uri
        self.auth = auth
        self.max_pool_size = max_pool_size
        self.connection_timeout = connection_timeout
        self._driver = None
        self._lock = threading.Lock()
        self._last_health_check = None
        self._health_status = False
        
        self._initialize_driver()
    
    def _initialize_driver(self):
        """初始化Neo4j驱动"""
        try:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=self.auth,
                max_connection_pool_size=self.max_pool_size,
                connection_timeout=self.connection_timeout,
                max_transaction_retry_time=30
            )
            # 验证连接
            with self._driver.session() as session:
                session.run("RETURN 1 as test").single()
            
            self._health_status = True
            self._last_health_check = datetime.now()
            
        except Exception as e:
            raise ConfigurationError(
                f"Neo4j连接初始化失败: {str(e)}", 
                "neo4j_connection"
            )
    
    @contextmanager
    def get_session(self) -> Generator:
        """
        获取数据库会话的上下文管理器
        
        Yields:
            neo4j.Session: 数据库会话对象
            
        Raises:
            DatabaseError: 当会话创建失败时
        """
        if not self._driver:
            raise DatabaseError("Neo4j驱动未初始化", "driver_not_initialized")
        
        session = None
        try:
            session = self._driver.session()
            yield session
        except Exception as e:
            raise DatabaseError(f"数据库会话操作失败: {str(e)}", "session_operation")
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass  # 忽略关闭时的错误
    
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> list:
        """
        执行Cypher查询
        
        Args:
            query: Cypher查询语句
            parameters: 查询参数
            
        Returns:
            list: 查询结果列表
            
        Raises:
            DatabaseError: 当查询执行失败时
        """
        try:
            with self.get_session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            raise DatabaseError(f"查询执行失败: {str(e)}", "query_execution")
    
    def is_healthy(self, force_check: bool = False) -> bool:
        """
        检查连接健康状态
        
        Args:
            force_check: 是否强制检查（忽略缓存）
            
        Returns:
            bool: 连接是否健康
        """
        # 缓存机制：1分钟内不重复检查
        now = datetime.now()
        if (not force_check and self._last_health_check and 
            now - self._last_health_check < timedelta(minutes=1)):
            return self._health_status
        
        try:
            with self.get_session() as session:
                result = session.run("RETURN 1 as health_check").single()
                self._health_status = result and result["health_check"] == 1
        except Exception:
            self._health_status = False
        
        self._last_health_check = now
        return self._health_status
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            "uri": self.uri,
            "max_pool_size": self.max_pool_size,
            "connection_timeout": self.connection_timeout,
            "is_healthy": self.is_healthy(),
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None
        }
    
    def close(self):
        """关闭连接池"""
        if self._driver:
            try:
                self._driver.close()
            except Exception:
                pass
            finally:
                self._driver = None
                self._health_status = False


class OllamaConnectionManager:
    """Ollama连接管理器"""
    
    def __init__(self, host: str, model: str, timeout: int = 120):
        """
        初始化Ollama连接管理器
        
        Args:
            host: Ollama服务地址
            model: 使用的模型名称
            timeout: 请求超时时间(秒)
        """
        # 关键修复：强制设置远程配置，防止ollama客户端启动本地服务
        # 设置所有可能的 ollama 环境变量，确保使用远程服务
        remote_host = host or 'http://120.232.79.82:11434'
        
        # 强制设置远程配置
        config_vars = {
            'OLLAMA_HOST': remote_host,
            'OLLAMA_BASE_URL': remote_host,
            'LLM_BINDING_HOST': remote_host,
            'OLLAMA_NO_SERVE': '1',
            'OLLAMA_ORIGINS': '*',
            'OLLAMA_KEEP_ALIVE': '5m'
        }
        
        for key, value in config_vars.items():
            old_value = os.environ.get(key)
            os.environ[key] = value
            if old_value != value:
                logging.info(f"OllamaConnectionManager强制配置: {key} = {value} (原值: {old_value})")
        
        # 验证配置正确性
        if '127.0.0.1' in remote_host or 'localhost' in remote_host:
            logging.warning(f"检测到本地地址，强制使用远程服务")
            remote_host = 'http://120.232.79.82:11434'
            for key in ['OLLAMA_HOST', 'OLLAMA_BASE_URL', 'LLM_BINDING_HOST']:
                os.environ[key] = remote_host
        
        self.host = remote_host
        self.model = model
        self.timeout = timeout
        self._lock = threading.Lock()
        self._last_health_check = None
        self._health_status = False
        
        logging.info(f"OllamaConnectionManager 初始化 - Host: {self.host}, Model: {model}")
        logging.info(f"强制远程配置已生效，OLLAMA_HOST: {os.environ.get('OLLAMA_HOST')}")
        
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化Ollama连接（使用HTTP API）"""
        try:
            # 测试服务可用性
            health_url = f"{self.host}/api/tags"
            response = requests.get(health_url, timeout=10)
            
            if response.status_code == 200:
                logging.info(f"Ollama服务连接成功: {self.host}")
                self._health_status = True
                self._last_health_check = datetime.now()
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            raise ConfigurationError(
                f"Ollama服务连接失败: {str(e)}", 
                "ollama_connection"
            )
    
    def _verify_model(self):
        """验证模型可用性（使用HTTP API）"""
        try:
            # 获取模型列表
            models_url = f"{self.host}/api/tags"
            response = requests.get(models_url, timeout=10)
            
            if response.status_code != 200:
                print(f"警告: 无法获取模型列表: HTTP {response.status_code}")
                return
            
            models_data = response.json()
            models_list = models_data.get('models', [])
            
            # 提取模型名称
            model_names = []
            for model in models_list:
                if isinstance(model, dict):
                    name = model.get('name') or model.get('model') or model.get('id') or str(model)
                    if name:
                        model_names.append(name)
                else:
                    model_names.append(str(model))
            
            # 检查目标模型是否可用
            if model_names:
                target_model = self.model.lower()
                available_models = [name.lower() for name in model_names]
                
                # 精确匹配或部分匹配
                model_found = any(
                    target_model == available or 
                    target_model in available or 
                    available.startswith(target_model)
                    for available in available_models
                )
                
                if not model_found:
                    # 如果没找到，尝试直接测试模型是否可用
                    try:
                        test_url = f"{self.host}/api/generate"
                        test_payload = {
                            "model": self.model,
                            "prompt": "test",
                            "stream": False
                        }
                        test_response = requests.post(test_url, json=test_payload, timeout=15)
                        if test_response.status_code == 200:
                            return  # 模型可用
                    except Exception:
                        pass  # 继续报错流程
                    
                    # 模型确实不可用
                    print(f"警告: 模型 '{self.model}' 在可用列表中未找到")
                    print(f"可用模型: {model_names}")
                    print("尝试继续运行，如果后续出现问题请检查模型名称")
            else:
                print("警告: 无法获取模型列表，跳过模型验证")
                
        except Exception as e:
            print(f"警告: 模型验证失败: {str(e)}，跳过验证")
            # 对于远程服务，允许跳过验证
    
    def chat(self, messages: list, **kwargs) -> Dict[str, Any]:
        """
        发送聊天请求（使用HTTP API）
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 响应结果
            
        Raises:
            LLMServiceError: 当请求失败时
        """
        try:
            url = f"{self.host}/api/chat"
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                **kwargs
            }
            
            headers = {"Content-Type": "application/json"}
            
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            raise LLMServiceError(f"LLM服务调用失败: {str(e)}", self.model)
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        生成文本（使用HTTP API）
        
        Args:
            prompt: 输入提示
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 生成结果
            
        Raises:
            LLMServiceError: 当生成失败时
        """
        try:
            url = f"{self.host}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                **kwargs
            }
            
            headers = {"Content-Type": "application/json"}
            
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            raise LLMServiceError(f"文本生成失败: {str(e)}", self.model)
    
    def is_healthy(self, force_check: bool = False) -> bool:
        """
        检查服务健康状态
        
        Args:
            force_check: 是否强制检查（忽略缓存）
            
        Returns:
            bool: 服务是否健康
        """
        # 缓存机制：1分钟内不重复检查
        now = datetime.now()
        if (not force_check and self._last_health_check and 
            now - self._last_health_check < timedelta(minutes=1)):
            return self._health_status
        
        try:
            # 检查服务可用性
            health_url = f"{self.host}/api/tags"
            response = requests.get(health_url, timeout=10)
            
            if response.status_code == 200:
                # 进一步检查模型可用性
                self._verify_model()
                self._health_status = True
            else:
                self._health_status = False
                
        except Exception:
            self._health_status = False
        
        self._last_health_check = now
        return self._health_status
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            "host": self.host,
            "model": self.model,
            "timeout": self.timeout,
            "is_healthy": self.is_healthy(),
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None
        }
    
    def get_available_models(self) -> list:
        """获取可用模型列表（使用HTTP API）"""
        try:
            url = f"{self.host}/api/tags"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            models_data = response.json()
            models_list = models_data.get('models', [])
            
            # 提取模型名称
            model_names = []
            for model in models_list:
                if isinstance(model, dict):
                    name = model.get('name') or model.get('model') or model.get('id') or str(model)
                    if name:
                        model_names.append(name)
                else:
                    model_names.append(str(model))
            
            return model_names
            
        except Exception:
            return []


class ConnectionManager:
    """统一连接管理器"""
    
    def __init__(self):
        self.neo4j: Optional[Neo4jConnectionManager] = None
        self.ollama: Optional[OllamaConnectionManager] = None
        self._initialized = False
    
    def initialize(self, neo4j_config: Dict[str, Any], ollama_config: Dict[str, Any], 
                  strict_mode: bool = False):
        """
        初始化所有连接
        
        Args:
            neo4j_config: Neo4j配置
            ollama_config: Ollama配置
            strict_mode: 严格模式，如果为True则任何连接失败都会抛出异常
        """
        initialization_errors = []
        
        try:
            # 初始化Neo4j连接
            self.neo4j = Neo4jConnectionManager(
                uri=neo4j_config['uri'],
                auth=(neo4j_config['username'], neo4j_config['password']),
                max_pool_size=neo4j_config.get('max_pool_size', 10),
                connection_timeout=neo4j_config.get('connection_timeout', 30)
            )
            print("✓ Neo4j连接管理器初始化成功")
            
        except Exception as e:
            error_msg = f"Neo4j连接初始化失败: {str(e)}"
            initialization_errors.append(error_msg)
            print(f"✗ {error_msg}")
            if strict_mode:
                raise ConfigurationError(error_msg, "neo4j_connection")
        
        try:
            # 初始化Ollama连接
            self.ollama = OllamaConnectionManager(
                host=ollama_config['host'],
                model=ollama_config['model'],
                timeout=ollama_config.get('timeout', 120)
            )
            print(f"✓ Ollama连接管理器初始化成功 (模型: {ollama_config['model']})")
            
        except Exception as e:
            error_msg = f"Ollama连接初始化失败: {str(e)}"
            initialization_errors.append(error_msg)
            print(f"✗ {error_msg}")
            if strict_mode:
                raise ConfigurationError(error_msg, "ollama_connection")
        
        # 设置初始化状态
        if initialization_errors:
            if strict_mode:
                raise ConfigurationError(
                    f"连接管理器初始化失败: {'; '.join(initialization_errors)}", 
                    "connection_manager"
                )
            else:
                print(f"⚠️  部分连接初始化失败，系统将以降级模式运行")
                print(f"错误详情: {'; '.join(initialization_errors)}")
                self._initialized = True  # 允许部分初始化
        else:
            self._initialized = True
            print("✓ 所有连接管理器初始化成功")
    
    def is_healthy(self) -> Dict[str, bool]:
        """检查所有连接的健康状态"""
        if not self._initialized:
            return {"neo4j": False, "ollama": False}
        
        return {
            "neo4j": self.neo4j.is_healthy() if self.neo4j else False,
            "ollama": self.ollama.is_healthy() if self.ollama else False
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取连接状态详情"""
        status = {
            "initialized": self._initialized,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.neo4j:
            status["neo4j"] = self.neo4j.get_connection_info()
        
        if self.ollama:
            status["ollama"] = self.ollama.get_connection_info()
        
        return status
    
    def close_all(self):
        """关闭所有连接"""
        if self.neo4j:
            self.neo4j.close()
        
        self._initialized = False


# 全局连接管理器实例
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """获取全局连接管理器实例"""
    return connection_manager