"""
模块导入测试脚本 - 验证backend模块是否可以正常导入
用于诊断和验证Python模块导入问题的修复效果
"""

import sys
import os
from pathlib import Path

def setup_project_path():
    """配置项目模块路径"""
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    print(f"项目根目录已添加到Python路径: {project_root}")

def test_basic_import():
    """测试基础模块导入"""
    print("=== 基础模块导入测试 ===")
    
    try:
        import backend
        print("✓ backend模块导入成功")
        print(f"  模块路径: {backend.__file__}")
        print(f"  模块版本: {getattr(backend, '__version__', '未知')}")
        return True
    except ImportError as e:
        print(f"✗ backend模块导入失败: {e}")
        return False

def test_component_imports():
    """测试组件模块导入"""
    print("\n=== 组件模块导入测试 ===")
    
    components = [
        ('backend.vector_retrieval', 'VectorRetriever', '向量检索模块'),
        ('backend.graph_query', 'GraphQueryEngine', '图查询引擎'),
        ('backend.entity_extractor', 'EntityExtractor', '实体提取器'),
        ('backend.hallucination_detector', 'HallucinationDetector', '幻觉检测器'),
        ('backend.graphrag_engine', 'GraphRAGEngine', 'GraphRAG引擎'),
        ('backend.api_server', 'app', 'API服务器'),
        ('backend.connections', 'ConnectionManager', '连接管理器'),
        ('backend.session_manager', 'SessionManager', '会话管理器')
    ]
    
    success_count = 0
    total_count = len(components)
    
    for module_name, class_name, description in components:
        try:
            module = __import__(module_name, fromlist=[class_name])
            
            # 检查类是否存在
            if hasattr(module, class_name):
                print(f"✓ {description}导入成功 ({module_name}.{class_name})")
                success_count += 1
            else:
                print(f"⚠ {description}模块导入成功，但缺少{class_name}类")
                success_count += 0.5
                
        except ImportError as e:
            print(f"✗ {description}导入失败: {e}")
        except Exception as e:
            print(f"✗ {description}导入时出现其他错误: {e}")
    
    print(f"\n组件导入结果: {success_count}/{total_count} 成功")
    return success_count >= total_count * 0.8  # 80%成功率认为通过

def test_import_paths():
    """测试Python路径配置"""
    print("\n=== Python路径配置测试 ===")
    
    project_root = Path(__file__).parent.parent
    
    print(f"当前工作目录: {os.getcwd()}")
    print(f"项目根目录: {project_root}")
    print(f"Python版本: {sys.version}")
    
    print("\nPython模块搜索路径:")
    for i, path in enumerate(sys.path[:10]):  # 只显示前10个路径
        marker = "★" if str(project_root) in path else " "
        print(f"  {marker} {i+1}. {path}")
    
    # 检查项目根目录是否在路径中
    if str(project_root) in sys.path:
        print("✓ 项目根目录已正确添加到Python路径")
        return True
    else:
        print("✗ 项目根目录未在Python路径中")
        return False

def test_environment_variables():
    """测试环境变量配置"""
    print("\n=== 环境变量配置测试 ===")
    
    pythonpath = os.environ.get('PYTHONPATH', '')
    project_root = str(Path(__file__).parent.parent)
    
    print(f"PYTHONPATH环境变量: {pythonpath}")
    
    if project_root in pythonpath:
        print("✓ 项目根目录已在PYTHONPATH中")
        return True
    elif not pythonpath:
        print("⚠ PYTHONPATH环境变量未设置")
        return False
    else:
        print("✗ 项目根目录未在PYTHONPATH中")
        return False

def run_diagnostic():
    """运行完整诊断"""
    print("=" * 60)
    print("政策法规RAG问答系统 - 模块导入诊断工具")
    print("=" * 60)
    
    # 设置项目路径
    setup_project_path()
    
    # 运行各项测试
    tests = [
        ("Python路径配置", test_import_paths),
        ("环境变量配置", test_environment_variables),
        ("基础模块导入", test_basic_import),
        ("组件模块导入", test_component_imports)
    ]
    
    results = []
    for test_name, test_func in tests:
        print()
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name}测试失败: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    success_rate = passed / len(results) * 100
    print(f"\n总体通过率: {passed}/{len(results)} ({success_rate:.1f}%)")
    
    if success_rate >= 75:
        print("🎉 模块导入问题已基本解决！")
        return True
    elif success_rate >= 50:
        print("⚠️ 部分问题已解决，但仍需进一步修复")
        return False
    else:
        print("❌ 模块导入问题依然严重，需要检查配置")
        return False

def main():
    """主函数"""
    try:
        success = run_diagnostic()
        
        if not success:
            print("\n建议解决方案:")
            print("1. 使用统一启动脚本: python start_server.py test-import")
            print("2. 手动设置环境变量: set PYTHONPATH=%CD%;%PYTHONPATH%")
            print("3. 检查backend目录结构和__init__.py文件")
            print("4. 确认在项目根目录运行脚本")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试过程中出现未预期错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()