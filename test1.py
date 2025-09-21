#!/usr/bin/env python3
import sys
from pathlib import Path
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

load_dotenv()

def test_updated_queries():
    print("测试更新后的图谱查询功能...")
    
    try:
        # 直接使用Neo4j测试
        uri = os.getenv('NEO4J_URI', 'neo4j://localhost:7687')
        username = os.getenv('NEO4J_USERNAME', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password')
        
        print(f"连接到: {uri}")
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session() as session:
            # 1. 检查数据存在情况
            print("\n=== 数据存在性检查 ===")
            
            # 检查HotpotEntity总数
            result = session.run("MATCH (he:HotpotEntity) RETURN count(he) as count")
            hotpot_count = result.single()["count"]
            print(f"HotpotEntity总数: {hotpot_count}")
            
            # 检查包含特定名称的实体
            test_names = ['Scott', 'Ed', 'Wood', 'Derrickson']
            for name in test_names:
                result = session.run(
                    "MATCH (he:HotpotEntity) WHERE he.name CONTAINS $name RETURN he.name, he.entity_type LIMIT 5", 
                    {"name": name}
                )
                entities = [(record["he.name"], record["he.entity_type"]) for record in result]
                print(f"包含'{name}'的实体: {entities}")
            
            # 2. 测试多类型查询
            print("\n=== 测试多类型实体查询 ===")
            query = """
            UNWIND ['Scott', 'Ed'] AS search_name
            CALL {
                WITH search_name
                // 查询传统Entity节点
                MATCH (e:Entity) 
                WHERE e.name CONTAINS search_name OR e.text CONTAINS search_name
                RETURN 
                    e.name as found_entity,
                    e.type as found_type,
                    'Entity' as node_label
                
                UNION
                
                WITH search_name
                // 查询HotpotEntity节点
                MATCH (he:HotpotEntity) 
                WHERE he.name CONTAINS search_name
                RETURN 
                    he.name as found_entity,
                    he.entity_type as found_type,
                    'HotpotEntity' as node_label
            }
            RETURN DISTINCT found_entity, found_type, node_label
            LIMIT 20
            """
            
            result = session.run(query)
            entities = [(record["found_entity"], record["found_type"], record["node_label"]) for record in result]
            print(f"多类型查询结果: {entities}")
            
            # 3. 查找相关的问题
            print("\n=== 查找相关问题 ===")
            nationality_query = """
            MATCH (hq:HotpotQuestion) 
            WHERE hq.question CONTAINS 'nationality' 
               OR hq.question CONTAINS 'Scott' 
               OR hq.question CONTAINS 'Ed Wood'
            RETURN hq.question, hq.answer 
            LIMIT 5
            """
            
            result = session.run(nationality_query)
            questions = [(record["hq.question"], record["hq.answer"]) for record in result]
            print(f"找到 {len(questions)} 个相关问题:")
            for i, (q, a) in enumerate(questions, 1):
                print(f"  {i}. 问题: {q}")
                print(f"     答案: {a}")
                print()
        
        driver.close()
        
        # 4. 测试更新后的GraphQueryEngine
        print("\n=== 测试GraphQueryEngine ===")
        from backend.graph_query import GraphQueryEngine
        
        graph_engine = GraphQueryEngine()
        
        # 测试实体查询
        test_entities = ['Scott', 'Ed', 'Wood']
        entities = graph_engine.query_entities_by_name(test_entities)
        print(f"GraphQueryEngine查询到 {len(entities)} 个实体:")
        for entity in entities:
            print(f"  - {entity['name']} ({entity['type']}) - 节点类型: {entity.get('node_label', 'unknown')}")
        
        # 测试HotpotEntity专门查询
        if hasattr(graph_engine, 'query_hotpot_entities_by_name'):
            hotpot_entities = graph_engine.query_hotpot_entities_by_name(test_entities)
            print(f"\nHotpotEntity专门查询到 {len(hotpot_entities)} 个实体:")
            for entity in hotpot_entities:
                print(f"  - {entity['name']} ({entity['type']})")
        else:
            print("\n⚠️ query_hotpot_entities_by_name 方法不存在")
        
        # 测试增强统计
        if hasattr(graph_engine, 'get_enhanced_graph_statistics'):
            stats = graph_engine.get_enhanced_graph_statistics()
            print(f"\n增强统计信息: {stats}")
        
        graph_engine.close()
        print("\n✓ 测试完成！")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_updated_queries()