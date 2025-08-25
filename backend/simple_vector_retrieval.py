
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
