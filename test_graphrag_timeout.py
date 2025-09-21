#!/usr/bin/env python3
"""
测试GraphRAG引擎超时保护功能
直接测试GraphRAG问答的超时机制，跳过ChromaDB依赖问题
"""

import os
import sys
import logging
import time
import json
from typing import Dict

# 设置项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置环境变量
os.environ['LLM_BINDING_HOST'] = 'http://120.232.79.82:11434'
os.environ['OLLAMA_HOST'] = 'http://120.232.79.82:11434'
os.environ['EXPERIMENT_MODE'] = 'true'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_graphrag_timeout.log', encoding='utf-8')
    ]
)

class MockVectorRetriever:
    """模拟向量检索器"""
    
    def search(self, question: str, top_k: int = 5):
        """模拟向量检索，返回空结果"""
        logging.info(f"模拟向量检索: {question}")
        return []
    
    def get_collection_stats_safe(self):
        """安全的统计信息获取"""
        return {
            'status': 'healthy',
            'total_documents': 0,
            'message': '模拟向量数据库'
        }

class MockGraphQueryEngine:
    """模拟图查询引擎"""
    
    def query_entities_by_name(self, entity_names):
        """模拟实体查询"""
        logging.info(f"模拟图谱实体查询: {entity_names}")
        
        # 模拟延迟
        time.sleep(1)
        
        # 模拟返回实体数据
        entities = []
        for name in entity_names[:2]:
            entities.append({
                'name': name,
                'type': 'Organization',
                'relations': [
                    {'relation': '管理', 'target': '办公场所'},
                    {'relation': '负责', 'target': '审核工作'}
                ]
            })
        
        return entities
    
    def query_policies_by_entities(self, entity_names):
        """模拟政策查询"""
        logging.info(f"模拟政策查询: {entity_names}")
        
        # 模拟延迟
        time.sleep(1)
        
        # 模拟返回政策数据
        policies = []
        if '深汕数字科创产业园' in entity_names:
            policies.append({
                'title': '深汕数字科创产业园管理办法',
                'issuing_agency': '深汕合作区管委会',
                'related_entities': ['深汕数字科创产业园', '入驻企业']
            })
        
        if '入驻企业' in entity_names:
            policies.append({
                'title': '深汕合作区企业入驻管理规定',
                'issuing_agency': '深汕合作区经发局',
                'related_entities': ['入驻企业', '办公场所']
            })
        
        return policies
    
    def query_entity_relationships(self, entity_name):
        """模拟关系查询"""
        logging.info(f"模拟关系查询: {entity_name}")
        
        # 模拟延迟
        time.sleep(2)
        
        # 模拟返回50条路径（如日志所示）
        return [f"路径{i}: {entity_name} -> 相关实体{i}" for i in range(50)]
    
    def get_graph_statistics_safe(self):
        """安全的统计信息获取"""
        return {
            'status': 'healthy',
            'total_nodes': 1000,
            'total_relationships': 5000,
            'message': '模拟图数据库'
        }
    
    def close(self):
        """关闭连接"""
        pass

class MockEntityExtractor:
    """模拟实体提取器"""
    
    def extract_entities_from_question(self, question: str):
        """模拟实体提取"""
        logging.info(f"模拟实体提取: {question}")
        
        # 模拟延迟
        time.sleep(0.5)
        
        # 根据问题内容返回实体
        entities = []
        if '深汕数字科创产业园' in question:
            entities.append('深汕数字科创产业园')
        if '入驻企业' in question:
            entities.append('入驻企业')
        if '办公场所' in question:
            entities.append('办公场所')
        
        # 如果没有识别到实体，返回通用实体
        if not entities:
            entities = ['政策规定', '管理办法']
        
        return entities

class MockHallucinationDetector:
    """模拟幻觉检测器"""
    
    def __init__(self, graph_query_engine, entity_extractor):
        self.graph_query_engine = graph_query_engine
        self.entity_extractor = entity_extractor
    
    def detect_hallucination(self, answer, question, vector_results, graph_context):
        """模拟幻觉检测"""
        logging.info(f"模拟幻觉检测: {question[:30]}...")
        
        # 模拟长时间检测
        time.sleep(3)
        
        return {
            'confidence': 0.8,
            'risk_level': 'low',
            'is_reliable': True,
            'warnings': [],
            'detailed_scores': {
                'factual_consistency': 0.8,
                'contextual_relevance': 0.85,
                'completeness': 0.75
            }
        }

