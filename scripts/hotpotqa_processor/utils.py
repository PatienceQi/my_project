"""
HotpotQA处理器工具函数模块
提供数据验证、类型定义、置信度计算等工具函数
"""

import re
import json
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass


class HotpotQADataFormat(Enum):
    """HotpotQA数据格式类型"""
    TRAIN = "train"
    DEV = "dev"
    TEST = "test"
    CUSTOM = "custom"


class EntityType(Enum):
    """实体类型枚举"""
    PERSON = "PERSON"
    LOCATION = "LOCATION" 
    ORGANIZATION = "ORGANIZATION"
    WORK = "WORK"
    EVENT = "EVENT"
    DATE = "DATE"
    OTHER = "OTHER"


class RelationType(Enum):
    """关系类型枚举"""
    ACTED_IN = "ACTED_IN"
    STARRED_WITH = "STARRED_WITH"
    BORN_IN = "BORN_IN"
    WORKED_FOR = "WORKED_FOR"
    MEMBER_OF = "MEMBER_OF"
    LOCATED_IN = "LOCATED_IN"
    FOUNDED_BY = "FOUNDED_BY"
    DIRECTED_BY = "DIRECTED_BY"
    WRITTEN_BY = "WRITTEN_BY"
    SUPPORTS_ANSWER = "SUPPORTS_ANSWER"
    MENTIONS = "MENTIONS"
    RELATES_TO = "RELATES_TO"
    PART_OF = "PART_OF"


@dataclass
class Entity:
    """实体数据结构"""
    name: str
    entity_type: str
    description: str
    confidence: float
    source_sentence: Optional[str] = None
    normalized_name: Optional[str] = None
    
    def __post_init__(self):
        if self.normalized_name is None:
            self.normalized_name = normalize_entity_name(self.name)


@dataclass
class Relation:
    """关系数据结构"""
    source_entity: str
    target_entity: str
    relation_type: str
    confidence: float
    evidence_text: str
    question_id: Optional[str] = None


@dataclass
class SupportingFact:
    """支撑事实数据结构"""
    entity_name: str
    sentence_idx: int
    confidence: float
    text: Optional[str] = None


def validate_hotpotqa_data(data: Dict) -> bool:
    """
    验证HotpotQA数据格式
    
    Args:
        data: HotpotQA数据项
        
    Returns:
        bool: 数据是否有效
    """
    required_fields = ['_id', 'question', 'answer', 'supporting_facts', 'context']
    
    # 检查必需字段
    for field in required_fields:
        if field not in data:
            logging.warning(f"缺少必需字段: {field}")
            return False
    
    # 验证question和answer不为空
    if not data['question'].strip() or not data['answer'].strip():
        logging.warning("问题或答案为空")
        return False
    
    # 验证supporting_facts格式
    supporting_facts = data['supporting_facts']
    if not isinstance(supporting_facts, list):
        logging.warning("supporting_facts格式错误")
        return False
    
    for fact in supporting_facts:
        if not isinstance(fact, list) or len(fact) != 2:
            logging.warning("supporting_fact格式错误，应为[entity_name, sentence_idx]")
            return False
        
        entity_name, sentence_idx = fact
        if not isinstance(entity_name, str) or not isinstance(sentence_idx, int):
            logging.warning("supporting_fact类型错误")
            return False
    
    # 验证context格式
    context = data['context']
    if not isinstance(context, list):
        logging.warning("context格式错误")
        return False
    
    for ctx_item in context:
        if not isinstance(ctx_item, list) or len(ctx_item) != 2:
            logging.warning("context项格式错误，应为[title, sentences]")
            return False
        
        title, sentences = ctx_item
        if not isinstance(title, str) or not isinstance(sentences, list):
            logging.warning("context项类型错误")
            return False
    
    return True


def normalize_entity_name(entity_name: str) -> str:
    """
    标准化实体名称
    
    Args:
        entity_name: 原始实体名称
        
    Returns:
        str: 标准化后的实体名称
    """
    if not entity_name:
        return ""
    
    # 移除多余空格
    normalized = re.sub(r'\s+', ' ', entity_name.strip())
    
    # 移除括号内容（如果是描述性的）
    normalized = re.sub(r'\s*\([^)]*\)\s*', ' ', normalized)
    
    # 移除常见前缀
    prefixes = ['the ', 'The ', 'a ', 'A ', 'an ', 'An ']
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    
    # 再次清理空格
    normalized = normalized.strip()
    
    return normalized


