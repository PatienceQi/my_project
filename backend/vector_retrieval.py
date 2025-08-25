"""
向量检索模块 - 基于Chroma的语义检索
支持文档嵌入、存储和相似度检索
使用远程Ollama服务获取bge-m3嵌入向量
"""

import os
import logging
from typing import List, Dict, Tuple, Optional
import chromadb
from chromadb.config import Settings
import numpy as np
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class VectorRetriever:
    """向量检索器 - 基于Chroma和远程Ollama嵌入服务"""
    
    def __init__(self):
        """初始化向量检索器"""
        # 使用bge-m3:latest模型（符合GraphRAG系统设计规范）
        self.embedding_model_name = os.getenv('EMBEDDING_MODEL', 'bge-m3:latest')
        self.ollama_host = os.getenv('LLM_BINDING_HOST', 'http://120.232.79.82:11434')
        self.persist_dir = os.getenv('CHROMA_PERSIST_DIR', './data/chroma_db')
        self.chunk_size = int(os.getenv('CHUNK_SIZE', 512))
        self.chunk_overlap = int(os.getenv('CHUNK_OVERLAP', 50))
        self.top_k = int(os.getenv('VECTOR_RETRIEVAL_TOP_K', 5))
        
        # 确保存储目录存在
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # 确保Ollama主机地址格式正确
        if not self.ollama_host.startswith('http'):
            self.ollama_host = f"http://{self.ollama_host}"
            
        # 初始化组件
        self.chroma_client = None
        self.collection = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化Chroma客户端和Ollama嵌入服务"""
        try:
            # 测试Ollama嵌入服务连接
            logging.info(f"初始化Ollama嵌入服务: {self.ollama_host}")
            logging.info(f"使用嵌入模型: {self.embedding_model_name}")
            
            # 测试连接
            test_response = self._get_embedding_from_ollama("测试")
            if test_response:
                logging.info(f"Ollama嵌入服务连接成功")
                self.use_ollama = True
            else:
                raise Exception("Ollama嵌入服务测试失败")
            
        except Exception as e:
            logging.warning(f"Ollama嵌入服务初始化失败: {e}")
            logging.info("尝试使用本地sentence-transformers作为备用方案...")
            
            try:
                # 回退到本地模型
                from sentence_transformers import SentenceTransformer
                fallback_model = 'all-MiniLM-L6-v2'
                self.embedding_model = SentenceTransformer(fallback_model)
                self.embedding_model_name = fallback_model
                self.use_ollama = False
                logging.info(f"使用本地备用模型: {fallback_model}")
                
            except Exception as fallback_error:
                logging.error(f"备用模型加载失败: {fallback_error}")
                raise Exception("无法初始化任何嵌入模型")
        
        try:
            # 初始化Chroma客户端
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 获取或创建集合 - 根据模型类型命名
            collection_name = f"policy_documents_{self.embedding_model_name.replace(':', '_').replace('-', '_')}"
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "description": f"政策法规文档向量集合 - {self.embedding_model_name}",
                    "embedding_model": self.embedding_model_name,
                    "ollama_host": self.ollama_host if hasattr(self, 'use_ollama') and self.use_ollama else "local",
                    "use_ollama": getattr(self, 'use_ollama', False)
                }
            )
            
            service_type = "Ollama远程服务" if getattr(self, 'use_ollama', False) else "本地sentence-transformers"
            logging.info(f"向量检索器初始化成功，使用{service_type}: {self.embedding_model_name}")
            
        except Exception as e:
            logging.error(f"向量检索器初始化失败: {e}")
            raise
    
    def _get_embedding_from_ollama(self, text: str) -> Optional[List[float]]:
        """通过Ollama API获取文本的嵌入向量"""
        if not text or not text.strip():
            return None
            
        url = f"{self.ollama_host}/api/embed"
        payload = {
            "model": self.embedding_model_name,
            "input": text.strip()
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=600)
            response.raise_for_status()
            
            result = response.json()
            embeddings = result.get('embeddings')
            
            if embeddings and len(embeddings) > 0:
                return embeddings[0]  # 返回第一个嵌入向量
            else:
                logging.error(f"Ollama嵌入响应中没有找到embeddings字段")
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Ollama嵌入API调用失败: {e}")
            return None
        except Exception as e:
            logging.error(f"嵌入向量获取失败: {e}")
            return None
    
    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """批量获取嵌入向量"""
        if getattr(self, 'use_ollama', False):
            return self._get_embeddings_batch_ollama(texts)
        else:
            return self._get_embeddings_batch_local(texts)
    
    def _get_embeddings_batch_ollama(self, texts: List[str]) -> List[List[float]]:
        """通过Ollama批量获取嵌入向量"""
        embeddings = []
        
        for i, text in enumerate(texts):
            if i % 10 == 0:  # 每10个文本显示进度
                logging.info(f"正在处理第 {i+1}/{len(texts)} 个文本块...")
                
            embedding = self._get_embedding_from_ollama(text)
            if embedding:
                embeddings.append(embedding)
            else:
                # 如果获取失败，跳过该文本
                logging.warning(f"文本块 {i} 嵌入获取失败，跳过")
                continue
                
        return embeddings
    
    def _get_embeddings_batch_local(self, texts: List[str]) -> List[List[float]]:
        """使用本地模型批量获取嵌入向量"""
        try:
            logging.info(f"使用本地模型为 {len(texts)} 个文本块生成嵌入向量...")
            embeddings = self.embedding_model.encode(
                texts, 
                show_progress_bar=True,
                convert_to_numpy=True
            )
            return embeddings.tolist()
        except Exception as e:
            logging.error(f"本地模型嵌入生成失败: {e}")
            return []
    
    def split_text(self, text: str) -> List[str]:
        """文本分块处理"""
        if not text or len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 如果不是最后一块，尝试在合适位置断开
            if end < len(text):
                # 向后查找句号、问号、感叹号等自然断句点
                for i in range(end, max(start + self.chunk_size // 2, start), -1):
                    if text[i] in '。！？\n':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 计算下一块的起始位置（考虑重叠）
            start = max(start + 1, end - self.chunk_overlap)
        
        return chunks
    
    def add_documents(self, documents: List[Dict]) -> bool:
        """添加文档到向量数据库"""
        try:
            all_chunks = []
            all_metadatas = []
            all_ids = []
            
            for doc_idx, doc in enumerate(documents):
                # 提取文档文本
                doc_text = self._extract_document_text(doc)
                
                # 文本分块
                chunks = self.split_text(doc_text)
                
                for chunk_idx, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue
                    
                    chunk_id = f"doc_{doc_idx}_chunk_{chunk_idx}"
                    
                    all_chunks.append(chunk)
                    all_metadatas.append({
                        'document_id': doc.get('id', f'doc_{doc_idx}'),
                        'title': doc.get('title', '未知标题'),
                        'source': doc.get('source', '未知来源'),
                        'chunk_index': chunk_idx,
                        'total_chunks': len(chunks)
                    })
                    all_ids.append(chunk_id)
            
            if not all_chunks:
                logging.warning("没有有效的文档块可添加")
                return False
            
            # 使用Ollama生成嵌入向量
            logging.info(f"为 {len(all_chunks)} 个文档块生成嵌入向量...")
            embeddings = self._get_embeddings_batch(all_chunks)
            
            if len(embeddings) != len(all_chunks):
                logging.warning(f"嵌入向量数量({len(embeddings)})与文档块数量({len(all_chunks)})不一致")
                # 调整数据以保持一致性
                min_length = min(len(embeddings), len(all_chunks))
                embeddings = embeddings[:min_length]
                all_chunks = all_chunks[:min_length]
                all_metadatas = all_metadatas[:min_length]
                all_ids = all_ids[:min_length]
            
            if not embeddings:
                logging.error("没有成功生成任何嵌入向量")
                return False
            
            # 添加到Chroma集合
            self.collection.add(
                embeddings=embeddings,
                documents=all_chunks,
                metadatas=all_metadatas,
                ids=all_ids
            )
            
            logging.info(f"成功添加 {len(all_chunks)} 个文档块到向量数据库")
            return True
            
        except Exception as e:
            logging.error(f"添加文档到向量数据库失败: {e}")
            return False
    
    def _extract_document_text(self, doc: Dict) -> str:
        """从文档字典中提取文本内容"""
        text_parts = []
        
        # 添加标题
        if 'title' in doc:
            text_parts.append(f"标题: {doc['title']}")
        
        # 添加正文内容
        if 'content' in doc:
            text_parts.append(doc['content'])
        elif 'text' in doc:
            text_parts.append(doc['text'])
        
        # 添加章节内容
        if 'sections' in doc:
            for section in doc['sections']:
                if isinstance(section, dict):
                    if 'title' in section:
                        text_parts.append(f"章节: {section['title']}")
                    if 'content' in section:
                        text_parts.append(section['content'])
                elif isinstance(section, str):
                    text_parts.append(section)
        
        return '\n'.join(text_parts)
    
    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """语义检索"""
        if top_k is None:
            top_k = self.top_k
        
        try:
            # 根据使用的服务类型生成查询嵌入向量
            if getattr(self, 'use_ollama', False):
                query_embedding = self._get_embedding_from_ollama(query)
                if not query_embedding:
                    logging.error("查询嵌入向量生成失败")
                    return []
                query_embeddings = [query_embedding]
            else:
                # 使用本地模型
                query_embeddings = self.embedding_model.encode([query]).tolist()
            
            # 执行检索
            results = self.collection.query(
                query_embeddings=query_embeddings,
                n_results=top_k
            )
            
            # 格式化结果
            formatted_results = []
            
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    result = {
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i],
                        'similarity': 1 - results['distances'][0][i],  # 转换为相似度
                        'id': results['ids'][0][i]
                    }
                    formatted_results.append(result)
            
            logging.info(f"检索到 {len(formatted_results)} 个相关文档块")
            return formatted_results
            
        except Exception as e:
            logging.error(f"向量检索失败: {e}")
            return []
    
    def get_collection_stats(self) -> Dict:
        """获取集合统计信息"""
        try:
            count = self.collection.count()
            return {
                'total_documents': count,
                'embedding_dimension': 1024,  # bge-m3的维度
                'collection_name': self.collection.name,
                'embedding_model': self.embedding_model_name,
                'ollama_host': self.ollama_host
            }
        except Exception as e:
            logging.error(f"获取集合统计信息失败: {e}")
            return {}
    
    def clear_collection(self) -> bool:
        """清空集合"""
        try:
            collection_name = self.collection.name
            
            # 删除现有集合
            self.chroma_client.delete_collection(collection_name)
            
            # 重新创建集合
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "description": f"政策法规文档向量集合 - {self.embedding_model_name}",
                    "embedding_model": self.embedding_model_name,
                    "ollama_host": self.ollama_host
                }
            )
            
            logging.info("成功清空向量数据库集合")
            return True
            
        except Exception as e:
            logging.error(f"清空集合失败: {e}")
            return False


def test_vector_retrieval():
    """测试向量检索功能"""
    logging.basicConfig(level=logging.INFO)
    
    # 创建测试实例
    retriever = VectorRetriever()
    
    # 测试文档
    test_docs = [
        {
            'id': 'test_1',
            'title': '中小企业税收优惠政策',
            'content': '为了支持中小企业发展，国家出台了一系列税收优惠政策，包括减免企业所得税、增值税等措施。',
            'source': '测试文档'
        },
        {
            'id': 'test_2', 
            'title': '科技创新扶持政策',
            'content': '国家大力支持科技创新，为科技企业提供研发费用加计扣除、高新技术企业所得税优惠等政策支持。',
            'source': '测试文档'
        }
    ]
    
    # 添加测试文档
    print("添加测试文档...")
    success = retriever.add_documents(test_docs)
    print(f"添加结果: {'成功' if success else '失败'}")
    
    # 获取统计信息
    stats = retriever.get_collection_stats()
    print(f"集合统计: {stats}")
    
    # 测试检索
    test_queries = [
        "中小企业税收政策",
        "科技创新优惠",
        "企业所得税减免"
    ]
    
    for query in test_queries:
        print(f"\n检索查询: {query}")
        results = retriever.search(query, top_k=3)
        
        for i, result in enumerate(results):
            print(f"  结果{i+1}: 相似度={result['similarity']:.3f}")
            print(f"    内容: {result['document'][:100]}...")
            print(f"    元数据: {result['metadata']}")


if __name__ == "__main__":
    test_vector_retrieval()