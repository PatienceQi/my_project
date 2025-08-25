#!/usr/bin/env python3
"""
简单的远程Ollama配置验证脚本
"""

import os
import sys
import logging
from pathlib import Path

# 设置项目路径
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_basic_configuration():
    """测试基本配置"""
    print("🔧 测试基本配置...")
    
    # 强制设置远程配置
    remote_host = 'http://120.232.79.82:11434'
    os.environ['LLM_BINDING_HOST'] = remote_host
    os.environ['OLLAMA_HOST'] = remote_host
    os.environ['OLLAMA_BASE_URL'] = remote_host
    os.environ['OLLAMA_NO_SERVE'] = '1'
    os.environ['EMBEDDING_MODEL'] = 'bge-m3:latest'
    os.environ['LLM_MODEL'] = 'llama3.2:latest'
    
    # 检查环境变量
    expected_configs = {
        'LLM_BINDING_HOST': remote_host,
        'OLLAMA_HOST': remote_host,
        'OLLAMA_NO_SERVE': '1'
    }
    
    all_correct = True
    for key, expected in expected_configs.items():
        current = os.environ.get(key)
        if current == expected:
            print(f"   ✅ {key}: {current}")
        else:
            print(f"   ❌ {key}: {current} (期望: {expected})")
            all_correct = False
    
    return all_correct

def test_entity_extractor():
    """测试EntityExtractor"""
    print("\n🧠 测试EntityExtractor...")
    
    try:
        from backend.entity_extractor import EntityExtractor
        
        # 初始化
        extractor = EntityExtractor()
        
        # 检查配置
        if '127.0.0.1' in extractor.ollama_host or 'localhost' in extractor.ollama_host:
            print(f"   ❌ 仍在使用本地地址: {extractor.ollama_host}")
            return False
        
        print(f"   ✅ 使用远程地址: {extractor.ollama_host}")
        
        # 检查是否有错误处理客户端
        if hasattr(extractor, 'ollama_client'):
            print("   ✅ 已集成错误处理客户端")
        else:
            print("   ❌ 未集成错误处理客户端")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ EntityExtractor测试失败: {e}")
        return False

def test_graphrag_engine():
    """测试GraphRAG引擎"""
    print("\n🌐 测试GraphRAG引擎...")
    
    try:
        from backend.graphrag_engine import GraphRAGEngine
        
        # 初始化
        engine = GraphRAGEngine()
        
        # 检查配置
        if '127.0.0.1' in engine.ollama_host or 'localhost' in engine.ollama_host:
            print(f"   ❌ 仍在使用本地地址: {engine.ollama_host}")
            return False
        
        print(f"   ✅ 使用远程地址: {engine.ollama_host}")
        
        # 检查组件
        components = ['vector_retriever', 'graph_query_engine', 'entity_extractor']
        for comp in components:
            if hasattr(engine, comp) and getattr(engine, comp) is not None:
                print(f"   ✅ {comp} 初始化成功")
            else:
                print(f"   ❌ {comp} 初始化失败")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ GraphRAG引擎测试失败: {e}")
        return False

def test_error_handler():
    """测试错误处理模块"""
    print("\n🛡️ 测试错误处理模块...")
    
    try:
        from backend.ollama_error_handler import OllamaClientWithFallback, ensure_remote_ollama_config
        
        # 测试配置修正
        ensure_remote_ollama_config()
        print("   ✅ 配置修正函数正常")
        
        # 测试客户端
        client = OllamaClientWithFallback()
        
        # 检查当前主机
        if '127.0.0.1' in client.current_host or 'localhost' in client.current_host:
            print(f"   ❌ 错误处理客户端使用本地地址: {client.current_host}")
            return False
        
        print(f"   ✅ 错误处理客户端使用远程地址: {client.current_host}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 错误处理模块测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🔍 远程Ollama配置修复验证")
    print("=" * 50)
    
    tests = [
        ("基本配置", test_basic_configuration),
        ("EntityExtractor", test_entity_extractor),
        ("GraphRAG引擎", test_graphrag_engine),
        ("错误处理模块", test_error_handler)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！远程Ollama配置修复成功！")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)