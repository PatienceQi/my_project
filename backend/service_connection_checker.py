"""
政策法规RAG问答系统 - 依赖服务连接检查工具

专门用于检测和诊断Neo4j、Ollama、ChromaDB等服务的连接状态
"""

import os
import time
import json
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta


class ServiceConnectionChecker:
    """服务连接检查器"""
    
    def __init__(self):
        self.neo4j_config = self._get_neo4j_config()
        self.ollama_config = self._get_ollama_config()
        self.chromadb_config = self._get_chromadb_config()
        
    def _get_neo4j_config(self) -> Dict[str, Any]:
        """获取Neo4j配置"""
        return {
            'uri': os.getenv('NEO4J_URI', 'neo4j://localhost:7687'),
            'username': os.getenv('NEO4J_USERNAME', 'neo4j'),
            'password': os.getenv('NEO4J_PASSWORD', 'password'),
            'timeout': int(os.getenv('NEO4J_CONNECTION_TIMEOUT', '30'))
        }
    
    def _get_ollama_config(self) -> Dict[str, Any]:
        """获取Ollama配置"""
        return {
            'host': os.getenv('LLM_BINDING_HOST', 'http://120.232.79.82:11434'),
            'model': os.getenv('LLM_MODEL', 'llama3.2:latest'),
            'timeout': int(os.getenv('LLM_TIMEOUT', '30'))
        }
    
    def _get_chromadb_config(self) -> Dict[str, Any]:
        """获取ChromaDB配置"""
        return {
            'data_path': os.path.join(os.getcwd(), 'data', 'simple_vector_store.json'),
            'collection_name': 'policy_documents'
        }
    
    def check_neo4j_connection(self) -> Dict[str, Any]:
        """检查Neo4j数据库连接"""
        result = {
            "service": "neo4j",
            "status": "healthy",
            "message": "",
            "details": {},
            "recommendations": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 检查配置
            config = self.neo4j_config
            result["details"]["config"] = {
                "uri": config['uri'],
                "username": config['username'],
                "timeout": config['timeout']
            }
            
            # 尝试连接数据库
            from neo4j import GraphDatabase
            
            start_time = time.time()
            
            driver = GraphDatabase.driver(
                config['uri'],
                auth=(config['username'], config['password']),
                connection_timeout=config['timeout']
            )
            
            # 测试连接
            with driver.session() as session:
                test_result = session.run("RETURN 1 as test").single()
                connection_time = time.time() - start_time
                
                if test_result and test_result["test"] == 1:
                    result["status"] = "healthy"
                    result["message"] = f"Neo4j连接正常，响应时间: {connection_time:.3f}秒"
                    result["details"]["connection_time"] = connection_time
                    result["details"]["test_query_result"] = test_result.data()
                    
                    # 获取数据库信息
                    try:
                        db_info = session.run("CALL db.info()").single()
                        result["details"]["database_info"] = db_info.data() if db_info else {}
                    except Exception:
                        pass  # 某些Neo4j版本可能不支持db.info()
                    
                    # 检查数据内容
                    try:
                        node_count = session.run("MATCH (n) RETURN count(n) as count").single()
                        result["details"]["node_count"] = node_count["count"] if node_count else 0
                        
                        # 检查政策节点
                        policy_count = session.run("MATCH (p:Policy) RETURN count(p) as count").single()
                        result["details"]["policy_count"] = policy_count["count"] if policy_count else 0
                        
                        if result["details"]["policy_count"] == 0:
                            result["recommendations"].append("数据库为空，需要导入政策数据")
                            
                    except Exception as e:
                        result["details"]["query_error"] = str(e)
                        result["recommendations"].append("数据库查询出现问题，检查权限和数据完整性")
                    
                    # 性能建议
                    if connection_time > 5:
                        result["status"] = "warning"
                        result["recommendations"].append("连接响应时间较慢，检查数据库性能")
                        
                else:
                    result["status"] = "error"
                    result["message"] = "Neo4j连接测试失败"
                    result["recommendations"].append("检查数据库服务状态")
            
            driver.close()
            
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Neo4j连接失败: {str(e)}"
            result["details"]["error"] = str(e)
            result["recommendations"].extend([
                "检查Neo4j服务是否启动",
                "验证连接配置（URI、用户名、密码）",
                "检查网络连接和防火墙设置",
                "确保Neo4j Python驱动已安装: pip install neo4j"
            ])
        
        return result
    
    def check_ollama_connection(self) -> Dict[str, Any]:
        """检查Ollama服务连接"""
        result = {
            "service": "ollama",
            "status": "healthy",
            "message": "",
            "details": {},
            "recommendations": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            config = self.ollama_config
            result["details"]["config"] = {
                "host": config['host'],
                "model": config['model'],
                "timeout": config['timeout']
            }
            
            # 检查是否配置了本地地址
            if '127.0.0.1' in config['host'] or 'localhost' in config['host']:
                result["status"] = "error"
                result["message"] = f"检测到本地Ollama地址配置: {config['host']}"
                result["recommendations"].extend([
                    "更新LLM_BINDING_HOST环境变量为远程地址",
                    "使用正确的远程Ollama服务地址: http://120.232.79.82:11434",
                    "重启应用以应用新配置"
                ])
                return result
            
            # 1. 基础连接测试
            start_time = time.time()
            
            tags_response = requests.get(f"{config['host']}/api/tags", timeout=10)
            basic_response_time = time.time() - start_time
            
            if tags_response.status_code != 200:
                result["status"] = "error"
                result["message"] = f"Ollama服务HTTP错误: {tags_response.status_code}"
                result["details"]["http_status"] = tags_response.status_code
                result["recommendations"].extend([
                    "检查Ollama服务是否正在运行",
                    "验证服务地址是否正确",
                    "检查网络连接"
                ])
                return result
            
            result["details"]["basic_response_time"] = basic_response_time
            result["message"] = f"Ollama服务连接正常，响应时间: {basic_response_time:.3f}秒"
            
            # 2. 获取可用模型列表
            try:
                models_data = tags_response.json()
                available_models = []
                
                if 'models' in models_data:
                    for model in models_data['models']:
                        if isinstance(model, dict):
                            name = model.get('name', str(model))
                            size = model.get('size', 'unknown')
                            modified = model.get('modified_at', 'unknown')
                            available_models.append({
                                "name": name,
                                "size": size,
                                "modified": modified
                            })
                        else:
                            available_models.append({"name": str(model)})
                
                result["details"]["available_models"] = available_models
                result["details"]["model_count"] = len(available_models)
                
                # 检查目标模型是否可用
                target_model = config['model'].lower()
                model_names = [m["name"].lower() for m in available_models]
                
                model_available = any(
                    target_model in name or name.startswith(target_model)
                    for name in model_names
                )
                
                if not model_available and available_models:
                    result["status"] = "warning"
                    result["message"] += f" | 目标模型 '{config['model']}' 可能不可用"
                    result["recommendations"].extend([
                        f"检查模型名称是否正确: {config['model']}",
                        "考虑使用可用模型列表中的模型",
                        "或下载目标模型到Ollama服务"
                    ])
                elif not available_models:
                    result["status"] = "warning"
                    result["message"] += " | 未找到可用模型"
                    result["recommendations"].append("Ollama服务中没有可用模型，需要下载模型")
                
            except json.JSONDecodeError:
                result["recommendations"].append("Ollama API响应格式异常，检查服务版本")
            
            # 3. 测试生成功能（仅在模型可用时）
            if result["status"] in ["healthy", "warning"]:
                try:
                    generate_start = time.time()
                    
                    generate_response = requests.post(
                        f"{config['host']}/api/generate",
                        json={
                            "model": config['model'],
                            "prompt": "Hello",
                            "stream": False
                        },
                        timeout=30  # 生成测试使用较短超时
                    )
                    
                    generate_time = time.time() - generate_start
                    result["details"]["generate_test_time"] = generate_time
                    
                    if generate_response.status_code == 200:
                        try:
                            generate_data = generate_response.json()
                            if 'response' in generate_data:
                                result["details"]["generate_test"] = "成功"
                                result["details"]["sample_response"] = generate_data['response'][:100]
                            else:
                                result["status"] = "warning"
                                result["recommendations"].append("模型生成响应格式异常")
                        except json.JSONDecodeError:
                            result["status"] = "warning"
                            result["recommendations"].append("模型生成响应解析失败")
                    else:
                        result["status"] = "warning"
                        result["message"] += f" | 生成测试失败: HTTP {generate_response.status_code}"
                        result["recommendations"].extend([
                            "模型可能未正确加载",
                            "检查模型权限和可用性"
                        ])
                    
                except requests.exceptions.Timeout:
                    result["status"] = "warning"
                    result["message"] += " | 生成测试超时"
                    result["recommendations"].extend([
                        "模型加载可能需要时间，稍后重试",
                        "检查服务器资源使用情况"
                    ])
                except Exception as e:
                    result["details"]["generate_test_error"] = str(e)
                    result["recommendations"].append("生成测试异常，检查模型状态")
            
            # 4. 性能评估
            if basic_response_time > 5:
                if result["status"] == "healthy":
                    result["status"] = "warning"
                result["recommendations"].append("服务响应时间较慢，检查网络或服务性能")
            
        except requests.exceptions.Timeout:
            result["status"] = "error"
            result["message"] = "Ollama服务连接超时"
            result["recommendations"].extend([
                "检查网络连接",
                "验证服务地址",
                "检查防火墙设置"
            ])
        except requests.exceptions.ConnectionError:
            result["status"] = "error"
            result["message"] = "无法连接到Ollama服务"
            result["recommendations"].extend([
                "确认Ollama服务正在运行",
                "检查服务地址是否正确",
                "检查网络连接"
            ])
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Ollama连接检查失败: {str(e)}"
            result["details"]["error"] = str(e)
            result["recommendations"].extend([
            ])
        
        return result
    
    def check_chromadb_status(self) -> Dict[str, Any]:
        """检查ChromaDB向量数据库状态"""
        result = {
            "service": "chromadb",
            "status": "healthy",
            "message": "",
            "details": {},
            "recommendations": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            config = self.chromadb_config
            vector_store_path = config['data_path']
            
            result["details"]["config"] = {
                "data_path": vector_store_path,
                "collection_name": config['collection_name']
            }
            
            # 1. 检查数据文件存在性
            if not os.path.exists(vector_store_path):
                result["status"] = "warning"
                result["message"] = "向量存储文件不存在"
                result["details"]["file_exists"] = False
                result["recommendations"].extend([
                    "初始化向量数据库",
                    "导入政策数据",
                    "检查数据目录权限"
                ])
                return result
            
            result["details"]["file_exists"] = True
            
            # 2. 检查文件大小和基本信息
            file_stats = os.stat(vector_store_path)
            file_size = file_stats.st_size
            modified_time = datetime.fromtimestamp(file_stats.st_mtime)
            
            result["details"]["file_size_bytes"] = file_size
            result["details"]["file_size_mb"] = round(file_size / (1024 * 1024), 2)
            result["details"]["last_modified"] = modified_time.isoformat()
            result["details"]["file_age_hours"] = round((datetime.now() - modified_time).total_seconds() / 3600, 1)
            
            if file_size == 0:
                result["status"] = "warning"
                result["message"] = "向量存储文件为空"
                result["recommendations"].extend([
                    "重新导入数据",
                    "检查数据导入过程",
                    "验证数据源文件"
                ])
                return result
            
            # 3. 尝试读取和验证文件内容
            try:
                with open(vector_store_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 分析数据结构
                if isinstance(data, dict):
                    result["details"]["data_structure"] = list(data.keys())
                    
                    # 检查文档数量
                    if 'documents' in data:
                        doc_count = len(data['documents'])
                        result["details"]["document_count"] = doc_count
                        
                        if doc_count > 0:
                            result["status"] = "healthy"
                            result["message"] = f"向量数据库正常，包含 {doc_count} 个文档"
                            
                            # 检查向量维度（如果存在）
                            if 'embeddings' in data and data['embeddings']:
                                if isinstance(data['embeddings'][0], list):
                                    vector_dim = len(data['embeddings'][0])
                                    result["details"]["vector_dimension"] = vector_dim
                                    result["details"]["embedding_count"] = len(data['embeddings'])
                                    
                                    # 检查文档和向量数量是否匹配
                                    if len(data['embeddings']) != doc_count:
                                        result["status"] = "warning"
                                        result["message"] += " | 文档和向量数量不匹配"
                                        result["recommendations"].append("重新生成向量索引")
                            
                            # 检查元数据
                            if 'metadatas' in data:
                                metadata_count = len(data['metadatas'])
                                result["details"]["metadata_count"] = metadata_count
                                
                                if metadata_count != doc_count:
                                    result["status"] = "warning"
                                    result["message"] += " | 元数据数量不匹配"
                                    result["recommendations"].append("检查数据完整性")
                            
                            # 数据新鲜度检查
                            if result["details"]["file_age_hours"] > 168:  # 一周
                                result["recommendations"].append("数据已超过一周未更新，考虑刷新数据")
                                
                        else:
                            result["status"] = "warning"
                            result["message"] = "向量数据库为空"
                            result["recommendations"].append("向量数据库为空，需要导入数据")
                    else:
                        result["status"] = "warning"
                        result["message"] = "向量存储文件结构异常，缺少documents字段"
                        result["recommendations"].extend([
                            "检查文件格式",
                            "重新生成向量存储文件"
                        ])
                        
                else:
                    result["status"] = "error"
                    result["message"] = "向量存储文件格式错误，不是有效的JSON对象"
                    result["details"]["data_type"] = type(data).__name__
                    result["recommendations"].extend([
                        "重新生成向量存储文件",
                        "检查数据导入脚本",
                        "备份并重新创建数据文件"
                    ])
            
            except json.JSONDecodeError as e:
                result["status"] = "error"
                result["message"] = f"向量存储文件JSON格式错误: {str(e)}"
                result["details"]["json_error"] = str(e)
                result["recommendations"].extend([
                    "重新生成向量存储文件",
                    "检查文件是否被损坏",
                    "从备份恢复数据文件"
                ])
            
            except Exception as e:
                result["status"] = "error"
                result["message"] = f"读取向量存储文件失败: {str(e)}"
                result["details"]["read_error"] = str(e)
                result["recommendations"].extend([
                    "检查文件权限",
                    "检查磁盘空间",
                    "重新生成数据文件"
                ])
                
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"ChromaDB状态检查失败: {str(e)}"
            result["details"]["error"] = str(e)
            result["recommendations"].extend([
                "检查ChromaDB配置",
                "验证数据目录结构",
                "检查相关依赖包"
            ])
        
        return result
    
    def run_comprehensive_connection_check(self) -> Dict[str, Any]:
        """运行全面的服务连接检查"""
        print("=== 依赖服务连接全面检查 ===")
        
        comprehensive_results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "summary": "",
            "services": {}
        }
        
        # 1. Neo4j连接检查
        print("1. 检查Neo4j数据库连接...")
        neo4j_result = self.check_neo4j_connection()
        comprehensive_results["services"]["neo4j"] = neo4j_result
        
        # 2. Ollama服务检查
        print("2. 检查Ollama服务连接...")
        ollama_result = self.check_ollama_connection()
        comprehensive_results["services"]["ollama"] = ollama_result
        
        # 3. ChromaDB状态检查
        print("3. 检查ChromaDB向量数据库...")
        chromadb_result = self.check_chromadb_status()
        comprehensive_results["services"]["chromadb"] = chromadb_result
        
        # 生成整体状态和摘要
        service_statuses = [result["status"] for result in comprehensive_results["services"].values()]
        
        error_count = service_statuses.count("error")
        warning_count = service_statuses.count("warning")
        healthy_count = service_statuses.count("healthy")
        
        if error_count > 0:
            comprehensive_results["overall_status"] = "error"
            comprehensive_results["summary"] = f"发现 {error_count} 个服务错误和 {warning_count} 个警告"
        elif warning_count > 0:
            comprehensive_results["overall_status"] = "warning"
            comprehensive_results["summary"] = f"发现 {warning_count} 个服务警告，{healthy_count} 个服务正常"
        else:
            comprehensive_results["overall_status"] = "healthy"
            comprehensive_results["summary"] = f"所有 {healthy_count} 个服务连接正常"
        
        return comprehensive_results
    
    def generate_connection_report(self, check_results: Dict[str, Any]) -> str:
        """生成连接检查报告"""
        report_lines = [
            "# 依赖服务连接检查报告",
            f"检查时间: {check_results['timestamp']}",
            f"整体状态: {check_results['overall_status']}",  
            f"摘要: {check_results['summary']}",
            ""
        ]
        
        for service_name, service_result in check_results["services"].items():
            report_lines.extend([
                f"## {service_name.upper()} 服务",
                f"状态: {service_result['status']}",
                f"消息: {service_result['message']}",
                ""
            ])
            
            if service_result.get("details"):
                report_lines.append("### 详细信息")
                for key, value in service_result["details"].items():
                    if isinstance(value, (str, int, float)):
                        report_lines.append(f"- {key}: {value}")
                report_lines.append("")
            
            if service_result.get("recommendations"):
                report_lines.append("### 建议")
                for rec in service_result["recommendations"]:
                    report_lines.append(f"- {rec}")
                report_lines.append("")
        
        return "\n".join(report_lines)


def main():
    """主函数 - 运行服务连接检查"""
    checker = ServiceConnectionChecker()
    
    # 运行全面检查
    results = checker.run_comprehensive_connection_check()
    
    # 生成并保存报告
    report = checker.generate_connection_report(results)
    
    report_path = os.path.join(os.getcwd(), "service_connection_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n=== 检查结果摘要 ===")
    print(f"整体状态: {results['overall_status']}")
    print(f"摘要: {results['summary']}")
    print(f"详细报告已生成: {report_path}")
    
    # 打印关键信息
    for service_name, service_result in results["services"].items():
        status_icon = "✓" if service_result["status"] == "healthy" else "⚠" if service_result["status"] == "warning" else "✗"
        print(f"{status_icon} {service_name}: {service_result['message']}")


if __name__ == "__main__":
    main()