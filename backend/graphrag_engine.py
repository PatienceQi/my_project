"""
GraphRAG核心引擎 - 整合图谱增强的检索生成系统
集成向量检索、图谱查询、实体提取、幻觉检测等模块，提供统一的问答接口
"""

import os
import logging
import time
from typing import List, Dict, Optional, Tuple
import requests
from dotenv import load_dotenv

from backend.vector_retrieval import VectorRetriever
from backend.graph_query import GraphQueryEngine
from backend.entity_extractor import EntityExtractor
from backend.hallucination_detector import HallucinationDetector

# 加载环境变量
load_dotenv()

class GraphRAGEngine:
    """GraphRAG引擎 - 图谱增强的检索生成系统"""
    
    def __init__(self):
        """初始化GraphRAG引擎"""
        # 关键修复：强制设置远程Ollama配置，防止所有子组件连接本地服务
        self._force_remote_ollama_config()
        
        # 初始化配置参数
        self.ollama_host = self._get_verified_ollama_host()
        self.model_name = os.getenv('LLM_MODEL', 'llama3.2:latest')
        self.experiment_mode = os.getenv('EXPERIMENT_MODE', 'true').lower() == 'true'
        
        # 初始化各个组件
        self.vector_retriever = None
        self.graph_query_engine = None
        self.entity_extractor = None
        self.hallucination_detector = None
        
        self._initialize_components()
        
        logging.info(f"GraphRAG引擎初始化完成 - 使用远程服务: {self.ollama_host}")
    
    def _force_remote_ollama_config(self):
        """强制设置远程Ollama配置，确保所有子组件使用相同配置"""
        remote_host = 'http://120.232.79.82:11434'
        
        # 设置所有可能影响Ollama连接的环境变量
        config_vars = {
            'OLLAMA_HOST': remote_host,
            'OLLAMA_BASE_URL': remote_host,
            'LLM_BINDING_HOST': remote_host,
            'OLLAMA_NO_SERVE': '1',
            'OLLAMA_ORIGINS': '*',
            'OLLAMA_KEEP_ALIVE': '5m'
        }
        
        for key, value in config_vars.items():
            old_value = os.environ.get(key)
            os.environ[key] = value
            if old_value != value:
                logging.info(f"GraphRAG引擎环境变量修正: {key} = {value} (原值: {old_value})")
        
        # 验证配置正确性
        self._validate_environment_config()
    
    def _get_verified_ollama_host(self) -> str:
        """获取并验证Ollama主机地址"""
        host = os.getenv('LLM_BINDING_HOST', 'http://120.232.79.82:11434')
        
        # 确保主机地址格式正确
        if not host.startswith('http'):
            host = f"http://{host}"
        
        # 验证是否为远程地址
        if '127.0.0.1' in host or 'localhost' in host:
            logging.warning(f"GraphRAG引擎检测到本地地址 {host}，强制使用远程服务")
            host = 'http://120.232.79.82:11434'
            os.environ['LLM_BINDING_HOST'] = host
        
        return host
    
    def _validate_environment_config(self):
        """验证环境配置的正确性"""
        required_vars = {
            'LLM_BINDING_HOST': 'http://120.232.79.82:11434',
            'OLLAMA_HOST': 'http://120.232.79.82:11434',
            'OLLAMA_NO_SERVE': '1'
        }
        
        config_valid = True
        for key, expected in required_vars.items():
            current = os.environ.get(key)
            if current != expected:
                logging.error(f"配置错误: {key} = {current}, 期望: {expected}")
                config_valid = False
        
        if not config_valid:
            raise ValueError("环境配置验证失败，请检查远程Ollama设置")
    
    def _initialize_components(self):
        """初始化所有组件"""
        try:
            # 初始化向量检索器
            logging.info("初始化向量检索器...")
            self.vector_retriever = VectorRetriever()
            
            # 初始化图谱查询引擎
            logging.info("初始化图谱查询引擎...")
            self.graph_query_engine = GraphQueryEngine()
            
            # 初始化实体提取器
            logging.info("初始化实体提取器...")
            self.entity_extractor = EntityExtractor()
            
            # 初始化幻觉检测器
            logging.info("初始化幻觉检测器...")
            self.hallucination_detector = HallucinationDetector(
                self.graph_query_engine, 
                self.entity_extractor
            )
            
            logging.info("所有组件初始化成功")
            
        except Exception as e:
            logging.error(f"组件初始化失败: {e}")
            raise
    
    def answer_question(self, question: str, use_graph: bool = True, 
                       return_confidence: bool = True) -> Dict:
        """
        回答问题的主要接口
        
        Args:
            question: 用户问题
            use_graph: 是否使用图谱增强
            return_confidence: 是否返回可信度信息
            
        Returns:
            包含答案、可信度、来源等信息的字典
        """
        start_time = time.time()
        
        try:
            logging.info(f"开始处理问题: {question}")
            
            # 1. 问题预处理和实体提取
            question_entities = self.entity_extractor.extract_entities_from_question(question)
            logging.info(f"从问题中提取到实体: {question_entities}")
            
            # 2. 并行执行向量检索和图谱查询
            vector_results = []
            graph_context = {}
            
            if use_graph and question_entities:
                # 图谱查询
                graph_context = self._query_graph_context(question_entities)
                
            # 向量检索
            vector_results = self.vector_retriever.search(question, top_k=5)
            
            # 3. 构建增强上下文
            enhanced_context = self._build_enhanced_context(
                question, question_entities, vector_results, graph_context
            )
            
            # 4. 生成答案
            answer = self._generate_answer(question, enhanced_context)
            
            # 5. 幻觉检测（如果启用）
            confidence_info = {}
            if return_confidence:
                confidence_info = self.hallucination_detector.detect_hallucination(
                    answer, question, vector_results, graph_context
                )
            
            # 6. 构建响应
            response = {
                'answer': answer,
                'processing_time': round(time.time() - start_time, 2),
                'sources': self._build_sources_info(vector_results, graph_context),
                'question_entities': question_entities,
                'graph_enhanced': use_graph and bool(graph_context)
            }
            
            # 添加可信度信息
            if return_confidence and confidence_info:
                response.update({
                    'confidence': confidence_info['confidence'],
                    'risk_level': confidence_info['risk_level'],
                    'is_reliable': confidence_info['is_reliable'],
                    'warnings': confidence_info['warnings'],
                    'detailed_scores': confidence_info['detailed_scores']
                })
            
            logging.info(f"问题处理完成，耗时: {response['processing_time']}秒")
            return response
            
        except Exception as e:
            logging.error(f"问题处理失败: {e}")
            return {
                'answer': f"抱歉，处理您的问题时出现错误: {str(e)}",
                'error': str(e),
                'processing_time': round(time.time() - start_time, 2),
                'sources': [],
                'confidence': 0.0,
                'risk_level': 'high',
                'is_reliable': False,
                'warnings': ['系统错误，无法生成可靠答案']
            }
    
    def _query_graph_context(self, question_entities: List[str]) -> Dict:
        """查询图谱上下文"""
        try:
            graph_context = {
                'entities': [],
                'policies': [],
                'relationships': []
            }
            
            if not question_entities:
                return graph_context
            
            # 查询相关实体
            entities = self.graph_query_engine.query_entities_by_name(question_entities)
            graph_context['entities'] = entities
            
            # 查询相关政策
            policies = self.graph_query_engine.query_policies_by_entities(question_entities)
            graph_context['policies'] = policies
            
            # 查询实体关系网络（仅查询第一个实体以避免过载）
            if question_entities:
                main_entity = question_entities[0]
                relationships = self.graph_query_engine.query_entity_relationships(main_entity)
                graph_context['relationships'] = relationships
            
            logging.info(f"图谱查询完成: {len(entities)}个实体, {len(policies)}个政策")
            return graph_context
            
        except Exception as e:
            logging.error(f"图谱查询失败: {e}")
            return {'entities': [], 'policies': [], 'relationships': []}
    
    def _build_enhanced_context(self, question: str, question_entities: List[str], 
                               vector_results: List[Dict], graph_context: Dict) -> str:
        """构建增强上下文"""
        context_parts = []
        
        # 添加问题信息
        context_parts.append(f"用户问题: {question}")
        
        if question_entities:
            context_parts.append(f"问题中的关键实体: {', '.join(question_entities)}")
        
        # 添加向量检索结果
        if vector_results:
            context_parts.append("\n=== 相关文档内容 ===")
            for i, result in enumerate(vector_results[:3], 1):
                context_parts.append(f"文档{i} (相似度: {result['similarity']:.3f}):")
                context_parts.append(result['document'][:300] + "...")
                
                metadata = result.get('metadata', {})
                if 'title' in metadata:
                    context_parts.append(f"标题: {metadata['title']}")
        
        # 添加图谱信息
        if graph_context:
            # 添加相关实体信息
            entities = graph_context.get('entities', [])
            if entities:
                context_parts.append("\n=== 相关实体信息 ===")
                for entity in entities[:3]:
                    context_parts.append(f"实体: {entity.get('name', 'unknown')} (类型: {entity.get('type', 'unknown')})")
                    relations = entity.get('relations', [])
                    if relations:
                        rel_texts = [f"{r['relation']}→{r['target']}" for r in relations[:3]]
                        context_parts.append(f"关系: {', '.join(rel_texts)}")
            
            # 添加相关政策信息
            policies = graph_context.get('policies', [])
            if policies:
                context_parts.append("\n=== 相关政策信息 ===")
                for policy in policies[:2]:
                    context_parts.append(f"政策: {policy.get('title', 'unknown')}")
                    if 'issuing_agency' in policy:
                        context_parts.append(f"发布机构: {policy['issuing_agency']}")
                    if 'related_entities' in policy:
                        context_parts.append(f"涉及实体: {', '.join(policy['related_entities'][:5])}")
        
        enhanced_context = "\n".join(context_parts)
        
        # 限制上下文长度
        if len(enhanced_context) > 2000:
            enhanced_context = enhanced_context[:2000] + "..."
        
        return enhanced_context
    
    def _generate_answer(self, question: str, context: str) -> str:
        """生成答案"""
        prompt = f"""
        你是一个专业的政策法规问答助手。请根据提供的上下文信息，准确回答用户问题。

        上下文信息：
        {context}

        用户问题：{question}

        回答要求：
        1. 基于上下文信息回答，不要编造不存在的信息
        2. 回答要准确、具体、有条理
        3. 如果信息不足，请如实说明
        4. 提及具体的政策名称、机构名称时要准确
        5. 回答长度控制在200-400字

        请回答：
        """
        
        try:
            response = self._call_ollama(prompt)
            
            # 清理回答
            answer = response.strip()
            if not answer:
                answer = "抱歉，无法根据现有信息回答您的问题。"
            
            return answer
            
        except Exception as e:
            logging.error(f"答案生成失败: {e}")
            return f"抱歉，生成答案时出现错误: {str(e)}"
    
    def _call_ollama(self, prompt: str) -> str:
        """调用Ollama API"""
        url = f"{self.ollama_host}/api/generate"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "top_k": 40,
                "max_tokens": 500
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '')
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Ollama API调用失败: {e}")
            raise
    
    def _build_sources_info(self, vector_results: List[Dict], graph_context: Dict) -> List[Dict]:
        """构建来源信息"""
        sources = []
        
        # 添加文档来源
        for result in vector_results[:3]:
            metadata = result.get('metadata', {})
            source = {
                'type': 'document',
                'title': metadata.get('title', '未知文档'),
                'relevance': result.get('similarity', 0),
                'content_preview': result['document'][:100] + "..."
            }
            sources.append(source)
        
        # 添加图谱来源
        if graph_context:
            entities = graph_context.get('entities', [])
            if entities:
                entity_names = [e.get('name', 'unknown') for e in entities[:3]]
                relations = []
                for entity in entities[:3]:
                    for rel in entity.get('relations', [])[:2]:
                        relations.append(rel['relation'])
                
                source = {
                    'type': 'graph_entity',
                    'entities': entity_names,
                    'relations': list(set(relations))
                }
                sources.append(source)
        
        return sources
    
    def get_system_stats(self) -> Dict:
        """获取系统统计信息"""
        try:
            stats = {
                'vector_db': self.vector_retriever.get_collection_stats(),
                'graph_db': self.graph_query_engine.get_graph_statistics(),
                'system_status': 'healthy'
            }
            
            return stats
            
        except Exception as e:
            logging.error(f"获取系统统计失败: {e}")
            return {'system_status': 'error', 'error': str(e)}
    
    def analyze_document(self, document: Dict) -> Dict:
        """分析单个文档，提取实体和关系"""
        try:
            result = self.entity_extractor.extract_all_from_document(document)
            
            # 添加到向量数据库
            vector_success = self.vector_retriever.add_documents([document])
            
            result['vector_indexed'] = vector_success
            return result
            
        except Exception as e:
            logging.error(f"文档分析失败: {e}")
            return {
                'entities': [],
                'relations': [],
                'vector_indexed': False,
                'error': str(e)
            }
    
    def close(self):
        """关闭所有连接"""
        try:
            if self.graph_query_engine:
                self.graph_query_engine.close()
            logging.info("GraphRAG引擎已关闭")
        except Exception as e:
            logging.error(f"关闭GraphRAG引擎时出错: {e}")


def test_graphrag_engine():
    """测试GraphRAG引擎"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # 创建引擎实例
        engine = GraphRAGEngine()
        
        # 测试系统状态
        print("=== 系统状态 ===")
        stats = engine.get_system_stats()
        print(f"系统状态: {stats.get('system_status', 'unknown')}")
        
        # 测试问答
        print("\n=== 问答测试 ===")
        test_questions = [
            "华侨经济文化合作试验区的管理机构是什么？",
            "中小企业有哪些税收优惠政策？",
            "投资项目需要哪些审批程序？"
        ]
        
        for question in test_questions:
            print(f"\n问题: {question}")
            
            # 测试普通RAG
            result_normal = engine.answer_question(question, use_graph=False, return_confidence=False)
            print(f"普通RAG答案: {result_normal['answer'][:100]}...")
            
            # 测试GraphRAG
            result_graph = engine.answer_question(question, use_graph=True, return_confidence=True)
            print(f"GraphRAG答案: {result_graph['answer'][:100]}...")
            print(f"可信度: {result_graph.get('confidence', 'N/A')}")
            print(f"风险等级: {result_graph.get('risk_level', 'N/A')}")
            
            if result_graph.get('warnings'):
                print(f"警告: {', '.join(result_graph['warnings'])}")
    
    finally:
        engine.close()


if __name__ == "__main__":
    test_graphrag_engine()