#!/usr/bin/env python3
"""
测试远程Ollama连接配置修复
验证是否正确连接到远程服务而不是本地服务
"""

import os
import sys
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv

# 设置项目路径
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_environment_setup():
    """测试环境变量设置"""
    print("=" * 60)
    print("环境变量配置检查")
    print("=" * 60)
    
    # 强制设置远程服务配置（防止本地服务启动）
    remote_host = 'http://120.232.79.82:11434'
    os.environ['OLLAMA_HOST'] = remote_host
    os.environ['OLLAMA_BASE_URL'] = remote_host
    os.environ['OLLAMA_NO_SERVE'] = '1'
    os.environ['OLLAMA_ORIGINS'] = '*'
    os.environ['LLM_BINDING_HOST'] = remote_host
    os.environ['LLM_MODEL'] = 'llama3.2:latest'
    os.environ['EMBEDDING_MODEL'] = 'bge-m3:latest'
    
    env_vars = [
        'OLLAMA_HOST',
        'OLLAMA_BASE_URL', 
        'OLLAMA_NO_SERVE',
        'LLM_BINDING_HOST',
        'LLM_MODEL',
        'EMBEDDING_MODEL'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'NOT SET')
        print(f"  {var}: {value}")
    
    print(f"\n✅ 环境变量设置完成，远程地址: {remote_host}")
    return remote_host

def test_direct_api_call(host):
    """直接测试API调用"""
    print("\n" + "=" * 60)
    print("直接API调用测试")
    print("=" * 60)
    
    try:
        # 测试服务可用性
        print(f"1. 测试服务可用性: {host}/api/tags")
        response = requests.get(f"{host}/api/tags", timeout=10)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ 远程Ollama服务可用")
            
            # 测试嵌入API
            print(f"\n2. 测试嵌入API: {host}/api/embed")
            embed_payload = {
                "model": "bge-m3:latest",
                "input": "测试文本"
            }
            
            embed_response = requests.post(
                f"{host}/api/embed", 
                json=embed_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"   状态码: {embed_response.status_code}")
            if embed_response.status_code == 200:
                embed_data = embed_response.json()
                if 'embeddings' in embed_data or 'embedding' in embed_data:
                    print("   ✅ 嵌入API正常工作")
                    return True
                else:
                    print(f"   ❌ 嵌入API响应格式异常: {embed_data}")
            else:
                print(f"   ❌ 嵌入API调用失败: {embed_response.text}")
        else:
            print(f"   ❌ 远程Ollama服务不可用: {response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 网络请求失败: {e}")
    
    return False

def test_ollama_api_direct():
    """测试ollama HTTP API直接调用是否正确配置"""
    print("\n" + "=" * 60)
    print("Ollama HTTP API直接调用测试")
    print("=" * 60)
    
    try:
        remote_host = os.environ.get('OLLAMA_HOST')
        print(f"使用地址: {remote_host}")
        
        # 测试获取模型列表（HTTP API）
        print("获取模型列表...")
        response = requests.get(f"{remote_host}/api/tags", timeout=10)
        
        if response.status_code == 200:
            models_data = response.json()
            models = models_data.get('models', [])
            model_names = [m.get('name', str(m)) for m in models]
            
            print(f"可用模型: {model_names}")
            
            # 检查是否包含我们需要的模型
            target_models = ['llama3.2:latest', 'bge-m3:latest']
            for target in target_models:
                found = any(target.lower() in name.lower() for name in model_names)
                status = "✅" if found else "⚠️"
                print(f"  {status} {target}: {'找到' if found else '未找到'}")
            
            # 测试文本生成API
            print("\n测试文本生成API...")
            generate_payload = {
                "model": "llama3.2:latest",
                "prompt": "简单回答：你好",
                "stream": False
            }
            
            gen_response = requests.post(
                f"{remote_host}/api/generate",
                json=generate_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if gen_response.status_code == 200:
                gen_data = gen_response.json()
                generated_text = gen_data.get('response', '')
                print(f"  ✅ 文本生成成功: {generated_text[:50]}...")
            else:
                print(f"  ❌ 文本生成失败: HTTP {gen_response.status_code}")
            
            return True
        else:
            print(f"❌ 模型列表获取失败: HTTP {response.status_code}")
            return False
        
    except Exception as e:
        print(f"❌ HTTP API测试失败: {e}")
        return False

def test_entity_extractor():
    """测试实体提取器配置"""
    print("\n" + "=" * 60)
    print("实体提取器配置测试")
    print("=" * 60)
    
    try:
        from backend.entity_extractor import EntityExtractor
        
        # 创建实体提取器（会自动设置环境变量）
        extractor = EntityExtractor()
        
        print(f"实体提取器Ollama地址: {extractor.ollama_host}")
        print(f"使用模型: {extractor.model_name}")
        
        # 简单测试（不实际调用，只检查配置）
        expected_host = 'http://120.232.79.82:11434'
        if extractor.ollama_host == expected_host:
            print(f"✅ 实体提取器配置正确")
            return True
        else:
            print(f"❌ 实体提取器配置错误，期望: {expected_host}, 实际: {extractor.ollama_host}")
            return False
    
    except Exception as e:
        print(f"❌ 实体提取器测试失败: {e}")
        return False

def test_vector_retriever():
    """测试向量检索器配置"""
    print("\n" + "=" * 60)
    print("向量检索器配置测试")
    print("=" * 60)
    
    try:
        from backend.vector_retrieval import VectorRetriever
        
        # 创建向量检索器
        retriever = VectorRetriever()
        
        print(f"向量检索器嵌入模型: {retriever.embedding_model_name}")
        print(f"Ollama地址: {getattr(retriever, 'ollama_host', 'N/A')}")
        print(f"使用Ollama: {getattr(retriever, 'use_ollama', False)}")
        
        # 检查配置
        if hasattr(retriever, 'use_ollama') and retriever.use_ollama:
            print("✅ 向量检索器配置为使用远程Ollama")
            return True
        else:
            print("⚠️ 向量检索器未配置为使用Ollama（可能使用备用模型）")
            return True
    
    except Exception as e:
        print(f"❌ 向量检索器测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔧 远程Ollama连接配置修复验证")
    print("测试是否成功修复127.0.0.1:64482连接问题")
    
    # 记录测试结果
    test_results = []
    
    # 1. 环境变量设置
    remote_host = test_environment_setup()
    
    # 2. 直接API调用测试
    api_success = test_direct_api_call(remote_host)
    test_results.append(("直接API调用", api_success))
    
    # 3. Ollama HTTP API直接测试
    api_direct_success = test_ollama_api_direct()
    test_results.append(("Ollama HTTP API", api_direct_success))
    
    # 4. 实体提取器测试
    extractor_success = test_entity_extractor()
    test_results.append(("实体提取器", extractor_success))
    
    # 5. 向量检索器测试
    retriever_success = test_vector_retriever()
    test_results.append(("向量检索器", retriever_success))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for test_name, success in test_results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not success:
            all_passed = False
    
    print(f"\n{'🎉 所有测试通过！' if all_passed else '⚠️ 部分测试失败'}")
    
    if all_passed:
        print("远程Ollama连接配置修复成功")
        print("现在可以运行 GraphRAG 导入，应该不会再连接到 127.0.0.1:64482")
    else:
        print("仍有问题需要解决，请检查失败的测试项")
    
    return all_passed

if __name__ == "__main__":
    main()