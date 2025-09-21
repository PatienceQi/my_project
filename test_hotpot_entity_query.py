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

def check_neo4j_data():
    print("检查Neo4j数据库中的HotpotQA数据...")
    
    try:
        uri = os.getenv('NEO4J_URI', 'neo4j://localhost:7687')
        username = os.getenv('NEO4J_USERNAME', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password')
        
        print(f"连接到: {uri}")
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session() as session:
            # 1. 检查节点标签
            print("\n1. 检查节点标签:")
            result = session.run("CALL db.labels()")
            labels = [record["label"] for record in result]
            print(f"   节点标签: {labels}")
            
            # 2. 检查HotpotEntity数量
            if 'HotpotEntity' in labels:
                result = session.run("MATCH (he:HotpotEntity) RETURN count(he) as count")
                count = result.single()["count"]
                print(f"\n2. HotpotEntity节点总数: {count}")
                
                # 3. 查看前10个HotpotEntity
                if count > 0:
                    print("\n3. 前10个HotpotEntity:")
                    result = session.run("MATCH (he:HotpotEntity) RETURN he.name, he.entity_type LIMIT 10")
                    for i, record in enumerate(result, 1):
                        name = record["he.name"]
                        entity_type = record["he.entity_type"]
                        print(f"   {i}. {name} ({entity_type})")
                    
                    # 4. 搜索包含特定关键词的实体
                    print("\n4. 搜索人名相关的实体:")
                    keywords = ['Scott', 'Ed', 'Wood', 'Derrickson', 'director', 'filmmaker']
                    for keyword in keywords:
                        result = session.run(
                            "MATCH (he:HotpotEntity) WHERE he.name CONTAINS $keyword RETURN he.name LIMIT 5", 
                            {"keyword": keyword}
                        )
                        names = [record["he.name"] for record in result]
                        if names:
                            print(f"   包含'{keyword}'的实体: {names}")
                        else:
                            print(f"   包含'{keyword}'的实体: 无")
            else:
                print("\n   ⚠️ 未找到HotpotEntity标签")
            
            # 5. 检查HotpotQuestion数量和示例
            if 'HotpotQuestion' in labels:
                result = session.run("MATCH (hq:HotpotQuestion) RETURN count(hq) as count")
                count = result.single()["count"]
                print(f"\n5. HotpotQuestion节点总数: {count}")
                
                if count > 0:
                    print("\n6. 前3个HotpotQuestion:")
                    result = session.run("MATCH (hq:HotpotQuestion) RETURN hq.question, hq.answer LIMIT 3")
                    for i, record in enumerate(result, 1):
                        question = record["hq.question"]
                        answer = record["hq.answer"]
                        print(f"   {i}. 问题: {question}")
                        print(f"      答案: {answer}")
                        print()
            
            # 6. 检查关系类型
            print("\n7. 检查关系类型:")
            result = session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in result]
            print(f"   关系类型: {rel_types}")
        
        driver.close()
        print("\n✓ 数据库检查完成")
        
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_neo4j_data()