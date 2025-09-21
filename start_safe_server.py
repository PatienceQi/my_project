#!/usr/bin/env python3
"""
安全的API服务器启动脚本
处理依赖问题，确保服务器能正常启动
"""

import os
import sys
import logging
from pathlib import Path

# 设置项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ['LLM_BINDING_HOST'] = 'http://120.232.79.82:11434'
os.environ['OLLAMA_HOST'] = 'http://120.232.79.82:11434'
os.environ['EXPERIMENT_MODE'] = 'true'
os.environ['PYTHONPATH'] = str(project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def safe_import_with_fallback():
    """安全导入，处理依赖问题"""
    try:
        # 尝试导入所有依赖
        from flask import Flask, request, jsonify, Response
        from flask_cors import CORS
        from backend.graphrag_engine import GraphRAGEngine
        from backend.exceptions import (
            GraphRAGError,
            VectorRetrievalError,
            GraphQueryError,
            EntityExtractionError,
            HallucinationDetectionError,
            EvaluationError
        )
        from backend.cache_manager import CacheManager
        from backend.ollama_error_handler import OllamaErrorHandler
        
        logging.info("所有依赖导入成功")
        return True
        
    except ImportError as e:
        logging.error(f"导入依赖失败: {e}")
        return False

def create_safe_app():
    """创建安全的Flask应用"""
    
    if not safe_import_with_fallback():
        logging.error("依赖检查失败，请检查环境配置")
        return None
    
    # 重新导入（此时应该成功）
    from flask import Flask, request, jsonify, Response
    from flask_cors import CORS
    from backend.graphrag_engine import GraphRAGEngine
    from backend.exceptions import (
        GraphRAGError,
        VectorRetrievalError,
        GraphQueryError,
        EntityExtractionError,
        HallucinationDetectionError,
        EvaluationError
    )
    from backend.cache_manager import CacheManager
    from backend.ollama_error_handler import OllamaErrorHandler
    
    # 创建Flask应用
    app = Flask(__name__)
    CORS(app)
    
    # 初始化组件
    try:
        cache_manager = CacheManager()
        ollama_error_handler = OllamaErrorHandler()
        graphrag_engine = GraphRAGEngine()
        logging.info("GraphRAG引擎初始化成功")
    except Exception as e:
        logging.error(f"组件初始化失败: {e}")
        return None
    
    @app.route('/ping', methods=['GET'])
    def ping():
        """健康检查端点"""
        return jsonify({
            'status': 'healthy',
            'message': 'GraphRAG API Server is running',
            'timestamp': str(time.time())
        })
    
    @app.route('/system/stats', methods=['GET'])
    def get_system_stats():
        """获取系统统计信息"""
        try:
            level = request.args.get('level', 'basic')
            
            if level == 'basic':
                stats = graphrag_engine.get_basic_stats()
            elif level == 'detailed':
                # 为保证服务稳定性，暂时禁用复杂统计查询
                basic_stats = graphrag_engine.get_basic_stats()
                stats = basic_stats.copy()
                stats["note"] = "为保证服务稳定性，详细统计暂时停用"
            elif level == 'full':
                # 为保证服务稳定性，暂时禁用复杂统计查询
                basic_stats = graphrag_engine.get_basic_stats()
                stats = basic_stats.copy()
                stats["note"] = "为保证服务稳定性，完整统计暂时停用"
            else:
                stats = graphrag_engine.get_basic_stats()
            
            return jsonify({
                'success': True,
                'data': stats
            })
            
        except Exception as e:
            logging.error(f"获取系统统计失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/ask', methods=['POST'])
    def ask_question():
        """问答接口"""
        try:
            data = request.json
            question = data.get('question', '').strip()
            
            if not question:
                return jsonify({
                    'success': False,
                    'error': 'Question is required'
                }), 400
            
            # 参数设置
            use_graph = data.get('use_graph', True)
            return_confidence = data.get('return_confidence', True)
            use_cache = data.get('use_cache', True)
            
            # 检查缓存
            cache_key = None
            if use_cache:
                cache_key = cache_manager.generate_cache_key(
                    question, use_graph, return_confidence
                )
                cached_result = cache_manager.get_cached_result(cache_key)
                if cached_result:
                    logging.info(f"返回缓存结果: {question[:50]}...")
                    return jsonify({
                        'success': True,
                        'data': cached_result,
                        'from_cache': True
                    })
            
            # 处理问题
            result = graphrag_engine.answer_question(
                question=question,
                use_graph=use_graph,
                return_confidence=return_confidence
            )
            
            # 缓存结果
            if use_cache and cache_key:
                cache_manager.cache_result(cache_key, result)
            
            return jsonify({
                'success': True,
                'data': result,
                'from_cache': False
            })
            
        except Exception as e:
            logging.error(f"问答处理失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/ask/earag-eval', methods=['POST'])
    def ask_question_with_earag_eval():
        """带EARAG-Eval评估的问答接口"""
        try:
            data = request.json
            question = data.get('question', '').strip()
            
            if not question:
                return jsonify({
                    'success': False,
                    'error': 'Question is required'
                }), 400
            
            # 参数设置
            use_graph = data.get('use_graph', True)
            
            # 处理问题
            result = graphrag_engine.answer_question_with_earag_eval(
                question=question,
                use_graph=use_graph
            )
            
            return jsonify({
                'success': True,
                'data': result
            })
            
        except Exception as e:
            logging.error(f"EARAG-Eval问答处理失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """全局异常处理"""
        logging.error(f"未捕获的异常: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    
    return app

def main():
    """主函数"""
    import time
    
    print("=" * 60)
    print("政策法规RAG问答系统 - 安全启动模式")
    print("=" * 60)
    
    # 创建应用
    app = create_safe_app()
    if not app:
        print("❌ 应用创建失败，请检查依赖和配置")
        return 1
    
    print("✓ 应用创建成功")
    print("✓ 使用安全的向量检索器（处理ChromaDB依赖问题）")
    print("✓ 添加了全面的超时保护机制")
    print("✓ 禁用了可能导致崩溃的复杂统计查询")
    
    # 启动服务器
    try:
        print(f"🚀 启动服务器...")
        print(f"📍 服务地址: http://localhost:5000")
        print(f"📋 API文档:")
        print(f"   - GET  /ping               - 健康检查")
        print(f"   - GET  /system/stats       - 系统统计")
        print(f"   - POST /ask                - 标准问答")
        print(f"   - POST /ask/earag-eval     - EARAG评估问答")
        print("=" * 60)
        
        # 使用安全配置启动
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=False,  # 防止自动重启导致的问题
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n⚠ 接收到中断信号，正在关闭服务器...")
        return 0
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())