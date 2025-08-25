"""
GraphRAG系统综合测试脚本
验证完整系统功能，包括各个模块的集成测试
"""

import os
import sys
import logging
import time
import json
from pathlib import Path
from typing import Dict, List, Any

# 添加backend目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

class GraphRAGSystemTester:
    """GraphRAG系统测试器"""
    
    def __init__(self):
        self.test_results = []
        self.setup_logging()
        
        print("GraphRAG系统综合测试")
        print("=" * 50)
    
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('test_graphrag.log'),
                logging.StreamHandler()
            ]
        )
    
    def test_environment_setup(self) -> Dict[str, Any]:
        """测试环境设置"""
        print("\n1. 测试环境设置...")
        result = {
            "test_name": "环境设置",
            "passed": True,
            "details": {},
            "errors": []
        }
        
        try:
            # 检查配置文件
            env_file = Path(".env")
            if env_file.exists():
                result["details"]["env_file"] = "✓ .env文件存在"
            else:
                result["details"]["env_file"] = "✗ .env文件不存在"
                result["passed"] = False
            
            # 检查数据目录
            data_dir = Path("data")
            if data_dir.exists():
                result["details"]["data_dir"] = "✓ 数据目录存在"
            else:
                result["details"]["data_dir"] = "✗ 数据目录不存在"
                result["passed"] = False
            
            # 检查Python依赖
            required_packages = ['neo4j', 'flask', 'requests', 'python-dotenv']
            for package in required_packages:
                try:
                    __import__(package.replace('-', '_'))
                    result["details"][f"package_{package}"] = f"✓ {package}已安装"
                except ImportError:
                    result["details"][f"package_{package}"] = f"✗ {package}未安装"
                    result["passed"] = False
            
            # 可选依赖检查
            optional_packages = ['chromadb', 'sentence_transformers', 'jieba']
            for package in optional_packages:
                try:
                    __import__(package.replace('-', '_'))
                    result["details"][f"optional_{package}"] = f"✓ {package}已安装"
                except ImportError:
                    result["details"][f"optional_{package}"] = f"⚠ {package}未安装（可选）"
            
        except Exception as e:
            result["passed"] = False
            result["errors"].append(str(e))
        
        self.test_results.append(result)
        return result
    
    def test_basic_imports(self) -> Dict[str, Any]:
        """测试基础模块导入"""
        print("\n2. 测试基础模块导入...")
        result = {
            "test_name": "基础模块导入",
            "passed": True,
            "details": {},
            "errors": []
        }
        
        modules_to_test = [
            ("backend.vector_retrieval", "VectorRetriever"),
            ("backend.graph_query", "GraphQueryEngine"),
            ("backend.entity_extractor", "EntityExtractor"),
            ("backend.hallucination_detector", "HallucinationDetector"),
            ("backend.graphrag_engine", "GraphRAGEngine")
        ]
        
        for module_name, class_name in modules_to_test:
            try:
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name)
                result["details"][f"import_{class_name}"] = f"✓ {class_name}导入成功"
            except ImportError as e:
                result["details"][f"import_{class_name}"] = f"✗ {class_name}导入失败: {e}"
                result["passed"] = False
                result["errors"].append(f"{class_name}: {e}")
            except Exception as e:
                result["details"][f"import_{class_name}"] = f"✗ {class_name}初始化失败: {e}"
                result["passed"] = False
                result["errors"].append(f"{class_name}: {e}")
        
        self.test_results.append(result)
        return result
    
    def test_vector_retrieval(self) -> Dict[str, Any]:
        """测试向量检索功能"""
        print("\n3. 测试向量检索功能...")
        result = {
            "test_name": "向量检索",
            "passed": True,
            "details": {},
            "errors": []
        }
        
        try:
            # 尝试导入简化版本
            try:
                from backend.vector_retrieval import VectorRetriever
                retriever_class = VectorRetriever
                result["details"]["vector_type"] = "完整向量检索器"
            except ImportError:
                try:
                    from backend.simple_vector_retrieval import SimpleVectorRetriever
                    retriever_class = SimpleVectorRetriever
                    result["details"]["vector_type"] = "简化向量检索器"
                except ImportError:
                    raise ImportError("无法导入任何向量检索器")
            
            # 创建实例
            retriever = retriever_class()
            result["details"]["instance_creation"] = "✓ 检索器实例创建成功"
            
            # 测试添加文档
            test_docs = [{
                'id': 'test_1',
                'title': '测试文档',
                'content': '这是一个用于测试的政策文档内容。'
            }]
            
            success = retriever.add_documents(test_docs)
            if success:
                result["details"]["add_documents"] = "✓ 文档添加成功"
            else:
                result["details"]["add_documents"] = "✗ 文档添加失败"
                result["passed"] = False
            
            # 测试搜索
            search_results = retriever.search("测试政策", top_k=3)
            if search_results:
                result["details"]["search"] = f"✓ 搜索成功，返回{len(search_results)}个结果"
            else:
                result["details"]["search"] = "⚠ 搜索返回空结果"
            
            # 测试统计信息
            stats = retriever.get_collection_stats()
            result["details"]["stats"] = f"✓ 统计信息获取成功: {stats}"
            
        except Exception as e:
            result["passed"] = False
            result["errors"].append(str(e))
            result["details"]["error"] = f"✗ 测试失败: {e}"
        
        self.test_results.append(result)
        return result
    
    def test_graph_query(self) -> Dict[str, Any]:
        """测试图谱查询功能"""
        print("\n4. 测试图谱查询功能...")
        result = {
            "test_name": "图谱查询",
            "passed": True,
            "details": {},
            "errors": []
        }
        
        try:
            from backend.graph_query import GraphQueryEngine
            
            # 创建实例
            graph_engine = GraphQueryEngine()
            result["details"]["instance_creation"] = "✓ 图谱查询引擎创建成功"
            
            # 测试连接
            stats = graph_engine.get_graph_statistics()
            result["details"]["connection"] = f"✓ Neo4j连接成功，统计: {stats}"
            
            # 测试查询（可能无数据）
            entities = graph_engine.query_entities_by_name(['测试'])
            result["details"]["entity_query"] = f"✓ 实体查询成功，返回{len(entities)}个结果"
            
            # 关闭连接
            graph_engine.close()
            result["details"]["cleanup"] = "✓ 连接正常关闭"
            
        except Exception as e:
            result["passed"] = False
            result["errors"].append(str(e))
            result["details"]["error"] = f"✗ 测试失败: {e}"
        
        self.test_results.append(result)
        return result
    
    def test_entity_extraction(self) -> Dict[str, Any]:
        """测试实体提取功能"""
        print("\n5. 测试实体提取功能...")
        result = {
            "test_name": "实体提取",
            "passed": True,
            "details": {},
            "errors": []
        }
        
        try:
            from backend.entity_extractor import EntityExtractor
            
            # 创建实例
            extractor = EntityExtractor()
            result["details"]["instance_creation"] = "✓ 实体提取器创建成功"
            
            # 测试问题实体提取
            test_question = "华侨试验区的税收优惠政策是什么？"
            entities = extractor.extract_entities_from_question(test_question)
            result["details"]["question_entities"] = f"✓ 问题实体提取成功，提取到{len(entities)}个实体: {entities}"
            
            # 测试文本实体提取
            test_text = "华侨经济文化合作试验区管理委员会负责试验区的开发建设工作。"
            text_entities = extractor.extract_entities(test_text)
            result["details"]["text_entities"] = f"✓ 文本实体提取成功，提取到{len(text_entities)}个实体"
            
            # 测试关系提取
            if text_entities:
                relations = extractor.extract_relations(test_text, text_entities)
                result["details"]["relations"] = f"✓ 关系提取成功，提取到{len(relations)}个关系"
            
        except Exception as e:
            result["passed"] = False
            result["errors"].append(str(e))
            result["details"]["error"] = f"✗ 测试失败: {e}"
            
            # 检查是否是Ollama连接问题
            if "Ollama" in str(e) or "connection" in str(e).lower():
                result["details"]["note"] = "⚠ 可能是Ollama服务未启动或不可达"
        
        self.test_results.append(result)
        return result
    
    def test_graphrag_engine(self) -> Dict[str, Any]:
        """测试GraphRAG引擎"""
        print("\n6. 测试GraphRAG引擎...")
        result = {
            "test_name": "GraphRAG引擎",
            "passed": True,
            "details": {},
            "errors": []
        }
        
        try:
            from backend.graphrag_engine import GraphRAGEngine
            
            # 创建实例
            engine = GraphRAGEngine()
            result["details"]["instance_creation"] = "✓ GraphRAG引擎创建成功"
            
            # 测试系统状态
            stats = engine.get_system_stats()
            result["details"]["system_stats"] = f"✓ 系统统计获取成功: {stats.get('system_status', 'unknown')}"
            
            # 测试问答功能
            test_question = "什么是华侨试验区？"
            answer_result = engine.answer_question(
                test_question, 
                use_graph=True, 
                return_confidence=True
            )
            
            result["details"]["question_answering"] = f"✓ 问答功能测试成功"
            result["details"]["answer_length"] = f"答案长度: {len(answer_result.get('answer', ''))}"
            result["details"]["confidence"] = f"可信度: {answer_result.get('confidence', 'N/A')}"
            result["details"]["processing_time"] = f"处理时间: {answer_result.get('processing_time', 'N/A')}秒"
            
            # 关闭引擎
            engine.close()
            result["details"]["cleanup"] = "✓ 引擎正常关闭"
            
        except Exception as e:
            result["passed"] = False
            result["errors"].append(str(e))
            result["details"]["error"] = f"✗ 测试失败: {e}"
        
        self.test_results.append(result)
        return result
    
    def test_api_server(self) -> Dict[str, Any]:
        """测试API服务器导入"""
        print("\n7. 测试API服务器...")
        result = {
            "test_name": "API服务器",
            "passed": True,
            "details": {},
            "errors": []
        }
        
        try:
            # 测试API模块导入
            from backend.api_server import app, GRAPHRAG_AVAILABLE
            result["details"]["api_import"] = "✓ API服务器模块导入成功"
            result["details"]["graphrag_available"] = f"GraphRAG可用性: {GRAPHRAG_AVAILABLE}"
            
            # 检查Flask应用
            if hasattr(app, 'url_map'):
                routes = [str(rule) for rule in app.url_map.iter_rules()]
                result["details"]["routes_count"] = f"✓ 发现{len(routes)}个API路由"
                
                # 检查GraphRAG路由
                graphrag_routes = [r for r in routes if 'enhanced' in r or 'graph' in r or 'compare' in r]
                result["details"]["graphrag_routes"] = f"GraphRAG路由数量: {len(graphrag_routes)}"
            
        except Exception as e:
            result["passed"] = False
            result["errors"].append(str(e))
            result["details"]["error"] = f"✗ 测试失败: {e}"
        
        self.test_results.append(result)
        return result
    
    def test_data_import(self) -> Dict[str, Any]:
        """测试数据导入功能"""
        print("\n8. 测试数据导入功能...")
        result = {
            "test_name": "数据导入",
            "passed": True,
            "details": {},
            "errors": []
        }
        
        try:
            # 检查数据文件
            database_dir = Path("database")
            if database_dir.exists():
                json_files = list(database_dir.glob("*.json"))
                non_checkpoint_files = [f for f in json_files if '.ipynb_checkpoints' not in str(f)]
                result["details"]["data_files"] = f"✓ 找到{len(non_checkpoint_files)}个数据文件"
                
                # 测试数据加载
                if non_checkpoint_files:
                    test_file = non_checkpoint_files[0]
                    with open(test_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    result["details"]["data_load"] = f"✓ 数据文件加载成功: {test_file.name}"
                    result["details"]["data_type"] = f"数据类型: {type(data).__name__}"
            else:
                result["details"]["data_files"] = "⚠ 数据目录不存在"
                result["passed"] = False
        
        except Exception as e:
            result["passed"] = False
            result["errors"].append(str(e))
            result["details"]["error"] = f"✗ 测试失败: {e}"
        
        self.test_results.append(result)
        return result
    
    def generate_test_report(self) -> str:
        """生成测试报告"""
        print("\n" + "="*50)
        print("生成测试报告...")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        failed_tests = total_tests - passed_tests
        
        report = []
        report.append("# GraphRAG系统测试报告")
        report.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("## 测试摘要")
        report.append(f"- 总测试数: {total_tests}")
        report.append(f"- 通过测试: {passed_tests}")
        report.append(f"- 失败测试: {failed_tests}")
        report.append(f"- 通过率: {(passed_tests/total_tests)*100:.1f}%")
        report.append("")
        
        # 详细结果
        report.append("## 详细测试结果")
        for i, result in enumerate(self.test_results, 1):
            status = "✓ 通过" if result["passed"] else "✗ 失败"
            report.append(f"### {i}. {result['test_name']} - {status}")
            
            for key, value in result["details"].items():
                report.append(f"- {value}")
            
            if result["errors"]:
                report.append("**错误信息:**")
                for error in result["errors"]:
                    report.append(f"- {error}")
            
            report.append("")
        
        # 建议
        report.append("## 建议")
        if failed_tests == 0:
            report.append("🎉 所有测试通过！系统运行正常。")
        else:
            report.append("⚠️ 存在失败的测试，请检查以下问题：")
            for result in self.test_results:
                if not result["passed"]:
                    report.append(f"- {result['test_name']}: {'; '.join(result['errors'])}")
        
        return "\n".join(report)
    
    def run_all_tests(self):
        """运行所有测试"""
        try:
            self.test_environment_setup()
            self.test_basic_imports()
            self.test_vector_retrieval()
            self.test_graph_query()
            self.test_entity_extraction()
            self.test_graphrag_engine()
            self.test_api_server()
            self.test_data_import()
            
            # 生成并保存报告
            report = self.generate_test_report()
            
            # 保存到文件
            report_file = Path("test_report.md")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"测试报告已保存到: {report_file}")
            
            # 打印摘要
            total_tests = len(self.test_results)
            passed_tests = sum(1 for r in self.test_results if r["passed"])
            
            print("\n" + "="*50)
            print("测试完成摘要:")
            print(f"通过测试: {passed_tests}/{total_tests}")
            print(f"通过率: {(passed_tests/total_tests)*100:.1f}%")
            
            if passed_tests == total_tests:
                print("🎉 所有测试通过！")
            else:
                print("⚠️ 部分测试失败，请查看详细报告")
            
        except Exception as e:
            logging.error(f"测试执行失败: {e}")
            print(f"测试执行失败: {e}")


def main():
    """主函数"""
    tester = GraphRAGSystemTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()