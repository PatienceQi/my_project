"""
增强数据导入脚本 - 支持GraphRAG的政策文档导入
集成向量索引、实体关系提取、知识图谱构建等功能
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = os.path.join(os.path.dirname(__file__), '..')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.vector_retrieval import VectorRetriever
from backend.graph_query import GraphQueryEngine
from backend.entity_extractor import EntityExtractor

# 加载环境变量
load_dotenv()

class GraphRAGDataImporter:
    """GraphRAG数据导入器"""
    
    def __init__(self):
        """初始化导入器"""
        self.data_dir = Path(__file__).parent.parent / 'database'
        self.experiment_mode = os.getenv('EXPERIMENT_MODE', 'true').lower() == 'true'
        
        # 初始化组件
        self.vector_retriever = None
        self.graph_query_engine = None
        self.entity_extractor = None
        
        self._initialize_components()
        
        logging.info("GraphRAG数据导入器初始化完成")
    
    def _initialize_components(self):
        """初始化各个组件"""
        try:
            logging.info("初始化向量检索器...")
            self.vector_retriever = VectorRetriever()
            
            logging.info("初始化图谱查询引擎...")
            self.graph_query_engine = GraphQueryEngine()
            
            logging.info("初始化实体提取器...")
            self.entity_extractor = EntityExtractor()
            
            logging.info("所有组件初始化成功")
            
        except Exception as e:
            logging.error(f"组件初始化失败: {e}")
            raise
    
    def load_policy_documents(self) -> List[Dict]:
        """加载政策文档"""
        documents = []
        
        # 查找所有JSON文件
        json_files = list(self.data_dir.glob('*.json'))
        
        # 过滤掉checkpoint文件
        json_files = [f for f in json_files if '.ipynb_checkpoints' not in str(f)]
        
        logging.info(f"找到 {len(json_files)} 个数据文件")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 处理不同的数据格式
                if isinstance(data, list):
                    for item in data:
                        doc = self._normalize_document(item, json_file.name)
                        if doc:
                            documents.append(doc)
                elif isinstance(data, dict):
                    doc = self._normalize_document(data, json_file.name)
                    if doc:
                        documents.append(doc)
                
                logging.info(f"从 {json_file.name} 加载了文档数据")
                
            except Exception as e:
                logging.error(f"加载文件 {json_file.name} 失败: {e}")
        
        logging.info(f"总共加载 {len(documents)} 个文档")
        return documents
    
    def _normalize_document(self, raw_data: Dict, source_file: str) -> Dict:
        """标准化文档格式"""
        try:
            # 检测数据格式
            doc_format = self._detect_data_format(raw_data)
            
            if doc_format == 'standard':
                return self._process_standard_format(raw_data, source_file)
            elif doc_format == 'ocr':
                return self._process_ocr_format(raw_data, source_file)
            else:
                logging.warning(f"未识别的数据格式: {source_file}")
                return None
                
        except Exception as e:
            logging.error(f"文档标准化失败 {source_file}: {e}")
            return None
    
    def _detect_data_format(self, data: Dict) -> str:
        """检测数据格式"""
        # 标准格式检测 - 修复：使用chapters而不是sections
        if 'title' in data and 'chapters' in data:
            return 'standard'
        
        # OCR格式检测 - 修复：使用main_body字段
        if 'title' in data and 'main_body' in data:
            return 'ocr'
        
        # 兼容旧格式：原始OCR字段检测
        if 'ocr_result' in data or 'ocr_text' in data:
            return 'ocr'
        
        # 简单文档格式
        if 'content' in data or 'text' in data:
            return 'simple'
        
        return 'unknown'
    
    def _process_standard_format(self, data: Dict, source_file: str) -> Dict:
        """处理标准格式数据"""
        document = {
            'id': data.get('id', f"{source_file}_{data.get('title', 'unknown')}"),
            'title': data.get('title', '未知标题'),
            'source': source_file,
            'document_number': data.get('document_number', ''),
            'publish_date': data.get('publish_date', ''),
            'issuing_agency': data.get('issuing_agency', ''),
            'sections': [],
            'content': ''
        }
        
        # 处理章节 - 修复：使用chapters而不是sections
        content_parts = [document['title']]
        
        for chapter in data.get('chapters', []):
            if isinstance(chapter, dict):
                chapter_title = chapter.get('title', '')
                chapter_number = chapter.get('number', '')
                
                # 格式化章节标题
                section_title = f"{chapter_number} {chapter_title}".strip()
                
                # 处理章节内的条款
                chapter_content_parts = []
                articles = chapter.get('articles', [])
                
                for article in articles:
                    if isinstance(article, dict):
                        article_number = article.get('number', '')
                        article_content = article.get('content', '')
                        
                        if article_number and article_content:
                            article_text = f"{article_number} {article_content}"
                            chapter_content_parts.append(article_text)
                        elif article_content:
                            chapter_content_parts.append(article_content)
                
                # 整合章节内容
                chapter_content = '\n'.join(chapter_content_parts)
                
                section_info = {
                    'title': section_title,
                    'number': chapter_number,
                    'content': chapter_content,
                    'articles': articles  # 保留原始条款结构
                }
                document['sections'].append(section_info)
                
                # 添加到全文内容
                if section_title:
                    content_parts.append(section_title)
                if chapter_content:
                    content_parts.append(chapter_content)
        
        document['content'] = '\n'.join(content_parts)
        
        return document
    
    def _process_ocr_format(self, data: Dict, source_file: str) -> Dict:
        """处理OCR格式数据"""
        document = {
            'id': f"ocr_{source_file}_{hash(str(data)) % 10000}",
            'title': data.get('title', 'OCR文档'),
            'source': source_file,
            'document_number': data.get('doc_number', ''),
            'publish_date': data.get('publish_date', ''),
            'issuing_agency': data.get('publish_agency', ''),
            'notification_body': data.get('notification_body', ''),
            'sections': [],
            'content': '',
            'ocr_confidence': data.get('confidence', 0.0)
        }
        
        content_parts = [document['title']]
        
        # 处理通知主体
        if document['notification_body']:
            content_parts.append(document['notification_body'])
        
        # 处理主体内容 - 修复：使用main_body结构
        main_body = data.get('main_body', [])
        if main_body:
            for section in main_body:
                if isinstance(section, dict):
                    section_title = section.get('section_title', '')
                    section_content = section.get('content', '')
                    
                    section_info = {
                        'title': section_title,
                        'content': section_content
                    }
                    document['sections'].append(section_info)
                    
                    # 添加到全文内容
                    if section_title:
                        content_parts.append(section_title)
                    if section_content:
                        content_parts.append(section_content)
        
        # 兼容旧格式：直接OCR结果
        elif 'ocr_result' in data:
            document['content'] = data['ocr_result']
            content_parts.append(data['ocr_result'])
        elif 'ocr_text' in data:
            document['content'] = data['ocr_text']
            content_parts.append(data['ocr_text'])
        elif 'text' in data:
            document['content'] = data['text']
            content_parts.append(data['text'])
        
        # 处理结尾和抄送部分
        if data.get('ending'):
            content_parts.append(data['ending'])
        if data.get('cc'):
            content_parts.append(f"抄送：{data['cc']}")
        
        document['content'] = '\n'.join(content_parts)
        
        return document
    
    def import_all_data(self, rebuild_vector_db: bool = False, rebuild_graph: bool = False):
        """导入所有数据到GraphRAG系统"""
        try:
            logging.info("开始GraphRAG数据导入...")
            
            # 清理现有数据（如果需要）
            if rebuild_vector_db:
                logging.info("清理向量数据库...")
                self.vector_retriever.clear_collection()
            
            if rebuild_graph:
                logging.info("清理知识图谱...")
                self._clear_graph_database()
            
            # 加载文档
            documents = self.load_policy_documents()
            
            if not documents:
                logging.warning("没有找到可导入的文档")
                return
            
            # 分批处理文档（避免内存问题）
            batch_size = 10
            total_batches = (len(documents) + batch_size - 1) // batch_size
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(documents))
                batch_docs = documents[start_idx:end_idx]
                
                logging.info(f"处理批次 {batch_idx + 1}/{total_batches}: {len(batch_docs)} 个文档")
                
                # 1. 向量索引
                self._index_documents_to_vector_db(batch_docs)
                
                # 2. 实体关系提取
                extraction_results = self._extract_entities_and_relations(batch_docs)
                
                # 3. 构建知识图谱
                self._build_knowledge_graph(batch_docs, extraction_results)
            
            # 获取最终统计
            self._print_import_statistics()
            
            logging.info("GraphRAG数据导入完成")
            
        except Exception as e:
            logging.error(f"数据导入失败: {e}")
            raise
    
    def _index_documents_to_vector_db(self, documents: List[Dict]):
        """将文档索引到向量数据库"""
        try:
            success = self.vector_retriever.add_documents(documents)
            if success:
                logging.info(f"成功将 {len(documents)} 个文档添加到向量数据库")
            else:
                logging.error("向量数据库索引失败")
                
        except Exception as e:
            logging.error(f"向量索引失败: {e}")
    
    def _extract_entities_and_relations(self, documents: List[Dict]) -> List[Dict]:
        """批量提取实体和关系"""
        try:
            logging.info(f"开始提取 {len(documents)} 个文档的实体和关系...")
            
            results = []
            for i, doc in enumerate(documents):
                logging.info(f"处理文档 {i+1}/{len(documents)}: {doc.get('title', 'unknown')}")
                
                try:
                    result = self.entity_extractor.extract_all_from_document(doc)
                    results.append(result)
                    
                    # 记录提取统计
                    entity_count = len(result.get('entities', []))
                    relation_count = len(result.get('relations', []))
                    logging.info(f"  提取到 {entity_count} 个实体, {relation_count} 个关系")
                    
                except Exception as e:
                    logging.error(f"文档 {i+1} 实体提取失败: {e}")
                    results.append({
                        'entities': [],
                        'relations': [],
                        'document_id': doc.get('id', f'doc_{i}'),
                        'error': str(e)
                    })
            
            logging.info("实体关系提取完成")
            return results
            
        except Exception as e:
            logging.error(f"批量实体提取失败: {e}")
            return []
    
    def _build_knowledge_graph(self, documents: List[Dict], extraction_results: List[Dict]):
        """构建知识图谱"""
        try:
            logging.info("开始构建知识图谱...")
            
            with self.graph_query_engine.driver.session() as session:
                for doc, result in zip(documents, extraction_results):
                    try:
                        # 创建文档节点
                        self._create_policy_node(session, doc)
                        
                        # 创建实体节点和关系
                        entities = result.get('entities', [])
                        relations = result.get('relations', [])
                        
                        if entities:
                            self._create_entity_nodes(session, entities, doc['id'])
                        
                        if relations:
                            self._create_relation_edges(session, relations, doc['id'])
                        
                        logging.debug(f"文档 {doc.get('title', 'unknown')} 图谱构建完成")
                        
                    except Exception as e:
                        logging.error(f"文档 {doc.get('title', 'unknown')} 图谱构建失败: {e}")
            
            logging.info("知识图谱构建完成")
            
        except Exception as e:
            logging.error(f"知识图谱构建失败: {e}")
    
    def _create_policy_node(self, session, document: Dict):
        """创建政策文档节点"""
        query = """
        MERGE (p:Policy {id: $doc_id})
        SET p.title = $title,
            p.document_number = $doc_number,
            p.publish_date = $publish_date,
            p.issuing_agency = $issuing_agency,
            p.source = $source,
            p.content_preview = $content_preview
        """
        
        parameters = {
            'doc_id': document['id'],
            'title': document.get('title', ''),
            'doc_number': document.get('document_number', ''),
            'publish_date': document.get('publish_date', ''),
            'issuing_agency': document.get('issuing_agency', ''),
            'source': document.get('source', ''),
            'content_preview': document.get('content', '')[:500]
        }
        
        session.run(query, parameters)
    
    def _create_entity_nodes(self, session, entities: List[Dict], doc_id: str):
        """创建实体节点"""
        for entity in entities:
            query = """
            MERGE (e:Entity {name: $name, type: $type})
            SET e.text = $text,
                e.confidence = $confidence
            WITH e
            MATCH (p:Policy {id: $doc_id})
            MERGE (e)-[:MENTIONED_IN]->(p)
            """
            
            parameters = {
                'name': entity.get('text', ''),
                'type': entity.get('label', 'UNKNOWN'),
                'text': entity.get('text', ''),
                'confidence': entity.get('confidence', 0.5),
                'doc_id': doc_id
            }
            
            session.run(query, parameters)
    
    def _create_relation_edges(self, session, relations: List[Dict], doc_id: str):
        """创建关系边"""
        for relation in relations:
            query = """
            MATCH (e1:Entity {name: $source})
            MATCH (e2:Entity {name: $target})
            MATCH (p:Policy {id: $doc_id})
            MERGE (e1)-[r:RELATES_TO {type: $relation_type}]->(e2)
            SET r.confidence = $confidence,
                r.document_id = $doc_id
            """
            
            parameters = {
                'source': relation.get('source', ''),
                'target': relation.get('target', ''),
                'relation_type': relation.get('relation', 'UNKNOWN'),
                'confidence': relation.get('confidence', 0.5),
                'doc_id': doc_id
            }
            
            try:
                session.run(query, parameters)
            except Exception as e:
                logging.debug(f"关系创建失败: {relation} - {e}")
    
    def _clear_graph_database(self):
        """清理图数据库"""
        try:
            with self.graph_query_engine.driver.session() as session:
                # 删除所有节点和关系
                session.run("MATCH (n) DETACH DELETE n")
                logging.info("图数据库已清理")
                
        except Exception as e:
            logging.error(f"清理图数据库失败: {e}")
    
    def _print_import_statistics(self):
        """打印导入统计信息"""
        try:
            # 向量数据库统计
            vector_stats = self.vector_retriever.get_collection_stats()
            
            # 图数据库统计
            graph_stats = self.graph_query_engine.get_graph_statistics()
            
            print("\n" + "="*50)
            print("GraphRAG数据导入统计")
            print("="*50)
            print(f"向量数据库:")
            print(f"  - 文档块数量: {vector_stats.get('total_documents', 0)}")
            print(f"  - 嵌入维度: {vector_stats.get('embedding_dimension', 0)}")
            
            print(f"\n知识图谱:")
            print(f"  - 总节点数: {graph_stats.get('total_nodes', 0)}")
            print(f"  - 总关系数: {graph_stats.get('total_relationships', 0)}")
            print(f"  - 政策文档: {graph_stats.get('policy_count', 0)}")
            print(f"  - 实体数量: {graph_stats.get('entity_count', 0)}")
            print("="*50)
            
        except Exception as e:
            logging.error(f"统计信息获取失败: {e}")
    
    def close(self):
        """关闭所有连接"""
        try:
            if self.graph_query_engine:
                self.graph_query_engine.close()
            logging.info("数据导入器已关闭")
        except Exception as e:
            logging.error(f"关闭数据导入器时出错: {e}")


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 创建导入器
    importer = GraphRAGDataImporter()
    
    try:
        # 导入所有数据
        print("开始GraphRAG数据导入...")
        print("这可能需要几分钟时间，请耐心等待...")
        
        importer.import_all_data(
            rebuild_vector_db=True,  # 重建向量数据库
            rebuild_graph=False      # 不重建图数据库（保留现有数据）
        )
        
        print("\nGraphRAG数据导入完成！")
        
    except Exception as e:
        logging.error(f"导入过程失败: {e}")
        print(f"导入失败: {e}")
        
    finally:
        importer.close()


if __name__ == "__main__":
    main()