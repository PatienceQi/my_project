#!/usr/bin/env python3
"""
修复后的GraphRAG数据导入脚本
使用远程Ollama服务的bge-m3:latest嵌入模型进行数据导入
包含完整的配置验证和诊断功能
"""

import os
import sys
import logging
import requests
import time
import psutil
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# 设置项目路径（遵循项目启动规范）
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 加载环境变量
load_dotenv()

# 关键修复：强制设置远程Ollama配置并验证
def force_remote_ollama_config():
    """强制设置远程Ollama配置"""
    remote_host = 'http://120.232.79.82:11434'
    
    # 设置所有可能影响Ollama连接的环境变量
    config_vars = {
        'EMBEDDING_MODEL': 'bge-m3:latest',
        'LLM_BINDING_HOST': remote_host,
        'LLM_MODEL': 'llama3.2:latest',
        'LLM_BINDING': 'ollama',
        'OLLAMA_HOST': remote_host,
        'OLLAMA_BASE_URL': remote_host,
        'OLLAMA_NO_SERVE': '1',
        'OLLAMA_ORIGINS': '*',
        'OLLAMA_KEEP_ALIVE': '5m'
    }
    
    print("\n⚙️  强制设置远程Ollama配置...")
    for key, value in config_vars.items():
        old_value = os.environ.get(key)
        os.environ[key] = value
        if old_value != value:
            print(f"   ✅ {key}: {old_value} -> {value}")
        else:
            print(f"   ✓ {key}: {value}")

