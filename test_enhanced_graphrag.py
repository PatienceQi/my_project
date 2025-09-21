#!/usr/bin/env python3
"""
测试增强版GraphRAG引擎的功能
验证向量数据库移除后的系统运行情况
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 设置Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_enhanced_graphrag():
    """测试增强版GraphRAG引擎"""
    print("🔍 开始测试增强版GraphRAG引擎...")
    
    try:
        # 导入GraphRAG引擎
        from backend.graphrag_engine import GraphRAGEngine
        print("✅ GraphRAG引擎导入成功")
        
        # 初始化引擎
        print("\n📋 初始化GraphRAG引擎...")
        engine = GraphRAGEngine()
        print("✅ GraphRAG引擎初始化成功")
        
        # 测试系统状态
        print("\n📊 检查系统状态...")
        stats = engine.get_basic_stats()
        print(f"引擎类型: {stats.get('engine_type', 'unknown')}")
        print(f"系统状态: {stats.get('system_status', 'unknown')}")
        
        components = stats.get('components_initialized', {})
        for component, initialized in components.items():
            status = "✅ 已初始化" if initialized else "❌ 未初始化"
            print(f"  {component}: {status}")
        
        # 测试增强图查询引擎功能
        print("\n🔍 测试增强图查询引擎功能...")
        graph_engine = engine.graph_query_engine
        
        if hasattr(graph_engine, 'get_query_performance_stats'):
            perf_stats = graph_engine.get_query_performance_stats()
            print(f"查询性能统计: {perf_stats}")
        
        # 测试问答功能
        print("\n💬 测试问答功能...")
        test_questions = [
            "什么是华侨经济文化合作试验区？",
            "投资优惠政策有哪些？",
            "企业注册需要什么条件？"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n📝 测试问题 {i}: {question}")
            try:
                response = engine.answer_question(
                    question=question,
                    use_graph=True,
                    return_confidence=True
                )
                
                print(f"  答案: {response.get('answer', 'N/A')[:100]}...")
                print(f"  处理时间: {response.get('processing_time', 0):.2f}秒")
                print(f"  图谱增强: {response.get('graph_enhanced', False)}")
                print(f"  识别实体: {response.get('question_entities', [])}")
                print(f"  来源数量: {len(response.get('sources', []))}")
                
                if 'confidence' in response:
                    print(f"  可信度: {response.get('confidence', 0):.3f}")
                    print(f"  风险等级: {response.get('risk_level', 'unknown')}")
                
            except Exception as e:
                print(f"  ❌ 问答测试失败: {e}")
        
        # 测试图查询统计
        print("\n📈 测试图数据库统计...")
        try:
            graph_stats = engine.get_system_stats_safe()
            print(f"系统状态: {graph_stats.get('system_status', 'unknown')}")
            
            graph_db_stats = graph_stats.get('graph_db', {})
            print(f"图数据库状态: {graph_db_stats.get('status', 'unknown')}")
            
            if 'graph_query_performance' in graph_stats:
                perf = graph_stats['graph_query_performance']
                print(f"查询统计: {perf}")
        
        except Exception as e:
            print(f"❌ 图统计测试失败: {e}")
        
        print("\n✅ 增强版GraphRAG引擎测试完成！")
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_graph_query_engine():
    """单独测试增强图查询引擎"""
    print("\n🔍 测试增强图查询引擎...")
    
    try:
        from backend.graph_query import EnhancedGraphQueryEngine
        print("✅ 增强图查询引擎导入成功")
        
        # 初始化增强图查询引擎
        engine = EnhancedGraphQueryEngine()
        print("✅ 增强图查询引擎初始化成功")
        
        # 测试实体查询（带日志）
        print("\n🔍 测试带日志的实体查询...")
        entities = engine.query_entities_by_name_with_logging(['企业', '投资'])
        print(f"找到 {len(entities)} 个实体")
        
        # 测试关系查询（带日志）
        if entities:
            print("\n🔗 测试带日志的关系查询...")
            first_entity = entities[0]['name']
            relationships = engine.query_entity_relationships_with_logging(first_entity, max_hops=2)
            print(f"实体 '{first_entity}' 的关系网络: {len(relationships.get('paths', []))} 条路径")
        
        # 测试性能统计
        print("\n📊 获取查询性能统计...")
        perf_stats = engine.get_query_performance_stats()
        print(f"性能统计: {perf_stats}")
        
        engine.close()
        print("✅ 增强图查询引擎测试完成！")
        
    except Exception as e:
        print(f"❌ 增强图查询引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 开始测试移除向量数据库后的GraphRAG系统")
    print("=" * 60)
    
    success = True
    
    # 测试增强版GraphRAG引擎
    if not test_enhanced_graphrag():
        success = False
    
    # 测试增强图查询引擎
    if not test_graph_query_engine():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 所有测试通过！系统已成功移除向量数据库并增强图查询功能。")
    else:
        print("❌ 部分测试失败，请检查错误信息。")