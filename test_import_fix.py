#!/usr/bin/env python3
"""
快速验证模块导入修复是否成功
"""

import sys
import os
from pathlib import Path

# 设置项目路径
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_backend_imports():
    """测试backend模块导入"""
    print("=== 测试Backend模块导入修复 ===")
    
    try:
        # 测试异常模块
        from backend.exceptions import ValidationError, DatabaseError
        print("✓ exceptions模块导入成功")
        
        # 测试验证模块
        from backend.validators import InputValidator
        print("✓ validators模块导入成功")
        
        # 测试连接管理模块
        from backend.connections import get_connection_manager
        print("✓ connections模块导入成功")
        
        # 测试会话管理模块
        from backend.session_manager import get_conversation_manager
        print("✓ session_manager模块导入成功")
        
        # 测试健康检查模块
        from backend.health_checker import get_health_checker
        print("✓ health_checker模块导入成功")
        
        # 测试API服务器模块
        from backend.api_server import app
        print("✓ api_server模块导入成功")
        
        # 测试GraphRAG引擎
        from backend.graphrag_engine import GraphRAGEngine
        print("✓ graphrag_engine模块导入成功")
        
        print("\n🎉 所有核心模块导入成功！模块导入问题已修复！")
        return True
        
    except ImportError as e:
        print(f"✗ 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 其他错误: {e}")
        return False

def test_original_issue():
    """测试原问题脚本"""
    print("\n=== 测试原问题脚本修复 ===")
    
    try:
        # 测试原问题脚本中的导入
        from backend.vector_retrieval import VectorRetriever
        from backend.graph_query import GraphQueryEngine
        from backend.entity_extractor import EntityExtractor
        
        print("✓ 原问题脚本中的模块导入成功")
        print("✓ scripts/import_graphrag_data.py应该能正常运行")
        return True
        
    except ImportError as e:
        print(f"✗ 原问题脚本导入失败: {e}")
        return False

def main():
    """主函数"""
    print("Python模块导入修复验证")
    print("=" * 40)
    
    success1 = test_backend_imports()
    success2 = test_original_issue()
    
    print("\n" + "=" * 40)
    if success1 and success2:
        print("✅ 验证成功：Python模块导入问题已完全修复！")
        print("\n您现在可以正常使用以下命令：")
        print("- python start_server.py api                    # 启动API服务")
        print("- python start_server.py script import_graphrag_data.py  # 运行数据导入")
        print("- python scripts/import_graphrag_data.py        # 直接运行原问题脚本")
        return 0
    else:
        print("❌ 验证失败：仍存在模块导入问题")
        return 1

if __name__ == "__main__":
    sys.exit(main())