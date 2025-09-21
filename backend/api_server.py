#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政策法规RAG问答系统 - 增强API服务器

支持传统RAG和GraphRAG两种模式，提供智能问答、会话管理和健康监控
"""

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# 导入自定义模块
from backend.exceptions import (
    SystemError, DatabaseError, LLMServiceError, ValidationError, 
    SessionError, handle_error, log_error
)
from backend.validators import InputValidator, SecurityChecker
from backend.connections import get_connection_manager
from backend.session_manager import get_conversation_manager
from backend.health_checker import get_health_checker, create_health_endpoints
from backend.metrics_collector import create_metrics_endpoints

# 尝试导入GraphRAG模块（可选）
GRAPHRAG_AVAILABLE = False
try:
    from backend.graphrag_engine import GraphRAGEngine
    GRAPHRAG_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("GraphRAG模块已加载")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"GraphRAG模块未找到，将使用传统RAG模式: {e}")

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
# 动态CORS配置函数
def configure_cors():
    """配置动态CORS支持"""
    def is_allowed_origin(origin):
        if not origin:
            return True  # 允许空源
        
        # 允许的源列表
        allowed_origins = [
            'http://localhost:3000', 'http://127.0.0.1:3000',
            'http://localhost:5000', 'http://127.0.0.1:5000',
            'file://', 'null'
        ]
        
        # 直接匹配
        if origin in allowed_origins:
            return True
            
        # 局域网地址匹配 (192.168.x.x:3000)
        import re
        if re.match(r'^http://192\.168\.\d+\.\d+:3000$', origin):
            return True
            
        # 其他局域网段 (10.x.x.x:3000, 172.16-31.x.x:3000)
        if re.match(r'^http://(10\.\d+\.\d+\.\d+|172\.(1[6-9]|2[0-9]|3[01])\.\d+\.\d+):3000$', origin):
            return True
            
        return False
    
    if os.getenv('ENVIRONMENT') == 'production':
        # 生产环境：使用严格的白名单
        CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])
    else:
        # 开发环境：使用动态验证
        CORS(app, 
             origin=is_allowed_origin,  # 使用函数进行动态验证
             supports_credentials=False,
             allow_headers=['Content-Type', 'Authorization', 'Accept', 'Origin'],
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
        
        logger.info("开发环境CORS配置已启用，支持局域网访问")

# 应用CORS配置
configure_cors()

# 全局管理器实例
connection_manager = get_connection_manager()
conversation_manager = get_conversation_manager()
health_checker = get_health_checker()

# GraphRAG引擎实例（全局）
graphrag_engine = None

def initialize_graphrag():
    """初始化GraphRAG引擎"""
    global graphrag_engine
    
    if not GRAPHRAG_AVAILABLE:
        logger.info("GraphRAG不可用，跳过初始化")
        return
    
    try:
        graphrag_engine = GraphRAGEngine()
        logger.info("GraphRAG引擎初始化成功")
    except Exception as e:
        logger.error(f"GraphRAG引擎初始化失败: {e}")
        logger.warning("系统将使用传统RAG模式")

# 初始化连接管理器
def initialize_connections():
    """初始化数据库和LLM连接"""
    try:
        neo4j_config = {
            'uri': os.getenv('NEO4J_URI', 'neo4j://localhost:7687'),
            'username': os.getenv('NEO4J_USERNAME', 'neo4j'),
            'password': os.getenv('NEO4J_PASSWORD', 'password'),
            'max_pool_size': int(os.getenv('NEO4J_MAX_POOL_SIZE', '10')),
            'connection_timeout': int(os.getenv('NEO4J_CONNECTION_TIMEOUT', '30'))
        }
        
        ollama_config = {
            'host': os.getenv('LLM_BINDING_HOST', ''),
            'model': os.getenv('LLM_MODEL', 'llama3.2:latest'),
            'timeout': int(os.getenv('LLM_TIMEOUT', '120'))
        }
        
        # 使用宽松模式初始化，允许部分服务不可用
        connection_manager.initialize(neo4j_config, ollama_config, strict_mode=False)
        logger.info("连接管理器初始化完成")
        
    except Exception as e:
        logger.error(f"连接管理器初始化失败: {str(e)}")
        # 不抛出异常，允许系统继续启动
        logger.warning("系统将以降级模式运行，某些功能可能不可用")

# 应用启动时初始化连接
initialize_connections()
initialize_graphrag()

def query_policy_knowledge(question: str) -> list:
    """
    查询政策法规知识图谱
    
    Args:
        question: 用户问题
        
    Returns:
        list: 查询结果列表
        
    Raises:
        DatabaseError: 当数据库查询失败时
    """
    try:
        query = (
            "MATCH (p:Policy) "
            "OPTIONAL MATCH (p)-[:HAS_SECTION]->(s:Section) "
            "OPTIONAL MATCH (s)-[:CONTAINS]->(sub:SubSection) "
            "OPTIONAL MATCH (p)-[:ISSUED_BY]->(a:Agency) "
            "WHERE p.title CONTAINS $query_text OR s.title CONTAINS $query_text OR sub.title CONTAINS $query_text "
            "RETURN p.title as policy_title, p.publish_agency as agency, s.title as section_title, s.content as section_content, sub.title as sub_title, sub.content as sub_content, a.name as agency_name "
            "LIMIT 5"
        )
        
        results = connection_manager.neo4j.execute_query(query, {'query_text': question})
        return results
        
    except Exception as e:
        logger.error(f"Neo4j查询失败: {str(e)}")
        raise DatabaseError(f"数据库查询失败: {str(e)}", "policy_query")

def generate_policy_answer(question: str, session_id: str = None) -> dict:
    """
    生成政策法规问答
    
    Args:
        question: 用户问题
        session_id: 会话ID（可选）
        
    Returns:
        dict: 包含答案和实体信息的字典
        
    Raises:
        DatabaseError: 数据库查询失败
        LLMServiceError: LLM服务调用失败
    """
    try:
        # 构建包含上下文的问题
        contextual_question = question
        if session_id:
            try:
                contextual_question = conversation_manager.get_context_for_question(
                    session_id, question, include_entities=True
                )
            except SessionError:
                # 如果会话不存在，使用原始问题
                pass
        
        # 查询知识图谱
        neo4j_results = query_policy_knowledge(question)
        
        if neo4j_results:
            context = ""
            entities = []
            
            for record in neo4j_results:
                policy_title = record.get('policy_title', '未知政策')
                section_title = record.get('section_title', '')
                section_content = record.get('section_content', '内容暂无')
                sub_title = record.get('sub_title', '')
                sub_content = record.get('sub_content', '内容暂无')
                agency_name = record.get('agency_name', '未知机构')
                
                context += f"政策标题: {policy_title}\n"
                if section_title:
                    context += f"章节标题: {section_title}\n"
                    context += f"章节内容: {section_content}\n"
                if sub_title:
                    context += f"条款标题: {sub_title}\n"
                    context += f"条款内容: {sub_content}\n"
                context += f"发布机构: {agency_name}\n\n"
                
                content_to_display = sub_content if sub_content != '内容暂无' else section_content
                entities.append({
                    "policy_title": policy_title,
                    "section_title": section_title if section_title else sub_title,
                    "content": content_to_display,
                    "agency": agency_name,
                    "relation": "发布单位",
                    "label": "Policy",
                    "name": policy_title
                })
            
            # 构建LLM提示
            prompt = (
                f"你是一个政策法规专家。请根据以下信息回答用户的问题：\n\n"
                f"{context}\n"
                f"用户的问题是：{contextual_question}\n"
                f"请用简洁、准确的语言回答，并在回答中引用政策标题和具体章节或条款。"
            )
            
            # 调用LLM生成答案
            answer = ""
            if connection_manager.ollama:
                try:
                    response = connection_manager.ollama.chat(
                        messages=[{"role": "user", "content": prompt}]
                    )
                    answer = response['message']['content']
                except LLMServiceError as e:
                    logger.warning(f"LLM服务调用失败: {str(e)}，使用默认回答")
                    answer = f"根据相关政策法规，找到以下信息：\n{context}\n请查阅具体条款获取详细信息。"
            else:
                # 如果LLM不可用，返回基本信息
                answer = f"根据相关政策法规，找到以下信息：\n{context}\n请查阅具体条款获取详细信息。"
            
            # 保存到会话历史
            if session_id:
                try:
                    conversation_manager.add_message_to_session(
                        session_id, 'user', question, entities
                    )
                    conversation_manager.add_message_to_session(
                        session_id, 'assistant', answer, entities
                    )
                except SessionError:
                    # 如果会话保存失败，不影响主要功能
                    logger.warning(f"保存会话消息失败: {session_id}")
            
            return {
                "answer": answer,
                "entities": entities,
                "session_id": session_id
            }
        else:
            # 没有找到相关信息，使用通用回答
            no_result_answer = "抱歉，我没有找到与您的问题相关的政策法规信息。请尝试使用不同的关键词或更具体的问题描述。"
            
            if session_id:
                try:
                    conversation_manager.add_message_to_session(
                        session_id, 'user', question, []
                    )
                    conversation_manager.add_message_to_session(
                        session_id, 'assistant', no_result_answer, []
                    )
                except SessionError:
                    pass
            
            return {
                "answer": no_result_answer,
                "entities": [],
                "session_id": session_id
            }
            
    except DatabaseError:
        raise
    except LLMServiceError:
        raise
    except Exception as e:
        logger.error(f"生成答案时发生未知错误: {str(e)}")
        raise SystemError(f"系统内部错误: {str(e)}")

# API路由定义

@app.route('/api/ask', methods=['POST'])
def ask():
    """
    智能问答API端点
    
    请求格式:
    {
        "question": "用户问题",
        "session_id": "会话ID（可选）"
    }
    
    响应格式:
    {
        "answer": "回答内容",
        "entities": [实体列表],
        "session_id": "会话ID"
    }
    """
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify(handle_error(ValidationError("请求数据格式错误", "request_body"))), 400
        
        # 验证输入
        SecurityChecker.validate_api_request(data)
        
        question = data.get('question', '').strip()
        session_id = data.get('session_id')
        
        # 验证问题内容
        is_valid, error_msg, cleaned_question = InputValidator.validate_question(question)
        if not is_valid:
            return jsonify(handle_error(ValidationError(error_msg, "question", question))), 400
        
        # 验证会话ID（如果提供）
        if session_id:
            is_valid, error_msg = InputValidator.validate_session_id(session_id)
            if not is_valid:
                return jsonify(handle_error(ValidationError(error_msg, "session_id", session_id))), 400
        
        # 生成答案
        result = generate_policy_answer(cleaned_question, session_id)
        
        logger.info(f"问答请求成功: question='{cleaned_question[:50]}...', session_id={session_id}")
        return jsonify(result)
        
    except ValidationError as e:
        log_error(e, {"endpoint": "/api/ask", "question": question[:100] if 'question' in locals() else "N/A"})
        return jsonify(handle_error(e)), 400
    except (DatabaseError, LLMServiceError) as e:
        log_error(e, {"endpoint": "/api/ask", "question": question[:100] if 'question' in locals() else "N/A"})
        return jsonify(handle_error(e)), 503
    except Exception as e:
        log_error(e, {"endpoint": "/api/ask", "question": question[:100] if 'question' in locals() else "N/A"})
        return jsonify(handle_error(SystemError("系统内部错误"))), 500


@app.route('/api/session/create', methods=['POST'])
def create_session():
    """
    创建新会话
    
    响应格式:
    {
        "session_id": "新会话ID",
        "created_at": "创建时间"
    }
    """
    try:
        session_id = conversation_manager.create_session()
        
        logger.info(f"创建新会话: {session_id}")
        return jsonify({
            "session_id": session_id,
            "created_at": conversation_manager.get_session(session_id).created_at.isoformat()
        })
        
    except Exception as e:
        log_error(e, {"endpoint": "/api/session/create"})
        return jsonify(handle_error(SystemError("创建会话失败"))), 500


@app.route('/api/session/<session_id>/summary', methods=['GET'])
def get_session_summary(session_id: str):
    """
    获取会话摘要
    
    响应格式:
    {
        "session_id": "会话ID",
        "summary": {会话摘要信息}
    }
    """
    try:
        # 验证会话ID
        is_valid, error_msg = InputValidator.validate_session_id(session_id)
        if not is_valid:
            return jsonify(handle_error(ValidationError(error_msg, "session_id", session_id))), 400
        
        summary = conversation_manager.get_session_summary(session_id)
        if not summary:
            return jsonify(handle_error(SessionError("会话不存在或已过期", session_id))), 404
        
        return jsonify({
            "session_id": session_id,
            "summary": summary
        })
        
    except Exception as e:
        log_error(e, {"endpoint": "/api/session/summary", "session_id": session_id})
        return jsonify(handle_error(SystemError("获取会话摘要失败"))), 500


@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """
    列出活跃会话
    
    响应格式:
    {
        "sessions": [会话列表],
        "count": 会话数量
    }
    """
    try:
        limit = min(int(request.args.get('limit', 50)), 100)  # 最大100个
        sessions = conversation_manager.list_active_sessions(limit)
        
        return jsonify({
            "sessions": sessions,
            "count": len(sessions)
        })
        
    except Exception as e:
        log_error(e, {"endpoint": "/api/sessions"})
        return jsonify(handle_error(SystemError("获取会话列表失败"))), 500


# GraphRAG增强API接口

@app.route('/api/ask/enhanced', methods=['POST'])
def ask_enhanced():
    """
    GraphRAG增强问答API端点
    
    请求格式:
    {
        "question": "用户问题",
        "use_graph": true,
        "return_confidence": true,
        "session_id": "会话 ID（可选）"
    }
    
    响应格式:
    {
        "answer": "回答内容",
        "confidence": 0.85,
        "risk_level": "low",
        "is_reliable": true,
        "sources": [来源信息],
        "warnings": [警告信息],
        "processing_time": 2.3,
        "question_entities": [问题实体],
        "graph_enhanced": true
    }
    """
    try:
        # 检查GraphRAG可用性
        if not GRAPHRAG_AVAILABLE or not graphrag_engine:
            return jsonify({
                "error": "GraphRAG功能不可用",
                "message": "请使用 /api/ask 接口访问传统RAG功能",
                "available_endpoints": ["/api/ask"]
            }), 503
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify(handle_error(ValidationError("请求数据格式错误", "request_body"))), 400
        
        # 验证输入
        SecurityChecker.validate_api_request(data)
        
        question = data.get('question', '').strip()
        use_graph = data.get('use_graph', True)
        return_confidence = data.get('return_confidence', True)
        session_id = data.get('session_id')
        
        # 验证问题内容
        is_valid, error_msg, cleaned_question = InputValidator.validate_question(question)
        if not is_valid:
            return jsonify(handle_error(ValidationError(error_msg, "question", question))), 400
        
        # 验证会话 ID（如果提供）
        if session_id:
            is_valid, error_msg = InputValidator.validate_session_id(session_id)
            if not is_valid:
                return jsonify(handle_error(ValidationError(error_msg, "session_id", session_id))), 400
        
        # 使用GraphRAG引擎生成答案
        result = graphrag_engine.answer_question(
            cleaned_question, 
            use_graph=use_graph, 
            return_confidence=return_confidence
        )
        
        # 保存到会话历史
        if session_id:
            try:
                conversation_manager.add_message_to_session(
                    session_id, 'user', cleaned_question, result.get('question_entities', [])
                )
                conversation_manager.add_message_to_session(
                    session_id, 'assistant', result['answer'], result.get('question_entities', [])
                )
            except SessionError:
                logger.warning(f"保存GraphRAG会话消息失败: {session_id}")
        
        result['session_id'] = session_id
        
        logger.info(f"GraphRAG问答请求成功: question='{cleaned_question[:50]}...', confidence={result.get('confidence', 'N/A')}")
        return jsonify(result)
        
    except ValidationError as e:
        log_error(e, {"endpoint": "/api/ask/enhanced"})
        return jsonify(handle_error(e)), 400
    except Exception as e:
        log_error(e, {"endpoint": "/api/ask/enhanced"})
        return jsonify(handle_error(SystemError("系统内部错误"))), 500


@app.route('/api/ask/evaluated', methods=['POST'])
def ask_with_earag_evaluation():
    """
    带EARAG-Eval多维度评估的问答API端点
    
    请求格式:
    {
        "question": "用户问题",
        "use_graph": true,
        "session_id": "会话 ID（可选）"
    }
    
    响应格式:
    {
        "answer": "回答内容",
        "quality_score": 0.85,
        "quality_level": "优秀",
        "quality_warning": false,
        "evaluation_diagnosis": "综合评估结果",
        "earag_evaluation": {
            "overall_score": 0.85,
            "dimension_scores": {...},
            "entity_analysis": {...},
            "detailed_analysis": {...}
        },
        "traditional_confidence": {...},
        "sources": [来源信息],
        "processing_time": 2.3,
        "recommendations": [改进建议]
    }
    """
    try:
        # 检查GraphRAG和EARAG-Eval可用性
        if not GRAPHRAG_AVAILABLE or not graphrag_engine:
            return jsonify({
                "error": "GraphRAG功能不可用",
                "message": "请使用 /api/ask 接口访问传统RAG功能",
                "available_endpoints": ["/api/ask"]
            }), 503
        
        if not hasattr(graphrag_engine, 'earag_evaluator') or not graphrag_engine.earag_evaluator:
            return jsonify({
                "error": "EARAG-Eval评估器不可用",
                "message": "请使用 /api/ask/enhanced 接口访问增强问答功能",
                "available_endpoints": ["/api/ask", "/api/ask/enhanced"]
            }), 503
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify(handle_error(ValidationError("请求数据格式错误", "request_body"))), 400
        
        # 验证输入
        SecurityChecker.validate_api_request(data)
        
        question = data.get('question', '').strip()
        use_graph = data.get('use_graph', True)
        session_id = data.get('session_id')
        
        # 验证问题内容
        is_valid, error_msg, cleaned_question = InputValidator.validate_question(question)
        if not is_valid:
            return jsonify(handle_error(ValidationError(error_msg, "question", question))), 400
        
        # 验证会话 ID（如果提供）
        if session_id:
            is_valid, error_msg = InputValidator.validate_session_id(session_id)
            if not is_valid:
                return jsonify(handle_error(ValidationError(error_msg, "session_id", session_id))), 400
        
        # 使用EARAG-Eval评估问答
        result = graphrag_engine.answer_question_with_earag_eval(
            cleaned_question, 
            use_graph=use_graph
        )
        
        # 保存到会话历史
        if session_id:
            try:
                conversation_manager.add_message_to_session(
                    session_id, 'user', cleaned_question, result.get('question_entities', [])
                )
                conversation_manager.add_message_to_session(
                    session_id, 'assistant', result['answer'], result.get('question_entities', [])
                )
            except SessionError:
                logger.warning(f"保存EARAG-Eval会话消息失败: {session_id}")
        
        result['session_id'] = session_id
        
        # 记录评估结果
        quality_info = f"score={result.get('quality_score', 'N/A')}, level={result.get('quality_level', 'N/A')}"
        logger.info(f"EARAG-Eval评估问答请求成功: question='{cleaned_question[:50]}...', {quality_info}")
        
        return jsonify(result)
        
    except ValidationError as e:
        log_error(e, {"endpoint": "/api/ask/evaluated"})
        return jsonify(handle_error(e)), 400
    except Exception as e:
        log_error(e, {"endpoint": "/api/ask/evaluated"})
        return jsonify(handle_error(SystemError("EARAG-Eval评估失败"))), 500


@app.route('/api/graph/analyze', methods=['POST'])
def analyze_entities():
    """
    实体关系分析API端点
    
    请求格式:
    {
        "text": "政策文本内容",
        "extract_entities": true,
        "extract_relations": true
    }
    
    响应格式:
    {
        "entities": [实体列表],
        "relations": [关系列表],
        "graph_summary": "提取了X个实体，Y个关系"
    }
    """
    try:
        # 检查GraphRAG可用性
        if not GRAPHRAG_AVAILABLE or not graphrag_engine:
            return jsonify({
                "error": "GraphRAG功能不可用",
                "message": "实体分析功能需要GraphRAG支持"
            }), 503
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify(handle_error(ValidationError("请求数据格式错误", "request_body"))), 400
        
        text = data.get('text', '').strip()
        extract_entities = data.get('extract_entities', True)
        extract_relations = data.get('extract_relations', True)
        
        if not text:
            return jsonify(handle_error(ValidationError("文本内容不能为空", "text"))), 400
        
        if len(text) > 5000:  # 限制文本长度
            return jsonify(handle_error(ValidationError("文本内容过长，请限制在5000字符内", "text"))), 400
        
        result = {
            "entities": [],
            "relations": [],
            "graph_summary": ""
        }
        
        # 提取实体
        if extract_entities:
            entities = graphrag_engine.entity_extractor.extract_entities(text)
            result['entities'] = entities
        
        # 提取关系
        if extract_relations and result['entities']:
            relations = graphrag_engine.entity_extractor.extract_relations(text, result['entities'])
            result['relations'] = relations
        
        # 生成摘要
        entity_count = len(result['entities'])
        relation_count = len(result['relations'])
        result['graph_summary'] = f"提取了{entity_count}个实体，{relation_count}个关系"
        
        logger.info(f"实体分析完成: {entity_count}个实体, {relation_count}个关系")
        return jsonify(result)
        
    except ValidationError as e:
        log_error(e, {"endpoint": "/api/graph/analyze"})
        return jsonify(handle_error(e)), 400
    except Exception as e:
        log_error(e, {"endpoint": "/api/graph/analyze"})
        return jsonify(handle_error(SystemError("实体分析失败"))), 500


@app.route('/api/system/stats', methods=['GET'])
def get_system_stats():
    """
    获取系统统计信息（分级查询）
    
    查询参数:
    - level: basic (default), detailed, full
    
    响应格式:
    {
        "graphrag_available": true,
        "vector_db": {向量数据库统计},
        "graph_db": {图数据库统计},
        "system_status": "healthy"
    }
    """
    try:
        level = request.args.get('level', 'basic')
        
        # 基础状态信息
        stats = {
            "graphrag_available": GRAPHRAG_AVAILABLE and graphrag_engine is not None,
            "traditional_rag_available": connection_manager.neo4j is not None,
            "llm_service_available": connection_manager.ollama is not None,
            "timestamp": datetime.now().isoformat()
        }
        
        # 根据级别返回不同的信息
        if not stats["graphrag_available"]:
            # GraphRAG不可用时的降级响应
            stats.update({
                "system_status": "partial",
                "message": "GraphRAG功能不可用",
                "available_services": {
                    "traditional_rag": stats["traditional_rag_available"],
                    "llm_service": stats["llm_service_available"]
                }
            })
            return jsonify(stats)
        
        # GraphRAG可用时的分级响应
        if level == 'basic':
            # 基础级别：快速返回，不执行复杂查询
            try:
                basic_stats = graphrag_engine.get_basic_stats()
                stats.update(basic_stats)
                stats["query_level"] = "basic"
            except Exception as e:
                logger.error(f"GraphRAG基础统计失败: {e}")
                stats.update({
                    "system_status": "error", 
                    "error": "基础统计查询失败",
                    "suggestion": "请尝试使用 /api/system/stats/quick 端点"
                })
        
        elif level == 'detailed':
            # 详细级别：为防止服务崩溃，暂时禁用复杂统计查询
            try:
                # 使用基础统计代替详细统计
                basic_stats = graphrag_engine.get_basic_stats()
                stats.update(basic_stats)
                stats["query_level"] = "basic_safe"
                stats["note"] = "为保证服务稳定性，详细统计暂时停用"
            except Exception as e:
                logger.error(f"GraphRAG基础统计失败: {e}")
                stats.update({
                    "system_status": "error",
                    "error": "系统统计查询失败",
                    "suggestion": "请尝试使用 /api/system/stats/quick 端点"
                })
        
        else:  # level == 'full' 或其他
            # 完整级别：为防止服务崩溃，暂时禁用复杂统计查询
            try:
                # 使用基础统计代替完整统计
                basic_stats = graphrag_engine.get_basic_stats()
                stats.update(basic_stats)
                stats["query_level"] = "basic_safe"
                stats["note"] = "为保证服务稳定性，完整统计暂时停用"
            except Exception as e:
                logger.error(f"GraphRAG完整统计失败: {e}")
                stats.update({
                    "system_status": "error",
                    "error": "所有统计方法都失败",
                    "fallback_error": str(e)
                })
        
        return jsonify(stats)
        
    except Exception as e:
        log_error(e, {"endpoint": "/api/system/stats"})
        # 返回基本的系统信息，即使部分功能不可用
        fallback_stats = {
            "graphrag_available": False,
            "traditional_rag_available": connection_manager.neo4j is not None if connection_manager else False,
            "llm_service_available": connection_manager.ollama is not None if connection_manager else False,
            "system_status": "error",
            "error": "系统统计服务暂时不可用",
            "fallback_mode": True,
            "timestamp": datetime.now().isoformat()
        }
        return jsonify(fallback_stats), 200  # 使用20x状态码而不是500，避免前端错误


@app.route('/api/system/stats/quick', methods=['GET'])
def get_quick_system_status():
    """
    快速系统状态检查（1秒内返回）
    
    响应格式:
    {
        "status": "healthy",
        "timestamp": "2025-01-20T...",
        "basic_connectivity": {
            "neo4j": true,
            "ollama": true,
            "graphrag": true
        }
    }
    """
    try:
        stats = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "basic_connectivity": {
                "neo4j": connection_manager.neo4j is not None if connection_manager else False,
                "ollama": connection_manager.ollama is not None if connection_manager else False,
                "graphrag": GRAPHRAG_AVAILABLE and graphrag_engine is not None
            },
            "response_type": "quick_check"
        }
        
        # 检查整体状态
        connected_services = sum(stats["basic_connectivity"].values())
        total_services = len(stats["basic_connectivity"])
        
        if connected_services == total_services:
            stats["status"] = "healthy"
        elif connected_services > 0:
            stats["status"] = "degraded"
        else:
            stats["status"] = "error"
        
        stats["connectivity_ratio"] = f"{connected_services}/{total_services}"
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"快速状态检查失败: {e}")
        return jsonify({
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": "快速状态检查失败",
            "response_type": "quick_check_error"
        }), 200  # 仍然返回200，避免前端报错


@app.route('/api/compare', methods=['POST'])
def compare_rag_methods():
    """
    对比传统RAG和GraphRAG的回答
    
    请求格式:
    {
        "question": "用户问题"
    }
    
    响应格式:
    {
        "question": "问题",
        "traditional_rag": {传统RAG结果},
        "graph_rag": {GraphRAG结果},
        "comparison": {对比分析}
    }
    """
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify(handle_error(ValidationError("请求数据格式错误", "request_body"))), 400
        
        question = data.get('question', '').strip()
        
        # 验证问题内容
        is_valid, error_msg, cleaned_question = InputValidator.validate_question(question)
        if not is_valid:
            return jsonify(handle_error(ValidationError(error_msg, "question", question))), 400
        
        result = {
            "question": cleaned_question,
            "traditional_rag": None,
            "graph_rag": None,
            "comparison": {}
        }
        
        # 获取传统RAG结果
        try:
            traditional_result = generate_policy_answer(cleaned_question)
            result["traditional_rag"] = {
                "answer": traditional_result["answer"],
                "entities": traditional_result["entities"],
                "method": "Traditional RAG"
            }
        except Exception as e:
            result["traditional_rag"] = {
                "error": f"传统RAG失败: {str(e)}",
                "method": "Traditional RAG"
            }
        
        # 获取GraphRAG结果
        if GRAPHRAG_AVAILABLE and graphrag_engine:
            try:
                graphrag_result = graphrag_engine.answer_question(
                    cleaned_question, 
                    use_graph=True, 
                    return_confidence=True
                )
                result["graph_rag"] = {
                    "answer": graphrag_result["answer"],
                    "confidence": graphrag_result.get("confidence", 0),
                    "risk_level": graphrag_result.get("risk_level", "unknown"),
                    "warnings": graphrag_result.get("warnings", []),
                    "method": "GraphRAG"
                }
            except Exception as e:
                result["graph_rag"] = {
                    "error": f"GraphRAG失败: {str(e)}",
                    "method": "GraphRAG"
                }
        else:
            result["graph_rag"] = {
                "error": "GraphRAG不可用",
                "method": "GraphRAG"
            }
        
        # 生成对比分析
        comparison = {
            "traditional_available": result["traditional_rag"] and "error" not in result["traditional_rag"],
            "graphrag_available": result["graph_rag"] and "error" not in result["graph_rag"],
            "confidence_provided": result["graph_rag"] and "confidence" in result["graph_rag"]
        }
        
        if comparison["graphrag_available"] and comparison["traditional_available"]:
            comparison["both_methods_working"] = True
            if "confidence" in result["graph_rag"]:
                comparison["graphrag_confidence"] = result["graph_rag"]["confidence"]
        
        result["comparison"] = comparison
        
        logger.info(f"对比分析完成: question='{cleaned_question[:50]}...'")
        return jsonify(result)
        
    except ValidationError as e:
        log_error(e, {"endpoint": "/api/compare"})
        return jsonify(handle_error(e)), 400
    except Exception as e:
        log_error(e, {"endpoint": "/api/compare"})
        return jsonify(handle_error(SystemError("对比分析失败"))), 500


# 健康检查端点
health_endpoints = create_health_endpoints()

# 监控指标端点
metrics_endpoints = create_metrics_endpoints()

@app.route('/ping', methods=['GET'])
def ping():
    """简单的连接测试端点"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "message": "服务正在运行"
    })

