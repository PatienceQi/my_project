"""
政策法规RAG问答系统 - 环境配置验证工具

专门用于验证系统环境配置的正确性和完整性
"""

import os
import sys
import subprocess
import importlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class EnvironmentConfigValidator:
    """环境配置验证器"""
    
    def __init__(self):
        # 必需的环境变量及其期望值
        self.required_env_vars = {
            'LLM_BINDING_HOST': {
                'expected': 'http://120.232.79.82:11434',
                'description': 'Ollama远程服务地址',
                'critical': True
            },
            'NEO4J_URI': {
                'expected': 'neo4j://localhost:7687',
                'description': 'Neo4j数据库连接URI',
                'critical': True
            },
            'NEO4J_USERNAME': {
                'expected': 'neo4j',
                'description': 'Neo4j数据库用户名',
                'critical': True
            },
            'NEO4J_PASSWORD': {
                'expected': None,  # 不验证具体值，只检查是否存在
                'description': 'Neo4j数据库密码',
                'critical': True
            },
            'LLM_MODEL': {
                'expected': 'llama3.2:latest',
                'description': '使用的语言模型',
                'critical': False
            },
            'LLM_TIMEOUT': {
                'expected': '600',
                'description': 'LLM请求超时时间(秒)',
                'critical': False
            },
            'NEO4J_MAX_POOL_SIZE': {
                'expected': '10',
                'description': 'Neo4j连接池最大大小',
                'critical': False
            },
            'EXPERIMENT_MODE': {
                'expected': 'true',
                'description': '实验模式开关',
                'critical': False
            }
        }
        
        # 核心Python包依赖
        self.required_packages = [
            {
                'name': 'neo4j',
                'min_version': '5.14.0',
                'description': 'Neo4j数据库驱动',
                'critical': True
            },
            {
                'name': 'flask',
                'min_version': '3.0.0',
                'description': 'Web框架',
                'critical': True
            },
            {
                'name': 'flask_cors',
                'min_version': '4.0.0',
                'description': 'Flask CORS支持',
                'critical': True
            },
            {
                'name': 'requests',
                'min_version': '2.31.0',
                'description': 'HTTP客户端库',
                'critical': True
            },
            {
                'name': 'python-dotenv',
                'min_version': None,
                'description': '环境变量加载',
                'critical': True
            },
            {
                'name': 'chromadb',
                'min_version': '0.4.15',
                'description': '向量数据库',
                'critical': True
            },
            {
                'name': 'sentence-transformers',
                'min_version': '2.2.2',
                'description': '句子嵌入模型',
                'critical': True
            },
            {
                'name': 'jieba',
                'min_version': None,
                'description': '中文分词',
                'critical': True
            },
            {
                'name': 'numpy',
                'min_version': None,
                'description': '数值计算库',
                'critical': True
            },
            {
                'name': 'psutil',
                'min_version': None,
                'description': '系统监控',
                'critical': False
            }
        ]
        
        # 系统环境要求
        self.system_requirements = {
            'python_min_version': '3.8',
            'memory_min_gb': 4,
            'disk_min_gb': 1
        }
    
    def validate_environment_variables(self) -> Dict[str, Any]:
        """验证环境变量配置"""
        result = {
            'status': 'healthy',
            'message': '环境变量配置正常',
            'details': {
                'missing_vars': [],
                'incorrect_vars': [],
                'warning_vars': [],
                'valid_vars': []
            },
            'recommendations': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for var_name, var_config in self.required_env_vars.items():
            current_value = os.getenv(var_name)
            expected_value = var_config['expected']
            is_critical = var_config['critical']
            
            if not current_value:
                result['details']['missing_vars'].append({
                    'name': var_name,
                    'description': var_config['description'],
                    'critical': is_critical
                })
                
                if is_critical:
                    result['status'] = 'error'
                    result['recommendations'].append(f'设置关键环境变量 {var_name}')
                else:
                    result['recommendations'].append(f'建议设置环境变量 {var_name}')
                
            elif expected_value and current_value != expected_value:
                # 特殊处理某些变量
                if var_name == 'LLM_BINDING_HOST':
                    # 检查是否使用了本地地址
                    if '127.0.0.1' in current_value or 'localhost' in current_value:
                        result['details']['incorrect_vars'].append({
                            'name': var_name,
                            'current': current_value,
                            'expected': expected_value,
                            'issue': '配置了本地地址',
                            'critical': True
                        })
                        result['status'] = 'error'
                        result['recommendations'].append(f'将 {var_name} 修改为远程地址: {expected_value}')
                    else:
                        # 不是期望值但也不是本地地址，给出警告
                        result['details']['warning_vars'].append({
                            'name': var_name,
                            'current': current_value,
                            'expected': expected_value,
                            'issue': '值不匹配期望配置'
                        })
                        if result['status'] == 'healthy':
                            result['status'] = 'warning'
                        result['recommendations'].append(f'检查 {var_name} 配置是否正确')
                else:
                    # 其他变量的不匹配处理
                    if is_critical:
                        result['details']['incorrect_vars'].append({
                            'name': var_name,
                            'current': current_value,
                            'expected': expected_value,
                            'critical': True
                        })
                        result['status'] = 'error'
                        result['recommendations'].append(f'修正关键环境变量 {var_name} 的值')
                    else:
                        result['details']['warning_vars'].append({
                            'name': var_name,
                            'current': current_value,
                            'expected': expected_value
                        })
                        if result['status'] == 'healthy':
                            result['status'] = 'warning'
            else:
                # 变量配置正确
                result['details']['valid_vars'].append({
                    'name': var_name,
                    'value': current_value if var_name != 'NEO4J_PASSWORD' else '***',
                    'description': var_config['description']
                })
        
        # 更新消息
        if result['status'] == 'error':
            error_count = len(result['details']['missing_vars']) + len(result['details']['incorrect_vars'])
            result['message'] = f'环境变量配置存在 {error_count} 个关键问题'
        elif result['status'] == 'warning':
            warning_count = len(result['details']['warning_vars'])
            result['message'] = f'环境变量配置存在 {warning_count} 个警告'
        
        return result
    
    def validate_python_packages(self) -> Dict[str, Any]:
        """验证Python包依赖"""
        result = {
            'status': 'healthy',
            'message': 'Python包依赖满足要求',
            'details': {
                'missing_packages': [],
                'version_issues': [],
                'valid_packages': [],
                'package_versions': {}
            },
            'recommendations': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for package_info in self.required_packages:
            package_name = package_info['name']
            min_version = package_info['min_version']
            is_critical = package_info['critical']
            
            try:
                # 尝试导入包
                package = importlib.import_module(package_name)
                
                # 获取版本信息
                version = getattr(package, '__version__', 'unknown')
                result['details']['package_versions'][package_name] = version
                
                # 版本检查
                if min_version and version != 'unknown':
                    if self._compare_versions(version, min_version) < 0:
                        result['details']['version_issues'].append({
                            'name': package_name,
                            'current': version,
                            'required': min_version,
                            'critical': is_critical
                        })
                        
                        if is_critical:
                            result['status'] = 'error'
                            result['recommendations'].append(f'升级关键包 {package_name} 到 {min_version} 或更高版本')
                        else:
                            if result['status'] == 'healthy':
                                result['status'] = 'warning'
                            result['recommendations'].append(f'建议升级 {package_name} 到 {min_version} 或更高版本')
                    else:
                        result['details']['valid_packages'].append({
                            'name': package_name,
                            'version': version,
                            'description': package_info['description']
                        })
                else:
                    result['details']['valid_packages'].append({
                        'name': package_name,
                        'version': version,
                        'description': package_info['description']
                    })
                    
            except ImportError:
                result['details']['missing_packages'].append({
                    'name': package_name,
                    'description': package_info['description'],
                    'required_version': min_version,
                    'critical': is_critical
                })
                
                if is_critical:
                    result['status'] = 'error'
                    result['recommendations'].append(f'安装关键包: pip install {package_name}')
                else:
                    if result['status'] == 'healthy':
                        result['status'] = 'warning'
                    result['recommendations'].append(f'建议安装: pip install {package_name}')
        
        # 更新消息
        if result['status'] == 'error':
            missing_critical = len([p for p in result['details']['missing_packages'] if p['critical']])
            version_critical = len([p for p in result['details']['version_issues'] if p['critical']])
            result['message'] = f'Python包依赖存在 {missing_critical + version_critical} 个关键问题'
        elif result['status'] == 'warning':
            warning_count = len(result['details']['missing_packages']) + len(result['details']['version_issues'])
            result['message'] = f'Python包依赖存在 {warning_count} 个建议性问题'
        
        return result
    
    def validate_system_environment(self) -> Dict[str, Any]:
        """验证系统环境"""
        result = {
            'status': 'healthy',
            'message': '系统环境满足要求', 
            'details': {
                'python_version': sys.version,
                'python_executable': sys.executable,
                'platform': sys.platform,
                'working_directory': os.getcwd(),
                'system_path': os.environ.get('PATH', ''),
                'python_path': sys.path
            },
            'recommendations': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # 检查Python版本
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        min_python_version = self.system_requirements['python_min_version']
        
        if self._compare_versions(python_version, min_python_version) < 0:
            result['status'] = 'error'
            result['message'] = f'Python版本过低: {python_version} < {min_python_version}'
            result['recommendations'].append(f'升级Python到 {min_python_version} 或更高版本')
        else:
            result['details']['python_version_check'] = 'passed'
        
        # 检查项目结构
        project_structure_issues = []
        
        # 检查backend目录
        if not os.path.exists('backend'):
            project_structure_issues.append('缺少backend目录')
        elif not os.path.exists('backend/__init__.py'):
            project_structure_issues.append('backend目录缺少__init__.py文件')
        
        # 检查关键文件
        critical_files = [
            'start_server.py',
            'requirements.txt',
            'backend/api_server.py',
            'backend/graphrag_engine.py'
        ]
        
        missing_files = []
        for file_path in critical_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            project_structure_issues.extend([f'缺少关键文件: {f}' for f in missing_files])
        
        if project_structure_issues:
            result['status'] = 'error'
            result['message'] = '项目结构不完整'
            result['details']['structure_issues'] = project_structure_issues
            result['recommendations'].extend([
                '检查项目目录结构',
                '确保在正确的项目根目录运行',
                '恢复缺失的文件'
            ])
        else:
            result['details']['project_structure'] = 'valid'
        
        # 检查磁盘空间（如果可能）
        try:
            import shutil
            total, used, free = shutil.disk_usage('.')
            free_gb = free / (1024**3)
            
            result['details']['disk_space_gb'] = {
                'total': round(total / (1024**3), 2),
                'used': round(used / (1024**3), 2),
                'free': round(free_gb, 2)
            }
            
            if free_gb < self.system_requirements['disk_min_gb']:
                if result['status'] == 'healthy':
                    result['status'] = 'warning'
                result['recommendations'].append(f'磁盘空间不足，建议至少 {self.system_requirements["disk_min_gb"]}GB')
                
        except Exception:
            pass  # 忽略磁盘空间检查失败
        
        return result
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """比较版本号，返回 -1, 0, 1"""
        try:
            v1_parts = [int(x) for x in version1.split('.')][:3]  # 只比较前3位
            v2_parts = [int(x) for x in version2.split('.')][:3]
            
            # 补齐到3位
            while len(v1_parts) < 3:
                v1_parts.append(0)
            while len(v2_parts) < 3:
                v2_parts.append(0)
            
            if v1_parts < v2_parts:
                return -1
            elif v1_parts > v2_parts:
                return 1
            else:
                return 0
        except ValueError:
            # 如果版本号格式不正确，认为相等
            return 0
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """运行全面的环境配置验证"""
        print("=== 环境配置全面验证 ===")
        
        comprehensive_results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'summary': '',
            'validations': {}
        }
        
        # 1. 环境变量验证
        print("1. 验证环境变量配置...")
        env_result = self.validate_environment_variables()
        comprehensive_results['validations']['environment_variables'] = env_result
        
        # 2. Python包依赖验证
        print("2. 验证Python包依赖...")
        package_result = self.validate_python_packages()
        comprehensive_results['validations']['python_packages'] = package_result
        
        # 3. 系统环境验证
        print("3. 验证系统环境...")
        system_result = self.validate_system_environment()
        comprehensive_results['validations']['system_environment'] = system_result
        
        # 生成整体状态和摘要
        validation_statuses = [result['status'] for result in comprehensive_results['validations'].values()]
        
        error_count = validation_statuses.count('error')
        warning_count = validation_statuses.count('warning')
        healthy_count = validation_statuses.count('healthy')
        
        if error_count > 0:
            comprehensive_results['overall_status'] = 'error'
            comprehensive_results['summary'] = f'环境配置存在 {error_count} 个严重问题和 {warning_count} 个警告'
        elif warning_count > 0:
            comprehensive_results['overall_status'] = 'warning'
            comprehensive_results['summary'] = f'环境配置存在 {warning_count} 个警告，{healthy_count} 项正常'
        else:
            comprehensive_results['overall_status'] = 'healthy'
            comprehensive_results['summary'] = f'环境配置完全正常，所有 {healthy_count} 项验证通过'
        
        return comprehensive_results
    
    def generate_environment_setup_script(self, validation_results: Dict[str, Any]) -> str:
        """根据验证结果生成环境配置脚本"""
        script_lines = [
            "#!/bin/bash",
            "# GraphRAG系统环境配置脚本",
            "# 根据验证结果自动生成",
            "",
            "echo '=== GraphRAG系统环境配置 ==='",
            ""
        ]
        
        # 环境变量设置
        env_validation = validation_results['validations'].get('environment_variables', {})
        if env_validation.get('details', {}).get('missing_vars') or env_validation.get('details', {}).get('incorrect_vars'):
            script_lines.extend([
                "echo '1. 设置环境变量...'",
                ""
            ])
            
            # 添加缺失的环境变量
            for var in env_validation.get('details', {}).get('missing_vars', []):
                var_name = var['name']
                expected_value = self.required_env_vars[var_name]['expected']
                if expected_value:
                    script_lines.append(f"export {var_name}='{expected_value}'")
                else:
                    script_lines.append(f"# 请手动设置 {var_name} 的值")
                    script_lines.append(f"# export {var_name}='your_value_here'")
            
            # 修正错误的环境变量
            for var in env_validation.get('details', {}).get('incorrect_vars', []):
                var_name = var['name']
                expected_value = var['expected']
                script_lines.append(f"export {var_name}='{expected_value}'")
            
            script_lines.append("")
        
        # Python包安装
        package_validation = validation_results['validations'].get('python_packages', {})
        missing_packages = package_validation.get('details', {}).get('missing_packages', [])
        version_issues = package_validation.get('details', {}).get('version_issues', [])
        
        if missing_packages or version_issues:
            script_lines.extend([
                "echo '2. 安装Python包依赖...'",
                ""
            ])
            
            # 安装缺失的包
            if missing_packages:
                package_names = [p['name'] for p in missing_packages]
                script_lines.append(f"pip install {' '.join(package_names)}")
            
            # 升级版本有问题的包
            if version_issues:
                for package in version_issues:
                    name = package['name']
                    required = package['required']
                    script_lines.append(f"pip install '{name}>={required}'")
            
            script_lines.extend([
                "",
                "# 或者使用requirements.txt安装所有依赖",
                "# pip install -r requirements.txt",
                ""
            ])
        
        # 项目结构修复
        system_validation = validation_results['validations'].get('system_environment', {})
        structure_issues = system_validation.get('details', {}).get('structure_issues', [])
        
        if structure_issues:
            script_lines.extend([
                "echo '3. 修复项目结构...'",
                ""
            ])
            
            if 'backend目录缺少__init__.py文件' in structure_issues:
                script_lines.append("touch backend/__init__.py")
            
            script_lines.append("")
        
        # 启动建议
        script_lines.extend([
            "echo '4. 配置完成，使用以下命令启动服务:'",
            "echo 'python start_server.py api'",
            ""
        ])
        
        return "\n".join(script_lines)


def main():
    """主函数 - 运行环境配置验证"""
    validator = EnvironmentConfigValidator()
    
    # 运行全面验证
    results = validator.run_comprehensive_validation()
    
    # 打印结果摘要
    print(f"\n=== 验证结果摘要 ===")
    print(f"整体状态: {results['overall_status']}")
    print(f"摘要: {results['summary']}")
    print(f"验证时间: {results['timestamp']}")
    
    # 打印详细结果
    for validation_name, validation_result in results['validations'].items():
        print(f"\n--- {validation_name} ---")
        print(f"状态: {validation_result['status']}")
        print(f"消息: {validation_result['message']}")
        
        if validation_result.get('recommendations'):
            print("建议:")
            for rec in validation_result['recommendations']:
                print(f"  → {rec}")
    
    # 生成配置脚本
    if results['overall_status'] in ['error', 'warning']:
        print(f"\n=== 生成环境配置脚本 ===")
        setup_script = validator.generate_environment_setup_script(results)
        
        script_path = os.path.join(os.getcwd(), "setup_environment.sh")
        with open(script_path, 'w') as f:
            f.write(setup_script)
        
        print(f"环境配置脚本已生成: {script_path}")
        print("运行配置脚本: bash setup_environment.sh")


if __name__ == "__main__":
    main()