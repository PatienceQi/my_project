#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试系统状态查询功能 - 验证修复是否有效
"""

import sys
import os
import time
import traceback
import requests

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

# 导入必要的模块
try:
    from backend.graphrag_engine import GraphRAGEngine
    from backend.vector_retrieval import VectorRetriever
    from backend.graph_query import GraphQueryEngine
    print("✅ 所有模块导入成功")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)

def test_graphrag_engine_stats():
    """测试GraphRAG引擎的统计方法"""
    print("\n🔍 测试GraphRAG引擎统计方法...")
    
    try:
        # 测试基础统计
        print("测试 get_basic_stats()...")
        engine = GraphRAGEngine()
        basic_stats = engine.get_basic_stats()
        print(f"✅ 基础统计成功: {basic_stats.get('system_status', 'unknown')}")
        
        # 测试安全统计
        print("测试 get_system_stats_safe()...")
        safe_stats = engine.get_system_stats_safe()
        print(f"✅ 安全统计成功: {safe_stats.get('system_status', 'unknown')}")
        
        # 测试原始统计方法
        print("测试 get_system_stats()...")
        normal_stats = engine.get_system_stats()
        print(f"✅ 原始统计成功: {normal_stats.get('system_status', 'unknown')}")
        
        engine.close()
        return True
        
    except Exception as e:
        print(f"❌ GraphRAG引擎测试失败: {e}")
        traceback.print_exc()
        return False

def test_vector_retriever_stats():
    """测试向量检索器的统计方法"""
    print("\n🔍 测试向量检索器统计方法...")
    
    try:
        retriever = VectorRetriever()
        
        # 测试安全统计
        print("测试 get_collection_stats_safe()...")
        safe_stats = retriever.get_collection_stats_safe()
        print(f"✅ 安全统计成功: {safe_stats.get('status', 'unknown')}")
        
        # 测试原始统计
        print("测试 get_collection_stats()...")
        normal_stats = retriever.get_collection_stats()
        print(f"✅ 原始统计成功: 返回了 {len(normal_stats)} 个字段")
        
        return True
        
    except Exception as e:
        print(f"❌ 向量检索器测试失败: {e}")
        traceback.print_exc()
        return False

def test_graph_query_stats():
    """测试图查询引擎的统计方法"""
    print("\n🔍 测试图查询引擎统计方法...")
    
    try:
        query_engine = GraphQueryEngine()
        
        # 测试安全统计
        print("测试 get_graph_statistics_safe()...")
        safe_stats = query_engine.get_graph_statistics_safe()
        print(f"✅ 安全统计成功: {safe_stats.get('status', 'unknown')}")
        
        # 测试原始统计
        print("测试 get_graph_statistics()...")
        normal_stats = query_engine.get_graph_statistics()
        print(f"✅ 原始统计成功: 返回了 {len(normal_stats)} 个字段")
        
        query_engine.close()
        return True
        
    except Exception as e:
        print(f"❌ 图查询引擎测试失败: {e}")
        traceback.print_exc()
        return False

def test_api_server():
    """测试API服务器（如果正在运行）"""
    print("\n🔍 测试API服务器...")
    
    base_url = "http://127.0.0.1:5000"
    
    # 测试基础连接
    try:
        print("测试 /ping 端点...")
        response = requests.get(f"{base_url}/ping", timeout=5)
        if response.ok:
            print("✅ Ping 成功")
            
            # 测试快速状态端点
            print("测试 /api/system/stats/quick 端点...")
            response = requests.get(f"{base_url}/api/system/stats/quick", timeout=5)
            if response.ok:
                data = response.json()
                print(f"✅ 快速状态检查成功: {data.get('status', 'unknown')}")
            else:
                print(f"⚠️ 快速状态检查失败: HTTP {response.status_code}")
            
            # 测试基础级别状态
            print("测试 /api/system/stats?level=basic 端点...")
            response = requests.get(f"{base_url}/api/system/stats?level=basic", timeout=10)
            if response.ok:
                data = response.json()
                print(f"✅ 基础级别状态成功: {data.get('system_status', 'unknown')}")
                return True
            else:
                print(f"⚠️ 基础级别状态失败: HTTP {response.status_code}")
                return False
                
        else:
            print(f"❌ API服务器未运行或无法访问: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API服务器连接失败: {e}")
        return False

def stress_test_stats():
    """压力测试 - 多次调用统计方法"""
    print("\n🧪 压力测试 - 多次调用统计方法...")
    
    success_count = 0
    total_tests = 10
    
    try:
        engine = GraphRAGEngine()
        
        for i in range(total_tests):
            try:
                # 交替测试不同的统计方法
                if i % 3 == 0:
                    stats = engine.get_basic_stats()
                elif i % 3 == 1:
                    stats = engine.get_system_stats_safe()
                else:
                    stats = engine.get_system_stats()
                
                if stats and stats.get('system_status') != 'error':
                    success_count += 1
                
                print(f"测试 {i+1}/{total_tests}: ✅")
                
            except Exception as e:
                print(f"测试 {i+1}/{total_tests}: ❌ {e}")
            
            time.sleep(0.5)  # 短暂延迟
        
        engine.close()
        
        print(f"\n📊 压力测试结果: {success_count}/{total_tests} 成功")
        return success_count == total_tests
        
    except Exception as e:
        print(f"❌ 压力测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试系统状态查询修复...")
    
    test_results = []
    
    # 执行各项测试
    test_results.append(("GraphRAG引擎统计", test_graphrag_engine_stats()))
    test_results.append(("向量检索器统计", test_vector_retriever_stats()))
    test_results.append(("图查询引擎统计", test_graph_query_stats()))
    test_results.append(("API服务器测试", test_api_server()))
    test_results.append(("压力测试", stress_test_stats()))
    
    # 汇总结果
    print("\n📊 测试结果汇总:")
    print("=" * 50)
    
    successful_tests = 0
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            successful_tests += 1
    
    print("=" * 50)
    print(f"总体结果: {successful_tests}/{len(test_results)} 测试通过")
    
    if successful_tests == len(test_results):
        print("🎉 所有测试通过！系统状态查询修复验证成功！")
        return True
    else:
        print("⚠️ 部分测试失败，请检查相关问题")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)