@app.route('/health', methods=['GET'])
def health():
    """基础健康检查"""
    return health_endpoints['health']()

@app.route('/health/deep', methods=['GET'])
def health_deep():
    """深度健康检查"""
    return health_endpoints['health_deep']()

@app.route('/health/graphrag', methods=['GET'])
def health_graphrag():
    """GraphRAG专项诊断"""
    return health_endpoints['health_graphrag']()

@app.route('/health/comprehensive', methods=['GET'])
def health_comprehensive():
    """综合健康报告"""
    return health_endpoints['health_comprehensive']()

@app.route('/health/graphrag/quick', methods=['GET'])
def health_quick_graphrag():
    """快速GraphRAG状态检查"""
    return health_endpoints['health_quick_graphrag']()

@app.route('/health/diagnosis/history', methods=['GET'])
def health_diagnosis_history():
    """GraphRAG诊断历史"""
    return health_endpoints['health_diagnosis_history']()

@app.route('/health/history', methods=['GET'])
def health_history():
    """健康检查历史"""
    return health_endpoints['health_history']()

@app.route('/api/uptime', methods=['GET'])
def uptime():
    """系统运行时间"""
    return health_endpoints['uptime']()


# 监控指标端点
@app.route('/metrics/system', methods=['GET'])
def metrics_system():
    """系统指标"""
    return metrics_endpoints['metrics_system']()

