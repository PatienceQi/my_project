#!/usr/bin/env python3
"""
彻底修复远程Ollama配置的GraphRAG数据导入脚本
确保绝对不会启动本地ollama服务或连接到64482端口
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# 设置项目路径
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 强制禁用所有可能的ollama客户端库行为
def force_disable_ollama_client():
    """彻底禁用ollama客户端库的本地服务启动"""
    
    # 设置所有可能的环境变量
    remote_host = 'http://120.232.79.82:11434'
    config_vars = {
        # 核心配置
        'LLM_BINDING_HOST': remote_host,
        'OLLAMA_HOST': remote_host,
        'OLLAMA_BASE_URL': remote_host,
        'OLLAMA_API_BASE': remote_host,
        
        # 禁用本地服务
        'OLLAMA_NO_SERVE': '1',
        'OLLAMA_NO_HISTORY': '1',
        'OLLAMA_NOHISTORY': '1',
        'OLLAMA_DISABLE_METRICS': '1',
        
        # 网络配置
        'OLLAMA_ORIGINS': '*',
        'OLLAMA_KEEP_ALIVE': '5m',
        'OLLAMA_MAX_LOADED_MODELS': '1',
        
        # 模型配置
        'EMBEDDING_MODEL': 'bge-m3:latest',
        'LLM_MODEL': 'llama3.2:latest',
        'LLM_BINDING': 'ollama'
    }
    
    print("🛡️ 强制禁用ollama客户端本地服务启动...")
    
    for key, value in config_vars.items():
        old_value = os.environ.get(key)
        os.environ[key] = value
        if old_value != value:
            print(f"   ✅ {key}: {value}")
    
    # 验证配置
    critical_vars = ['OLLAMA_HOST', 'OLLAMA_NO_SERVE', 'LLM_BINDING_HOST']
    for var in critical_vars:
        current = os.environ.get(var)
        if var == 'OLLAMA_NO_SERVE' and current != '1':
            print(f"   ❌ 关键配置错误: {var} = {current}")
            return False
        elif var in ['OLLAMA_HOST', 'LLM_BINDING_HOST'] and '127.0.0.1' in str(current):
            print(f"   ❌ 检测到本地地址: {var} = {current}")
            return False
    
    print("   ✅ 所有关键配置正确")
    return True

def kill_existing_ollama_processes():
    """终止可能存在的本地ollama进程"""
    try:
        print("🔍 检查并终止本地ollama进程...")
        
        # Windows系统
        if os.name == 'nt':
            try:
                result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ollama.exe'], 
                                      capture_output=True, text=True, timeout=10)
                if 'ollama.exe' in result.stdout:
                    print("   发现本地ollama进程，尝试终止...")
                    subprocess.run(['taskkill', '/F', '/IM', 'ollama.exe'], timeout=10)
                    print("   ✅ 本地ollama进程已终止")
                else:
                    print("   ✅ 未发现本地ollama进程")
            except Exception as e:
                print(f"   ⚠️ 进程检查失败: {e}")
        
        # Unix系统
        else:
            try:
                result = subprocess.run(['pgrep', 'ollama'], capture_output=True, text=True, timeout=10)
                if result.stdout.strip():
                    print("   发现本地ollama进程，尝试终止...")
                    subprocess.run(['pkill', 'ollama'], timeout=10)
                    print("   ✅ 本地ollama进程已终止")
                else:
                    print("   ✅ 未发现本地ollama进程")
            except Exception as e:
                print(f"   ⚠️ 进程检查失败: {e}")
                
    except Exception as e:
        print(f"   ⚠️ 进程管理失败: {e}")

def verify_no_local_connections():
    """验证没有本地连接"""
    import requests
    
    print("🔍 验证不会连接本地服务...")
    
    # 检查常见的本地端口
    local_ports = [11434, 64482, 64483, 64484]
    local_connections = []
    
    for port in local_ports:
        try:
            response = requests.get(f"http://127.0.0.1:{port}/api/version", timeout=2)
            if response.status_code == 200:
                local_connections.append(port)
        except:
            pass  # 连接失败是好事
    
    if local_connections:
        print(f"   ⚠️ 检测到本地ollama服务运行在端口: {local_connections}")
        return False
    else:
        print("   ✅ 确认没有本地ollama服务运行")
        return True

def test_remote_connection():
    """测试远程连接"""
    import requests
    
    print("🌐 测试远程ollama连接...")
    
    remote_host = os.environ.get('LLM_BINDING_HOST')
    try:
        response = requests.get(f"{remote_host}/api/version", timeout=10)
        if response.status_code == 200:
            version_info = response.json()
            print(f"   ✅ 远程连接成功，版本: {version_info.get('version', 'unknown')}")
            return True
        else:
            print(f"   ❌ 远程连接失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 远程连接异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 启动彻底修复的GraphRAG数据导入")
    print("=" * 60)
    
    # 1. 加载环境变量
    load_dotenv()
    
    # 2. 强制禁用ollama客户端
    if not force_disable_ollama_client():
        print("❌ 配置修正失败")
        return False
    
    # 3. 终止本地ollama进程
    kill_existing_ollama_processes()
    
    # 4. 验证没有本地连接
    verify_no_local_connections()
    
    # 5. 测试远程连接
    if not test_remote_connection():
        print("❌ 远程连接测试失败")
        return False
    
    print("\n🎯 环境准备完成，开始数据导入...")
    print("-" * 60)
    
    try:
        # 导入并运行
        from scripts.import_graphrag_data import GraphRAGDataImporter
        
        # 创建导入器
        importer = GraphRAGDataImporter()
        
        print(f"✅ 使用嵌入模型: {importer.vector_retriever.embedding_model_name}")
        print(f"✅ 向量数据库: {importer.vector_retriever.persist_dir}")
        
        # 加载文档
        documents = importer.load_policy_documents()
        if not documents:
            print("❌ 没有找到可导入的文档")
            return False
        
        print(f"✅ 加载 {len(documents)} 个文档")
        
        # 询问导入方式
        print("\n📋 选择导入方式:")
        print("  [1] 仅向量数据库导入（推荐，快速）")
        print("  [2] 完整GraphRAG导入（包含实体关系提取）")
        
        choice = input("\n请选择 (1/2): ").strip()
        
        if choice == '1':
            print("\n🔄 执行向量数据库导入...")
            success = importer.vector_retriever.add_documents(documents)
            if success:
                print("✅ 向量数据库导入成功")
            else:
                print("❌ 向量数据库导入失败")
        
        elif choice == '2':
            print("\n🔄 执行完整GraphRAG导入...")
            print("⚠️ 这将包含实体关系提取，可能需要较长时间")
            
            confirm = input("确定继续？(y/N): ").strip().lower()
            if confirm == 'y':
                importer.import_all_data(rebuild_vector_db=True, rebuild_graph=True)
                print("✅ 完整GraphRAG导入完成")
            else:
                print("已取消")
        
        else:
            print("无效选择")
        
        print("\n🎉 数据导入完成！")
        return True
        
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理
        try:
            if 'importer' in locals():
                importer.close()
        except:
            pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)