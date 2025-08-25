#!/usr/bin/env python3
"""
最终远程Ollama配置验证器
确保系统完全使用远程Ollama服务，检查所有可能的本地连接源
"""

import os
import sys
import psutil
import requests
import subprocess
import logging
import glob
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any

# 添加项目路径
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class RemoteConfigValidator:
    """远程配置验证器"""
    
    def __init__(self):
        self.remote_host = 'http://120.232.79.82:11434'
        self.required_models = ['bge-m3:latest', 'llama3.2:latest']
        self.validation_results = {}
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def run_full_validation(self) -> bool:
        """运行完整的配置验证"""
        print("=" * 80)
        print("🔍 政策法规RAG问答系统 - 远程Ollama配置验证器")
        print("=" * 80)
        
        all_passed = True
        
        # 验证步骤
        validation_steps = [
            ("1️⃣  进程检查", self.check_local_processes),
            ("2️⃣  端口检查", self.check_port_usage),
            ("3️⃣  环境变量验证", self.validate_environment_variables),
            ("4️⃣  代码文件扫描", self.scan_code_files),
            ("5️⃣  远程服务连接", self.test_remote_connection),
            ("6️⃣  模型可用性验证", self.verify_models),
            ("7️⃣  功能测试", self.test_functionality),
            ("8️⃣  组件初始化测试", self.test_component_initialization)
        ]
        
        for step_name, step_func in validation_steps:
            print(f"\n{step_name}")
            print("-" * 60)
            
            try:
                result = step_func()
                self.validation_results[step_name] = result
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"   ❌ 验证步骤失败: {e}")
                self.validation_results[step_name] = False
                all_passed = False
        
        # 打印总结
        self.print_summary()
        
        return all_passed
    
    def check_local_processes(self) -> bool:
        """检查本地ollama进程"""
        print("   检查本地ollama进程...")
        
        ollama_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_name = proc.info['name'].lower()
                    proc_cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    if 'ollama' in proc_name or 'ollama' in proc_cmdline.lower():
                        ollama_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc_name,
                            'cmdline': proc_cmdline
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            print(f"   ⚠️  进程检查失败: {e}")
            return False
        
        if ollama_processes:
            print(f"   ❌ 发现 {len(ollama_processes)} 个本地ollama进程:")
            for proc in ollama_processes:
                print(f"      PID={proc['pid']}, Name={proc['name']}")
                print(f"      命令行: {proc['cmdline'][:100]}...")
            return False
        else:
            print("   ✅ 没有发现本地ollama进程")
            return True
    
    def check_port_usage(self) -> bool:
        """检查关键端口使用情况"""
        print("   检查关键端口使用情况...")
        
        critical_ports = [11434, 64482]  # ollama常用端口
        port_issues = []
        
        try:
            for port in critical_ports:
                listening_processes = []
                for conn in psutil.net_connections():
                    if (conn.laddr.port == port and 
                        conn.status == 'LISTEN'):
                        try:
                            if conn.pid:
                                proc = psutil.Process(conn.pid)
                                listening_processes.append({
                                    'pid': conn.pid,
                                    'name': proc.name(),
                                    'port': port
                                })
                        except:
                            listening_processes.append({
                                'pid': conn.pid or 'unknown',
                                'name': 'unknown',
                                'port': port
                            })
                
                if listening_processes:
                    port_issues.extend(listening_processes)
                    print(f"   ❌ 端口 {port} 被占用:")
                    for proc in listening_processes:
                        print(f"      PID={proc['pid']}, Name={proc['name']}")
                else:
                    print(f"   ✅ 端口 {port} 空闲")
                    
        except Exception as e:
            print(f"   ⚠️  端口检查失败: {e}")
            return False
        
        return len(port_issues) == 0
    
    def validate_environment_variables(self) -> bool:
        """验证环境变量配置"""
        print("   验证环境变量配置...")
        
        required_vars = {
            'LLM_BINDING_HOST': self.remote_host,
            'OLLAMA_HOST': self.remote_host,
            'OLLAMA_BASE_URL': self.remote_host,
            'OLLAMA_NO_SERVE': '1',
            'EMBEDDING_MODEL': 'bge-m3:latest',
            'LLM_MODEL': 'llama3.2:latest'
        }
        
        all_correct = True
        
        for var_name, expected_value in required_vars.items():
            current_value = os.environ.get(var_name)
            if current_value == expected_value:
                print(f"   ✅ {var_name}: {current_value}")
            else:
                print(f"   ❌ {var_name}: '{current_value}' (期望: '{expected_value}')")
                all_correct = False
        
        # 检查可疑的本地配置
        suspicious_patterns = ['127.0.0.1', 'localhost', ':64482']
        for var_name, var_value in os.environ.items():
            if 'OLLAMA' in var_name or 'LLM' in var_name:
                for pattern in suspicious_patterns:
                    if pattern in str(var_value):
                        print(f"   ⚠️  可疑配置: {var_name}={var_value}")
                        all_correct = False
        
        return all_correct
    
    def scan_code_files(self) -> bool:
        """扫描代码文件查找本地连接引用"""
        print("   扫描代码文件查找本地连接引用...")
        
        # 要扫描的文件模式
        file_patterns = [
            'backend/*.py',
            'scripts/*.py',
            '*.py'
        ]
        
        # 要查找的模式
        suspicious_patterns = [
            r'localhost:11434',
            r'127\.0\.0\.1:11434',
            r'localhost:64482',
            r'127\.0\.0\.1:64482',
            r'http://localhost',
            r'http://127\.0\.0\.1',
            r'ollama\.Client\(',
            r'import ollama',
            r'from ollama import'
        ]
        
        issues_found = []
        
        for pattern in file_patterns:
            for file_path in glob.glob(pattern):
                # 跳过某些文件
                if any(skip in file_path for skip in [
                    'final_remote_config_validator.py',
                    'ollama_config_diagnostics.py',
                    '__pycache__',
                    '.pyc'
                ]):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        for i, line in enumerate(content.split('\n'), 1):
                            for pattern_regex in suspicious_patterns:
                                if re.search(pattern_regex, line, re.IGNORECASE):
                                    issues_found.append({
                                        'file': file_path,
                                        'line': i,
                                        'content': line.strip(),
                                        'pattern': pattern_regex
                                    })
                                    
                except Exception as e:
                    print(f"   ⚠️  无法读取文件 {file_path}: {e}")
        
        if issues_found:
            print(f"   ❌ 发现 {len(issues_found)} 个可疑的代码引用:")
            for issue in issues_found[:10]:  # 只显示前10个
                print(f"      {issue['file']}:{issue['line']} - {issue['content'][:80]}...")
            if len(issues_found) > 10:
                print(f"      ... 还有 {len(issues_found) - 10} 个问题")
            return False
        else:
            print("   ✅ 没有发现可疑的代码引用")
            return True
    
    def test_remote_connection(self) -> bool:
        """测试远程服务连接"""
        print("   测试远程Ollama服务连接...")
        
        try:
            # 版本检查
            response = requests.get(f"{self.remote_host}/api/version", timeout=10)
            if response.status_code == 200:
                version_info = response.json()
                print(f"   ✅ 远程服务连接成功，版本: {version_info.get('version', 'unknown')}")
            else:
                print(f"   ❌ 远程服务响应异常: HTTP {response.status_code}")
                return False
                
            # 模型列表检查
            response = requests.get(f"{self.remote_host}/api/tags", timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                models = models_data.get('models', [])
                print(f"   ✅ 成功获取模型列表，共 {len(models)} 个模型")
                return True
            else:
                print(f"   ❌ 模型列表获取失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ 远程连接测试失败: {e}")
            return False
    
    def verify_models(self) -> bool:
        """验证必需模型的可用性"""
        print("   验证必需模型的可用性...")
        
        try:
            response = requests.get(f"{self.remote_host}/api/tags", timeout=10)
            if response.status_code != 200:
                print(f"   ❌ 无法获取模型列表: HTTP {response.status_code}")
                return False
            
            models_data = response.json()
            models = models_data.get('models', [])
            model_names = [m.get('name', '') for m in models]
            
            all_available = True
            for required_model in self.required_models:
                if any(required_model in name for name in model_names):
                    print(f"   ✅ 模型可用: {required_model}")
                else:
                    print(f"   ❌ 模型缺失: {required_model}")
                    all_available = False
            
            if not all_available:
                print(f"   📝 可用模型列表: {', '.join(model_names)}")
            
            return all_available
            
        except Exception as e:
            print(f"   ❌ 模型验证失败: {e}")
            return False
    
    def test_functionality(self) -> bool:
        """测试基本功能"""
        print("   测试基本功能...")
        
        # 测试嵌入模型
        try:
            embedding_payload = {
                "model": "bge-m3:latest",
                "prompt": "测试文本"
            }
            response = requests.post(
                f"{self.remote_host}/api/embeddings", 
                json=embedding_payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'embedding' in result and result['embedding']:
                    print(f"   ✅ 嵌入模型功能正常，向量维度: {len(result['embedding'])}")
                else:
                    print("   ❌ 嵌入模型返回结果异常")
                    return False
            else:
                print(f"   ❌ 嵌入模型测试失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ 嵌入模型测试异常: {e}")
            return False
        
        # 测试LLM模型
        try:
            llm_payload = {
                "model": "llama3.2:latest",
                "prompt": "简单回答：什么是人工智能？",
                "stream": False
            }
            response = requests.post(
                f"{self.remote_host}/api/generate", 
                json=llm_payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'response' in result and result['response']:
                    print(f"   ✅ LLM模型功能正常，响应长度: {len(result['response'])}")
                    return True
                else:
                    print("   ❌ LLM模型返回结果异常")
                    return False
            else:
                print(f"   ❌ LLM模型测试失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ LLM模型测试异常: {e}")
            return False
    
    def test_component_initialization(self) -> bool:
        """测试关键组件初始化"""
        print("   测试关键组件初始化...")
        
        try:
            # 强制设置环境变量
            os.environ['LLM_BINDING_HOST'] = self.remote_host
            os.environ['OLLAMA_HOST'] = self.remote_host
            os.environ['OLLAMA_NO_SERVE'] = '1'
            
            # 测试错误处理客户端
            from backend.ollama_error_handler import OllamaClientWithFallback
            client = OllamaClientWithFallback()
            current_host = client.current_host
            
            if 'localhost' in current_host or '127.0.0.1' in current_host:
                print(f"   ❌ 错误处理客户端仍使用本地地址: {current_host}")
                return False
            else:
                print(f"   ✅ 错误处理客户端使用正确地址: {current_host}")
            
            # 测试实体提取器
            from backend.entity_extractor import EntityExtractor
            extractor = EntityExtractor()
            extractor_host = extractor.ollama_host
            
            if 'localhost' in extractor_host or '127.0.0.1' in extractor_host:
                print(f"   ❌ 实体提取器仍使用本地地址: {extractor_host}")
                return False
            else:
                print(f"   ✅ 实体提取器使用正确地址: {extractor_host}")
            
            # 测试连接管理器
            from backend.connections import OllamaConnectionManager
            conn_manager = OllamaConnectionManager(
                host=self.remote_host,
                model='llama3.2:latest'
            )
            manager_host = conn_manager.host
            
            if 'localhost' in manager_host or '127.0.0.1' in manager_host:
                print(f"   ❌ 连接管理器仍使用本地地址: {manager_host}")
                return False
            else:
                print(f"   ✅ 连接管理器使用正确地址: {manager_host}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 组件初始化测试失败: {e}")
            return False
    
    def print_summary(self):
        """打印验证总结"""
        print("\n" + "=" * 80)
        print("📊 验证结果总结")
        print("=" * 80)
        
        passed_count = sum(1 for result in self.validation_results.values() if result)
        total_count = len(self.validation_results)
        
        for step_name, result in self.validation_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{step_name:<30} {status}")
        
        print("-" * 80)
        print(f"总体结果: {passed_count}/{total_count} 项通过")
        
        if passed_count == total_count:
            print("\n🎉 恭喜！所有验证都通过了")
            print("✅ 系统已正确配置为使用远程Ollama服务")
            print("✅ 不会再出现本地连接尝试")
            print("✅ 可以安全运行GraphRAG数据导入")
        else:
            print(f"\n⚠️  还有 {total_count - passed_count} 项验证失败")
            print("请根据上述错误信息进行修复")
            
            # 提供修复建议
            print("\n🔧 修复建议:")
            if not self.validation_results.get("1️⃣  进程检查", True):
                print("   - 终止所有本地ollama进程: taskkill /F /IM ollama.exe")
            if not self.validation_results.get("2️⃣  端口检查", True):
                print("   - 释放被占用的11434/64482端口")
            if not self.validation_results.get("3️⃣  环境变量验证", True):
                print("   - 设置正确的环境变量指向远程服务")
            if not self.validation_results.get("4️⃣  代码文件扫描", True):
                print("   - 修复代码中的本地连接引用")
            if not self.validation_results.get("5️⃣  远程服务连接", True):
                print("   - 检查网络连接和远程服务状态")
    
    def force_fix_issues(self):
        """强制修复发现的问题"""
        print("\n🔧 尝试自动修复问题...")
        
        # 1. 终止本地进程
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if 'ollama' in proc.info['name'].lower():
                    proc.terminate()
                    print(f"   ✅ 已终止进程: {proc.info['pid']}")
        except Exception as e:
            print(f"   ⚠️  进程终止失败: {e}")
        
        # 2. 强制设置环境变量
        required_vars = {
            'LLM_BINDING_HOST': self.remote_host,
            'OLLAMA_HOST': self.remote_host,
            'OLLAMA_BASE_URL': self.remote_host,
            'OLLAMA_NO_SERVE': '1',
            'OLLAMA_ORIGINS': '*'
        }
        
        for var, value in required_vars.items():
            os.environ[var] = value
            print(f"   ✅ 设置环境变量: {var}={value}")


def main():
    """主函数"""
    validator = RemoteConfigValidator()
    
    success = validator.run_full_validation()
    
    if not success:
        print("\n🤔 是否尝试自动修复问题？(y/N): ", end="")
        try:
            user_input = input().strip().lower()
            if user_input == 'y':
                validator.force_fix_issues()
                print("\n🔄 重新运行验证...")
                success = validator.run_full_validation()
        except KeyboardInterrupt:
            print("\n⏹️  用户取消操作")
    
    if success:
        print("\n🚀 系统配置正确，可以运行:")
        print("   python run_graphrag_import.py")
    else:
        print("\n❌ 系统配置仍有问题，请手动修复")
    
    return success


if __name__ == '__main__':
    main()