@app.route('/metrics/api', methods=['GET'])
def metrics_api():
    """API指标"""
    return metrics_endpoints['metrics_api']()

@app.route('/metrics/business', methods=['GET'])
def metrics_business():
    """业务指标"""
    return metrics_endpoints['metrics_business']()

@app.route('/metrics/summary', methods=['GET'])
def metrics_summary():
    """指标摘要"""
    return metrics_endpoints['metrics_summary']()

@app.route('/metrics/comprehensive', methods=['GET'])
def metrics_comprehensive():
    """综合指标报告"""
    return metrics_endpoints['metrics_comprehensive']()


@app.route('/api/status', methods=['GET'])
def system_status():
    """
    系统状态综合信息
    
    响应格式:
    {
        "system": {系统健康状态},
        "connections": {连接状态},
        "sessions": {会话统计}
    }
    """
    try:
        health_data = health_checker.get_system_health()
        connection_status = connection_manager.get_status()
        session_stats = conversation_manager.get_statistics()
        
        return jsonify({
            "system": health_data,
            "connections": connection_status,
            "sessions": session_stats
        })
        
    except Exception as e:
        log_error(e, {"endpoint": "/api/status"})
        return jsonify(handle_error(SystemError("获取系统状态失败"))), 500


# 错误处理器
@app.errorhandler(404)
def not_found(error):
    return jsonify(handle_error(SystemError("API端点不存在", "NOT_FOUND"))), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify(handle_error(SystemError("HTTP方法不允许", "METHOD_NOT_ALLOWED"))), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify(handle_error(SystemError("服务器内部错误", "INTERNAL_ERROR"))), 500

