"""
政策法规RAG问答系统 - 模块导入故障检查工具

专门用于检测和修复Python模块导入问题
"""

import os
import sys
import importlib
import subprocess
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class ModuleImportChecker:
    """模块导入检查器"""
    
    def __init__(self):
        self.project_root = self._find_project_root()
        self.backend_path = os.path.join(self.project_root, 'backend')
        
        # 核心模块检查列表
        self.core_modules = [
            'backend',
            'backend.api_server',
            'backend.graphrag_engine',
            'backend.vector_retrieval',
            'backend.graph_query',
            'backend.entity_extractor',
            'backend.hallucination_detector',
            'backend.earag_evaluator',
            'backend.connections',
            'backend.session_manager',
            'backend.health_checker',
            'backend.exceptions',
            'backend.validators'
        ]
        
        # 外部依赖检查列表
        self.external_dependencies = [
            'neo4j',
            'flask',
            'flask_cors',
            'requests',
            'python-dotenv',
            'chromadb',
            'sentence-transformers',
            'jieba',
            'numpy',
            'psutil'
        ]
    
    def _find_project_root(self) -> str:
        """查找项目根目录"""
        current_dir = os.path.abspath(__file__)
        
        # 向上查找包含backend目录的根目录
        while current_dir != '/':
            if os.path.exists(os.path.join(current_dir, 'backend')):
                return current_dir
            current_dir = os.path.dirname(current_dir)
        
        # 如果找不到，使用当前工作目录的上级目录
        return os.path.dirname(os.getcwd())
    
    def check_python_path_configuration(self) -> Dict[str, any]:
        """检查Python路径配置"""
        results = {
            "status": "healthy",
            "issues": [],
            "recommendations": [],
            "details": {
                "project_root": self.project_root,
                "backend_path": self.backend_path,
                "current_working_directory": os.getcwd(),
                "python_path": sys.path,
                "python_version": sys.version
            }
        }
        
        # 检查项目根目录是否在Python路径中
        if self.project_root not in sys.path:
            results["issues"].append(f"项目根目录不在Python路径中: {self.project_root}")
            results["recommendations"].append("将项目根目录添加到Python路径")
            results["status"] = "error"
        
        # 检查backend目录是否存在
        if not os.path.exists(self.backend_path):
            results["issues"].append(f"backend目录不存在: {self.backend_path}")
            results["recommendations"].append("确认项目目录结构正确")
            results["status"] = "error"
        
        # 检查backend包的__init__.py文件
        backend_init_file = os.path.join(self.backend_path, '__init__.py')
        if not os.path.exists(backend_init_file):
            results["issues"].append(f"backend包缺少__init__.py文件: {backend_init_file}")
            results["recommendations"].append("创建backend/__init__.py文件")
            results["status"] = "error"
        
        # 检查工作目录是否正确
        if not os.path.exists(os.path.join(os.getcwd(), 'backend')):
            results["issues"].append(f"当前工作目录可能不正确: {os.getcwd()}")
            results["recommendations"].append("在项目根目录运行程序")
            results["status"] = "warning"
        
        return results
    
    def check_core_modules(self) -> Dict[str, any]:
        """检查核心模块导入状态"""
        results = {
            "status": "healthy",
            "successful_imports": [],
            "failed_imports": [],
            "import_details": {},
            "recommendations": []
        }
        
        for module_name in self.core_modules:
            try:
                # 尝试导入模块
                module = importlib.import_module(module_name)
                results["successful_imports"].append(module_name)
                
                # 获取模块详细信息
                module_info = {
                    "file_path": getattr(module, '__file__', 'unknown'),
                    "package": getattr(module, '__package__', 'unknown'),
                    "spec": str(getattr(module, '__spec__', 'unknown'))
                }
                results["import_details"][module_name] = module_info
                
            except ImportError as e:
                results["failed_imports"].append({
                    "module": module_name,
                    "error": str(e),
                    "error_type": "ImportError"
                })
                results["status"] = "error"
                
            except Exception as e:
                results["failed_imports"].append({
                    "module": module_name,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                results["status"] = "error"
        
        # 生成建议
        if results["failed_imports"]:
            results["recommendations"].extend([
                "检查Python模块路径配置",
                "确保使用start_server.py启动程序",
                "验证backend目录下存在__init__.py文件",
                "检查相关依赖包是否安装"
            ])
        
        return results
    
    def check_external_dependencies(self) -> Dict[str, any]:
        """检查外部依赖包"""
        results = {
            "status": "healthy",
            "available_packages": [],
            "missing_packages": [],
            "package_versions": {},
            "recommendations": []
        }
        
        for package_name in self.external_dependencies:
            try:
                # 尝试导入包
                package = importlib.import_module(package_name)
                results["available_packages"].append(package_name)
                
                # 尝试获取版本信息
                version = getattr(package, '__version__', 'unknown')
                results["package_versions"][package_name] = version
                
            except ImportError:
                results["missing_packages"].append(package_name)
                results["status"] = "error"
        
        # 生成建议
        if results["missing_packages"]:
            results["recommendations"].extend([
                "使用 pip install -r requirements.txt 安装依赖",
                f"单独安装缺失的包: pip install {' '.join(results['missing_packages'])}",
                "检查虚拟环境是否正确激活"
            ])
        
        return results
    
    def check_specific_classes(self) -> Dict[str, any]:
        """检查特定类的可用性"""
        class_checks = [
            ('backend.graphrag_engine', 'GraphRAGEngine'),
            ('backend.vector_retrieval', 'VectorRetriever'),
            ('backend.graph_query', 'GraphQueryEngine'),
            ('backend.entity_extractor', 'EntityExtractor'),
            ('backend.hallucination_detector', 'HallucinationDetector'),
            ('backend.earag_evaluator', 'EARAGEvaluator')
        ]
        
        results = {
            "status": "healthy",
            "available_classes": [],
            "missing_classes": [],
            "class_details": {},
            "recommendations": []
        }
        
        for module_name, class_name in class_checks:
            try:
                # 导入模块
                module = importlib.import_module(module_name)
                
                # 检查类是否存在
                if hasattr(module, class_name):
                    results["available_classes"].append(f"{module_name}.{class_name}")
                    
                    # 获取类信息
                    cls = getattr(module, class_name)
                    class_info = {
                        "module": module_name,
                        "class": class_name,
                        "doc": getattr(cls, '__doc__', 'No documentation'),
                        "methods": [method for method in dir(cls) if not method.startswith('_')]
                    }
                    results["class_details"][f"{module_name}.{class_name}"] = class_info
                    
                else:
                    results["missing_classes"].append({
                        "module": module_name,
                        "class": class_name,
                        "error": f"Class {class_name} not found in module {module_name}"
                    })
                    results["status"] = "error"
                    
            except ImportError as e:
                results["missing_classes"].append({
                    "module": module_name,
                    "class": class_name,
                    "error": f"Module import failed: {str(e)}"
                })
                results["status"] = "error"
            except Exception as e:
                results["missing_classes"].append({
                    "module": module_name,
                    "class": class_name,
                    "error": f"Unexpected error: {str(e)}"
                })
                results["status"] = "error"
        
        # 生成建议
        if results["missing_classes"]:
            results["recommendations"].extend([
                "检查相关模块的完整性",
                "验证类名和模块名是否正确",
                "重新安装或更新相关包"
            ])
        
        return results
    
    def run_comprehensive_check(self) -> Dict[str, any]:
        """运行全面的模块导入检查"""
        print("=== Python模块导入全面检查 ===")
        
        comprehensive_results = {
            "timestamp": "",
            "overall_status": "healthy",
            "summary": "",
            "checks": {}
        }
        
        from datetime import datetime
        comprehensive_results["timestamp"] = datetime.now().isoformat()
        
        # 1. Python路径配置检查
        print("1. 检查Python路径配置...")
        path_results = self.check_python_path_configuration()
        comprehensive_results["checks"]["python_path"] = path_results
        
        # 2. 核心模块导入检查
        print("2. 检查核心模块导入...")
        core_results = self.check_core_modules()
        comprehensive_results["checks"]["core_modules"] = core_results
        
        # 3. 外部依赖检查
        print("3. 检查外部依赖包...")
        dependency_results = self.check_external_dependencies()
        comprehensive_results["checks"]["external_dependencies"] = dependency_results
        
        # 4. 特定类检查
        print("4. 检查特定类可用性...")
        class_results = self.check_specific_classes()
        comprehensive_results["checks"]["specific_classes"] = class_results
        
        # 生成整体状态和摘要
        error_count = sum(1 for check in comprehensive_results["checks"].values() if check["status"] == "error")
        warning_count = sum(1 for check in comprehensive_results["checks"].values() if check["status"] == "warning")
        
        if error_count > 0:
            comprehensive_results["overall_status"] = "error"
            comprehensive_results["summary"] = f"发现 {error_count} 个错误和 {warning_count} 个警告"
        elif warning_count > 0:
            comprehensive_results["overall_status"] = "warning"
            comprehensive_results["summary"] = f"发现 {warning_count} 个警告"
        else:
            comprehensive_results["overall_status"] = "healthy"
            comprehensive_results["summary"] = "所有模块导入检查通过"
        
        return comprehensive_results
    
    def generate_fix_script(self, check_results: Dict[str, any]) -> str:
        """根据检查结果生成修复脚本"""
        fix_script_lines = [
            "#!/bin/bash",
            "# GraphRAG模块导入问题修复脚本",
            "# 自动生成于检查结果",
            "",
            "echo '=== GraphRAG模块导入问题修复 ==='",
            ""
        ]
        
        # 检查Python路径问题
        if "python_path" in check_results["checks"]:
            path_check = check_results["checks"]["python_path"]
            if path_check["status"] == "error":
                fix_script_lines.extend([
                    "echo '1. 修复Python路径配置...'",
                    f"export PYTHONPATH=\"{self.project_root}:$PYTHONPATH\"",
                    ""
                ])
                
                # 检查并创建__init__.py文件
                backend_init = os.path.join(self.backend_path, '__init__.py')
                if not os.path.exists(backend_init):
                    fix_script_lines.extend([
                        "echo '创建backend/__init__.py文件...'",
                        f"touch {backend_init}",
                        ""
                    ])
        
        # 检查外部依赖问题
        if "external_dependencies" in check_results["checks"]:
            dep_check = check_results["checks"]["external_dependencies"]
            if dep_check["missing_packages"]:
                fix_script_lines.extend([
                    "echo '2. 安装缺失的Python包...'",
                    f"pip install {' '.join(dep_check['missing_packages'])}",
                    ""
                ])
        
        # 添加启动建议
        fix_script_lines.extend([
            "echo '3. 使用正确的启动方式...'",
            "echo '请使用以下命令启动服务:'",
            f"echo 'cd {self.project_root}'",
            "echo 'python start_server.py api'",
            ""
        ])
        
        return "\n".join(fix_script_lines)


def main():
    """主函数 - 运行模块导入检查"""
    checker = ModuleImportChecker()
    
    # 运行全面检查
    results = checker.run_comprehensive_check()
    
    # 打印结果摘要
    print(f"\n=== 检查结果摘要 ===")
    print(f"整体状态: {results['overall_status']}")
    print(f"摘要: {results['summary']}")
    print(f"检查时间: {results['timestamp']}")
    
    # 打印详细结果
    for check_name, check_result in results["checks"].items():
        print(f"\n--- {check_name} ---")
        print(f"状态: {check_result['status']}")
        
        if check_result.get("issues"):
            print("问题:")
            for issue in check_result["issues"]:
                print(f"  ✗ {issue}")
        
        if check_result.get("failed_imports"):
            print("失败的导入:")
            for failed in check_result["failed_imports"]:
                if isinstance(failed, dict):
                    print(f"  ✗ {failed['module']}: {failed['error']}")
                else:
                    print(f"  ✗ {failed}")
        
        if check_result.get("missing_packages"):
            print("缺失的包:")
            for package in check_result["missing_packages"]:
                print(f"  ✗ {package}")
        
        if check_result.get("recommendations"):
            print("建议:")
            for rec in check_result["recommendations"]:
                print(f"  → {rec}")
    
    # 生成修复脚本
    if results["overall_status"] in ["error", "warning"]:
        print(f"\n=== 生成修复脚本 ===")
        fix_script = checker.generate_fix_script(results)
        
        fix_script_path = os.path.join(checker.project_root, "fix_module_imports.sh")
        with open(fix_script_path, 'w') as f:
            f.write(fix_script)
        
        print(f"修复脚本已生成: {fix_script_path}")
        print("运行修复脚本: bash fix_module_imports.sh")


if __name__ == "__main__":
    main()