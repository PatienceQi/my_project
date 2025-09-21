"""
政策法规RAG问答系统 - GraphRAG故障诊断模块

提供GraphRAG系统的全面故障检测、定位和修复功能
基于设计文档实现系统性的诊断和监控方案
"""

import os
import sys
import time
import logging
import traceback
import importlib
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.exceptions import SystemError, DatabaseError, LLMServiceError, ConfigurationError


class DiagnosticLevel(Enum):
    """诊断级别"""
    BASIC = "basic"
    FULL = "full"
    REPAIR = "repair"


class ComponentStatus(Enum):
    """组件状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNAVAILABLE = "unavailable"
    INITIALIZING = "initializing"


@dataclass
class DiagnosticResult:
    """诊断结果数据结构"""
    component: str
    status: ComponentStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    error_details: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "recommendations": self.recommendations,
            "error_details": self.error_details,
            "timestamp": self.timestamp.isoformat()
        }


class GraphRAGDiagnostic:
    """GraphRAG故障诊断器"""
    
    def __init__(self):
        """初始化故障诊断器"""
        self.logger = logging.getLogger(__name__)
        self.diagnosis_history: List[Dict[str, Any]] = []
        self.max_history = 50
        
        # 预定义的模块导入检查
        self.import_checks = [
            ('backend.vector_retrieval', 'VectorRetriever'),
            ('backend.graph_query', 'GraphQueryEngine'), 
            ('backend.entity_extractor', 'EntityExtractor'),
            ('backend.hallucination_detector', 'HallucinationDetector'),
            ('backend.earag_evaluator', 'EARAGEvaluator'),
            ('backend.graphrag_engine', 'GraphRAGEngine')
        ]
        
        # 必需环境变量配置
        self.required_env_vars = {
            'LLM_BINDING_HOST': 'http://120.232.79.82:11434',
            'NEO4J_URI': 'neo4j://localhost:7687',
            'NEO4J_USERNAME': 'neo4j',
            'NEO4J_PASSWORD': None  # 需要检查但不验证特定值
        }
        
        # 核心Python包依赖
        self.core_dependencies = [
            'neo4j', 'flask', 'requests', 'python-dotenv', 'flask-cors',
            'chromadb', 'sentence-transformers', 'jieba', 'numpy'
        ]
    
    def diagnose_system(self, level: DiagnosticLevel = DiagnosticLevel.BASIC, 
                       components: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        执行系统诊断
        
        Args:
            level: 诊断级别
            components: 要检查的组件列表，None表示检查所有组件
            
        Returns:
            Dict[str, Any]: 诊断结果
        """
        start_time = datetime.now()
        
        self.logger.info(f"开始执行GraphRAG系统诊断 - 级别: {level.value}")
        
        # 初始化诊断结果
        diagnosis = {
            "diagnosis_id": f"graphrag_diag_{int(time.time())}",
            "timestamp": start_time.isoformat(),
            "level": level.value,
            "components_checked": components or ["all"],
            "overall_status": ComponentStatus.HEALTHY.value,
            "summary": "",
            "component_results": {},
            "recommendations": [],
            "repair_actions": [],
            "processing_time": 0.0
        }
        
        try:
            # 1. 模块导入故障检查
            if not components or "import" in components or "all" in components:
                import_result = self._diagnose_module_imports()
                diagnosis["component_results"]["module_imports"] = import_result.to_dict()
            
            # 2. 依赖服务连接检查
            if not components or "connections" in components or "all" in components:
                connection_results = self._diagnose_service_connections()
                diagnosis["component_results"]["service_connections"] = {
                    conn_name: result.to_dict() 
                    for conn_name, result in connection_results.items()
                }
            
            # 3. 环境配置验证
            if not components or "environment" in components or "all" in components:
                env_result = self._diagnose_environment_config()
                diagnosis["component_results"]["environment_config"] = env_result.to_dict()
            
            # 4. GraphRAG组件状态检查
            if not components or "graphrag" in components or "all" in components:
                graphrag_results = self._diagnose_graphrag_components()
                diagnosis["component_results"]["graphrag_components"] = {
                    comp_name: result.to_dict()
                    for comp_name, result in graphrag_results.items()
                }
            
            # 5. 生成综合诊断报告
            diagnosis.update(self._generate_diagnosis_summary(diagnosis["component_results"]))
            
            # 6. 生成修复建议（REPAIR级别）
            if level == DiagnosticLevel.REPAIR:
                repair_actions = self._generate_repair_actions(diagnosis["component_results"])
                diagnosis["repair_actions"] = repair_actions
            
        except Exception as e:
            self.logger.error(f"诊断过程中发生错误: {e}")
            diagnosis["overall_status"] = ComponentStatus.ERROR.value
            diagnosis["summary"] = f"诊断过程失败: {str(e)}"
            diagnosis["error"] = str(e)
        
        # 计算处理时间
        diagnosis["processing_time"] = (datetime.now() - start_time).total_seconds()
        
        # 保存诊断历史
        self._save_diagnosis_history(diagnosis)
        
        self.logger.info(f"GraphRAG系统诊断完成 - 状态: {diagnosis['overall_status']}")
        
        return diagnosis
    
    def _diagnose_module_imports(self) -> DiagnosticResult:
        """诊断模块导入状态"""
        self.logger.info("检查模块导入状态...")
        
        import_results = []
        failed_imports = []
        
        for module_name, class_name in self.import_checks:
            try:
                # 尝试导入模块
                module = importlib.import_module(module_name)
                
                # 尝试获取类
                if hasattr(module, class_name):
                    import_results.append(f"✓ {module_name}.{class_name}")
                else:
                    failed_imports.append(f"✗ {module_name}.{class_name} - 类不存在")
                    
            except ImportError as e:
                failed_imports.append(f"✗ {module_name} - 导入失败: {str(e)}")
            except Exception as e:
                failed_imports.append(f"✗ {module_name} - 未知错误: {str(e)}")
        
        # 检查Python路径配置
        python_path_issues = self._check_python_path()
        
        # 生成结果
        if not failed_imports:
            status = ComponentStatus.HEALTHY
            message = f"所有模块导入正常 ({len(import_results)}个)"
            recommendations = []
        else:
            status = ComponentStatus.ERROR
            message = f"模块导入失败 ({len(failed_imports)}个失败)"
            recommendations = [
                "检查Python模块路径配置",
                "确保使用项目根目录的start_server.py启动",
                "验证backend目录下存在__init__.py文件",
                "检查缺失的依赖包"
            ]
        
        return DiagnosticResult(
            component="module_imports",
            status=status,
            message=message,
            details={
                "successful_imports": import_results,
                "failed_imports": failed_imports,
                "python_path_issues": python_path_issues,
                "python_version": sys.version,
                "current_working_directory": os.getcwd()
            },
            recommendations=recommendations
        )
    
    def _check_python_path(self) -> List[str]:
        """检查Python路径配置问题"""
        issues = []
        
        # 检查项目根目录是否在sys.path中
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            issues.append(f"项目根目录未在Python路径中: {project_root}")
        
        # 检查backend包是否可导入
        try:
            import backend
        except ImportError:
            issues.append("backend包无法导入，可能缺少__init__.py文件")
        
        # 检查工作目录
        cwd = os.getcwd()
        if not os.path.exists(os.path.join(cwd, 'backend')):
            issues.append(f"当前工作目录可能不正确: {cwd}")
        
        return issues
    
    def _diagnose_service_connections(self) -> Dict[str, DiagnosticResult]:
        """诊断服务连接状态"""
        self.logger.info("检查服务连接状态...")
        
        results = {}
        
        # 检查Neo4j连接
        results["neo4j"] = self._check_neo4j_connection()
        
        # 检查Ollama连接
        results["ollama"] = self._check_ollama_connection()
        
        # 检查ChromaDB状态
        results["chromadb"] = self._check_chromadb_status()
        
        return results
    
    def _check_neo4j_connection(self) -> DiagnosticResult:
        """检查Neo4j连接状态"""
        try:
            from backend.connections import get_connection_manager
            
            connection_manager = get_connection_manager()
            
            if not connection_manager.neo4j:
                return DiagnosticResult(
                    component="neo4j",
                    status=ComponentStatus.UNAVAILABLE,
                    message="Neo4j连接管理器未初始化",
                    recommendations=[
                        "检查Neo4j配置参数",
                        "确保Neo4j服务正在运行",
                        "验证连接字符串和认证信息"
                    ]
                )
            
            # 测试连接健康状态
            is_healthy = connection_manager.neo4j.is_healthy(force_check=True)
            
            if is_healthy:
                return DiagnosticResult(
                    component="neo4j",
                    status=ComponentStatus.HEALTHY,
                    message="Neo4j连接正常",
                    details={
                        "connection_info": connection_manager.neo4j.get_connection_info()
                    }
                )
            else:
                return DiagnosticResult(
                    component="neo4j",
                    status=ComponentStatus.ERROR,
                    message="Neo4j连接不健康",
                    recommendations=[
                        "重启Neo4j服务",
                        "检查网络连接",
                        "验证认证信息"
                    ]
                )
                
        except Exception as e:
            return DiagnosticResult(
                component="neo4j",
                status=ComponentStatus.ERROR,
                message=f"Neo4j连接检查失败: {str(e)}",
                error_details=str(e),
                recommendations=[
                    "检查Neo4j配置",
                    "确保相关Python包已安装"
                ]
            )
    
    def _check_ollama_connection(self) -> DiagnosticResult:
        """检查Ollama连接状态"""
        try:
            # 获取配置的Ollama地址
            ollama_host = os.getenv('LLM_BINDING_HOST', 'http://120.232.79.82:11434')
            model_name = os.getenv('LLM_MODEL', 'llama3.2:latest')
            
            # 检查是否配置了本地地址
            local_addresses = ['127.0.0.1', 'localhost']
            is_local = any(addr in ollama_host for addr in local_addresses)
            
            if is_local:
                return DiagnosticResult(
                    component="ollama",
                    status=ComponentStatus.ERROR,
                    message=f"检测到本地Ollama地址配置: {ollama_host}",
                    details={"configured_host": ollama_host},
                    recommendations=[
                        "更新LLM_BINDING_HOST环境变量为远程地址",
                        "使用正确的远程Ollama服务地址: http://120.232.79.82:11434"
                    ]
                )
            
            # 测试服务可达性
            try:
                response = requests.get(f"{ollama_host}/api/tags", timeout=10)
                
                if response.status_code == 200:
                    return DiagnosticResult(
                        component="ollama",
                        status=ComponentStatus.HEALTHY,
                        message="Ollama服务正常",
                        details={
                            "host": ollama_host,
                            "model": model_name,
                            "status_code": response.status_code
                        }
                    )
                else:
                    return DiagnosticResult(
                        component="ollama",
                        status=ComponentStatus.ERROR,
                        message=f"Ollama服务HTTP错误: {response.status_code}",
                        recommendations=["检查Ollama服务状态"]
                    )
                    
            except requests.exceptions.Timeout:
                return DiagnosticResult(
                    component="ollama",
                    status=ComponentStatus.ERROR,
                    message="Ollama服务连接超时",
                    recommendations=["检查网络连接", "验证服务地址"]
                )
                
        except Exception as e:
            return DiagnosticResult(
                component="ollama",
                status=ComponentStatus.ERROR,
                message=f"Ollama连接检查失败: {str(e)}",
                error_details=str(e)
            )
    
    def _check_chromadb_status(self) -> DiagnosticResult:
        """检查ChromaDB状态"""
        try:
            # 检查向量存储文件
            vector_store_path = os.path.join(os.getcwd(), 'data', 'simple_vector_store.json')
            
            if not os.path.exists(vector_store_path):
                return DiagnosticResult(
                    component="chromadb",
                    status=ComponentStatus.WARNING,
                    message="向量存储文件不存在",
                    details={"expected_path": vector_store_path},
                    recommendations=["初始化向量数据库", "导入政策数据"]
                )
            
            # 检查文件大小
            file_size = os.path.getsize(vector_store_path)
            
            if file_size == 0:
                return DiagnosticResult(
                    component="chromadb",
                    status=ComponentStatus.WARNING,
                    message="向量存储文件为空",
                    recommendations=["重新导入数据"]
                )
            
            return DiagnosticResult(
                component="chromadb",
                status=ComponentStatus.HEALTHY,
                message=f"向量数据库正常，文件大小: {file_size/1024:.1f}KB",
                details={
                    "file_path": vector_store_path,
                    "file_size_bytes": file_size
                }
            )
                
        except Exception as e:
            return DiagnosticResult(
                component="chromadb",
                status=ComponentStatus.ERROR,
                message=f"ChromaDB状态检查失败: {str(e)}",
                error_details=str(e)
            )
    
    def _diagnose_environment_config(self) -> DiagnosticResult:
        """诊断环境配置"""
        self.logger.info("检查环境配置...")
        
        config_issues = []
        missing_vars = []
        
        # 检查必需的环境变量
        for var_name, expected_value in self.required_env_vars.items():
            current_value = os.getenv(var_name)
            
            if not current_value:
                missing_vars.append(var_name)
                continue
            
            # 对于有期望值的变量，检查是否匹配
            if expected_value and current_value != expected_value:
                if var_name == 'LLM_BINDING_HOST':
                    # 检查是否配置了本地地址
                    if '127.0.0.1' in current_value or 'localhost' in current_value:
                        config_issues.append(
                            f"{var_name} 配置了本地地址: {current_value}"
                        )
        
        # 检查Python包依赖
        missing_packages = self._check_package_dependencies()
        
        # 生成结果
        if not config_issues and not missing_vars and not missing_packages:
            status = ComponentStatus.HEALTHY
            message = "环境配置正常"
        else:
            status = ComponentStatus.ERROR
            issue_count = len(config_issues) + len(missing_vars) + len(missing_packages)
            message = f"环境配置存在问题 ({issue_count}个错误)"
        
        recommendations = []
        if missing_vars:
            recommendations.append("设置缺失的环境变量")
        if config_issues:
            recommendations.append("修正配置错误")
        if missing_packages:
            recommendations.append("安装缺失的Python包")
        
        return DiagnosticResult(
            component="environment_config",
            status=status,
            message=message,
            details={
                "missing_env_vars": missing_vars,
                "config_issues": config_issues,
                "missing_packages": missing_packages
            },
            recommendations=recommendations
        )
    
    def _check_package_dependencies(self) -> List[str]:
        """检查Python包依赖"""
        missing_packages = []
        
        for package_name in self.core_dependencies:
            try:
                importlib.import_module(package_name)
            except ImportError:
                missing_packages.append(package_name)
        
        return missing_packages
    
    def _diagnose_graphrag_components(self) -> Dict[str, DiagnosticResult]:
        """诊断GraphRAG组件状态"""
        self.logger.info("检查GraphRAG组件状态...")
        
        results = {}
        
        try:
            # 检查GraphRAG引擎全局实例
            results["graphrag_engine"] = self._check_graphrag_engine_status()
            
            # 检查各个子组件
            components = [
                ("vector_retriever", "VectorRetriever", "backend.vector_retrieval"),
                ("graph_query_engine", "GraphQueryEngine", "backend.graph_query"),
                ("entity_extractor", "EntityExtractor", "backend.entity_extractor"),
                ("hallucination_detector", "HallucinationDetector", "backend.hallucination_detector"),
                ("earag_evaluator", "EARAGEvaluator", "backend.earag_evaluator")
            ]
            
            for comp_name, class_name, module_name in components:
                results[comp_name] = self._check_component_status(class_name, module_name)
                
        except Exception as e:
            results["graphrag_engine"] = DiagnosticResult(
                component="graphrag_engine",
                status=ComponentStatus.ERROR,
                message=f"GraphRAG组件检查失败: {str(e)}",
                error_details=str(e),
                recommendations=[
                    "检查模块导入路径",
                    "确保使用start_server.py启动"
                ]
            )
        
        return results
    
    def _check_graphrag_engine_status(self) -> DiagnosticResult:
        """检查GraphRAG引擎状态"""
        try:
            # 检查API服务器中的GraphRAG可用性
            from backend.api_server import GRAPHRAG_AVAILABLE, graphrag_engine
            
            if not GRAPHRAG_AVAILABLE:
                return DiagnosticResult(
                    component="graphrag_engine",
                    status=ComponentStatus.UNAVAILABLE,
                    message="GraphRAG功能在API服务器中不可用",
                    recommendations=[
                        "检查GraphRAG模块导入",
                        "重启服务器"
                    ]
                )
            
            if graphrag_engine is None:
                return DiagnosticResult(
                    component="graphrag_engine",
                    status=ComponentStatus.ERROR,
                    message="GraphRAG引擎全局实例未初始化",
                    recommendations=[
                        "检查引擎初始化过程",
                        "重启服务器"
                    ]
                )
            
            return DiagnosticResult(
                component="graphrag_engine",
                status=ComponentStatus.HEALTHY,
                message="GraphRAG引擎运行正常",
                details={"engine_available": True}
            )
                
        except Exception as e:
            return DiagnosticResult(
                component="graphrag_engine",
                status=ComponentStatus.ERROR,
                message=f"GraphRAG引擎检查失败: {str(e)}",
                error_details=str(e)
            )
    
    def _check_component_status(self, class_name: str, module_name: str) -> DiagnosticResult:
        """检查单个组件状态"""
        try:
            module = importlib.import_module(module_name)
            
            if not hasattr(module, class_name):
                return DiagnosticResult(
                    component=class_name.lower(),
                    status=ComponentStatus.ERROR,
                    message=f"类 {class_name} 不存在"
                )
            
            return DiagnosticResult(
                component=class_name.lower(),
                status=ComponentStatus.HEALTHY,
                message=f"{class_name} 组件可用",
                details={"module": module_name, "class": class_name}
            )
            
        except ImportError as e:
            return DiagnosticResult(
                component=class_name.lower(),
                status=ComponentStatus.ERROR,
                message=f"模块 {module_name} 导入失败",
                error_details=str(e)
            )
    
    def _generate_diagnosis_summary(self, component_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成诊断摘要"""
        total_components = 0
        healthy_components = 0
        error_components = 0
        warning_components = 0
        
        all_recommendations = []
        
        # 统计各组件状态
        for category, category_data in component_results.items():
            if isinstance(category_data, dict):
                if 'status' in category_data:
                    # 单个组件
                    total_components += 1
                    status = category_data['status']
                    if status == ComponentStatus.HEALTHY.value:
                        healthy_components += 1
                    elif status == ComponentStatus.ERROR.value:
                        error_components += 1
                    elif status == ComponentStatus.WARNING.value:
                        warning_components += 1
                    
                    # 收集建议
                    if 'recommendations' in category_data:
                        all_recommendations.extend(category_data['recommendations'])
                else:
                    # 组件组（如service_connections）
                    for comp_name, comp_data in category_data.items():
                        if isinstance(comp_data, dict) and 'status' in comp_data:
                            total_components += 1
                            status = comp_data['status']
                            if status == ComponentStatus.HEALTHY.value:
                                healthy_components += 1
                            elif status == ComponentStatus.ERROR.value:
                                error_components += 1
                            elif status == ComponentStatus.WARNING.value:
                                warning_components += 1
                            
                            if 'recommendations' in comp_data:
                                all_recommendations.extend(comp_data['recommendations'])
        
        # 确定整体状态
        if error_components > 0:
            overall_status = ComponentStatus.ERROR.value
            summary = f"系统存在问题: {error_components}个错误, {warning_components}个警告, {healthy_components}个正常"
        elif warning_components > 0:
            overall_status = ComponentStatus.WARNING.value
            summary = f"系统基本正常但有警告: {warning_components}个警告, {healthy_components}个正常"
        else:
            overall_status = ComponentStatus.HEALTHY.value
            summary = f"系统运行正常: {healthy_components}个组件均健康"
        
        # 去重建议
        unique_recommendations = list(set(all_recommendations))
        
        return {
            "overall_status": overall_status,
            "summary": summary,
            "component_stats": {
                "total": total_components,
                "healthy": healthy_components,
                "warning": warning_components,
                "error": error_components
            },
            "recommendations": unique_recommendations[:10]  # 最多10个建议
        }
    
    def _generate_repair_actions(self, component_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成修复操作建议"""
        repair_actions = []
        
        # 模块导入问题修复
        if 'module_imports' in component_results:
            module_result = component_results['module_imports']
            if module_result.get('status') == ComponentStatus.ERROR.value:
                repair_actions.append({
                    "action": "fix_module_imports",
                    "description": "修复模块导入问题",
                    "steps": [
                        "检查项目根目录下是否存在backend/__init__.py",
                        "使用start_server.py启动服务而不是直接运行api_server.py",
                        "安装缺失的Python依赖包"
                    ],
                    "priority": "high"
                })
        
        # 环境配置问题修复
        if 'environment_config' in component_results:
            env_result = component_results['environment_config']
            if env_result.get('status') == ComponentStatus.ERROR.value:
                repair_actions.append({
                    "action": "fix_environment_config",
                    "description": "修复环境配置问题",
                    "steps": [
                        "设置LLM_BINDING_HOST=http://120.232.79.82:11434",
                        "设置NEO4J_URI=neo4j://localhost:7687",
                        "设置NEO4J_USERNAME和NEO4J_PASSWORD",
                        "pip install -r requirements.txt"
                    ],
                    "priority": "high"
                })
        
        # 服务连接问题修复
        if 'service_connections' in component_results:
            connections = component_results['service_connections']
            if connections.get('neo4j', {}).get('status') == ComponentStatus.ERROR.value:
                repair_actions.append({
                    "action": "fix_neo4j_connection",
                    "description": "修复Neo4j连接问题",
                    "steps": [
                        "启动Neo4j服务",
                        "检查Neo4j认证信息",
                        "验证端口7687是否可访问"
                    ],
                    "priority": "medium"
                })
            
            if connections.get('ollama', {}).get('status') == ComponentStatus.ERROR.value:
                repair_actions.append({
                    "action": "fix_ollama_connection",
                    "description": "修复Ollama服务连接问题",
                    "steps": [
                        "验证远程Ollama服务地址",
                        "检查网络连接",
                        "确认模型可用性"
                    ],
                    "priority": "high"
                })
        
        return repair_actions
    
    def _save_diagnosis_history(self, diagnosis: Dict[str, Any]):
        """保存诊断历史"""
        # 保留关键信息
        history_entry = {
            "diagnosis_id": diagnosis["diagnosis_id"],
            "timestamp": diagnosis["timestamp"],
            "overall_status": diagnosis["overall_status"],
            "summary": diagnosis["summary"],
            "processing_time": diagnosis["processing_time"]
        }
        
        self.diagnosis_history.append(history_entry)
        
        # 保持历史记录在限制范围内
        if len(self.diagnosis_history) > self.max_history:
            self.diagnosis_history = self.diagnosis_history[-self.max_history:]
    
    def get_diagnosis_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取诊断历史"""
        return self.diagnosis_history[-limit:]
    
    def get_quick_status(self) -> Dict[str, Any]:
        """获取快速状态检查"""
        try:
            # 执行基本诊断
            diagnosis = self.diagnose_system(DiagnosticLevel.BASIC)
            
            return {
                "overall_status": diagnosis["overall_status"],
                "summary": diagnosis["summary"],
                "timestamp": diagnosis["timestamp"],
                "component_count": diagnosis.get("component_stats", {}).get("total", 0),
                "healthy_count": diagnosis.get("component_stats", {}).get("healthy", 0),
                "error_count": diagnosis.get("component_stats", {}).get("error", 0)
            }
        except Exception as e:
            return {
                "overall_status": ComponentStatus.ERROR.value,
                "summary": f"快速检查失败: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }