#!/usr/bin/env python3
"""
远程Ollama配置诊断工具
用于诊断和修复远程Ollama服务配置问题
"""

import os
import sys
import logging
import requests
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

# 设置项目路径
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 加载环境变量
load_dotenv()

class OllamaConfigDiagnostics:
    """远程Ollama配置诊断工具"""
    
    def __init__(self):
        self.remote_host = 'http://120.232.79.82:11434'
        self.required_models = ['bge-m3:latest', 'llama3.2:latest']
        self.timeout = 30
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def run_full_diagnosis(self) -> Dict:
        """运行完整诊断"""
        print("🔍 开始远程Ollama配置全面诊断")
        print("=" * 60)
        
        # 诊断结果
        results = {
            'overall_status': 'unknown',
            'checks': {},
            'recommendations': [],
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 1. 环境变量检查
        print("\n📋 1. 环境变量配置检查")
        env_result = self.check_environment_variables()
        results['checks']['environment'] = env_result
        self.print_check_result("环境变量配置", env_result)
        
        # 2. 网络连接检查
        print("\n🌐 2. 网络连接检查")
        network_result = self.check_network_connectivity()
        results['checks']['network'] = network_result
        self.print_check_result("网络连接", network_result)
        
        # 3. Ollama服务检查
        print("\n🛠️ 3. Ollama服务可用性检查")
        service_result = self.check_ollama_service()
        results['checks']['service'] = service_result
        self.print_check_result("Ollama服务", service_result)
        
        # 4. 模型可用性检查
        print("\n🤖 4. 模型可用性检查")
        model_result = self.check_model_availability()
        results['checks']['models'] = model_result
        self.print_check_result("模型可用性", model_result)
        
        # 5. 功能测试
        print("\n⚡ 5. 功能测试")
        function_result = self.test_ollama_functions()
        results['checks']['functions'] = function_result
        self.print_check_result("功能测试", function_result)
        
        # 6. 本地配置冲突检查
        print("\n🔧 6. 本地配置冲突检查")
        conflict_result = self.check_local_conflicts()
        results['checks']['conflicts'] = conflict_result
        self.print_check_result("本地配置冲突", conflict_result)
        
        # 计算总体状态
        results['overall_status'] = self.calculate_overall_status(results['checks'])
        
        # 生成建议
        results['recommendations'] = self.generate_recommendations(results['checks'])
        
        # 显示总结
        self.print_summary(results)
        
        return results
    
    def check_environment_variables(self) -> Dict:
        """检查环境变量配置"""
        required_configs = {
            'LLM_BINDING_HOST': self.remote_host,
            'OLLAMA_HOST': self.remote_host,
            'OLLAMA_BASE_URL': self.remote_host,
            'OLLAMA_NO_SERVE': '1',
            'EMBEDDING_MODEL': 'bge-m3:latest',
            'LLM_MODEL': 'llama3.2:latest'
        }
        
        results = {
            'success': True,
            'details': {},
            'issues': []
        }
        
        for key, expected in required_configs.items():
            current = os.environ.get(key)
            if current == expected:
                results['details'][key] = {'status': 'correct', 'value': current}
                print(f"   ✅ {key}: {current}")
            else:
                results['details'][key] = {
                    'status': 'incorrect', 
                    'current': current, 
                    'expected': expected
                }
                results['issues'].append(f"{key} 配置错误: {current} (期望: {expected})")
                results['success'] = False
                print(f"   ❌ {key}: {current} (期望: {expected})")
        
        # 检查可疑的本地配置
        suspicious_patterns = ['127.0.0.1', 'localhost', ':64482']
        for key in ['LLM_BINDING_HOST', 'OLLAMA_HOST', 'OLLAMA_BASE_URL']:
            value = os.environ.get(key, '')
            for pattern in suspicious_patterns:
                if pattern in value:
                    results['issues'].append(f"检测到可疑的本地配置: {key}={value}")
                    results['success'] = False
                    print(f"   ⚠️ 可疑配置: {key}={value}")
        
        return results
    
    def check_network_connectivity(self) -> Dict:
        """检查网络连接"""
        try:
            print(f"   🔗 测试连接: {self.remote_host}")
            response = requests.get(f"{self.remote_host}/api/version", timeout=10)
            
            if response.status_code == 200:
                version_data = response.json()
                return {
                    'success': True,
                    'response_time': response.elapsed.total_seconds(),
                    'version': version_data.get('version', 'unknown'),
                    'details': f"连接成功，响应时间: {response.elapsed.total_seconds():.2f}秒"
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'details': f"服务响应异常: {response.status_code}"
                }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'timeout',
                'details': '连接超时，可能是网络问题或服务不可用'
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'success': False,
                'error': 'connection_error',
                'details': f'连接失败: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': 'unknown',
                'details': f'未知错误: {str(e)}'
            }
    
    def check_ollama_service(self) -> Dict:
        """检查Ollama服务状态"""
        try:
            # 检查服务健康状态
            response = requests.get(f"{self.remote_host}/api/tags", timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                
                return {
                    'success': True,
                    'model_count': len(models),
                    'models': [m.get('name', '') for m in models],
                    'details': f"服务正常，已安装 {len(models)} 个模型"
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'details': f"服务状态异常: {response.status_code}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': f'服务检查失败: {str(e)}'
            }
    
    def check_model_availability(self) -> Dict:
        """检查所需模型是否可用"""
        try:
            response = requests.get(f"{self.remote_host}/api/tags", timeout=self.timeout)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'details': '无法获取模型列表'
                }
            
            data = response.json()
            available_models = [m.get('name', '') for m in data.get('models', [])]
            
            results = {
                'success': True,
                'available_models': available_models,
                'model_status': {},
                'missing_models': []
            }
            
            for required_model in self.required_models:
                is_available = any(required_model in model for model in available_models)
                results['model_status'][required_model] = is_available
                
                if is_available:
                    print(f"   ✅ {required_model}: 可用")
                else:
                    print(f"   ❌ {required_model}: 不可用")
                    results['missing_models'].append(required_model)
                    results['success'] = False
            
            return results
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': f'模型检查失败: {str(e)}'
            }
    
    def test_ollama_functions(self) -> Dict:
        """测试Ollama核心功能"""
        results = {
            'success': True,
            'tests': {},
            'details': []
        }
        
        # 测试嵌入功能
        embedding_result = self.test_embedding_function()
        results['tests']['embedding'] = embedding_result
        if not embedding_result['success']:
            results['success'] = False
        
        # 测试生成功能
        generation_result = self.test_generation_function()
        results['tests']['generation'] = generation_result
        if not generation_result['success']:
            results['success'] = False
        
        return results
    
    def test_embedding_function(self) -> Dict:
        """测试嵌入功能"""
        try:
            print("   🧪 测试嵌入功能...")
            payload = {
                "model": "bge-m3:latest",
                "prompt": "测试文本"
            }
            
            response = requests.post(
                f"{self.remote_host}/api/embeddings", 
                json=payload, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'embedding' in result and result['embedding']:
                    embedding_dim = len(result['embedding'])
                    print(f"      ✅ 嵌入功能正常，向量维度: {embedding_dim}")
                    return {
                        'success': True,
                        'embedding_dimension': embedding_dim,
                        'response_time': response.elapsed.total_seconds()
                    }
                else:
                    print("      ❌ 嵌入功能异常：返回结果格式错误")
                    return {
                        'success': False,
                        'error': '返回结果格式错误'
                    }
            else:
                print(f"      ❌ 嵌入功能异常：HTTP {response.status_code}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            print(f"      ❌ 嵌入功能测试失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_generation_function(self) -> Dict:
        """测试文本生成功能"""
        try:
            print("   🧪 测试文本生成功能...")
            payload = {
                "model": "llama3.2:latest",
                "prompt": "简单回答：1+1等于多少？",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "max_tokens": 50
                }
            }
            
            response = requests.post(
                f"{self.remote_host}/api/generate", 
                json=payload, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'response' in result and result['response']:
                    generated_text = result['response'].strip()
                    print(f"      ✅ 文本生成功能正常，生成内容: {generated_text[:50]}...")
                    return {
                        'success': True,
                        'generated_text': generated_text,
                        'response_time': response.elapsed.total_seconds()
                    }
                else:
                    print("      ❌ 文本生成功能异常：返回结果格式错误")
                    return {
                        'success': False,
                        'error': '返回结果格式错误'
                    }
            else:
                print(f"      ❌ 文本生成功能异常：HTTP {response.status_code}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            print(f"      ❌ 文本生成功能测试失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_local_conflicts(self) -> Dict:
        """检查本地配置冲突"""
        conflicts = []
        
        # 检查环境变量中的本地地址
        local_patterns = ['127.0.0.1', 'localhost', ':64482', ':11434']
        env_vars_to_check = [
            'LLM_BINDING_HOST', 'OLLAMA_HOST', 'OLLAMA_BASE_URL',
            'OLLAMA_API_BASE', 'OLLAMA_ENDPOINT'
        ]
        
        for var in env_vars_to_check:
            value = os.environ.get(var, '')
            for pattern in local_patterns:
                if pattern in value and 'http://120.232.79.82' not in value:
                    conflicts.append(f"环境变量 {var} 包含本地地址模式: {value}")
        
        # 检查OLLAMA_NO_SERVE设置
        no_serve = os.environ.get('OLLAMA_NO_SERVE', '')
        if no_serve != '1':
            conflicts.append(f"OLLAMA_NO_SERVE 未正确设置为 '1'，当前值: '{no_serve}'")
        
        if conflicts:
            for conflict in conflicts:
                print(f"   ⚠️ {conflict}")
            return {
                'success': False,
                'conflicts': conflicts,
                'details': f"发现 {len(conflicts)} 个配置冲突"
            }
        else:
            print("   ✅ 未发现本地配置冲突")
            return {
                'success': True,
                'conflicts': [],
                'details': "未发现配置冲突"
            }
    
    def print_check_result(self, check_name: str, result: Dict):
        """打印检查结果"""
        status = "✅ 通过" if result['success'] else "❌ 失败"
        details = result.get('details', '')
        print(f"   状态: {status}")
        if details:
            print(f"   详情: {details}")
    
    def calculate_overall_status(self, checks: Dict) -> str:
        """计算总体状态"""
        critical_checks = ['network', 'service', 'models']
        critical_passed = all(checks.get(check, {}).get('success', False) for check in critical_checks)
        
        if critical_passed:
            return 'healthy'
        else:
            return 'unhealthy'
    
    def generate_recommendations(self, checks: Dict) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        # 环境变量建议
        if not checks.get('environment', {}).get('success', False):
            recommendations.append("修复环境变量配置：运行 force_remote_ollama_config() 函数")
        
        # 网络连接建议
        if not checks.get('network', {}).get('success', False):
            recommendations.append("检查网络连接：确保可以访问 http://120.232.79.82:11434")
        
        # 模型建议
        model_check = checks.get('models', {})
        if not model_check.get('success', False):
            missing = model_check.get('missing_models', [])
            if missing:
                recommendations.append(f"安装缺失的模型：{', '.join(missing)}")
        
        # 功能测试建议
        function_check = checks.get('functions', {})
        if not function_check.get('success', False):
            recommendations.append("Ollama功能异常，检查服务状态和模型安装")
        
        # 配置冲突建议
        conflict_check = checks.get('conflicts', {})
        if not conflict_check.get('success', False):
            recommendations.append("解决配置冲突：清理本地Ollama配置")
        
        return recommendations
    
    def print_summary(self, results: Dict):
        """打印诊断总结"""
        print("\n" + "=" * 60)
        print("🎯 诊断总结")
        print("=" * 60)
        
        status = results['overall_status']
        if status == 'healthy':
            print("✅ 总体状态: 健康 - 远程Ollama配置正常")
        else:
            print("❌ 总体状态: 异常 - 需要修复配置问题")
        
        recommendations = results.get('recommendations', [])
        if recommendations:
            print("\n🔧 修复建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        else:
            print("\n🎉 无需额外修复，配置已正确！")
        
        print(f"\n📅 诊断时间: {results['timestamp']}")
    
    def force_fix_configuration(self):
        """强制修复配置"""
        print("🔧 开始强制修复远程Ollama配置...")
        
        config_vars = {
            'LLM_BINDING_HOST': self.remote_host,
            'OLLAMA_HOST': self.remote_host,
            'OLLAMA_BASE_URL': self.remote_host,
            'OLLAMA_NO_SERVE': '1',
            'OLLAMA_ORIGINS': '*',
            'OLLAMA_KEEP_ALIVE': '5m',
            'EMBEDDING_MODEL': 'bge-m3:latest',
            'LLM_MODEL': 'llama3.2:latest',
            'LLM_BINDING': 'ollama'
        }
        
        for key, value in config_vars.items():
            old_value = os.environ.get(key)
            os.environ[key] = value
            if old_value != value:
                print(f"   ✅ {key}: {old_value} -> {value}")
            else:
                print(f"   ✓ {key}: {value}")
        
        print("✅ 配置修复完成")


def main():
    """主函数"""
    print("🔍 远程Ollama配置诊断工具")
    print("=" * 60)
    
    diagnostics = OllamaConfigDiagnostics()
    
    # 运行诊断
    results = diagnostics.run_full_diagnosis()
    
    # 如果检测到问题，询问是否自动修复
    if results['overall_status'] != 'healthy':
        print("\n❓ 检测到配置问题，是否自动修复？")
        choice = input("输入 'y' 自动修复，其他键跳过: ").strip().lower()
        
        if choice == 'y':
            diagnostics.force_fix_configuration()
            print("\n🔄 重新运行诊断验证修复效果...")
            diagnostics.run_full_diagnosis()
    
    return results


if __name__ == "__main__":
    main()