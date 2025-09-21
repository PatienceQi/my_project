"""
HotpotQA图构建器

负责将提取的实体关系转换为Neo4j图结构。
创建HotpotQuestion、HotpotEntity、HotpotParagraph等节点类型，
并建立相应的关系边。
"""

import logging
import time
from typing import List, Dict, Any, Optional, Set
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class HotpotQAGraphBuilder:
    """HotpotQA图构建器"""
    
    def __init__(self, neo4j_uri: str = None, neo4j_user: str = None, neo4j_password: str = None):
        # 从环境变量获取Neo4j连接信息
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = neo4j_user or os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD", "password")
        
        self.logger = logging.getLogger(__name__)
        
        # 记录连接信息（隐藏密码）
        self.logger.info(f"尝试连接Neo4j: {self.neo4j_uri}, 用户: {self.neo4j_user}")
        
        # 初始化Neo4j连接
        try:
            self.driver = GraphDatabase.driver(
                self.neo4j_uri, 
                auth=(self.neo4j_user, self.neo4j_password)
            )
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.logger.info("Neo4j连接成功")
        except Exception as e:
            self.logger.error(f"Neo4j连接失败: {e}")
            raise
        
        # 统计信息
        self.stats = {
            'total_questions_created': 0,
            'total_entities_created': 0,
            'total_paragraphs_created': 0,
            'total_supporting_facts_created': 0,
            'total_relations_created': 0,
            'total_graphs_built': 0,
            'avg_build_time': 0.0
        }
        
        # 创建索引
        self._create_indexes()
    
    def _create_indexes(self):
        """创建必要的数据库索引"""
        indexes = [
            "CREATE INDEX hotpot_question_id IF NOT EXISTS FOR (q:HotpotQuestion) ON (q.question_id)",
            "CREATE INDEX hotpot_entity_id IF NOT EXISTS FOR (e:HotpotEntity) ON (e.entity_id)",
            "CREATE INDEX hotpot_entity_name IF NOT EXISTS FOR (e:HotpotEntity) ON (e.name)",
            "CREATE INDEX hotpot_paragraph_id IF NOT EXISTS FOR (p:HotpotParagraph) ON (p.paragraph_id)",
            "CREATE INDEX hotpot_fact_id IF NOT EXISTS FOR (f:HotpotSupportingFact) ON (f.fact_id)"
        ]
        
        try:
            with self.driver.session() as session:
                for index_query in indexes:
                    session.run(index_query)
            self.logger.info("数据库索引创建完成")
        except Exception as e:
            self.logger.warning(f"创建索引时出现警告: {e}")
    
    def build_question_graph(self, question_data: Dict[str, Any], extraction_result: Dict[str, Any]) -> str:
        """
        构建问题图谱
        
        Args:
            question_data: 预处理后的问题数据
            extraction_result: 实体关系提取结果
            
        Returns:
            创建的问题节点ID
        """
        start_time = time.time()
        
        try:
            with self.driver.session() as session:
                # 开启事务
                with session.begin_transaction() as tx:
                    # 1. 创建问题节点
                    question_id = self.create_hotpot_question_node(tx, question_data)
                    
                    # 2. 创建实体节点
                    entity_ids = self.create_hotpot_entity_nodes(tx, extraction_result['entities'])
                    
                    # 3. 创建段落节点
                    paragraph_ids = self.create_hotpot_paragraph_nodes(tx, question_data['paragraphs'])
                    
                    # 4. 创建支持事实节点
                    fact_ids = self.create_supporting_fact_nodes(tx, question_data['supporting_facts'])
                    
                    # 5. 建立关系
                    self.establish_relationships(tx, {
                        'question_id': question_id,
                        'entity_ids': entity_ids,
                        'paragraph_ids': paragraph_ids,
                        'fact_ids': fact_ids,
                        'entities': extraction_result['entities'],
                        'relations': extraction_result['relations']
                    })
                    
                    # 提交事务
                    tx.commit()
            
            # 更新统计信息
            build_time = time.time() - start_time
            self.stats['total_graphs_built'] += 1
            self._update_avg_build_time(build_time)
            
            self.logger.info(
                f"成功构建问题图谱 {question_data['question_id']}: "
                f"{len(entity_ids)} 个实体, {len(paragraph_ids)} 个段落, "
                f"{len(fact_ids)} 个支持事实, 用时 {build_time:.2f}s"
            )
            
            return question_id
            
        except Exception as e:
            self.logger.error(f"构建问题图谱失败 {question_data['question_id']}: {e}")
            raise
    
    def create_hotpot_question_node(self, tx, question_data: Dict[str, Any]) -> str:
        """创建HotpotQuestion节点"""
        try:
            query = """
            CREATE (q:HotpotQuestion {
                question_id: $question_id,
                question: $question,
                answer: $answer,
                level: $level,
                type: $type,
                created_at: datetime()
            })
            RETURN q.question_id as question_id
            """
            
            result = tx.run(query, {
                'question_id': question_data['question_id'],
                'question': question_data['question'],
                'answer': question_data['answer'],
                'level': question_data.get('level', 'unknown'),
                'type': question_data.get('type', 'unknown')
            })
            
            record = result.single()
            question_id = record['question_id']
            
            self.stats['total_questions_created'] += 1
            return question_id
            
        except Exception as e:
            self.logger.error(f"创建问题节点失败: {e}")
            raise
    
    def create_hotpot_entity_nodes(self, tx, entities: List[Dict[str, Any]]) -> List[str]:
        """创建HotpotEntity节点"""
        if not entities:
            return []
        
        entity_ids = []
        
        for entity in entities:
            try:
                # 检查实体是否已存在
                check_query = """
                MATCH (e:HotpotEntity {name: $name})
                RETURN e.entity_id as entity_id
                """
                
                check_result = tx.run(check_query, {'name': entity['name']})
                existing = check_result.single()
                
                if existing:
                    # 实体已存在，更新置信度
                    entity_id = existing['entity_id']
                    update_query = """
                    MATCH (e:HotpotEntity {entity_id: $entity_id})
                    SET e.confidence = CASE 
                        WHEN e.confidence < $confidence THEN $confidence 
                        ELSE e.confidence 
                    END,
                    e.aliases = e.aliases + $new_aliases
                    RETURN e.entity_id as entity_id
                    """
                    
                    tx.run(update_query, {
                        'entity_id': entity_id,
                        'confidence': entity['confidence'],
                        'new_aliases': entity.get('aliases', [])
                    })
                else:
                    # 创建新实体
                    create_query = """
                    CREATE (e:HotpotEntity {
                        entity_id: $entity_id,
                        name: $name,
                        entity_type: $entity_type,
                        confidence: $confidence,
                        aliases: $aliases,
                        source_context: $source_context,
                        created_at: datetime()
                    })
                    RETURN e.entity_id as entity_id
                    """
                    
                    result = tx.run(create_query, {
                        'entity_id': entity['entity_id'],
                        'name': entity['name'],
                        'entity_type': entity['entity_type'],
                        'confidence': entity['confidence'],
                        'aliases': entity.get('aliases', []),
                        'source_context': entity.get('source_context', '')
                    })
                    
                    record = result.single()
                    entity_id = record['entity_id']
                    self.stats['total_entities_created'] += 1
                
                entity_ids.append(entity_id)
                
            except Exception as e:
                self.logger.warning(f"创建实体节点失败 {entity.get('name', 'unknown')}: {e}")
                continue
        
        return entity_ids
    
    def create_hotpot_paragraph_nodes(self, tx, paragraphs: List[Dict[str, Any]]) -> List[str]:
        """创建HotpotParagraph节点"""
        if not paragraphs:
            return []
        
        paragraph_ids = []
        
        for paragraph in paragraphs:
            try:
                query = """
                CREATE (p:HotpotParagraph {
                    paragraph_id: $paragraph_id,
                    title: $title,
                    text: $text,
                    order: $order,
                    source_index: $source_index,
                    created_at: datetime()
                })
                RETURN p.paragraph_id as paragraph_id
                """
                
                result = tx.run(query, {
                    'paragraph_id': paragraph['paragraph_id'],
                    'title': paragraph['title'],
                    'text': paragraph['text'],
                    'order': paragraph['order'],
                    'source_index': paragraph.get('source_index', 0)
                })
                
                record = result.single()
                paragraph_id = record['paragraph_id']
                paragraph_ids.append(paragraph_id)
                
                self.stats['total_paragraphs_created'] += 1
                
            except Exception as e:
                self.logger.warning(f"创建段落节点失败 {paragraph.get('paragraph_id', 'unknown')}: {e}")
                continue
        
        return paragraph_ids
    
    def create_supporting_fact_nodes(self, tx, supporting_facts: List[Dict[str, Any]]) -> List[str]:
        """创建HotpotSupportingFact节点"""
        if not supporting_facts:
            return []
        
        fact_ids = []
        
        for fact in supporting_facts:
            try:
                query = """
                CREATE (f:HotpotSupportingFact {
                    fact_id: $fact_id,
                    title: $title,
                    sentence_id: $sentence_id,
                    fact_text: $fact_text,
                    relevance_score: $relevance_score,
                    created_at: datetime()
                })
                RETURN f.fact_id as fact_id
                """
                
                result = tx.run(query, {
                    'fact_id': fact['fact_id'],
                    'title': fact['title'],
                    'sentence_id': fact['sentence_id'],
                    'fact_text': fact.get('fact_text', ''),
                    'relevance_score': fact['relevance_score']
                })
                
                record = result.single()
                fact_id = record['fact_id']
                fact_ids.append(fact_id)
                
                self.stats['total_supporting_facts_created'] += 1
                
            except Exception as e:
                self.logger.warning(f"创建支持事实节点失败 {fact.get('fact_id', 'unknown')}: {e}")
                continue
        
        return fact_ids
    
    def establish_relationships(self, tx, graph_data: Dict) -> bool:
        """建立图谱关系"""
        try:
            # 1. 建立问题-实体关系
            self._create_question_entity_links(tx, graph_data['question_id'], graph_data['entity_ids'])
            
            # 2. 建立段落-实体关系
            self._create_paragraph_entity_links(tx, graph_data['paragraph_ids'], graph_data['entities'])
            
            # 3. 建立问题-段落关系
            self._create_question_paragraph_links(tx, graph_data['question_id'], graph_data['paragraph_ids'])
            
            # 4. 建立问题-支持事实关系
            self._create_question_fact_links(tx, graph_data['question_id'], graph_data['fact_ids'])
            
            # 5. 建立实体-实体关系
            self._create_entity_relations(tx, graph_data['relations'])
            
            return True
            
        except Exception as e:
            self.logger.error(f"建立关系失败: {e}")
            raise
    
    def _create_question_entity_links(self, tx, question_id: str, entity_ids: List[str]):
        """建立问题-实体关系"""
        if not entity_ids:
            return
        
        query = """
        MATCH (q:HotpotQuestion {question_id: $question_id})
        MATCH (e:HotpotEntity)
        WHERE e.entity_id IN $entity_ids
        CREATE (q)-[:HAS_ENTITY]->(e)
        """
        
        tx.run(query, {'question_id': question_id, 'entity_ids': entity_ids})
        self.stats['total_relations_created'] += len(entity_ids)
    
    def _create_paragraph_entity_links(self, tx, paragraph_ids: List[str], entities: List[Dict]):
        """建立段落-实体关系"""
        if not paragraph_ids or not entities:
            return
        
        # 根据实体的源段落建立关系
        for entity in entities:
            source_paragraph = entity.get('source_paragraph')
            if source_paragraph:
                query = """
                MATCH (p:HotpotParagraph {paragraph_id: $paragraph_id})
                MATCH (e:HotpotEntity {entity_id: $entity_id})
                CREATE (p)-[:MENTIONS]->(e)
                """
                
                try:
                    tx.run(query, {
                        'paragraph_id': source_paragraph,
                        'entity_id': entity['entity_id']
                    })
                    self.stats['total_relations_created'] += 1
                except Exception as e:
                    self.logger.warning(f"建立段落-实体关系失败: {e}")
    
    def _create_question_paragraph_links(self, tx, question_id: str, paragraph_ids: List[str]):
        """建立问题-段落关系"""
        if not paragraph_ids:
            return
        
        query = """
        MATCH (q:HotpotQuestion {question_id: $question_id})
        MATCH (p:HotpotParagraph)
        WHERE p.paragraph_id IN $paragraph_ids
        CREATE (q)-[:HAS_CONTEXT]->(p)
        """
        
        tx.run(query, {'question_id': question_id, 'paragraph_ids': paragraph_ids})
        self.stats['total_relations_created'] += len(paragraph_ids)
    
    def _create_question_fact_links(self, tx, question_id: str, fact_ids: List[str]):
        """建立问题-支持事实关系"""
        if not fact_ids:
            return
        
        query = """
        MATCH (q:HotpotQuestion {question_id: $question_id})
        MATCH (f:HotpotSupportingFact)
        WHERE f.fact_id IN $fact_ids
        CREATE (q)-[:SUPPORTS_ANSWER]->(f)
        """
        
        tx.run(query, {'question_id': question_id, 'fact_ids': fact_ids})
        self.stats['total_relations_created'] += len(fact_ids)
    
    def _create_entity_relations(self, tx, relations: List[Dict]):
        """建立实体-实体关系"""
        if not relations:
            return
        
        for relation in relations:
            try:
                query = """
                MATCH (e1:HotpotEntity {name: $source})
                MATCH (e2:HotpotEntity {name: $target})
                CREATE (e1)-[:RELATED_TO {
                    relation_type: $relation_type,
                    confidence: $confidence,
                    description: $description
                }]->(e2)
                """
                
                tx.run(query, {
                    'source': relation['source'],
                    'target': relation['target'],
                    'relation_type': relation['relation_type'],
                    'confidence': relation['confidence'],
                    'description': relation.get('description', '')
                })
                
                self.stats['total_relations_created'] += 1
                
            except Exception as e:
                self.logger.warning(f"建立实体关系失败 {relation.get('source')} -> {relation.get('target')}: {e}")
    
    def optimize_graph_structure(self) -> Dict[str, Any]:
        """优化图结构 - 修复Neo4j 5.x语法兼容性"""
        try:
            optimization_results = {}
            
            with self.driver.session() as session:
                # 1. 移除孤立节点
                orphan_query = """
                MATCH (n:HotpotEntity)
                WHERE NOT (n)--()
                DELETE n
                RETURN COUNT(n) as orphan_count
                """
                result = session.run(orphan_query)
                optimization_results['orphan_entities_removed'] = result.single()['orphan_count']
                
                # 2. 合并相似实体
                # 这里可以添加更复杂的实体合并逻辑
                
                # 3. 更新实体重要性评分 - 修复后的Cypher语法
                importance_query = """
                MATCH (e:HotpotEntity)
                SET e.importance = 
                    size([(e)<-[:HAS_ENTITY]-(:HotpotQuestion) | 1]) * 2 +
                    size([(e)<-[:MENTIONS]-(:HotpotParagraph) | 1]) +
                    size([(e)-[:RELATED_TO]-(:HotpotEntity) | 1])
                RETURN COUNT(e) as updated_count
                """
                result = session.run(importance_query)
                optimization_results['importance_scores_updated'] = result.single()['updated_count']
            
            self.logger.info(f"图结构优化完成: {optimization_results}")
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"优化图结构失败: {e}")
            return {}
    
    def clear_hotpotqa_data(self, confirm: bool = False) -> bool:
        """清除HotpotQA数据"""
        if not confirm:
            self.logger.warning("清除数据需要确认参数")
            return False
        
        try:
            with self.driver.session() as session:
                # 删除所有HotpotQA相关节点和关系
                queries = [
                    "MATCH (q:HotpotQuestion) DETACH DELETE q",
                    "MATCH (e:HotpotEntity) DETACH DELETE e", 
                    "MATCH (p:HotpotParagraph) DETACH DELETE p",
                    "MATCH (f:HotpotSupportingFact) DETACH DELETE f"
                ]
                
                for query in queries:
                    session.run(query)
            
            # 重置统计信息
            self.stats = {
                'total_questions_created': 0,
                'total_entities_created': 0,
                'total_paragraphs_created': 0,
                'total_supporting_facts_created': 0,
                'total_relations_created': 0,
                'total_graphs_built': 0,
                'avg_build_time': 0.0
            }
            
            self.logger.info("HotpotQA数据清除完成")
            return True
            
        except Exception as e:
            self.logger.error(f"清除数据失败: {e}")
            return False
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        try:
            with self.driver.session() as session:
                stats_queries = {
                    'hotpot_questions': "MATCH (q:HotpotQuestion) RETURN COUNT(q) as count",
                    'hotpot_entities': "MATCH (e:HotpotEntity) RETURN COUNT(e) as count",
                    'hotpot_paragraphs': "MATCH (p:HotpotParagraph) RETURN COUNT(p) as count",
                    'hotpot_supporting_facts': "MATCH (f:HotpotSupportingFact) RETURN COUNT(f) as count",
                    'has_entity_relations': "MATCH ()-[r:HAS_ENTITY]->() RETURN COUNT(r) as count",
                    'mentions_relations': "MATCH ()-[r:MENTIONS]->() RETURN COUNT(r) as count",
                    'related_to_relations': "MATCH ()-[r:RELATED_TO]->() RETURN COUNT(r) as count"
                }
                
                graph_stats = {}
                for key, query in stats_queries.items():
                    result = session.run(query)
                    graph_stats[key] = result.single()['count']
                
                # 添加构建统计信息
                graph_stats.update(self.stats)
                
                return graph_stats
                
        except Exception as e:
            self.logger.error(f"获取图谱统计失败: {e}")
            return self.stats
    
    def _update_avg_build_time(self, build_time: float):
        """更新平均构建时间"""
        total_time = self.stats['avg_build_time'] * (self.stats['total_graphs_built'] - 1)
        self.stats['avg_build_time'] = (total_time + build_time) / self.stats['total_graphs_built']
    
    def close(self):
        """关闭Neo4j连接"""
        if hasattr(self, 'driver'):
            self.driver.close()
            self.logger.info("Neo4j连接已关闭")