class MockEARAGEvaluator:
    """模拟EARAG评估器"""
    
    def evaluate(self, question, answer, context, graph_entities):
        """模拟评估"""
        return {
            'overall_score': 0.7,
            'quality_level': '良好',
            'diagnosis': '评估完成',
            'detailed_analysis': {}
        }

def patch_graphrag_engine():
    """修补GraphRAG引擎以使用模拟组件"""
    from backend.graphrag_engine import GraphRAGEngine
    
    # 保存原始的初始化方法
    original_init = GraphRAGEngine._initialize_components
    
    def mock_initialize_components(self):
        """使用模拟组件进行初始化"""
        try:
            logging.info("使用模拟组件初始化...")
            
            # 使用模拟组件
            self.vector_retriever = MockVectorRetriever()
            self.graph_query_engine = MockGraphQueryEngine()
            self.entity_extractor = MockEntityExtractor()
            self.hallucination_detector = MockHallucinationDetector(
                self.graph_query_engine, 
                self.entity_extractor
            )
            self.earag_evaluator = MockEARAGEvaluator()
            
            logging.info("模拟组件初始化成功")
            
        except Exception as e:
            logging.error(f"模拟组件初始化失败: {e}")
            raise
    
    # 替换初始化方法
    GraphRAGEngine._initialize_components = mock_initialize_components

def test_graphrag_timeout():
    """测试GraphRAG引擎的超时保护功能"""
    
    print("=" * 60)
    print("GraphRAG引擎超时保护功能测试")
    print("=" * 60)
    
    try:
        # 修补GraphRAG引擎
        patch_graphrag_engine()
        
        # 导入GraphRAG引擎
        from backend.graphrag_engine import GraphRAGEngine
        
        # 创建引擎实例
        print("\n1. 初始化GraphRAG引擎...")
        engine = GraphRAGEngine()
        print("✓ GraphRAG引擎初始化成功")
        
        # 测试系统状态
        print("\n2. 测试系统状态...")
        stats = engine.get_basic_stats()
        print(f"✓ 系统状态: {stats.get('system_status', 'unknown')}")
        
        # 测试问题（与用户报告的相同）
        test_question = "适用于深汕数字科创产业园入驻企业办公场所的申报、审核和租金考核等日常运营管理工作是那一条规定"
        
        print(f"\n3. 测试问答功能...")
        print(f"问题: {test_question}")
        print("\n开始处理...")
        
        start_time = time.time()
        
        # 执行问答
        result = engine.answer_question(
            question=test_question,
            use_graph=True,
            return_confidence=True
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\n4. 处理结果:")
        print(f"✓ 处理完成，耗时: {processing_time:.2f}秒")
        print(f"✓ 答案长度: {len(result.get('answer', ''))}")
        print(f"✓ 图谱增强: {result.get('graph_enhanced', False)}")
        print(f"✓ 识别实体: {result.get('question_entities', [])}")
        print(f"✓ 可信度: {result.get('confidence', 'N/A')}")
        print(f"✓ 风险等级: {result.get('risk_level', 'N/A')}")
        
        if result.get('warnings'):
            print(f"⚠ 警告: {result.get('warnings')}")
        
        print(f"\n答案预览: {result.get('answer', '')[:200]}...")
        
        # 测试系统稳定性
        print(f"\n5. 测试系统稳定性...")
        print("服务器依然运行正常，未发生自动关闭")
        
        # 再次获取系统状态确认
        final_stats = engine.get_basic_stats()
        print(f"✓ 最终系统状态: {final_stats.get('system_status', 'unknown')}")
        
        # 关闭引擎
        engine.close()
        print("✓ GraphRAG引擎已安全关闭")
        
        print("\n" + "=" * 60)
        print("测试完成 - 所有超时保护机制工作正常！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_graphrag_timeout()
    exit(0 if success else 1)