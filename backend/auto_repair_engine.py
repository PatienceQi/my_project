"""
政策法规RAG问答系统 - 自动修复策略模块

提供智能的故障自动修复功能，基于诊断结果生成和执行修复操作
"""

import os
import sys
import subprocess
import shutil
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class RepairPriority(Enum):
    """修复优先级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RepairStatus(Enum):
    """修复状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RepairAction:
    """修复操作数据结构"""
    action_id: str
    name: str
    description: str
    priority: RepairPriority
    commands: List[str]
    validation_check: Optional[str] = None
    rollback_commands: Optional[List[str]] = None
    status: RepairStatus = RepairStatus.PENDING
    error_message: Optional[str] = None
    execution_time: Optional[float] = None


class AutoRepairEngine:
    """自动修复引擎"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.repair_history: List[Dict[str, Any]] = []
        self.dry_run = False
        
        # 预定义修复策略
        self.repair_strategies = {
            "python_path_fix": self._create_python_path_repair,
            "missing_init_files": self._create_init_files_repair,
            "environment_variables": self._create_env_vars_repair,
            "package_installation": self._create_package_install_repair,
            "service_restart": self._create_service_restart_repair,
            "configuration_fix": self._create_config_fix_repair
        }
    
    def generate_repair_plan(self, diagnosis_result: Dict[str, Any]) -> List[RepairAction]:
        """基于诊断结果生成修复计划"""
        repair_actions = []
        
        # 分析诊断结果，生成相应的修复操作
        component_results = diagnosis_result.get("component_results", {})
        
        # 1. 处理模块导入问题
        if "module_imports" in component_results:
            module_result = component_results["module_imports"]
            if module_result.get("status") == "error":
                repair_actions.extend(self._generate_module_import_repairs(module_result))
        
        # 2. 处理服务连接问题  
        if "service_connections" in component_results:
            service_results = component_results["service_connections"]
            repair_actions.extend(self._generate_service_connection_repairs(service_results))
        
        # 3. 处理环境配置问题
        if "environment_config" in component_results:
            env_result = component_results["environment_config"]
            if env_result.get("status") == "error":
                repair_actions.extend(self._generate_environment_repairs(env_result))
        
        # 4. 处理GraphRAG组件问题
        if "graphrag_components" in component_results:
            graphrag_results = component_results["graphrag_components"]
            repair_actions.extend(self._generate_graphrag_repairs(graphrag_results))
        
        # 按优先级排序
        repair_actions.sort(key=lambda x: list(RepairPriority).index(x.priority))
        
        return repair_actions
    
    def _generate_module_import_repairs(self, module_result: Dict[str, Any]) -> List[RepairAction]:
        """生成模块导入修复操作"""
        repairs = []
        details = module_result.get("details", {})
        
        # Python路径问题修复
        if details.get("python_path_issues"):
            repairs.append(self._create_python_path_repair())
        
        # 缺失__init__.py文件修复
        python_path_issues = details.get("python_path_issues", [])
        if any("__init__.py" in issue for issue in python_path_issues):
            repairs.append(self._create_init_files_repair())
        
        # 失败的导入修复
        failed_imports = details.get("failed_imports", [])
        if failed_imports:
            repairs.append(self._create_package_install_repair(failed_imports))
        
        return repairs
    
    def _generate_service_connection_repairs(self, service_results: Dict[str, Any]) -> List[RepairAction]:
        """生成服务连接修复操作"""
        repairs = []
        
        # Neo4j连接修复
        if service_results.get("neo4j", {}).get("status") == "error":
            repairs.append(RepairAction(
                action_id="neo4j_connection_fix",
                name="修复Neo4j连接",
                description="重启Neo4j服务并验证连接",
                priority=RepairPriority.HIGH,
                commands=[
                    "neo4j restart",
                    "sleep 10"  # 等待服务启动
                ],
                validation_check="neo4j status"
            ))
        
        # Ollama服务修复
        ollama_result = service_results.get("ollama", {})
        if ollama_result.get("status") == "error":
            if "本地地址" in ollama_result.get("message", ""):
                repairs.append(self._create_ollama_config_repair())
        
        return repairs
    
    def _generate_environment_repairs(self, env_result: Dict[str, Any]) -> List[RepairAction]:
        """生成环境配置修复操作"""
        repairs = []
        details = env_result.get("details", {})
        
        # 环境变量修复
        missing_vars = details.get("missing_env_vars", [])
        incorrect_vars = details.get("config_issues", [])
        
        if missing_vars or incorrect_vars:
            repairs.append(self._create_env_vars_repair(missing_vars, incorrect_vars))
        
        # Python包安装修复
        missing_packages = details.get("missing_packages", [])
        if missing_packages:
            repairs.append(self._create_package_install_repair(missing_packages))
        
        return repairs
    
    def _generate_graphrag_repairs(self, graphrag_results: Dict[str, Any]) -> List[RepairAction]:
        """生成GraphRAG组件修复操作"""
        repairs = []
        
        # 检查各个组件状态并生成修复操作
        for component_name, component_result in graphrag_results.items():
            if isinstance(component_result, dict) and component_result.get("status") == "error":
                if component_name == "graphrag_engine":
                    repairs.append(RepairAction(
                        action_id="restart_graphrag_engine",
                        name="重启GraphRAG引擎",
                        description="重新初始化GraphRAG引擎实例",
                        priority=RepairPriority.HIGH,
                        commands=["python start_server.py api --restart-graphrag"]
                    ))
        
        return repairs
    
    def _create_python_path_repair(self) -> RepairAction:
        """创建Python路径修复操作"""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        return RepairAction(
            action_id="python_path_fix",
            name="修复Python路径配置",
            description="设置正确的Python模块路径",
            priority=RepairPriority.CRITICAL,
            commands=[
                f"export PYTHONPATH=\"{project_root}:$PYTHONPATH\"",
                f"cd {project_root}"
            ],
            validation_check=f"python -c \"import sys; print('{project_root}' in sys.path)\""
        )
    
    def _create_init_files_repair(self) -> RepairAction:
        """创建__init__.py文件修复操作"""
        backend_path = os.path.join(os.getcwd(), "backend", "__init__.py")
        
        return RepairAction(
            action_id="create_init_files",
            name="创建缺失的__init__.py文件",
            description="在backend目录创建__init__.py文件",
            priority=RepairPriority.HIGH,
            commands=[f"touch {backend_path}"],
            validation_check=f"test -f {backend_path}"
        )
    
    def _create_env_vars_repair(self, missing_vars: List[str] = None, incorrect_vars: List[str] = None) -> RepairAction:
        """创建环境变量修复操作"""
        commands = []
        
        # 设置缺失的环境变量
        env_mappings = {
            "LLM_BINDING_HOST": "http://120.232.79.82:11434",
            "NEO4J_URI": "neo4j://localhost:7687",
            "NEO4J_USERNAME": "neo4j",
            "LLM_MODEL": "llama3.2:latest"
        }
        
        for var in missing_vars or []:
            if var in env_mappings:
                commands.append(f"export {var}='{env_mappings[var]}'")
        
        # 修正错误的环境变量
        for var_info in incorrect_vars or []:
            if isinstance(var_info, str) and "LLM_BINDING_HOST" in var_info:
                commands.append("export LLM_BINDING_HOST='http://120.232.79.82:11434'")
        
        return RepairAction(
            action_id="fix_environment_variables",
            name="修复环境变量配置",
            description="设置或修正关键环境变量",
            priority=RepairPriority.HIGH,
            commands=commands,
            validation_check="env | grep -E '(LLM_BINDING_HOST|NEO4J_URI)'"
        )
    
    def _create_package_install_repair(self, missing_items: List[Any]) -> RepairAction:
        """创建包安装修复操作"""
        packages = []
        
        # 处理不同格式的缺失项
        for item in missing_items:
            if isinstance(item, dict):
                if "module" in item:
                    # 来自模块导入检查
                    module_name = item["module"].replace("backend.", "")
                    if module_name not in ["graphrag_engine", "vector_retrieval"]:
                        packages.append(module_name)
                elif "name" in item:
                    # 来自包依赖检查
                    packages.append(item["name"])
            elif isinstance(item, str):
                packages.append(item)
        
        # 包名映射
        package_mapping = {
            "flask_cors": "flask-cors",
            "python-dotenv": "python-dotenv"
        }
        
        install_packages = []
        for pkg in packages:
            mapped_pkg = package_mapping.get(pkg, pkg)
            if mapped_pkg:
                install_packages.append(mapped_pkg)
        
        commands = []
        if install_packages:
            commands.extend([
                f"pip install {' '.join(install_packages)}",
                "pip install -r requirements.txt"  # 确保所有依赖都安装
            ])
        
        return RepairAction(
            action_id="install_missing_packages",
            name="安装缺失的Python包",
            description=f"安装 {len(install_packages)} 个缺失的包",
            priority=RepairPriority.HIGH,
            commands=commands,
            validation_check=f"python -c \"import {install_packages[0] if install_packages else 'sys'}\""
        )
    
    def _create_ollama_config_repair(self) -> RepairAction:
        """创建Ollama配置修复操作"""
        return RepairAction(
            action_id="fix_ollama_config",  
            name="修复Ollama服务配置",
            description="设置正确的远程Ollama服务地址",
            priority=RepairPriority.CRITICAL,
            commands=[
                "export LLM_BINDING_HOST='http://120.232.79.82:11434'",
                "export OLLAMA_HOST='http://120.232.79.82:11434'",
                "export OLLAMA_NO_SERVE='1'"
            ],
            validation_check="curl -s http://120.232.79.82:11434/api/tags"
        )
    
    def _create_service_restart_repair(self, service_name: str) -> RepairAction:
        """创建服务重启修复操作"""
        service_commands = {
            "neo4j": ["neo4j restart", "sleep 5"],
            "api_server": ["python start_server.py api --restart"]
        }
        
        return RepairAction(
            action_id=f"restart_{service_name}",
            name=f"重启{service_name}服务",
            description=f"重启{service_name}服务以解决连接问题",
            priority=RepairPriority.MEDIUM,
            commands=service_commands.get(service_name, [f"systemctl restart {service_name}"])
        )
    
    def _create_config_fix_repair(self) -> RepairAction:
        """创建配置文件修复操作"""  
        return RepairAction(
            action_id="fix_configuration",
            name="修复配置文件",
            description="检查和修复系统配置文件",
            priority=RepairPriority.MEDIUM,
            commands=[
                "python -c \"from backend.connections import get_connection_manager; get_connection_manager().initialize({}, {}, strict_mode=False)\""
            ]
        )
    
    def execute_repair_plan(self, repair_actions: List[RepairAction], auto_confirm: bool = False) -> Dict[str, Any]:
        """执行修复计划"""
        execution_result = {
            "start_time": datetime.now().isoformat(),
            "total_actions": len(repair_actions),
            "executed_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "skipped_actions": 0,
            "action_results": [],
            "overall_status": "success"
        }
        
        self.logger.info(f"开始执行修复计划，共 {len(repair_actions)} 个操作")
        
        for action in repair_actions:
            if not auto_confirm and not self.dry_run:
                # 询问用户确认
                response = input(f"执行修复操作 '{action.name}'? [y/N/s(跳过)/q(退出)]: ").lower()
                if response == 'q':
                    break
                elif response == 's':
                    action.status = RepairStatus.SKIPPED
                    execution_result["skipped_actions"] += 1
                    continue
                elif response != 'y':
                    action.status = RepairStatus.SKIPPED
                    execution_result["skipped_actions"] += 1
                    continue
            
            # 执行修复操作
            result = self._execute_single_repair(action)
            execution_result["action_results"].append(result)
            execution_result["executed_actions"] += 1
            
            if result["status"] == "success":
                execution_result["successful_actions"] += 1
            else:
                execution_result["failed_actions"] += 1
                
                # 如果是关键操作失败，考虑停止
                if action.priority == RepairPriority.CRITICAL:
                    self.logger.error(f"关键修复操作失败: {action.name}")
                    execution_result["overall_status"] = "failed"
                    if not auto_confirm:
                        response = input("关键操作失败，是否继续? [y/N]: ").lower()
                        if response != 'y':
                            break
        
        # 更新整体状态
        if execution_result["failed_actions"] > 0:
            if execution_result["successful_actions"] > execution_result["failed_actions"]:
                execution_result["overall_status"] = "partial_success"
            else:
                execution_result["overall_status"] = "failed"
        
        execution_result["end_time"] = datetime.now().isoformat()
        
        # 保存执行历史
        self.repair_history.append(execution_result)
        
        return execution_result
    
    def _execute_single_repair(self, action: RepairAction) -> Dict[str, Any]:
        """执行单个修复操作"""
        import time
        
        action.status = RepairStatus.IN_PROGRESS
        start_time = time.time()
        
        result = {
            "action_id": action.action_id,
            "name": action.name,
            "status": "success",
            "message": "",
            "execution_time": 0,
            "output": ""
        }
        
        try:
            self.logger.info(f"执行修复操作: {action.name}")
            
            if self.dry_run:
                # 干运行模式，只记录不执行
                result["message"] = "干运行模式 - 操作未实际执行"
                result["output"] = f"将执行命令: {'; '.join(action.commands)}"
                action.status = RepairStatus.SUCCESS
            else:
                # 执行修复命令
                output_lines = []
                for command in action.commands:
                    self.logger.debug(f"执行命令: {command}")
                    
                    try:
                        if command.startswith("export "):
                            # 处理环境变量设置
                            var_assignment = command.replace("export ", "")
                            if "=" in var_assignment:
                                var_name, var_value = var_assignment.split("=", 1)
                                var_value = var_value.strip("'\"")
                                os.environ[var_name] = var_value
                                output_lines.append(f"设置环境变量 {var_name}={var_value}")
                        elif command.startswith("cd "):
                            # 处理目录切换
                            target_dir = command.replace("cd ", "").strip()
                            os.chdir(target_dir)
                            output_lines.append(f"切换到目录: {target_dir}")
                        elif command.startswith("touch "):
                            # 处理文件创建
                            file_path = command.replace("touch ", "").strip()
                            os.makedirs(os.path.dirname(file_path), exist_ok=True)
                            with open(file_path, 'a'):
                                pass
                            output_lines.append(f"创建文件: {file_path}")
                        else:
                            # 执行其他命令
                            process_result = subprocess.run(
                                command, 
                                shell=True, 
                                capture_output=True, 
                                text=True, 
                                timeout=300  # 5分钟超时
                            )
                            
                            if process_result.returncode == 0:
                                output_lines.append(f"命令成功: {command}")
                                if process_result.stdout:
                                    output_lines.append(process_result.stdout.strip())
                            else:
                                raise subprocess.CalledProcessError(
                                    process_result.returncode, 
                                    command, 
                                    process_result.stdout, 
                                    process_result.stderr
                                )
                    
                    except subprocess.CalledProcessError as e:
                        result["status"] = "failed"
                        result["message"] = f"命令执行失败: {command}"
                        result["output"] = f"错误输出: {e.stderr}"
                        action.status = RepairStatus.FAILED
                        action.error_message = str(e)
                        break
                    except Exception as e:
                        result["status"] = "failed"
                        result["message"] = f"命令执行异常: {str(e)}"
                        action.status = RepairStatus.FAILED
                        action.error_message = str(e)
                        break
                
                if result["status"] == "success":
                    result["output"] = "\\n".join(output_lines)
                    result["message"] = "修复操作执行成功"
                    action.status = RepairStatus.SUCCESS
                    
                    # 执行验证检查
                    if action.validation_check:
                        try:
                            validation_result = subprocess.run(
                                action.validation_check, 
                                shell=True, 
                                capture_output=True, 
                                text=True, 
                                timeout=30
                            )
                            
                            if validation_result.returncode != 0:
                                result["status"] = "failed"
                                result["message"] = "修复操作执行成功但验证失败"
                                action.status = RepairStatus.FAILED
                        except Exception as e:
                            self.logger.warning(f"验证检查失败: {e}")
        
        except Exception as e:
            result["status"] = "failed"
            result["message"] = f"修复操作失败: {str(e)}"
            action.status = RepairStatus.FAILED
            action.error_message = str(e)
            self.logger.error(f"修复操作失败: {action.name} - {e}")
        
        finally:
            execution_time = time.time() - start_time
            result["execution_time"] = round(execution_time, 2)
            action.execution_time = execution_time
        
        return result
    
    def get_repair_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取修复历史"""
        return self.repair_history[-limit:]
    
    def set_dry_run(self, dry_run: bool):
        """设置干运行模式"""
        self.dry_run = dry_run


