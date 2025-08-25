#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政策法规RAG问答系统 - 统一启动脚本

推荐的启动方式，遵循Python最佳实践
"""

import os
import sys

def setup_python_path():
    """配置Python路径，但不改变工作目录"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(project_root, 'backend')
    
    # 确保路径在sys.path最前面
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    return project_root, backend_dir

def main():
    """主启动函数"""
    try:
        project_root, backend_dir = setup_python_path()
        
        # 导入后端应用
        from backend.api_server import app
        
        print("="*60)
        print("政策法规RAG问答系统")
        print("="*60)
        print(f"项目根目录: {project_root}")
        print(f"Backend目录: {backend_dir}")
        print(f"当前工作目录: {os.getcwd()}")
        print(f"启动脚本位置: {__file__}")
        print("="*60)
        print("服务端点:")
        print("  - 主页面: http://127.0.0.1:5000")
        print("  - 健康检查: http://127.0.0.1:5000/health")
        print("  - 问答API: http://127.0.0.1:5000/api/ask")
        print("  - 系统状态: http://127.0.0.1:5000/api/status")
        print("  - Ping测试: http://127.0.0.1:5000/ping")
        print("="*60)
        print("前端文件:")
        print(f"  - 主页面: {os.path.join(project_root, 'frontend', 'index.html')}")
        print(f"  - 诊断页面: {os.path.join(project_root, 'frontend', 'diagnostic.html')}")
        print("="*60)
        print("提示: 使用 Ctrl+C 停止服务")
        print("="*60)
        
        # 启动Flask应用
        app.run(
            debug=True, 
            host='127.0.0.1', 
            port=5000, 
            threaded=True,
            use_reloader=False  # 避免重启时的路径问题
        )
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保所有依赖已安装：pip install -r requirements.txt")
        print("当前Python路径:")
        for path in sys.path:
            print(f"  - {path}")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()