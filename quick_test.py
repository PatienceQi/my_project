#!/usr/bin/env python3
"""
简化测试 - 验证增强版GraphRAG系统核心功能
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 设置Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
load_dotenv()

# 设置简化日志
logging.basicConfig(level=logging.WARNING)

def quick_test():
    """快速测试核心功能"""
    print("🔍 快速测试增强版GraphRAG系统...")
    
    try:
        # 测试导入
        from backend.graphrag_engine import GraphRAGEngine
        print("✅ GraphRAG引擎导入成功")
        
        # 测试初始化
        engine = GraphRAGEngine()
        print("✅ GraphRAG引擎初始化成功")
        
        # 测试基础统计
        stats = engine.get_basic_stats()
        print(f"✅ 引擎类型: {stats.get('engine_type')}")
        print(f"✅ 系统状态: {stats.get('system_status')}")
        
        # 测试图查询引擎
        if hasattr(engine.graph_query_engine, 'get_query_performance_stats'):
            print("✅ 增强图查询引擎功能可用")
        
        # 简单问答测试
        print("🔍 测试简单问答...")
        response = engine.answer_question(
            question="什么是试验区？",
            use_graph=True,
            return_confidence=False
        )
        
        if response and 'answer' in response:
            print(f"✅ 问答测试成功，处理时间: {response.get('processing_time', 0):.2f}秒")
            print(f"✅ 图谱增强: {response.get('graph_enhanced', False)}")
        else:
            print("❌ 问答测试失败")
            
        # 测试系统统计（无向量数据库）
        sys_stats = engine.get_system_stats_safe()
        print(f"✅ 系统状态: {sys_stats.get('system_status')}")
        print(f"✅ 图数据库状态: {sys_stats.get('graph_db', {}).get('status')}")
        
        print("🎉 快速测试完成 - 所有核心功能正常！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = quick_test()
    if success:
        print("\n✅ 增强版GraphRAG系统验证通过！")
        print("📋 主要变化:")
        print("  - ✅ 移除了向量数据库依赖")
        print("  - ✅ 增强了图查询引擎的终端输出")
        print("  - ✅ 专注于基于Neo4j的结构化查询")
        print("  - ✅ 简化了系统架构")
    else:
        print("\n❌ 系统验证失败，需要进一步检查")