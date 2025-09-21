#!/usr/bin/env python3
"""
政策法规RAG问答系统 - 统一启动脚本
支持API服务、数据导入、系统测试等多种模式
解决模块导入问题，遵循项目启动规范
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def setup_python_path():
    """设置Python模块路径"""
    project_root = Path(__file__).parent.absolute()
    
    # 将项目根目录添加到PYTHONPATH
    current_path = os.environ.get('PYTHONPATH', '')
    if str(project_root) not in current_path:
        if current_path:
            os.environ['PYTHONPATH'] = f"{project_root}{os.pathsep}{current_path}"
        else:
            os.environ['PYTHONPATH'] = str(project_root)
    
    # 同时添加到sys.path以确保当前进程也能导入
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    print(f"✓ Python模块路径已配置: {project_root}")

def start_api_server():
    """启动API服务器"""
    setup_python_path()
    
    print("正在启动政策法规RAG问答系统API服务...")
    
    try:
        # 导入backend模块测试
        from backend.api_server import app
        print("✓ Backend模块导入成功")
        
        # 启动Flask服务
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
        
    except ImportError as e:
        print(f"✗ Backend模块导入失败: {e}")
        print("请检查backend目录是否存在且包含__init__.py文件")
        sys.exit(1)
    except Exception as e:
        print(f"✗ API服务启动失败: {e}")
        sys.exit(1)

def run_data_import(rebuild_vector=False, rebuild_graph=False):
    """执行GraphRAG数据导入"""
    setup_python_path()
    
    print("正在执行GraphRAG数据导入...")
    
    try:
        # 导入数据导入脚本并执行
        script_path = Path(__file__).parent / 'scripts' / 'import_graphrag_data.py'
        
        cmd = [sys.executable, str(script_path)]
        if rebuild_vector:
            cmd.append('--rebuild-vector')
        if rebuild_graph:
            cmd.append('--rebuild-graph')
            
        result = subprocess.run(cmd, env=os.environ)
        
        if result.returncode == 0:
            print("✓ 数据导入完成")
        else:
            print("✗ 数据导入失败")
            sys.exit(1)
        
    except Exception as e:
        print(f"✗ 数据导入执行失败: {e}")
        sys.exit(1)

def test_import():
    """测试模块导入"""
    setup_python_path()
    
    print("=== Backend模块导入测试 ===")
    
    modules_to_test = [
        ('backend', 'Backend主模块'),
        ('backend.vector_retrieval', 'VectorRetriever'),
        ('backend.graph_query', 'GraphQueryEngine'),
        ('backend.entity_extractor', 'EntityExtractor'),
        ('backend.hallucination_detector', 'HallucinationDetector'),
        ('backend.graphrag_engine', 'GraphRAGEngine')
    ]
    
    success_count = 0
    total_count = len(modules_to_test)
    
    for module_name, display_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✓ {display_name}导入成功")
            success_count += 1
        except ImportError as e:
            print(f"✗ {display_name}导入失败: {e}")
        except Exception as e:
            print(f"✗ {display_name}导入时出现其他错误: {e}")
    
    print(f"\n测试结果: {success_count}/{total_count} 模块导入成功")
    
    return success_count == total_count

def run_script(script_name, *args):
    """运行指定脚本"""
    setup_python_path()
    
    script_path = Path(__file__).parent / 'scripts' / script_name
    if not script_path.exists():
        print(f"✗ 脚本 {script_name} 不存在")
        return 1
    
    print(f"正在运行脚本: {script_name}")
    
    cmd = [sys.executable, str(script_path)] + list(args)
    
    try:
        result = subprocess.run(cmd, env=os.environ)
        return result.returncode
    except Exception as e:
        print(f"✗ 执行脚本时出错: {e}")
        return 1

def run_graphrag_test():
    """运行GraphRAG系统测试"""
    setup_python_path()
    
    print("正在运行GraphRAG系统测试...")
    
    try:
        script_path = Path(__file__).parent / 'test_graphrag_basic.py'
        if not script_path.exists():
            print("✗ GraphRAG测试脚本不存在")
            return 1
            
        result = subprocess.run([sys.executable, str(script_path)], env=os.environ)
        return result.returncode
        
    except Exception as e:
        print(f"✗ 执行GraphRAG测试时出错: {e}")
        return 1

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='政策法规RAG问答系统 - 统一启动脚本',
        epilog="""
使用示例:
  python start_server.py api                    # 启动API服务
  python start_server.py import                 # 导入数据
  python start_server.py import --rebuild-all   # 重建所有数据
  python start_server.py test-import            # 测试模块导入
  python start_server.py test-graphrag          # 运行GraphRAG系统测试
  python start_server.py script import_graphrag_data.py  # 运行指定脚本
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # API服务命令
    subparsers.add_parser('api', help='启动API服务器')
    
    # 数据导入命令
    import_parser = subparsers.add_parser('import', help='导入GraphRAG数据')
    import_parser.add_argument('--rebuild-vector', action='store_true', help='重建向量数据库')
    import_parser.add_argument('--rebuild-graph', action='store_true', help='重建知识图谱')
    import_parser.add_argument('--rebuild-all', action='store_true', help='重建所有数据')
    
    # 测试命令
    subparsers.add_parser('test-import', help='测试模块导入')
    subparsers.add_parser('test-graphrag', help='运行GraphRAG系统测试')
    
    # 脚本执行命令
    script_parser = subparsers.add_parser('script', help='运行指定脚本')
    script_parser.add_argument('script_name', help='脚本文件名')
    script_parser.add_argument('args', nargs='*', help='脚本参数')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'api':
        start_api_server()
    elif args.command == 'import':
        rebuild_vector = args.rebuild_vector or args.rebuild_all
        rebuild_graph = args.rebuild_graph or args.rebuild_all
        run_data_import(rebuild_vector, rebuild_graph)
    elif args.command == 'test-import':
        success = test_import()
        sys.exit(0 if success else 1)
    elif args.command == 'test-graphrag':
        exit_code = run_graphrag_test()
        sys.exit(exit_code)
    elif args.command == 'script':
        exit_code = run_script(args.script_name, *args.args)
        sys.exit(exit_code)

if __name__ == "__main__":
    main()