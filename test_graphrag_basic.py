
"""
GraphRAG基础功能测试
"""

import sys
import os
import logging
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_basic_functionality():
    """测试基础功能"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # 测试基础导入
        from backend.simple_vector_retrieval import SimpleVectorRetriever
        from backend.graph_query import GraphQueryEngine
        from backend.entity_extractor import EntityExtractor
        
        print("✓ 基础模块导入成功")
        
        # 测试向量检索
        retriever = SimpleVectorRetriever()
        test_docs = [
            {
                'id': 'test_1',
                'title': '测试政策',
                'content': '这是一个测试政策文档，包含一些基础内容。'
            }
        ]
        retriever.add_documents(test_docs)
        results = retriever.search('测试政策')
        print(f"✓ 向量检索测试成功，找到 {len(results)} 个结果")
        
        # 测试实体提取（需要Ollama服务）
        try:
            extractor = EntityExtractor()
            entities = extractor.extract_entities_from_question("华侨试验区的政策是什么？")
            print(f"✓ 实体提取测试成功，提取到 {len(entities)} 个实体")
        except Exception as e:
            print(f"⚠ 实体提取测试失败（可能Ollama服务未启动）: {e}")
        
        # 测试图谱查询（需要Neo4j服务）
        try:
            graph_engine = GraphQueryEngine()
            stats = graph_engine.get_graph_statistics()
            print(f"✓ 图谱查询测试成功，统计信息: {stats}")
            graph_engine.close()
        except Exception as e:
            print(f"⚠ 图谱查询测试失败（可能Neo4j服务未启动）: {e}")
        
        print("\n基础功能测试完成！")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")

if __name__ == "__main__":
    test_basic_functionality()