def calculate_confidence_score(
    entity: str, 
    context: str, 
    supporting_facts: List[Tuple[str, int]],
    answer: str
) -> float:
    """
    计算实体或关系的置信度分数
    
    Args:
        entity: 实体名称
        context: 上下文文本
        supporting_facts: 支撑事实列表
        answer: 答案文本
        
    Returns:
        float: 置信度分数 (0-1)
    """
    score = 0.5  # 基础分数
    
    # 如果实体在支撑事实中，增加置信度
    for fact_entity, _ in supporting_facts:
        if entity.lower() in fact_entity.lower() or fact_entity.lower() in entity.lower():
            score += 0.3
            break
    
    # 如果实体在答案中，增加置信度
    if entity.lower() in answer.lower():
        score += 0.2
    
    # 根据实体在上下文中的出现频率调整
    entity_count = context.lower().count(entity.lower())
    if entity_count > 2:
        score += 0.1
    elif entity_count == 0:
        score -= 0.2
    
    # 确保分数在合理范围内
    return max(0.1, min(1.0, score))


def extract_entity_from_title(title: str) -> Optional[Entity]:
    """
    从标题中提取主要实体
    
    Args:
        title: 段落标题
        
    Returns:
        Entity or None: 提取的实体
    """
    if not title or len(title.strip()) < 2:
        return None
    
    # 基本清理
    cleaned_title = title.strip()
    
    # 尝试识别实体类型
    entity_type = classify_entity_by_title(cleaned_title)
    
    return Entity(
        name=cleaned_title,
        entity_type=entity_type.value,
        description=f"实体来源于段落标题: {title}",
        confidence=0.9,  # 标题实体通常有较高置信度
        normalized_name=normalize_entity_name(cleaned_title)
    )


def classify_entity_by_title(title: str) -> EntityType:
    """
    根据标题特征分类实体类型
    
    Args:
        title: 标题文本
        
    Returns:
        EntityType: 实体类型
    """
    title_lower = title.lower()
    
    # 人名模式
    person_patterns = [
        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
        r'\b[A-Z]\. [A-Z][a-z]+\b',       # A. Last
    ]
    
    for pattern in person_patterns:
        if re.search(pattern, title):
            return EntityType.PERSON
    
    # 地点模式
    location_keywords = ['city', 'state', 'country', 'county', 'province', 'district']
    if any(keyword in title_lower for keyword in location_keywords):
        return EntityType.LOCATION
    
    # 组织模式
    org_keywords = ['company', 'corporation', 'university', 'school', 'institute', 'association']
    if any(keyword in title_lower for keyword in org_keywords):
        return EntityType.ORGANIZATION
    
    # 作品模式
    work_keywords = ['film', 'movie', 'book', 'novel', 'album', 'song', 'series']
    if any(keyword in title_lower for keyword in work_keywords):
        return EntityType.WORK
    
    # 默认为其他类型
    return EntityType.OTHER


def build_reasoning_path(
    question_entities: List[str],
    answer_entities: List[str], 
    relations: List[Relation]
) -> List[Tuple[str, str, str]]:
    """
    构建推理路径
    
    Args:
        question_entities: 问题中的实体
        answer_entities: 答案中的实体
        relations: 关系列表
        
    Returns:
        List[Tuple[str, str, str]]: 推理路径 [(source, relation, target), ...]
    """
    reasoning_paths = []
    
    # 构建实体关系图
    entity_graph = {}
    for relation in relations:
        source = relation.source_entity
        target = relation.target_entity
        rel_type = relation.relation_type
        
        if source not in entity_graph:
            entity_graph[source] = []
        entity_graph[source].append((target, rel_type))
    
    # 查找从问题实体到答案实体的路径
    for q_entity in question_entities:
        for a_entity in answer_entities:
            path = find_shortest_path(entity_graph, q_entity, a_entity)
            if path:
                reasoning_paths.extend(path)
    
    return reasoning_paths


def find_shortest_path(
    graph: Dict[str, List[Tuple[str, str]]], 
    start: str, 
    end: str,
    max_depth: int = 3
) -> List[Tuple[str, str, str]]:
    """
    查找两个实体间的最短路径
    
    Args:
        graph: 实体关系图
        start: 起始实体
        end: 目标实体
        max_depth: 最大搜索深度
        
    Returns:
        List[Tuple[str, str, str]]: 路径中的关系三元组
    """
    if start == end:
        return []
    
    # BFS搜索
    queue = [(start, [])]
    visited = {start}
    
    while queue:
        current_entity, path = queue.pop(0)
        
        if len(path) >= max_depth:
            continue
        
        if current_entity in graph:
            for next_entity, relation in graph[current_entity]:
                if next_entity == end:
                    # 找到目标，返回路径
                    return path + [(current_entity, relation, next_entity)]
                
                if next_entity not in visited:
                    visited.add(next_entity)
                    queue.append((next_entity, path + [(current_entity, relation, next_entity)]))
    
    return []  # 未找到路径


def merge_duplicate_entities(entities: List[Entity]) -> List[Entity]:
    """
    合并重复实体
    
    Args:
        entities: 实体列表
        
    Returns:
        List[Entity]: 去重后的实体列表
    """
    merged = {}
    
    for entity in entities:
        normalized_name = entity.normalized_name or normalize_entity_name(entity.name)
        
        if normalized_name in merged:
            # 保留置信度更高的实体
            if entity.confidence > merged[normalized_name].confidence:
                merged[normalized_name] = entity
        else:
            merged[normalized_name] = entity
    
    return list(merged.values())


def validate_relation_consistency(
    relations: List[Relation],
    entities: List[Entity]
) -> List[Relation]:
    """
    验证关系一致性
    
    Args:
        relations: 关系列表
        entities: 实体列表
        
    Returns:
        List[Relation]: 验证后的关系列表
    """
    entity_names = {entity.normalized_name or normalize_entity_name(entity.name) 
                   for entity in entities}
    
    valid_relations = []
    
    for relation in relations:
        source_normalized = normalize_entity_name(relation.source_entity)
        target_normalized = normalize_entity_name(relation.target_entity)
        
        # 检查源实体和目标实体是否存在
        if source_normalized in entity_names and target_normalized in entity_names:
            valid_relations.append(relation)
        else:
            logging.warning(f"关系验证失败: {relation.source_entity} -> {relation.target_entity}")
    
    return valid_relations


def format_for_neo4j(data: Any) -> str:
    """
    格式化数据用于Neo4j查询
    
    Args:
        data: 要格式化的数据
        
    Returns:
        str: 格式化后的字符串
    """
    if isinstance(data, str):
        # 转义特殊字符
        escaped = data.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
        return f'"{escaped}"'
    elif isinstance(data, (int, float)):
        return str(data)
    elif isinstance(data, bool):
        return str(data).lower()
    elif data is None:
        return 'null'
    else:
        return f'"{str(data)}"'


def log_processing_stats(
    processed_questions: int,
    total_entities: int,
    total_relations: int,
    failed_questions: int
):
    """
    记录处理统计信息
    
    Args:
        processed_questions: 已处理问题数量
        total_entities: 总实体数量
        total_relations: 总关系数量
        failed_questions: 失败问题数量
    """
    success_rate = (processed_questions - failed_questions) / processed_questions * 100
    avg_entities = total_entities / processed_questions if processed_questions > 0 else 0
    avg_relations = total_relations / processed_questions if processed_questions > 0 else 0
    
    logging.info("=== HotpotQA处理统计 ===")
    logging.info(f"处理问题数量: {processed_questions}")
    logging.info(f"成功率: {success_rate:.1f}%")
    logging.info(f"失败问题数量: {failed_questions}")
    logging.info(f"总实体数量: {total_entities}")
    logging.info(f"总关系数量: {total_relations}")
    logging.info(f"平均实体/问题: {avg_entities:.1f}")
    logging.info(f"平均关系/问题: {avg_relations:.1f}")
    logging.info("========================")