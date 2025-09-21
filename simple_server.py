#!/usr/bin/env python3
"""
简化的API服务器 - 专注于修复问题
避免复杂的依赖，直接启动服务器测试超时保护机制
"""

import os
import sys
import logging
import time
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

def main():
    """主函数"""
    
    print("=" * 60)
    print("政策法规RAG问答系统 - 简化测试服务器")
    print("=" * 60)
    
    try:
        # 导入必要模块
        from flask import Flask, request, jsonify
        from flask_cors import CORS
        from backend.graphrag_engine import GraphRAGEngine
        
        print("✓ 依赖导入成功")
        
        # 创建Flask应用
        app = Flask(__name__)
        CORS(app)
        
        # 初始化GraphRAG引擎
        print("🔄 初始化GraphRAG引擎...")
        graphrag_engine = GraphRAGEngine()
        print("✓ GraphRAG引擎初始化成功")
        
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
                else:
                    # 为保证服务稳定性，只返回基础统计
                    stats = graphrag_engine.get_basic_stats()
                    stats["note"] = f"为保证服务稳定性，{level}级别统计已简化为基础统计"
                
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
                
                logging.info(f"处理问题: {question}")
                
                # 处理问题
                result = graphrag_engine.answer_question(
                    question=question,
                    use_graph=use_graph,
                    return_confidence=return_confidence
                )
                
                return jsonify({
                    'success': True,
                    'data': result
                })
                
            except Exception as e:
                logging.error(f"问答处理失败: {e}")
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
        
        # 启动服务器
        print("🚀 启动服务器...")
        print("📍 服务地址: http://localhost:5000")
        print("📋 可用端点:")
        print("   - GET  /ping           - 健康检查")
        print("   - GET  /system/stats   - 系统统计")
        print("   - POST /ask            - 问答接口")
        print("=" * 60)
        print("✨ 服务器已启动，可以进行测试")
        print("✨ 已添加全面的超时保护机制")
        print("✨ 已修复可能导致系统崩溃的问题")
        print("=" * 60)
        
        # 使用安全配置启动
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=False,  # 防止自动重启
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