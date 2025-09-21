"""
图谱查询模块 - 基于Neo4j的知识图谱查询
支持实体查询、关系查询、路径查询等多种图谱操作
增强版本包含详细的终端输出和查询性能统计
"""

import os
import logging
import time
from typing import List, Dict, Optional, Tuple
from neo4j import GraphDatabase
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class GraphQueryEngine:
    """图谱查询引擎 - 基于Neo4j"""
    
    def __init__(self):
        """初始化图谱查询引擎"""
        self.uri = os.getenv('NEO4J_URI', 'neo4j://localhost:7687')
        self.username = os.getenv('NEO4J_USERNAME', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'password')
        self.top_k = int(os.getenv('GRAPH_RETRIEVAL_TOP_K', 5))
        
        self.driver = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """初始化Neo4j连接"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            logging.info("Neo4j图谱查询引擎初始化成功")
            
        except Exception as e:
            logging.error(f"Neo4j连接失败: {e}")
            raise
    
    def _validate_max_hops(self, max_hops: int) -> int:
        """验证并修正max_hops参数"""
        if not isinstance(max_hops, int):
            logging.warning(f"max_hops参数类型错误: {type(max_hops)}, 使用默认值2")
            return 2
        
        if max_hops < 1:
            logging.warning(f"max_hops过小: {max_hops}, 修正为1")
            return 1
        
        if max_hops > 10:
            logging.warning(f"max_hops过大: {max_hops}, 修正为10")
            return 10
        
        return max_hops
    
    def _empty_relationship_result(self, entity_name: str) -> Dict:
        """返回空的关系查询结果"""
        return {
            'center_entity': entity_name,
            'paths': [],
            'related_entities': [],
            'related_policies': []
        }
    
    def query_entities_by_name(self, entity_names: List[str]) -> List[Dict]:
        """根据实体名称查询相关信息（支持多种实体类型）"""
        if not entity_names:
            return []
        
        # 支持多种实体类型的查询
        query = """
        UNWIND $entity_names AS search_entity_name
        CALL {
            WITH search_entity_name
            // 查询传统Entity节点
            MATCH (e:Entity) 
            WHERE e.name CONTAINS search_entity_name OR e.text CONTAINS search_entity_name
            OPTIONAL MATCH (e)-[r]->(related)
            WHERE related:Entity OR related:Policy OR related:Agency
            RETURN 
                e.name as entity_name,
                e.type as entity_type,
                e.text as entity_text,
                'Entity' as node_label,
                collect(DISTINCT {
                    relation: type(r),
                    target: coalesce(related.name, related.title),
                    target_type: coalesce(related.type, 'unknown'),
                    target_labels: labels(related)
                }) as relations
            
            UNION
            
            WITH search_entity_name
            // 查询HotpotEntity节点
            MATCH (he:HotpotEntity) 
            WHERE he.name CONTAINS search_entity_name
            OPTIONAL MATCH (he)-[r]->(related)
            WHERE related:HotpotEntity OR related:HotpotQuestion OR related:HotpotParagraph
            RETURN 
                he.name as entity_name,
                he.entity_type as entity_type,
                he.name as entity_text,
                'HotpotEntity' as node_label,
                collect(DISTINCT {
                    relation: type(r),
                    target: coalesce(related.name, related.question, related.title),
                    target_type: coalesce(related.entity_type, 'hotpot_node'),
                    target_labels: labels(related)
                }) as relations
        }
        RETURN DISTINCT 
            entity_name,
            entity_type,
            entity_text,
            node_label,
            relations
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {
                    'entity_names': entity_names,
                    'limit': self.top_k * len(entity_names)
                })
                
                entities = []
                for record in result:
                    entity = {
                        'name': record['entity_name'],
                        'type': record['entity_type'],
                        'text': record['entity_text'],
                        'node_label': record['node_label'],
                        'relations': [r for r in record['relations'] if r['target'] is not None]
                    }
                    entities.append(entity)
                
                logging.info(f"查询到 {len(entities)} 个相关实体（包括HotpotEntity）")
                return entities
                
        except Exception as e:
            logging.error(f"实体查询失败: {e}")
            return []
    
    def query_hotpot_entities_by_name(self, entity_names: List[str]) -> List[Dict]:
        """专门查询HotpotEntity类型的实体"""
        if not entity_names:
            return []
        
        query = """
        UNWIND $entity_names AS search_entity_name
        MATCH (he:HotpotEntity) 
        WHERE he.name CONTAINS search_entity_name
        OPTIONAL MATCH (he)-[r]->(related)
        WHERE related:HotpotEntity OR related:HotpotQuestion OR related:HotpotParagraph
        RETURN 
            he.name as entity_name,
            he.entity_type as entity_type,
            he.name as entity_text,
            'HotpotEntity' as node_label,
            collect(DISTINCT {
                relation: type(r),
                target: coalesce(related.name, related.question, related.title),
                target_type: coalesce(related.entity_type, 'hotpot_node'),
                target_labels: labels(related)
            }) as relations
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {
                    'entity_names': entity_names,
                    'limit': self.top_k * len(entity_names)
                })
                
                entities = []
                for record in result:
                    entity = {
                        'name': record['entity_name'],
                        'type': record['entity_type'],
                        'text': record['entity_text'],
                        'node_label': record['node_label'],
                        'relations': [r for r in record['relations'] if r['target'] is not None]
                    }
                    entities.append(entity)
                
                logging.info(f"查询到 {len(entities)} 个HotpotEntity实体")
                return entities
                
        except Exception as e:
            logging.error(f"HotpotEntity查询失败: {e}")
            return []

    def query_policies_by_entities(self, entity_names: List[str]) -> List[Dict]:
        """根据实体查询相关政策文档（支持多种数据类型）"""
        if not entity_names:
            return []
        
        query = """
        UNWIND $entity_names AS search_entity_name
        CALL {
            WITH search_entity_name
            // 查询传统政策数据
            MATCH (e:Entity)-[:MENTIONED_IN]->(p:Policy)
            WHERE e.name CONTAINS search_entity_name OR e.text CONTAINS search_entity_name
            OPTIONAL MATCH (p)-[:HAS_SECTION]->(s:Section)
            OPTIONAL MATCH (p)-[:ISSUED_BY]->(agency:Agency)
            RETURN DISTINCT
                p.title as policy_title,
                p.document_number as document_number,
                p.publish_date as publish_date,
                agency.name as issuing_agency,
                collect(DISTINCT s.title) as sections,
                collect(DISTINCT e.name) as related_entities,
                'Policy' as data_type
            
            UNION
            
            WITH search_entity_name
            // 查询HotpotQA问题数据作为"政策"
            MATCH (he:HotpotEntity)-[:HAS_ENTITY|MENTIONS|RELATED_TO]->(hq:HotpotQuestion)
            WHERE he.name CONTAINS search_entity_name
            OPTIONAL MATCH (hq)-[:HAS_PARAGRAPH]->(hp:HotpotParagraph)
            RETURN DISTINCT
                hq.question as policy_title,
                hq.question_id as document_number,
                null as publish_date,
                'HotpotQA Dataset' as issuing_agency,
                collect(DISTINCT hp.title) as sections,
                collect(DISTINCT he.name) as related_entities,
                'HotpotQuestion' as data_type
        }
        RETURN DISTINCT
            policy_title,
            document_number,
            publish_date,
            issuing_agency,
            sections,
            related_entities,
            data_type
        ORDER BY data_type, policy_title
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {
                    'entity_names': entity_names,
                    'limit': self.top_k * 2  # 增加限制以包含更多数据类型
                })
                
                policies = []
                for record in result:
                    policy = {
                        'title': record['policy_title'],
                        'document_number': record['document_number'],
                        'publish_date': record['publish_date'],
                        'issuing_agency': record['issuing_agency'],
                        'sections': [s for s in record['sections'] if s],
                        'related_entities': [e for e in record['related_entities'] if e],
                        'data_type': record['data_type']
                    }
                    policies.append(policy)
                
                logging.info(f"查询到 {len(policies)} 个相关政策/问题")
                return policies
                
        except Exception as e:
            logging.error(f"政策查询失败: {e}")
            return []
    
    def query_entity_relationships(self, entity_name: str, max_hops: int = 2) -> Dict:
        """查询实体的关系网络（支持多种实体类型）"""
        # 验证并修正max_hops参数
        max_hops = self._validate_max_hops(max_hops)
        
        if not entity_name or not entity_name.strip():
            logging.error("entity_name参数为空")
            return self._empty_relationship_result(entity_name)
        
        # 构建支持多种实体类型的查询语句
        query = f"""
        CALL {{
            // 查询传统Entity节点的关系
            MATCH (e:Entity) 
            WHERE e.name CONTAINS $entity_name OR e.text CONTAINS $entity_name
            MATCH path = (e)-[*1..{max_hops}]-(related)
            WHERE related:Entity OR related:Policy OR related:Agency
            RETURN 
                e.name as center_entity,
                'Entity' as center_type,
                [node in nodes(path) | {{
                    id: id(node),
                    labels: labels(node),
                    name: coalesce(node.name, node.title),
                    type: coalesce(node.type, 'unknown')
                }}] as path_nodes,
                [rel in relationships(path) | {{
                    type: type(rel),
                    properties: properties(rel)
                }}] as path_relations
            
            UNION
            
            // 查询HotpotEntity节点的关系
            MATCH (he:HotpotEntity) 
            WHERE he.name CONTAINS $entity_name
            MATCH path = (he)-[*1..{max_hops}]-(related)
            WHERE related:HotpotEntity OR related:HotpotQuestion OR related:HotpotParagraph OR related:HotpotSupportingFact
            RETURN 
                he.name as center_entity,
                'HotpotEntity' as center_type,
                [node in nodes(path) | {{
                    id: id(node),
                    labels: labels(node),
                    name: coalesce(node.name, node.question, node.title, node.fact_text),
                    type: coalesce(node.entity_type, node.type, 'hotpot_node')
                }}] as path_nodes,
                [rel in relationships(path) | {{
                    type: type(rel),
                    properties: properties(rel)
                }}] as path_relations
        }}
        RETURN 
            center_entity,
            center_type,
            path_nodes,
            path_relations
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {
                    'entity_name': entity_name.strip(),
                    'limit': 50  # 增加限制以获取更多HotpotQA数据
                })
                
                relationships = {
                    'center_entity': entity_name,
                    'center_type': None,
                    'paths': [],
                    'related_entities': set(),
                    'related_policies': set(),
                    'hotpot_questions': set(),
                    'hotpot_entities': set()
                }
                
                for record in result:
                    if relationships['center_type'] is None:
                        relationships['center_type'] = record['center_type']
                    
                    path_info = {
                        'nodes': record['path_nodes'],
                        'relations': record['path_relations']
                    }
                    relationships['paths'].append(path_info)
                    
                    # 收集相关实体和节点
                    for node in record['path_nodes']:
                        node_labels = node['labels']
                        node_name = node['name']
                        
                        if 'Entity' in node_labels:
                            relationships['related_entities'].add(node_name)
                        elif 'Policy' in node_labels:
                            relationships['related_policies'].add(node_name)
                        elif 'HotpotEntity' in node_labels:
                            relationships['hotpot_entities'].add(node_name)
                        elif 'HotpotQuestion' in node_labels:
                            relationships['hotpot_questions'].add(node_name)
                
                # 转换set为list
                relationships['related_entities'] = list(relationships['related_entities'])
                relationships['related_policies'] = list(relationships['related_policies'])
                relationships['hotpot_questions'] = list(relationships['hotpot_questions'])
                relationships['hotpot_entities'] = list(relationships['hotpot_entities'])
                
                logging.info(f"查询到实体 {entity_name} 的关系网络，共 {len(relationships['paths'])} 条路径")
                return relationships
                
        except Exception as e:
            logging.error(f"关系查询失败: {e}")
            return self._empty_relationship_result(entity_name)
    
    def search_similar_policies(self, query_text: str) -> List[Dict]:
        """基于文本相似度的政策搜索"""
        query = """
        MATCH (p:Policy)
        OPTIONAL MATCH (p)-[:HAS_SECTION]->(s:Section)
        OPTIONAL MATCH (s)-[:CONTAINS]->(sub:SubSection)
        OPTIONAL MATCH (p)-[:ISSUED_BY]->(agency:Agency)
        WHERE 
            p.title CONTAINS $query_text OR 
            s.title CONTAINS $query_text OR 
            s.content CONTAINS $query_text OR
            sub.title CONTAINS $query_text OR
            sub.content CONTAINS $query_text
        RETURN DISTINCT
            p.title as policy_title,
            p.document_number as document_number,
            agency.name as agency_name,
            collect(DISTINCT {
                section_title: s.title,
                section_content: left(s.content, 200),
                subsection_title: sub.title,
                subsection_content: left(sub.content, 200)
            }) as content_snippets
        ORDER BY size(content_snippets) DESC
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {
                    'query_text': query_text,
                    'limit': self.top_k
                })
                
                policies = []
                for record in result:
                    policy = {
                        'title': record['policy_title'],
                        'document_number': record['document_number'],
                        'agency': record['agency_name'],
                        'content_snippets': [
                            snippet for snippet in record['content_snippets']
                            if snippet['section_title'] or snippet['subsection_title']
                        ]
                    }
                    policies.append(policy)
                
                logging.info(f"文本搜索找到 {len(policies)} 个相关政策")
                return policies
                
        except Exception as e:
            logging.error(f"政策搜索失败: {e}")
            return []
    
    def get_policy_context(self, policy_title: str) -> Dict:
        """获取政策的完整上下文信息"""
        query = """
        MATCH (p:Policy)
        WHERE p.title CONTAINS $policy_title
        OPTIONAL MATCH (p)-[:HAS_SECTION]->(s:Section)
        OPTIONAL MATCH (s)-[:CONTAINS]->(sub:SubSection)
        OPTIONAL MATCH (p)-[:ISSUED_BY]->(agency:Agency)
        OPTIONAL MATCH (e:Entity)-[:MENTIONED_IN]->(p)
        RETURN 
            p.title as title,
            p.document_number as document_number,
            p.publish_date as publish_date,
            p.effective_date as effective_date,
            agency.name as issuing_agency,
            collect(DISTINCT {
                section_title: s.title,
                section_content: s.content,
                subsections: collect(DISTINCT {
                    title: sub.title,
                    content: sub.content
                })
            }) as sections,
            collect(DISTINCT {
                name: e.name,
                type: e.type
            }) as mentioned_entities
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {'policy_title': policy_title})
                record = result.single()
                
                if not record:
                    return {}
                
                context = {
                    'title': record['title'],
                    'document_number': record['document_number'],
                    'publish_date': record['publish_date'],
                    'effective_date': record['effective_date'],
                    'issuing_agency': record['issuing_agency'],
                    'sections': [s for s in record['sections'] if s['section_title']],
                    'mentioned_entities': [e for e in record['mentioned_entities'] if e['name']]
                }
                
                logging.info(f"获取政策上下文: {policy_title}")
                return context
                
        except Exception as e:
            logging.error(f"获取政策上下文失败: {e}")
            return {}
    
    def verify_entity_relations(self, entities: List[str], relations: List[str]) -> List[Dict]:
        """验证实体间的关系是否存在于图谱中"""
        if len(entities) < 2:
            return []
        
        verification_results = []
        
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                entity1, entity2 = entities[i], entities[j]
                
                query = """
                MATCH (e1:Entity)-[r]-(e2:Entity)
                WHERE 
                    (e1.name CONTAINS $entity1 OR e1.text CONTAINS $entity1) AND
                    (e2.name CONTAINS $entity2 OR e2.text CONTAINS $entity2)
                RETURN 
                    e1.name as entity1_name,
                    e2.name as entity2_name,
                    type(r) as relation_type,
                    properties(r) as relation_properties
                LIMIT 5
                """
                
                try:
                    with self.driver.session() as session:
                        result = session.run(query, {
                            'entity1': entity1,
                            'entity2': entity2
                        })
                        
                        for record in result:
                            verification_results.append({
                                'entity1': record['entity1_name'],
                                'entity2': record['entity2_name'],
                                'relation': record['relation_type'],
                                'properties': record['relation_properties'],
                                'verified': True
                            })
                
                except Exception as e:
                    logging.error(f"关系验证失败: {e}")
                    verification_results.append({
                        'entity1': entity1,
                        'entity2': entity2,
                        'relation': 'unknown',
                        'properties': {},
                        'verified': False
                    })
        
        return verification_results
    
    def get_graph_statistics_safe(self) -> Dict:
        """安全的图统计获取"""
        try:
            if not self.driver:
                return {'status': 'not_connected'}
            
            # 优先使用轻量级查询避免长时间锁定
            lightweight_queries = {
                'label_count': "CALL db.labels() YIELD label RETURN count(label) as count",
                'relationship_types_count': "CALL db.relationshipTypes() YIELD relationshipType RETURN count(relationshipType) as count"
            }
            
            stats = {'status': 'healthy'}
            
            with self.driver.session() as session:
                for stat_name, query in lightweight_queries.items():
                    try:
                        result = session.run(query)
                        record = result.single()
                        stats[stat_name] = record['count'] if record else 0
                    except Exception as e:
                        logging.warning(f"轻量级查询 {stat_name} 失败: {e}")
                        stats[stat_name] = 0
                
                # 尝试获取一个基本的节点数量（使用LIMIT限制）
                try:
                    result = session.run("MATCH (n) RETURN count(n) as count LIMIT 1")
                    record = result.single()
                    stats['total_nodes_sample'] = record['count'] if record else 0
                except Exception as e:
                    logging.warning(f"节点数量查询失败: {e}")
                    stats['total_nodes_sample'] = 'unknown'
            
            return stats
                
        except Exception as e:
            logging.error(f"图数据库查询失败: {e}")
            return {
                'status': 'error',
                'message': f'图数据库查询失败: {str(e)}'
            }
    
    def get_graph_statistics(self) -> Dict:
        """获取图谱统计信息（保持向后兼容）"""
        try:
            # 首先尝试安全版本
            return self.get_graph_statistics_safe()
        except Exception as e:
            logging.error(f"获取图谱统计信息失败: {e}")
            return {}
    
    def get_enhanced_graph_statistics(self) -> Dict:
        """获取增强的图谱统计信息，包括HotpotQA数据"""
        enhanced_queries = {
            'total_nodes': "MATCH (n) RETURN count(n) as count",
            'total_relationships': "MATCH ()-[r]->() RETURN count(r) as count",
            'policy_count': "MATCH (p:Policy) RETURN count(p) as count",
            'entity_count': "MATCH (e:Entity) RETURN count(e) as count",
            'agency_count': "MATCH (a:Agency) RETURN count(a) as count",
            'hotpot_entity_count': "MATCH (he:HotpotEntity) RETURN count(he) as count",
            'hotpot_question_count': "MATCH (hq:HotpotQuestion) RETURN count(hq) as count",
            'hotpot_paragraph_count': "MATCH (hp:HotpotParagraph) RETURN count(hp) as count"
        }
        
        stats = {}
        
        try:
            with self.driver.session() as session:
                for stat_name, query in enhanced_queries.items():
                    try:
                        result = session.run(query)
                        record = result.single()
                        stats[stat_name] = record['count'] if record else 0
                    except Exception as e:
                        logging.warning(f"查询 {stat_name} 失败: {e}")
                        stats[stat_name] = 0
            
            logging.info("获取增强图谱统计信息成功")
            return stats
            
        except Exception as e:
            logging.error(f"获取增强图谱统计信息失败: {e}")
            return {}

    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            logging.info("Neo4j连接已关闭")


class EnhancedGraphQueryEngine(GraphQueryEngine):
    """增强的图谱查询引擎 - 带有详细的终端输出和性能统计"""
    
    def __init__(self):
        """初始化增强的图谱查询引擎"""
        super().__init__()
        self.query_logger = self._setup_query_logger()
        self.query_stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'total_query_time': 0.0,
            'average_query_time': 0.0
        }
    
    def _setup_query_logger(self):
        """设置专门的图查询日志器"""
        logger = logging.getLogger('enhanced_graph_query')
        logger.setLevel(logging.INFO)
        
        # 检查是否已经有handler，避免重复添加
        if not logger.handlers:
            # 终端输出处理器
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '🔍 [图查询] %(asctime)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            # 设置不传播到父logger
            logger.propagate = False
        
        return logger
    
    def _update_query_stats(self, query_time: float, success: bool):
        """更新查询统计信息"""
        self.query_stats['total_queries'] += 1
        if success:
            self.query_stats['successful_queries'] += 1
        else:
            self.query_stats['failed_queries'] += 1
        
        self.query_stats['total_query_time'] += query_time
        self.query_stats['average_query_time'] = (
            self.query_stats['total_query_time'] / self.query_stats['total_queries']
        )
    
    def query_entities_by_name_with_logging(self, entity_names: List[str]) -> List[Dict]:
        """带详细输出的实体查询"""
        self.query_logger.info(f"开始实体查询: {entity_names}")
        self.query_logger.info(f"查询参数: top_k={self.top_k}")
        
        start_time = time.time()
        
        # 构建查询语句
        self.query_logger.info(f"生成Cypher查询语句")
        query = """
        UNWIND $entity_names AS search_entity_name
        CALL {
            WITH search_entity_name
            // 查询传统Entity节点
            MATCH (e:Entity) 
            WHERE e.name CONTAINS search_entity_name OR e.text CONTAINS search_entity_name
            OPTIONAL MATCH (e)-[r]->(related)
            WHERE related:Entity OR related:Policy OR related:Agency
            RETURN 
                e.name as entity_name,
                e.type as entity_type,
                e.text as entity_text,
                'Entity' as node_label,
                collect(DISTINCT {
                    relation: type(r),
                    target: coalesce(related.name, related.title),
                    target_type: coalesce(related.type, 'unknown'),
                    target_labels: labels(related)
                }) as relations
            
            UNION
            
            WITH search_entity_name
            // 查询HotpotEntity节点
            MATCH (he:HotpotEntity) 
            WHERE he.name CONTAINS search_entity_name
            OPTIONAL MATCH (he)-[r]->(related)
            WHERE related:HotpotEntity OR related:HotpotQuestion OR related:HotpotParagraph
            RETURN 
                he.name as entity_name,
                he.entity_type as entity_type,
                he.name as entity_text,
                'HotpotEntity' as node_label,
                collect(DISTINCT {
                    relation: type(r),
                    target: coalesce(related.name, related.question, related.title),
                    target_type: coalesce(related.entity_type, 'hotpot_node'),
                    target_labels: labels(related)
                }) as relations
        }
        RETURN DISTINCT 
            entity_name,
            entity_type,
            entity_text,
            node_label,
            relations
        LIMIT $limit
        """
        
        self.query_logger.debug(f"查询语句: {query[:200]}...")
        
        try:
            with self.driver.session() as session:
                self.query_logger.info("执行数据库查询...")
                
                result = session.run(query, {
                    'entity_names': entity_names,
                    'limit': self.top_k * len(entity_names)
                })
                
                entities = []
                for i, record in enumerate(result, 1):
                    entity = {
                        'name': record['entity_name'],
                        'type': record['entity_type'],
                        'text': record['entity_text'],
                        'node_label': record['node_label'],
                        'relations': [r for r in record['relations'] if r['target'] is not None]
                    }
                    entities.append(entity)
                    
                    self.query_logger.info(f"  实体 {i}: {entity['name']} ({entity['type']})")
                    self.query_logger.info(f"    节点类型: {entity['node_label']}")
                    self.query_logger.info(f"    关系数量: {len(entity['relations'])}")
                    
                    # 输出关系详情
                    for relation in entity['relations'][:3]:  # 只显示前3个关系
                        self.query_logger.info(f"    -> {relation['relation']}: {relation['target']}")
                
                elapsed_time = time.time() - start_time
                self.query_logger.info(f"查询完成: 找到 {len(entities)} 个实体，耗时 {elapsed_time:.2f}s")
                
                self._update_query_stats(elapsed_time, True)
                return entities
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.query_logger.error(f"实体查询失败: {e}")
            self._update_query_stats(elapsed_time, False)
            return []
    
    def query_entity_relationships_with_logging(self, entity_name: str, max_hops: int = 2) -> Dict:
        """带详细输出的关系查询"""
        self.query_logger.info(f"开始关系网络查询")
        self.query_logger.info(f"中心实体: {entity_name}")
        self.query_logger.info(f"最大跳数: {max_hops}")
        
        start_time = time.time()
        
        # 验证参数
        max_hops = self._validate_max_hops(max_hops)
        if max_hops != max_hops:
            self.query_logger.warning(f"最大跳数已调整为: {max_hops}")
        
        try:
            with self.driver.session() as session:
                # 分步骤执行查询
                self.query_logger.info("步骤 1: 查找中心实体...")
                center_entities = self._find_center_entities(session, entity_name)
                
                if not center_entities:
                    self.query_logger.warning(f"未找到中心实体: {entity_name}")
                    return self._empty_relationship_result(entity_name)
                
                self.query_logger.info(f"找到 {len(center_entities)} 个匹配的中心实体")
                
                all_paths = []
                all_entities = set()
                all_policies = set()
                all_hotpot_questions = set()
                all_hotpot_entities = set()
                
                for center_entity in center_entities:
                    self.query_logger.info(f"步骤 2: 探索实体 '{center_entity['name']}' 的关系网络...")
                    
                    # 执行路径查询
                    paths = self._query_entity_paths_with_logging(session, center_entity, max_hops)
                    all_paths.extend(paths)
                    
                    # 统计相关实体和政策
                    for path in paths:
                        for node in path.get('nodes', []):
                            node_labels = node.get('labels', [])
                            node_name = node.get('name', '')
                            
                            if 'Entity' in node_labels or 'HotpotEntity' in node_labels:
                                all_entities.add(node_name)
                            elif 'Policy' in node_labels:
                                all_policies.add(node_name)
                            elif 'HotpotQuestion' in node_labels:
                                all_hotpot_questions.add(node_name)
                            elif 'HotpotEntity' in node_labels:
                                all_hotpot_entities.add(node_name)
                
                elapsed_time = time.time() - start_time
                self.query_logger.info(f"关系网络查询完成:")
                self.query_logger.info(f"  发现路径: {len(all_paths)} 条")
                self.query_logger.info(f"  相关实体: {len(all_entities)} 个")
                self.query_logger.info(f"  相关政策: {len(all_policies)} 个")
                self.query_logger.info(f"  HotpotQA问题: {len(all_hotpot_questions)} 个")
                self.query_logger.info(f"  HotpotQA实体: {len(all_hotpot_entities)} 个")
                self.query_logger.info(f"  查询耗时: {elapsed_time:.2f}s")
                
                self._update_query_stats(elapsed_time, True)
                
                return {
                    'center_entity': entity_name,
                    'paths': all_paths,
                    'related_entities': list(all_entities),
                    'related_policies': list(all_policies),
                    'hotpot_questions': list(all_hotpot_questions),
                    'hotpot_entities': list(all_hotpot_entities),
                    'query_stats': {
                        'total_paths': len(all_paths),
                        'total_entities': len(all_entities),
                        'total_policies': len(all_policies),
                        'total_hotpot_questions': len(all_hotpot_questions),
                        'total_hotpot_entities': len(all_hotpot_entities),
                        'query_time': elapsed_time
                    }
                }
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.query_logger.error(f"关系查询失败: {e}")
            self._update_query_stats(elapsed_time, False)
            return self._empty_relationship_result(entity_name)
    
    def _find_center_entities(self, session, entity_name: str) -> List[Dict]:
        """查找中心实体"""
        query = """
        CALL {
            // 查找传统Entity节点
            MATCH (e:Entity) 
            WHERE e.name CONTAINS $entity_name OR e.text CONTAINS $entity_name
            RETURN e.name as name, e.type as type, 'Entity' as label, id(e) as node_id
            
            UNION
            
            // 查找HotpotEntity节点
            MATCH (he:HotpotEntity) 
            WHERE he.name CONTAINS $entity_name
            RETURN he.name as name, he.entity_type as type, 'HotpotEntity' as label, id(he) as node_id
        }
        RETURN DISTINCT name, type, label, node_id
        LIMIT 5
        """
        
        result = session.run(query, {'entity_name': entity_name.strip()})
        center_entities = []
        
        for record in result:
            center_entities.append({
                'name': record['name'],
                'type': record['type'],
                'label': record['label'],
                'node_id': record['node_id']
            })
            self.query_logger.info(f"  找到中心实体: {record['name']} ({record['label']})")
        
        return center_entities
    
    def _query_entity_paths_with_logging(self, session, center_entity: Dict, max_hops: int) -> List[Dict]:
        """查询实体路径并记录详细日志"""
        entity_label = center_entity['label']
        entity_name = center_entity['name']
        
        if entity_label == 'Entity':
            query = f"""
            MATCH (e:Entity) 
            WHERE e.name = $entity_name
            MATCH path = (e)-[*1..{max_hops}]-(related)
            WHERE related:Entity OR related:Policy OR related:Agency
            RETURN 
                [node in nodes(path) | {{
                    id: id(node),
                    labels: labels(node),
                    name: coalesce(node.name, node.title),
                    type: coalesce(node.type, 'unknown')
                }}] as path_nodes,
                [rel in relationships(path) | {{
                    type: type(rel),
                    properties: properties(rel)
                }}] as path_relations
            LIMIT 20
            """
        else:  # HotpotEntity
            query = f"""
            MATCH (he:HotpotEntity) 
            WHERE he.name = $entity_name
            MATCH path = (he)-[*1..{max_hops}]-(related)
            WHERE related:HotpotEntity OR related:HotpotQuestion OR related:HotpotParagraph OR related:HotpotSupportingFact
            RETURN 
                [node in nodes(path) | {{
                    id: id(node),
                    labels: labels(node),
                    name: coalesce(node.name, node.question, node.title, node.fact_text),
                    type: coalesce(node.entity_type, node.type, 'hotpot_node')
                }}] as path_nodes,
                [rel in relationships(path) | {{
                    type: type(rel),
                    properties: properties(rel)
                }}] as path_relations
            LIMIT 20
            """
        
        self.query_logger.info(f"  执行 {entity_label} 类型的路径查询...")
        
        result = session.run(query, {'entity_name': entity_name})
        paths = []
        
        for i, record in enumerate(result, 1):
            path_info = {
                'nodes': record['path_nodes'],
                'relations': record['path_relations']
            }
            paths.append(path_info)
            
            # 记录路径信息
            if i <= 3:  # 只记录前3条路径的详细信息
                self.query_logger.info(f"    路径 {i}: {len(path_info['nodes'])} 个节点, {len(path_info['relations'])} 个关系")
                
                # 显示路径概要
                node_names = [node.get('name', 'unknown')[:15] for node in path_info['nodes'][:3]]
                self.query_logger.info(f"      节点: {' -> '.join(node_names)}...")
        
        self.query_logger.info(f"  从实体 '{entity_name}' 找到 {len(paths)} 条路径")
        return paths
    
    def query_policies_by_entities_with_logging(self, entity_names: List[str]) -> List[Dict]:
        """带详细输出的政策查询"""
        self.query_logger.info(f"开始政策查询: {entity_names}")
        
        start_time = time.time()
        
        try:
            policies = self.query_policies_by_entities(entity_names)
            
            elapsed_time = time.time() - start_time
            self.query_logger.info(f"政策查询完成: 找到 {len(policies)} 个相关政策/问题，耗时 {elapsed_time:.2f}s")
            
            # 输出政策详情
            for i, policy in enumerate(policies[:3], 1):
                self.query_logger.info(f"  政策 {i}: {policy['title'][:50]}...")
                self.query_logger.info(f"    数据类型: {policy.get('data_type', 'unknown')}")
                self.query_logger.info(f"    发布机构: {policy.get('issuing_agency', 'unknown')}")
                self.query_logger.info(f"    相关实体: {len(policy.get('related_entities', []))} 个")
            
            self._update_query_stats(elapsed_time, True)
            return policies
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.query_logger.error(f"政策查询失败: {e}")
            self._update_query_stats(elapsed_time, False)
            return []
    
    def get_query_performance_stats(self) -> Dict:
        """获取查询性能统计"""
        return {
            'performance_stats': self.query_stats.copy(),
            'success_rate': (
                self.query_stats['successful_queries'] / max(self.query_stats['total_queries'], 1)
            ) * 100,
            'engine_type': 'EnhancedGraphQueryEngine'
        }


def test_graph_query():
    """测试图谱查询功能"""
    logging.basicConfig(level=logging.INFO)
    
    # 创建查询引擎
    query_engine = GraphQueryEngine()
    
    try:
        # 测试统计信息
        print("=== 图谱统计信息 ===")
        stats = query_engine.get_graph_statistics()
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        # 测试实体查询
        print("\n=== 实体查询测试 ===")
        entities = query_engine.query_entities_by_name(['企业', '投资'])
        print(f"找到 {len(entities)} 个相关实体")
        for entity in entities[:3]:
            print(f"  实体: {entity['name']} (类型: {entity['type']})")
            print(f"  关系数: {len(entity['relations'])}")
        
        # 测试政策查询
        print("\n=== 政策查询测试 ===")
        policies = query_engine.search_similar_policies('投资')
        print(f"找到 {len(policies)} 个相关政策")
        for policy in policies[:2]:
            print(f"  政策: {policy['title']}")
            print(f"  发布机构: {policy['agency']}")
        
    finally:
        query_engine.close()


if __name__ == "__main__":
    test_graph_query()