# 应用关闭时的清理工作
@app.teardown_appcontext
def cleanup(error):
    """应用上下文销毁时的清理工作"""
    pass

def shutdown_handler():
    """应用关闭处理"""
    logger.info("应用正在关闭...")
    try:
        connection_manager.close_all()
        logger.info("连接已关闭")
    except Exception as e:
        logger.error(f"关闭连接时出错: {str(e)}")

import atexit
atexit.register(shutdown_handler)

if __name__ == '__main__':
    try:
        logger.info("政策法规RAG问答系统启动中...")
        logger.info(f"健康检查端点: http://127.0.0.1:5000/health")
        logger.info(f"传统RAG API: http://127.0.0.1:5000/api/ask")
        
        if GRAPHRAG_AVAILABLE and graphrag_engine:
            logger.info(f"GraphRAG API: http://127.0.0.1:5000/api/ask/enhanced")
            logger.info(f"实体分析API: http://127.0.0.1:5000/api/graph/analyze")
            logger.info(f"对比分析API: http://127.0.0.1:5000/api/compare")
            logger.info("GraphRAG功能已启用")
        else:
            logger.warning("GraphRAG功能不可用，仅支持传统RAG")
        
        logger.info(f"系统统计端点: http://127.0.0.1:5000/api/system/stats")
        logger.info(f"系统状态端点: http://127.0.0.1:5000/api/status")
        
        # 如果是直接运行，显示路径警告
        import os
        if not os.path.basename(os.getcwd()) == 'backend':
            logger.warning("建议使用项目根目录的 start_server.py 启动脚本")
        
        app.run(debug=True, host='127.0.0.1', port=5000, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭应用...")
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise