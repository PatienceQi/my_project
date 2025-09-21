"""
GraphRAG核心引擎 - 整合图谱增强的检索生成系统
集成向量检索、图谱查询、实体提取、幻觉检测等模块，提供统一的问答接口
"""

import os
import logging
import time
from typing import List, Dict, Optional, Tuple
import requests
from datetime import datetime
from dotenv import load_dotenv

# 移除向量检索器依赖
# from backend.vector_retrieval_safe import SafeVectorRetriever
from backend.graph_query import EnhancedGraphQueryEngine
from backend.entity_extractor import EntityExtractor
from backend.hallucination_detector import HallucinationDetector
from backend.earag_evaluator import EARAGEvaluator

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
        # self.vector_retriever = None  # 移除向量检索器
        self.graph_query_engine = None
        self.entity_extractor = None
        self.hallucination_detector = None
        self.earag_evaluator = None  # EARAG-Eval多维度评估器
        
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
            # 移除向量检索器初始化
            # logging.info("初始化向量检索器...")
            # self.vector_retriever = SafeVectorRetriever()
            
            # 初始化增强图谱查询引擎
            logging.info("初始化增强图谱查询引擎...")
            self.graph_query_engine = EnhancedGraphQueryEngine()
            
            # 初始化实体提取器
            logging.info("初始化实体提取器...")
            self.entity_extractor = EntityExtractor()
            
            # 初始化幻觉检测器
            logging.info("初始化幻觉检测器...")
            self.hallucination_detector = HallucinationDetector(
                self.graph_query_engine, 
                self.entity_extractor
            )
            
            # 初始化EARAG-Eval多维度评估器
            logging.info("初始化EARAG-Eval多维度评估器...")
            self.earag_evaluator = EARAGEvaluator()
            
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
            
            # 安全的图谱查询（使用增强版引擎）
            if use_graph and question_entities:
                try:
                    # 使用增强图谱查询引擎进行详细查询
                    graph_context = self._query_graph_context_with_logging(question_entities)
                    logging.info(f"图谱查询结果: entities={len(graph_context.get('entities', []))}, policies={len(graph_context.get('policies', []))}, relationships={len(graph_context.get('relationships', {}).get('paths', []))}")
                except Exception as e:
                    logging.warning(f"图谱查询失败，使用空上下文: {e}")
                    graph_context = {'entities': [], 'policies': [], 'relationships': {'paths': [], 'related_entities': [], 'related_policies': []}}
            
            # 3. 构建基于图谱的上下文（移除向量检索部分）
            try:
                # 构建仅基于图谱的上下文
                enhanced_context = self._build_graph_only_context(
                    question, question_entities, graph_context
                )
                
                if not enhanced_context or len(enhanced_context.strip()) < 10:
                    logging.warning("上下文构建结果为空或过短")
                    enhanced_context = f"用户问题: {question}\n问题中的关键实体: {', '.join(question_entities)}"
                else:
                    logging.info("基于图谱的上下文构建完成")
                    
            except Exception as e:
                logging.warning(f"构建图谱上下文失败，使用基础上下文: {e}")
                enhanced_context = f"用户问题: {question}\n问题中的关键实体: {', '.join(question_entities)}"
            
            # 4. 生成答案（添加超时保护）
            try:
                # 添加超时保护的答案生成
                import threading
                import queue
                
                def run_answer_generation():
                    try:
                        return self._generate_answer(question, enhanced_context)
                    except Exception as e:
                        logging.warning(f"答案生成执行异常: {e}")
                        return "抱歉，由于系统问题无法生成回答。这个问题似乎超出了当前知识库的范围。"
                
                # 使用线程和队列实现超时控制
                result_queue = queue.Queue()
                
                def worker():
                    result = run_answer_generation()
                    result_queue.put(result)
                
                thread = threading.Thread(target=worker)
                thread.daemon = True
                thread.start()
                
                try:
                    # 等待30秒（答案生成可能需要更长时间）
                    answer = result_queue.get(timeout=30)
                    if not answer or not answer.strip():
                        logging.warning("答案生成结果为空")
                        answer = "抱歉，由于系统问题无法生成回答。这个问题似乎超出了当前知识库的范围。"
                    else:
                        logging.info("答案生成完成")
                except queue.Empty:
                    logging.warning("答案生成超时(30秒)")
                    answer = "抱歉，由于网络或系统问题导致答案生成超时，请稍后重试。"
                    
            except Exception as e:
                logging.error(f"答案生成失败: {e}")
                answer = "抱歉，由于系统问题无法生成回答。这个问题似乎超出了当前知识库的范围。"
            
            # 5. 幻觉检测（如果启用）
            confidence_info = {}
            if return_confidence:
                try:
                    # 添加超时保护的幻觉检测
                    import threading
                    import queue
                    
                    def run_hallucination_detection():
                        try:
                            return self.hallucination_detector.detect_hallucination(
                                answer, question, [], graph_context  # 向量结果传入空列表
                            )
                        except Exception as e:
                            logging.warning(f"幻觉检测执行异常: {e}")
                            return {
                                'confidence': 0.5,
                                'risk_level': 'medium',
                                'is_reliable': False,
                                'warnings': [f'幻觉检测异常: {str(e)}'],
                                'detailed_scores': {}
                            }
                    
                    # 使用线程和队列实现超时控制
                    result_queue = queue.Queue()
                    
                    def worker():
                        result = run_hallucination_detection()
                        result_queue.put(result)
                    
                    thread = threading.Thread(target=worker)
                    thread.daemon = True
                    thread.start()
                    
                    try:
                        # 等待15秒
                        confidence_info = result_queue.get(timeout=15)
                        logging.info("幻觉检测完成")
                    except queue.Empty:
                        logging.warning("幻觉检测超时(15秒)")
                        confidence_info = {
                            'confidence': 0.3,
                            'risk_level': 'high',
                            'is_reliable': False,
                            'warnings': ['幻觉检测超时，建议谨慎对待答案'],
                            'detailed_scores': {}
                        }
                        
                except Exception as e:
                    logging.warning(f"幻觉检测失败: {e}")
                    confidence_info = {
                        'confidence': 0.5,
                        'risk_level': 'medium',
                        'is_reliable': False,
                        'warnings': ['幻觉检测系统异常'],
                        'detailed_scores': {}
                    }
            
            # 6. 构建响应
            try:
                response = {
                    'answer': answer,
                    'processing_time': round(time.time() - start_time, 2),
                    'sources': self._build_sources_info([], graph_context),  # 移除向量结果
                    'question_entities': question_entities,
                    'graph_enhanced': use_graph and bool(graph_context.get('entities', []) or graph_context.get('policies', []))
                }
                
                # 添加可信度信息
                if return_confidence and confidence_info:
                    response.update({
                        'confidence': confidence_info.get('confidence', 0.5),
                        'risk_level': confidence_info.get('risk_level', 'medium'),
                        'is_reliable': confidence_info.get('is_reliable', False),
                        'warnings': confidence_info.get('warnings', []),
                        'detailed_scores': confidence_info.get('detailed_scores', {})
                    })
            except Exception as e:
                logging.error(f"构建响应失败: {e}")
                response = {
                    'answer': answer,
                    'processing_time': round(time.time() - start_time, 2),
                    'sources': [],
                    'question_entities': question_entities,
                    'graph_enhanced': False,
                    'error': '部分功能异常'
                }
            
            logging.info(f"问题处理完成，耗时: {response['processing_time']}秒")
            return response
            
        except Exception as e:
            logging.error(f"问题处理失败: {e}")
            import traceback
            traceback.print_exc()
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
    
    def answer_question_with_earag_eval(self, question: str, use_graph: bool = True) -> Dict:
        """
        带EARAG-Eval多维度评估的问答接口
        
        Args:
            question: 用户问题
            use_graph: 是否使用图谱增强
            
        Returns:
            包含答案、EARAG-Eval评估结果等信息的字典
        """
        start_time = time.time()
        
        try:
            logging.info(f"开始执行EARAG-Eval评估问答: {question}")
            
            # 1. 问题预处理和实体提取
            question_entities = self.entity_extractor.extract_entities_from_question(question)
            logging.info(f"从问题中提取到实体: {question_entities}")
            
            # 2. 并行执行向量检索和图谱查询
            vector_results = []
            graph_context = {}
            
            # 安全的图谱查询（使用增强版引擎）
            if use_graph and question_entities:
                try:
                    # 使用增强图谱查询引擎进行详细查询
                    graph_context = self._query_graph_context_with_logging(question_entities)
                    logging.info(f"图谱查询结果: entities={len(graph_context.get('entities', []))}, policies={len(graph_context.get('policies', []))}, relationships={len(graph_context.get('relationships', {}).get('paths', []))}")
                except Exception as e:
                    logging.warning(f"图谱查询失败，使用空上下文: {e}")
                    graph_context = {'entities': [], 'policies': [], 'relationships': {'paths': [], 'related_entities': [], 'related_policies': []}}
            
            # 移除向量检索部分
            vector_results = []  # 不再使用向量检索
            
            # 3. 构建增强上下文（使用图谱专用方法）
            try:
                enhanced_context = self._build_graph_only_context(
                    question, question_entities, graph_context
                )
            except Exception as e:
                logging.warning(f"构建增强上下文失败，使用基础上下文: {e}")
                enhanced_context = f"用户问题: {question}\n问题中的关键实体: {', '.join(question_entities)}"
            
            # 4. 生成答案
            try:
                answer = self._generate_answer(question, enhanced_context)
            except Exception as e:
                logging.error(f"答案生成失败: {e}")
                answer = "抱歉，由于系统问题无法生成回答。这个问题似乎超出了当前知识库的范围。"
            
            # 5. 准备图谱实体集合
            graph_entities = set()
            try:
                if graph_context:
                    # 从图谱上下文中提取实体
                    for entity in graph_context.get('entities', []):
                        if isinstance(entity, dict) and 'name' in entity:
                            graph_entities.add(entity['name'].lower())
                        elif isinstance(entity, str):
                            graph_entities.add(entity.lower())
                    
                    # 从政策中提取相关实体
                    for policy in graph_context.get('policies', []):
                        if isinstance(policy, dict) and 'related_entities' in policy:
                            for ent in policy['related_entities']:
                                graph_entities.add(ent.lower())
            except Exception as e:
                logging.warning(f"提取图谱实体失败: {e}")
                graph_entities = set()
            
            # 6. 执行EARAG-Eval多维度评估
            try:
                context_list = []
                for result in vector_results:
                    context_list.append(result.get('document', ''))
                
                earag_evaluation = self.earag_evaluator.evaluate(
                    question=question,
                    answer=answer,
                    context=context_list,
                    graph_entities=graph_entities
                )
            except Exception as e:
                logging.warning(f"EARAG-Eval评估失败: {e}")
                earag_evaluation = {
                    'overall_score': 0.5,
                    'quality_level': '系统异常',
                    'diagnosis': f'评估系统异常: {str(e)}',
                    'detailed_analysis': {'error': str(e)}
                }
            
            # 7. 构建综合响应
            try:
                response = {
                    'answer': answer,
                    'processing_time': round(time.time() - start_time, 2),
                    'sources': self._build_sources_info(vector_results, graph_context),
                    'question_entities': question_entities,
                    'graph_enhanced': use_graph and bool(graph_context.get('entities', []) or graph_context.get('policies', [])),
                    
                    # EARAG-Eval评估结果
                    'earag_evaluation': earag_evaluation,
                    'quality_score': earag_evaluation.get('overall_score', 0.5),
                    'quality_level': earag_evaluation.get('quality_level', '未知'),
                    'evaluation_diagnosis': earag_evaluation.get('diagnosis', '评估完成'),
                    
                    # 质量警告
                    'quality_warning': earag_evaluation.get('overall_score', 0.5) < 0.7,
                    'recommendations': earag_evaluation.get('detailed_analysis', {}).get('overall', {}).get('recommendations', [])
                }
            except Exception as e:
                logging.error(f"构建综合响应失败: {e}")
                response = {
                    'answer': answer,
                    'processing_time': round(time.time() - start_time, 2),
                    'sources': [],
                    'question_entities': question_entities,
                    'graph_enhanced': False,
                    'earag_evaluation': {'error': str(e)},
                    'quality_score': 0.0,
                    'quality_level': '错误',
                    'quality_warning': True,
                    'error': '响应构建异常'
                }
            
            # 添加传统幻觉检测结果（作为对比）
            try:
                traditional_confidence = self.hallucination_detector.detect_hallucination(
                    answer, question, [], graph_context  # 向量结果传入空列表
                )
                response['traditional_confidence'] = traditional_confidence
            except Exception as e:
                logging.warning(f"传统幻觉检测失败: {e}")
                response['traditional_confidence'] = {'error': str(e)}
            
            logging.info(f"EARAG-Eval评估问答完成，整体评分: {response.get('quality_score', 0):.3f}")
            return response
            
        except Exception as e:
            logging.error(f"EARAG-Eval评估问答失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'answer': f"抱歉，处理您的问题时出现错误: {str(e)}",
                'error': str(e),
                'processing_time': round(time.time() - start_time, 2),
                'sources': [],
                'quality_score': 0.0,
                'quality_level': '错误',
                'quality_warning': True,
                'earag_evaluation': {'error': str(e)}
            }
    
    def _query_graph_context_with_logging(self, question_entities: List[str]) -> Dict:
        """使用增强图谱查询引擎进行带日志输出的查询"""
        try:
            graph_context = {
                'entities': [],
                'policies': [],
                'relationships': {'paths': [], 'related_entities': [], 'related_policies': []}
            }
            
            if not question_entities:
                return graph_context
            
            # 使用增强版实体查询
            entities = self.graph_query_engine.query_entities_by_name_with_logging(question_entities)
            graph_context['entities'] = entities
            
            # 使用增强版政策查询
            policies = self.graph_query_engine.query_policies_by_entities_with_logging(question_entities)
            graph_context['policies'] = policies
            
            # 使用增强版关系查询（仅查询第一个实体以避免过载）
            if question_entities:
                main_entity = question_entities[0]
                relationships = self.graph_query_engine.query_entity_relationships_with_logging(main_entity)
                graph_context['relationships'] = relationships
            
            logging.info(f"增强图谱查询完成: {len(entities)}个实体, {len(policies)}个政策")
            return graph_context
            
        except Exception as e:
            logging.error(f"增强图谱查询失败: {e}")
            return {'entities': [], 'policies': [], 'relationships': {'paths': [], 'related_entities': [], 'related_policies': []}}
    
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
    
    def _build_graph_only_context(self, question: str, question_entities: List[str], 
                                 graph_context: Dict) -> str:
        """构建仅基于图查询的增强上下文"""
        context_parts = []
        
        try:
            # 添加问题信息
            context_parts.append(f"用户问题: {question}")
            
            if question_entities:
                context_parts.append(f"问题中的关键实体: {', '.join(question_entities)}")
            
            # 添加图谱查询结果
            if graph_context and isinstance(graph_context, dict):
                context_parts.append("\n=== 知识图谱查询结果 ===")
                
                # 添加实体信息
                entities = graph_context.get('entities', [])
                if entities and len(entities) > 0:
                    context_parts.append(f"相关实体 ({len(entities)} 个):")
                    for entity in entities[:5]:  # 限制显示数量
                        try:
                            if isinstance(entity, dict):
                                entity_name = entity.get('name', '')
                                entity_type = entity.get('type', '')
                                node_label = entity.get('node_label', '')
                                context_parts.append(f"- {entity_name}: {entity_type} ({node_label})")
                                
                                # 添加关系信息
                                relations = entity.get('relations', [])
                                if relations and len(relations) > 0:
                                    rel_texts = []
                                    for r in relations[:3]:  # 只显示前3个关系
                                        if isinstance(r, dict):
                                            rel_text = f"{r.get('relation', '')}→{r.get('target', '')}"
                                            rel_texts.append(rel_text)
                                    if rel_texts:
                                        context_parts.append(f"  关系: {', '.join(rel_texts)}")
                        except Exception as e:
                            logging.warning(f"处理实体信息失败: {e}")
                            continue
                
                # 添加政策信息
                policies = graph_context.get('policies', [])
                if policies and len(policies) > 0:
                    context_parts.append(f"\n相关政策/问题 ({len(policies)} 个):")
                    for policy in policies[:3]:  # 限制显示数量
                        try:
                            if isinstance(policy, dict):
                                policy_title = policy.get('title', '')
                                data_type = policy.get('data_type', 'unknown')
                                issuing_agency = policy.get('issuing_agency', 'unknown')
                                context_parts.append(f"- {policy_title[:80]}...")
                                context_parts.append(f"  数据类型: {data_type}, 发布机构: {issuing_agency}")
                                
                                # 添加相关实体
                                related_entities = policy.get('related_entities', [])
                                if related_entities:
                                    entities_list = related_entities[:5]
                                    context_parts.append(f"  涉及实体: {', '.join(entities_list)}")
                        except Exception as e:
                            logging.warning(f"处理政策信息失败: {e}")
                            continue
                
                # 添加关系网络信息
                relationships = graph_context.get('relationships', {})
                if relationships and isinstance(relationships, dict):
                    paths = relationships.get('paths', [])
                    related_entities = relationships.get('related_entities', [])
                    related_policies = relationships.get('related_policies', [])
                    
                    if paths or related_entities or related_policies:
                        context_parts.append(f"\n关系网络信息:")
                        
                        if paths:
                            context_parts.append(f"  发现路径: {len(paths)} 条")
                        
                        if related_entities:
                            context_parts.append(f"  相关实体: {', '.join(related_entities[:5])}")
                        
                        if related_policies:
                            context_parts.append(f"  相关政策: {', '.join(related_policies[:3])}")
                        
                        # 显示更多类型的数据
                        hotpot_questions = relationships.get('hotpot_questions', [])
                        hotpot_entities = relationships.get('hotpot_entities', [])
                        
                        if hotpot_questions:
                            context_parts.append(f"  HotpotQA问题: {len(hotpot_questions)} 个")
                        
                        if hotpot_entities:
                            context_parts.append(f"  HotpotQA实体: {len(hotpot_entities)} 个")
                
                # 如果没有任何结果
                if (not entities and not policies and 
                    not relationships.get('paths', []) and 
                    not relationships.get('related_entities', [])):
                    context_parts.append("当前知识图谱中未找到与问题直接相关的信息")
            else:
                context_parts.append("\n=== 知识图谱查询结果 ===")
                context_parts.append("未找到相关的图谱信息")
            
            enhanced_context = "\n".join(context_parts)
            
            # 限制上下文长度
            if len(enhanced_context) > 3000:
                enhanced_context = enhanced_context[:3000] + "..."
            
            return enhanced_context
            
        except Exception as e:
            logging.error(f"构建图谱上下文失败: {e}")
            # 返回最基本的上下文
            return f"用户问题: {question}\n问题中的关键实体: {', '.join(question_entities) if question_entities else '无'}"
    
    def _build_enhanced_context(self, question: str, question_entities: List[str], 
                               vector_results: List[Dict], graph_context: Dict) -> str:
        """构建增强上下文（安全版本）"""
        context_parts = []
        
        try:
            # 添加问题信息
            context_parts.append(f"用户问题: {question}")
            
            if question_entities:
                context_parts.append(f"问题中的关键实体: {', '.join(question_entities)}")
            
            # 添加向量检索结果
            if vector_results and len(vector_results) > 0:
                context_parts.append("\n=== 相关文档内容 ===")
                for i, result in enumerate(vector_results[:3], 1):
                    try:
                        similarity = result.get('similarity', 0)
                        document = result.get('document', '')
                        if document:
                            context_parts.append(f"文档{i} (相似度: {similarity:.3f}):")
                            context_parts.append(document[:300] + "...")
                            
                            metadata = result.get('metadata', {})
                            if 'title' in metadata:
                                context_parts.append(f"标题: {metadata['title']}")
                    except Exception as e:
                        logging.warning(f"处理第{i}个文档结果失败: {e}")
                        continue
            else:
                context_parts.append("\n=== 文档检索结果 ===")
                context_parts.append("未找到相关文档")
            
            # 添加图谱信息
            if graph_context and isinstance(graph_context, dict):
                # 添加相关实体信息
                entities = graph_context.get('entities', [])
                if entities and len(entities) > 0:
                    context_parts.append("\n=== 相关实体信息 ===")
                    for entity in entities[:3]:
                        try:
                            if isinstance(entity, dict):
                                entity_name = entity.get('name', 'unknown')
                                entity_type = entity.get('type', 'unknown')
                                context_parts.append(f"实体: {entity_name} (类型: {entity_type})")
                                
                                relations = entity.get('relations', [])
                                if relations and len(relations) > 0:
                                    rel_texts = []
                                    for r in relations[:3]:
                                        if isinstance(r, dict):
                                            rel_text = f"{r.get('relation', '')}→{r.get('target', '')}"
                                            rel_texts.append(rel_text)
                                    if rel_texts:
                                        context_parts.append(f"关系: {', '.join(rel_texts)}")
                        except Exception as e:
                            logging.warning(f"处理实体信息失败: {e}")
                            continue
                
                # 添加相关政策信息
                policies = graph_context.get('policies', [])
                if policies and len(policies) > 0:
                    context_parts.append("\n=== 相关政策信息 ===")
                    for policy in policies[:2]:
                        try:
                            if isinstance(policy, dict):
                                policy_title = policy.get('title', 'unknown')
                                context_parts.append(f"政策: {policy_title}")
                                
                                if 'issuing_agency' in policy:
                                    context_parts.append(f"发布机构: {policy['issuing_agency']}")
                                
                                if 'related_entities' in policy and policy['related_entities']:
                                    entities_list = policy['related_entities'][:5]
                                    context_parts.append(f"涉及实体: {', '.join(entities_list)}")
                        except Exception as e:
                            logging.warning(f"处理政策信息失败: {e}")
                            continue
                else:
                    if vector_results and len(vector_results) == 0:
                        # 如果向量和图谱都没有结果，添加提示
                        context_parts.append("\n=== 检索结果 ===")
                        context_parts.append("当前知识库中未找到与问题直接相关的信息")
            
            enhanced_context = "\n".join(context_parts)
            
            # 限制上下文长度
            if len(enhanced_context) > 3000:
                enhanced_context = enhanced_context[:3000] + "..."
            
            return enhanced_context
            
        except Exception as e:
            logging.error(f"构建增强上下文失败: {e}")
            # 返回最基本的上下文
            return f"用户问题: {question}\n问题中的关键实体: {', '.join(question_entities) if question_entities else '无'}"
    
    def _generate_answer(self, question: str, context: str) -> str:
        """生成答案（安全版本）"""
        try:
            # 检查上下文是否为空或无效
            if not context or len(context.strip()) < 10:
                # 如果上下文太短或为空，直接返回通用回答
                return "抱歉，我在当前知识库中未找到与您的问题相关的信息。请尝试使用不同的关键词或更具体的问题描述。"
            
            # 检查是否包含有效的相关内容
            if "未找到相关文档" in context and "未找到与问题直接相关的信息" in context:
                return "抱歉，我在当前政策法规知识库中未找到与您的问题相关的信息。请检查问题是否在我的专业领域范围内（中国政策法规）。"
            
            prompt = f"""
            你是一个专业的政策法规问答助手。请根据提供的上下文信息，准确回答用户问题。

            上下文信息：
            {context}

            用户问题：{question}

            回答要求：
            1. 基于上下文信息回答，不要编造不存在的信息
            2. 回答要准确、具体、有条理
            3. 如果信息不足或问题超出专业领域，请如实说明
            4. 提及具体的政策名称、机构名称时要准确
            5. 回答长度控制在200-400字
            6. 如果问题不在中国政策法规领域，请明确说明并提示用户

            请回答：
            """
            
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
        """调用Ollama API（安全版本）"""
        url = f"{self.ollama_host}/api/generate"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 500  # 使用num_predict而不是max_tokens
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            # 根据项目配置设置超时为3000秒
            response = requests.post(url, json=payload, headers=headers, timeout=3000)
            response.raise_for_status()
            
            result = response.json()
            ollama_response = result.get('response', '')
            
            if not ollama_response or not ollama_response.strip():
                logging.warning("Ollama返回空响应")
                return "抱歉，系统暂时无法生成回答，请稍后重试。"
            
            return ollama_response.strip()
            
        except requests.exceptions.Timeout:
            logging.error("Ollama API调用超时(3000秒)")
            return "抱歉，由于网络问题导致响应超时，请稍后重试。"
        except requests.exceptions.RequestException as e:
            logging.error(f"Ollama API调用失败: {e}")
            return f"抱歉，服务调用失败: {str(e)}"
        except Exception as e:
            logging.error(f"Ollama调用发生未知错误: {e}")
            return f"抱歉，发生未知错误: {str(e)}"
    
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
    
    def get_basic_stats(self) -> Dict:
        """获取基础统计信息（轻量级）"""
        try:
            return {
                'components_initialized': {
                    # 'vector_retriever': self.vector_retriever is not None,  # 移除向量检索器
                    'graph_query_engine': self.graph_query_engine is not None,
                    'entity_extractor': self.entity_extractor is not None,
                    'hallucination_detector': self.hallucination_detector is not None,
                    'earag_evaluator': self.earag_evaluator is not None
                },
                'system_status': 'healthy',
                'last_check': time.time(),
                'engine_type': 'GraphRAG-Enhanced'
            }
        except Exception as e:
            logging.error(f"获取基础统计失败: {e}")
            return {
                'system_status': 'error',
                'error': str(e),
                'last_check': time.time(),
                'engine_type': 'GraphRAG'
            }
    
    def get_system_stats_safe(self) -> Dict:
        """安全的系统统计信息获取（移除向量数据库）"""
        stats = {
            # 'vector_db': {'status': 'removed'},  # 移除向量数据库
            'graph_db': {'status': 'unknown'},
            'system_status': 'partial'
        }
        
        # 获取图数据库统计
        try:
            graph_stats = self._get_graph_stats_with_timeout()
            stats['graph_db'] = graph_stats
        except Exception as e:
            logging.warning(f"图数据库统计获取失败: {e}")
            stats['graph_db'] = {'status': 'error', 'message': str(e)}
        
        # 添加增强图谱引擎统计
        try:
            if hasattr(self.graph_query_engine, 'get_query_performance_stats'):
                performance_stats = self.graph_query_engine.get_query_performance_stats()
                stats['graph_query_performance'] = performance_stats
        except Exception as e:
            logging.warning(f"获取图查询性能统计失败: {e}")
        
        # 确定整体状态
        if stats['graph_db'].get('status') == 'healthy':
            stats['system_status'] = 'healthy'
        elif stats['graph_db'].get('status') == 'error':
            stats['system_status'] = 'error'
        else:
            stats['system_status'] = 'degraded'
        
        return stats
    
    # 移除向量数据库统计方法
    # def _get_vector_stats_with_timeout(self) -> Dict:
    #     """带超时保护的向量数据库统计获取（跨平台兼容）"""
    #     已移除，不再使用向量数据库
    
    def _get_graph_stats_with_timeout(self) -> Dict:
        """带超时保护的图数据库统计获取（跨平台兼容）"""
        import threading
        import queue
        
        def run_stats_query():
            try:
                if not self.graph_query_engine:
                    return {'status': 'not_connected'}
                
                # 调用安全的统计方法
                if hasattr(self.graph_query_engine, 'get_graph_statistics_safe'):
                    result = self.graph_query_engine.get_graph_statistics_safe()
                else:
                    # 回退到原方法，但在超时保护下
                    result = self.graph_query_engine.get_graph_statistics()
                    if result:
                        result['status'] = 'healthy'
                    else:
                        result = {'status': 'error', 'message': '统计信息为空'}
                
                return result
            except Exception as e:
                return {'status': 'error', 'message': f'图数据库查询失败: {str(e)}'}
        
        # 使用线程和队列实现超时控制
        result_queue = queue.Queue()
        
        def worker():
            result = run_stats_query()
            result_queue.put(result)
        
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        
        try:
            # 等待10秒
            result = result_queue.get(timeout=10)
            return result
        except queue.Empty:
            return {'status': 'timeout', 'message': '图数据库查询超时(10秒)'}
    
    def get_system_stats(self) -> Dict:
        """获取系统统计信息（保持向后兼容）"""
        try:
            # 首先尝试使用安全版本
            return self.get_system_stats_safe()
        except Exception as e:
            logging.error(f"获取系统统计失败: {e}")
            return {
                'system_status': 'error', 
                'error': str(e),
                'fallback_info': '建议使用 get_basic_stats() 或 get_system_stats_safe() 方法'
            }
    
    def analyze_document(self, document: Dict) -> Dict:
        """分析单个文档，提取实体和关系"""
        try:
            result = self.entity_extractor.extract_all_from_document(document)
            
            # 添加到向量数据库
            # 移除向量数据库部分
            # vector_success = self.vector_retriever.add_documents([document])
            vector_success = True  # 不再使用向量数据库
            
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