def main():
    """主函数 - 演示自动修复功能"""
    print("=== GraphRAG自动修复系统演示 ===")
    
    # 创建修复引擎
    repair_engine = AutoRepairEngine()
    
    # 模拟诊断结果
    mock_diagnosis = {
        "component_results": {
            "module_imports": {
                "status": "error",
                "details": {
                    "python_path_issues": ["项目根目录未在Python路径中"],
                    "failed_imports": [{"module": "backend.test_module"}]
                }
            },
            "environment_config": {
                "status": "error", 
                "details": {
                    "missing_env_vars": ["LLM_BINDING_HOST"],
                    "config_issues": ["LLM_BINDING_HOST 配置了本地地址"]
                }
            }
        }
    }
    
    # 生成修复计划
    print("生成修复计划...")
    repair_actions = repair_engine.generate_repair_plan(mock_diagnosis)
    
    print(f"生成了 {len(repair_actions)} 个修复操作:")
    for i, action in enumerate(repair_actions, 1):
        print(f"  {i}. {action.name} (优先级: {action.priority.value})")
        print(f"     描述: {action.description}")
    
    # 设置干运行模式进行演示
    repair_engine.set_dry_run(True)
    
    # 执行修复计划
    print("\\n执行修复计划 (干运行模式)...")
    result = repair_engine.execute_repair_plan(repair_actions, auto_confirm=True)
    
    print(f"\\n修复执行结果:")
    print(f"  总计操作: {result['total_actions']}")
    print(f"  执行操作: {result['executed_actions']}")
    print(f"  成功操作: {result['successful_actions']}")
    print(f"  失败操作: {result['failed_actions']}")
    print(f"  整体状态: {result['overall_status']}")


if __name__ == "__main__":
    main()