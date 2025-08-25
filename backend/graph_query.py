"""
图谱查询模块 - 基于Neo4j的知识图谱查询
支持实体查询、关系查询、路径查询等多种图谱操作
"""

import os
import logging
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
        """根据实体名称查询相关信息"""
        if not entity_names:
            return []
        
        query = """
        UNWIND $entity_names AS entity_name
        MATCH (e:Entity) 
        WHERE e.name CONTAINS entity_name OR e.text CONTAINS entity_name
        OPTIONAL MATCH (e)-[r]->(related:Entity)
        RETURN DISTINCT 
            e.name as entity_name,
            e.type as entity_type,
            e.text as entity_text,
            collect(DISTINCT {
                relation: type(r),
                target: related.name,
                target_type: related.type
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
                        'relations': [r for r in record['relations'] if r['target'] is not None]
                    }
                    entities.append(entity)
                
                logging.info(f"查询到 {len(entities)} 个相关实体")
                return entities
                
        except Exception as e:
            logging.error(f"实体查询失败: {e}")
            return []
    
    def query_policies_by_entities(self, entity_names: List[str]) -> List[Dict]:
        """根据实体查询相关政策文档"""
        if not entity_names:
            return []
        
        query = """
        UNWIND $entity_names AS entity_name
        MATCH (e:Entity)-[:MENTIONED_IN]->(p:Policy)
        WHERE e.name CONTAINS entity_name OR e.text CONTAINS entity_name
        OPTIONAL MATCH (p)-[:HAS_SECTION]->(s:Section)
        OPTIONAL MATCH (p)-[:ISSUED_BY]->(agency:Agency)
        RETURN DISTINCT
            p.title as policy_title,
            p.document_number as document_number,
            p.publish_date as publish_date,
            agency.name as issuing_agency,
            collect(DISTINCT s.title) as sections,
            collect(DISTINCT e.name) as related_entities
        ORDER BY p.publish_date DESC
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {
                    'entity_names': entity_names,
                    'limit': self.top_k
                })
                
                policies = []
                for record in result:
                    policy = {
                        'title': record['policy_title'],
                        'document_number': record['document_number'],
                        'publish_date': record['publish_date'],
                        'issuing_agency': record['issuing_agency'],
                        'sections': [s for s in record['sections'] if s],
                        'related_entities': [e for e in record['related_entities'] if e]
                    }
                    policies.append(policy)
                
                logging.info(f"查询到 {len(policies)} 个相关政策")
                return policies
                
        except Exception as e:
            logging.error(f"政策查询失败: {e}")
            return []
    
    def query_entity_relationships(self, entity_name: str, max_hops: int = 2) -> Dict:
        """查询实体的关系网络"""
        # 验证并修正max_hops参数
        max_hops = self._validate_max_hops(max_hops)
        
        if not entity_name or not entity_name.strip():
            logging.error("entity_name参数为空")
            return self._empty_relationship_result(entity_name)
        
        # 构建查询语句 - 使用字符串拼接而不是参数传递max_hops
        query = f"""
        MATCH (e:Entity) 
        WHERE e.name CONTAINS $entity_name OR e.text CONTAINS $entity_name
        MATCH path = (e)-[*1..{max_hops}]-(related)
        WHERE related:Entity OR related:Policy OR related:Agency
        RETURN 
            e.name as center_entity,
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
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {
                    'entity_name': entity_name.strip(),
                    'limit': 20
                })
                
                relationships = {
                    'center_entity': entity_name,
                    'paths': [],
                    'related_entities': set(),
                    'related_policies': set()
                }
                
                for record in result:
                    path_info = {
                        'nodes': record['path_nodes'],
                        'relations': record['path_relations']
                    }
                    relationships['paths'].append(path_info)
                    
                    # 收集相关实体和政策
                    for node in record['path_nodes']:
                        if 'Entity' in node['labels']:
                            relationships['related_entities'].add(node['name'])
                        elif 'Policy' in node['labels']:
                            relationships['related_policies'].add(node['name'])
                
                # 转换set为list
                relationships['related_entities'] = list(relationships['related_entities'])
                relationships['related_policies'] = list(relationships['related_policies'])
                
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
    
    def get_graph_statistics(self) -> Dict:
        """获取图谱统计信息"""
        queries = {
            'total_nodes': "MATCH (n) RETURN count(n) as count",
            'total_relationships': "MATCH ()-[r]->() RETURN count(r) as count",
            'policy_count': "MATCH (p:Policy) RETURN count(p) as count",
            'entity_count': "MATCH (e:Entity) RETURN count(e) as count",
            'agency_count': "MATCH (a:Agency) RETURN count(a) as count"
        }
        
        stats = {}
        
        try:
            with self.driver.session() as session:
                for stat_name, query in queries.items():
                    result = session.run(query)
                    record = result.single()
                    stats[stat_name] = record['count'] if record else 0
            
            logging.info("获取图谱统计信息成功")
            return stats
            
        except Exception as e:
            logging.error(f"获取图谱统计信息失败: {e}")
            return {}
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            logging.info("Neo4j连接已关闭")


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