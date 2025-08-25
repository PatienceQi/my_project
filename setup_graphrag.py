"""
GraphRAG安装和验证脚本
简化的安装流程，用于验证GraphRAG功能
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def install_missing_packages():
    """安装缺失的包"""
    required_packages = [
        'jieba',  # 中文分词，轻量级
        # 暂时不安装大型依赖，先验证基本功能
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            logging.info(f"包 {package} 已安装")
        except ImportError:
            logging.info(f"安装包: {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def create_data_directory():
    """创建数据目录"""
    data_dir = Path("data")
    chroma_dir = data_dir / "chroma_db"
    
    data_dir.mkdir(exist_ok=True)
    chroma_dir.mkdir(exist_ok=True)
    
    logging.info(f"数据目录已创建: {data_dir.absolute()}")

def create_simplified_vector_retrieval():
    """创建简化的向量检索模块"""
    content = '''
"""
简化向量检索 - 不依赖外部向量数据库的基础实现
"""

import json
import logging
from typing import List, Dict
import os

class SimpleVectorRetriever:
    """简化向量检索器"""
    
    def __init__(self):
        self.documents = []
        self.data_file = "data/simple_vector_store.json"
        self._load_documents()
    
    def _load_documents(self):
        """加载文档"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
                    logging.info(f"加载了 {len(self.documents)} 个文档")
        except Exception as e:
            logging.error(f"加载文档失败: {e}")
            self.documents = []
    
    def add_documents(self, documents: List[Dict]) -> bool:
        """添加文档"""
        try:
            for doc in documents:
                doc_data = {
                    'id': doc.get('id', 'unknown'),
                    'title': doc.get('title', ''),
                    'content': doc.get('content', ''),
                    'source': doc.get('source', '')
                }
                self.documents.append(doc_data)
            
            self._save_documents()
            logging.info(f"添加了 {len(documents)} 个文档")
            return True
            
        except Exception as e:
            logging.error(f"添加文档失败: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """简单的关键词搜索"""
        results = []
        query_lower = query.lower()
        
        for doc in self.documents:
            score = 0
            content = (doc.get('title', '') + ' ' + doc.get('content', '')).lower()
            
            # 简单的关键词匹配评分
            for word in query_lower.split():
                if word in content:
                    score += 1
            
            if score > 0:
                results.append({
                    'document': content[:200] + '...',
                    'metadata': {
                        'title': doc.get('title', ''),
                        'source': doc.get('source', '')
                    },
                    'similarity': score / len(query_lower.split()),
                    'id': doc.get('id', '')
                })
        
        # 按相似度排序
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def _save_documents(self):
        """保存文档"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存文档失败: {e}")
    
    def get_collection_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_documents': len(self.documents),
            'storage_type': 'simple_json'
        }
    
    def clear_collection(self) -> bool:
        """清空集合"""
        self.documents = []
        self._save_documents()
        return True
'''
    
    with open('backend/simple_vector_retrieval.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    logging.info("创建简化向量检索模块")

def create_test_script():
    """创建测试脚本"""
    content = '''
"""
GraphRAG基础功能测试
"""

import sys
import os
import logging
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_basic_functionality():
    """测试基础功能"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # 测试基础导入
        from backend.simple_vector_retrieval import SimpleVectorRetriever
        from backend.graph_query import GraphQueryEngine
        from backend.entity_extractor import EntityExtractor
        
        print("✓ 基础模块导入成功")
        
        # 测试向量检索
        retriever = SimpleVectorRetriever()
        test_docs = [
            {
                'id': 'test_1',
                'title': '测试政策',
                'content': '这是一个测试政策文档，包含一些基础内容。'
            }
        ]
        retriever.add_documents(test_docs)
        results = retriever.search('测试政策')
        print(f"✓ 向量检索测试成功，找到 {len(results)} 个结果")
        
        # 测试实体提取（需要Ollama服务）
        try:
            extractor = EntityExtractor()
            entities = extractor.extract_entities_from_question("华侨试验区的政策是什么？")
            print(f"✓ 实体提取测试成功，提取到 {len(entities)} 个实体")
        except Exception as e:
            print(f"⚠ 实体提取测试失败（可能Ollama服务未启动）: {e}")
        
        # 测试图谱查询（需要Neo4j服务）
        try:
            graph_engine = GraphQueryEngine()
            stats = graph_engine.get_graph_statistics()
            print(f"✓ 图谱查询测试成功，统计信息: {stats}")
            graph_engine.close()
        except Exception as e:
            print(f"⚠ 图谱查询测试失败（可能Neo4j服务未启动）: {e}")
        
        print("\\n基础功能测试完成！")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")

if __name__ == "__main__":
    test_basic_functionality()
'''
    
    with open('test_graphrag_basic.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    logging.info("创建测试脚本")

def main():
    """主函数"""
    setup_logging()
    
    print("GraphRAG简化安装和验证")
    print("=" * 40)
    
    # 1. 安装基础包
    print("1. 安装基础依赖包...")
    install_missing_packages()
    
    # 2. 创建目录
    print("2. 创建数据目录...")
    create_data_directory()
    
    # 3. 创建简化模块
    print("3. 创建简化模块...")
    create_simplified_vector_retrieval()
    
    # 4. 创建测试脚本
    print("4. 创建测试脚本...")
    create_test_script()
    
    print("\\n✓ 基础安装完成！")
    print("\\n下一步操作：")
    print("1. 运行测试: python test_graphrag_basic.py")
    print("2. 如需完整功能，请确保Neo4j和Ollama服务正常运行")
    print("3. 如需向量检索，可以安装: pip install chromadb sentence-transformers")

if __name__ == "__main__":
    main()