def diagnose_ollama_connection():
    """诊断远程Ollama连接状态"""
    remote_host = os.environ.get('LLM_BINDING_HOST', 'http://120.232.79.82:11434')
    embedding_model = os.environ.get('EMBEDDING_MODEL', 'bge-m3:latest')
    llm_model = os.environ.get('LLM_MODEL', 'llama3.2:latest')
    
    print(f"\n🔍 诊断远程Ollama连接: {remote_host}")
    
    # 1. 网络连接测试
    try:
        print("   1. 网络连接测试...")
        response = requests.get(f"{remote_host}/api/version", timeout=10)
        if response.status_code == 200:
            version_info = response.json()
            print(f"      ✅ Ollama服务连接成功，版本: {version_info.get('version', 'unknown')}")
        else:
            print(f"      ❌ 服务响应异常: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"      ❌ 网络连接失败: {e}")
        return False
    
    # 2. 模型可用性检查
    try:
        print("   2. 模型可用性检查...")
        response = requests.get(f"{remote_host}/api/tags", timeout=10)
        if response.status_code == 200:
            models_data = response.json()
            models = models_data.get('models', [])
            model_names = [m.get('name', '') for m in models]
            
            # 检查嵌入模型
            embedding_available = any(embedding_model in name for name in model_names)
            if embedding_available:
                print(f"      ✅ 嵌入模型 {embedding_model} 可用")
            else:
                print(f"      ⚠️  嵌入模型 {embedding_model} 不可用")
                print(f"         可用模型: {', '.join(model_names)}")
            
            # 检查LLM模型
            llm_available = any(llm_model in name for name in model_names)
            if llm_available:
                print(f"      ✅ LLM模型 {llm_model} 可用")
            else:
                print(f"      ⚠️  LLM模型 {llm_model} 不可用")
                print(f"         可用模型: {', '.join(model_names)}")
            
            return embedding_available  # 至少嵌入模型可用
        else:
            print(f"      ❌ 模型列表获取失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"      ❌ 模型检查失败: {e}")
        return False
    
    # 3. 嵌入模型功能测试
    try:
        print("   3. 嵌入模型功能测试...")
        test_payload = {
            "model": embedding_model,
            "prompt": "测试文本"
        }
        response = requests.post(f"{remote_host}/api/embeddings", json=test_payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if 'embedding' in result and result['embedding']:
                print(f"      ✅ 嵌入模型功能正常，向量维度: {len(result['embedding'])}")
                return True
            else:
                print(f"      ❌ 嵌入模型返回结果异常")
        else:
            print(f"      ❌ 嵌入模型测试失败: HTTP {response.status_code}")
    except Exception as e:
        print(f"      ❌ 嵌入模型测试异常: {e}")
    
    return False

def validate_environment():
    """验证环境配置"""
    print("\n🔍 验证环境配置...")
    
    required_configs = {
        'LLM_BINDING_HOST': 'http://120.232.79.82:11434',
        'OLLAMA_HOST': 'http://120.232.79.82:11434',
        'OLLAMA_NO_SERVE': '1',
        'EMBEDDING_MODEL': 'bge-m3:latest'
    }
    
    all_valid = True
    for key, expected in required_configs.items():
        current = os.environ.get(key)
        if current == expected:
            print(f"   ✅ {key}: {current}")
        else:
            print(f"   ❌ {key}: {current} (期望: {expected})")
            all_valid = False
    
    # 检查是否有本地连接配置
    suspicious_configs = [
        ('LLM_BINDING_HOST', ['127.0.0.1', 'localhost']),
        ('OLLAMA_HOST', ['127.0.0.1', 'localhost'])
    ]
    
    for config_key, suspicious_values in suspicious_configs:
        current_value = os.environ.get(config_key, '')
        for suspicious in suspicious_values:
            if suspicious in current_value:
                print(f"   ⚠️  检测到可疑的本地配置: {config_key}={current_value}")
                all_valid = False
    
    return all_valid

# 设置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('graphrag_import.log', encoding='utf-8')
    ]
)

def main():
    """主函数 - 执行修复后的GraphRAG数据导入"""
    
    print("="*60)
    print("GraphRAG数据导入 - 使用远程Ollama服务")
    print("="*60)
    
    # 步骤1：强制设置远程配置
    force_remote_ollama_config()
    
    # 步骤2：验证环境配置
    if not validate_environment():
        print("\n❌ 环境配置验证失败，请检查上述错误")
        return False
    
    # 步骤3：诊断远程Ollama连接
    if not diagnose_ollama_connection():
        print("\n❌ 远程Ollama连接诊断失败，无法继续导入")
        print("📝 请检查：")
        print("   1. 远程服务地址是否可访问: http://120.232.79.82:11434")
        print("   2. 需要的模型是否已安装: bge-m3:latest, llama3.2:latest")
        print("   3. 网络连接是否正常")
        return False
    
    # 显示最终配置信息
    print(f"\n✅ 配置验证成功")
    print(f"   嵌入模型: {os.environ.get('EMBEDDING_MODEL')}")
    print(f"   Ollama服务: {os.environ.get('LLM_BINDING_HOST')}")
    print(f"   LLM模型: {os.environ.get('LLM_MODEL')}")
    
    try:
        # 导入修复后的GraphRAG导入器
        from scripts.import_graphrag_data import GraphRAGDataImporter
        
        # 初始化导入器
        print("\n🔄 初始化GraphRAG导入器...")
        importer = GraphRAGDataImporter()
        
        print(f"   ✅ 使用嵌入模型: {importer.vector_retriever.embedding_model_name}")
        print(f"   ✅ 向量数据库路径: {importer.vector_retriever.persist_dir}")
        
        # 测试数据加载
        print("\n📁 加载政策文档数据...")
        documents = importer.load_policy_documents()
        
        if not documents:
            print("   ❌ 没有找到可导入的文档")
            return False
        
        print(f"   ✅ 成功加载 {len(documents)} 个文档")
        
        # 显示文档统计
        print("\n📊 文档统计信息:")
        standard_count = sum(1 for doc in documents if doc.get('source', '').endswith('.json') and not doc.get('source', '').startswith('[OCR]'))
        ocr_count = sum(1 for doc in documents if doc.get('source', '').startswith('[OCR]'))
        
        print(f"   - 标准格式文档: {standard_count}")
        print(f"   - OCR格式文档: {ocr_count}")
        print(f"   - 总章节数: {sum(len(doc.get('sections', [])) for doc in documents)}")
        print(f"   - 总内容长度: {sum(len(doc.get('content', '')) for doc in documents):,} 字符")
        
        # 询问是否执行完整导入
        print("\n🚀 导入选项:")
        print("   [1] 仅向量数据库导入（快速）")
        print("   [2] 完整GraphRAG导入（包含实体关系提取）")
        print("   [3] 跳过导入，仅验证数据格式修复")
        
        choice = input("\n请选择导入方式 (1/2/3): ").strip()
        
        if choice == '1':
            print("\n🔄 正在执行向量数据库导入...")
            success = importer.vector_retriever.add_documents(documents)
            if success:
                print("✅ 向量数据库导入成功")
                print(f"   集合统计: {importer.vector_retriever.get_collection_stats()}")
            else:
                print("❌ 向量数据库导入失败")
                
        elif choice == '2':
            print("\n🔄 正在执行完整GraphRAG导入...")
            print("⚠️  注意：完整导入可能需要较长时间，特别是实体关系提取部分")
            
            confirm = input("确定继续吗？(y/N): ").strip().lower()
            if confirm == 'y':
                print("🔄 正在执行完整导入，请耐心等待...")
                importer.import_all_data(rebuild_vector_db=True, rebuild_graph=True)
                print("✅ 完整GraphRAG导入完成")
            else:
                print("已取消完整导入")
                
        elif choice == '3':
            print("✅ 数据格式修复验证完成，跳过导入")
            
        else:
            print("无效选择，跳过导入")
        
        print("\n" + "="*60)
        print("✅ GraphRAG数据导入完成")
        print("="*60)
        
        return True
        
    except Exception as e:
        logging.error(f"GraphRAG数据导入失败: {e}")
        print(f"\n❌ 导入失败: {e}")
        
        # 提供调试信息
        print("\n📝 调试信息:")
        print("1. 请确保已安装所需依赖：")
        print("   pip install sentence-transformers chromadb")
        print("2. 如果使用bge-m3模型失败，会自动回退到备用模型")
        print("3. 检查网络连接以下载模型文件")
        print("4. 请确保远程Ollama服务正常运行")
        
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    main()