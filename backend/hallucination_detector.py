"""
幻觉检测模块 - 基于知识图谱的答案验证
通过实体验证、关系验证、内容对比等多维度检测答案中的潜在幻觉
"""

import os
import logging
import re
from typing import List, Dict, Tuple, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class HallucinationDetector:
    """幻觉检测器 - 基于知识图谱验证"""
    
    def __init__(self, graph_query_engine, entity_extractor):
        """
        初始化幻觉检测器
        
        Args:
            graph_query_engine: 图谱查询引擎实例
            entity_extractor: 实体提取器实例
        """
        self.graph_query = graph_query_engine
        self.entity_extractor = entity_extractor
        self.hallucination_threshold = float(os.getenv('HALLUCINATION_THRESHOLD', 0.7))
        
        # 权重配置
        self.weights = {
            'entity_consistency': 0.4,    # 实体一致性权重
            'relation_verification': 0.3,  # 关系验证权重
            'content_overlap': 0.2,        # 内容重叠权重
            'semantic_coherence': 0.1      # 语义连贯性权重
        }
        
        logging.info("幻觉检测器初始化完成")
    
    def detect_hallucination(self, answer: str, question: str, retrieved_docs: List[Dict], 
                           graph_context: Dict) -> Dict:
        """
        检测答案中的潜在幻觉
        
        Args:
            answer: 生成的答案
            question: 原始问题
            retrieved_docs: 检索到的相关文档
            graph_context: 图谱查询上下文
            
        Returns:
            检测结果字典
        """
        try:
            # 1. 实体一致性检查
            entity_score = self._check_entity_consistency(answer, graph_context)
            
            # 2. 关系验证检查
            relation_score = self._verify_relations(answer, graph_context)
            
            # 3. 内容重叠度检查
            content_score = self._check_content_overlap(answer, retrieved_docs)
            
            # 4. 语义连贯性检查
            coherence_score = self._check_semantic_coherence(answer, question)
            
            # 计算综合可信度
            confidence = (
                entity_score * self.weights['entity_consistency'] +
                relation_score * self.weights['relation_verification'] +
                content_score * self.weights['content_overlap'] +
                coherence_score * self.weights['semantic_coherence']
            )
            
            # 确定风险等级
            risk_level = self._determine_risk_level(confidence)
            
            # 生成警告信息
            warnings = self._generate_warnings(entity_score, relation_score, content_score, coherence_score)
            
            result = {
                'confidence': round(confidence, 3),
                'risk_level': risk_level,
                'is_reliable': confidence >= self.hallucination_threshold,
                'detailed_scores': {
                    'entity_consistency': round(entity_score, 3),
                    'relation_verification': round(relation_score, 3),
                    'content_overlap': round(content_score, 3),
                    'semantic_coherence': round(coherence_score, 3)
                },
                'warnings': warnings
            }
            
            logging.info(f"幻觉检测完成 - 可信度: {confidence:.3f}, 风险等级: {risk_level}")
            return result
            
        except Exception as e:
            logging.error(f"幻觉检测失败: {e}")
            return {
                'confidence': 0.0,
                'risk_level': 'high',
                'is_reliable': False,
                'detailed_scores': {},
                'warnings': ['检测系统异常，无法验证答案可信度']
            }
    
    def _check_entity_consistency(self, answer: str, graph_context: Dict) -> float:
        """检查实体一致性"""
        try:
            # 从答案中提取实体
            answer_entities = self.entity_extractor.extract_entities_from_question(answer)
            
            if not answer_entities:
                return 0.5  # 没有提取到实体，给中等分数
            
            # 获取图谱中的已知实体
            known_entities = set()
            
            # 从图谱上下文中收集已知实体
            if 'entities' in graph_context:
                for entity in graph_context['entities']:
                    if isinstance(entity, dict) and 'name' in entity:
                        known_entities.add(entity['name'].lower())
                    elif isinstance(entity, str):
                        known_entities.add(entity.lower())
            
            if 'policies' in graph_context:
                for policy in graph_context['policies']:
                    if isinstance(policy, dict):
                        # 添加政策中的实体
                        if 'related_entities' in policy:
                            for entity in policy['related_entities']:
                                known_entities.add(entity.lower())
            
            # 计算实体匹配度
            verified_entities = 0
            total_entities = len(answer_entities)
            
            for entity in answer_entities:
                entity_lower = entity.lower()
                
                # 检查完全匹配
                if entity_lower in known_entities:
                    verified_entities += 1
                    continue
                
                # 检查部分匹配
                for known_entity in known_entities:
                    if (entity_lower in known_entity or known_entity in entity_lower) and len(entity_lower) > 2:
                        verified_entities += 0.5
                        break
            
            consistency_score = verified_entities / total_entities if total_entities > 0 else 0.5
            
            logging.debug(f"实体一致性: {verified_entities}/{total_entities} = {consistency_score:.3f}")
            return min(1.0, consistency_score)
            
        except Exception as e:
            logging.error(f"实体一致性检查失败: {e}")
            return 0.3
    
    def _verify_relations(self, answer: str, graph_context: Dict) -> float:
        """验证关系的正确性"""
        try:
            # 从答案中提取简单的主谓宾关系
            relations = self._extract_simple_relations(answer)
            
            if not relations:
                return 0.5  # 没有明显关系表述，给中等分数
            
            verified_relations = 0
            total_relations = len(relations)
            
            # 检查关系是否在图谱中存在
            for relation in relations:
                subject = relation['subject']
                predicate = relation['predicate']
                object_entity = relation['object']
                
                # 使用图谱查询验证关系
                if self._verify_relation_in_graph(subject, object_entity, predicate):
                    verified_relations += 1
            
            relation_score = verified_relations / total_relations if total_relations > 0 else 0.5
            
            logging.debug(f"关系验证: {verified_relations}/{total_relations} = {relation_score:.3f}")
            return relation_score
            
        except Exception as e:
            logging.error(f"关系验证失败: {e}")
            return 0.4
    
    def _check_content_overlap(self, answer: str, retrieved_docs: List[Dict]) -> float:
        """检查内容重叠度"""
        try:
            if not retrieved_docs:
                return 0.3  # 没有参考文档，分数较低
            
            # 获取答案中的关键词
            answer_keywords = self._extract_keywords(answer)
            
            if not answer_keywords:
                return 0.3
            
            # 计算与检索文档的重叠度
            total_overlap = 0
            doc_count = 0
            
            for doc in retrieved_docs:
                doc_content = doc.get('document', '') or doc.get('content', '')
                if not doc_content:
                    continue
                
                doc_keywords = self._extract_keywords(doc_content)
                
                if doc_keywords:
                    overlap = len(answer_keywords.intersection(doc_keywords))
                    overlap_ratio = overlap / len(answer_keywords)
                    total_overlap += overlap_ratio
                    doc_count += 1
            
            if doc_count == 0:
                return 0.3
            
            content_score = total_overlap / doc_count
            
            logging.debug(f"内容重叠度: {content_score:.3f}")
            return min(1.0, content_score)
            
        except Exception as e:
            logging.error(f"内容重叠检查失败: {e}")
            return 0.3
    
    def _check_semantic_coherence(self, answer: str, question: str) -> float:
        """检查语义连贯性"""
        try:
            # 基本长度检查
            if len(answer.strip()) < 10:
                return 0.2  # 答案太短
            
            # 检查是否回答了问题
            question_keywords = self._extract_keywords(question)
            answer_keywords = self._extract_keywords(answer)
            
            if not question_keywords or not answer_keywords:
                return 0.4
            
            # 计算问题和答案的关键词重叠
            overlap = len(question_keywords.intersection(answer_keywords))
            relevance_score = overlap / len(question_keywords) if question_keywords else 0
            
            # 检查逻辑连贯性（简单的启发式规则）
            coherence_indicators = 0
            
            # 检查是否有逻辑连接词
            logical_connectors = ['因为', '所以', '由于', '因此', '根据', '按照', '依据']
            for connector in logical_connectors:
                if connector in answer:
                    coherence_indicators += 1
            
            # 检查是否有具体信息
            if any(keyword in answer for keyword in ['规定', '要求', '政策', '条款', '办法']):
                coherence_indicators += 1
            
            # 综合评分
            coherence_score = (relevance_score + min(coherence_indicators / 5, 0.5)) / 1.5
            
            logging.debug(f"语义连贯性: {coherence_score:.3f}")
            return min(1.0, coherence_score)
            
        except Exception as e:
            logging.error(f"语义连贯性检查失败: {e}")
            return 0.4
    
    def _extract_keywords(self, text: str) -> set:
        """提取文本关键词"""
        # 简单的关键词提取（可以用更复杂的NLP方法替代）
        import jieba
        
        # 中文分词
        words = jieba.lcut(text)
        
        # 过滤停用词和标点
        stop_words = {'的', '了', '在', '是', '有', '和', '与', '或', '等', '及', '以及', 
                     '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
                     '年', '月', '日', '号', '第', '条', '款', '项', '、', '，', '。', 
                     '？', '！', '：', '；', '"', '"', ''', '''}
        
        keywords = set()
        for word in words:
            word = word.strip()
            if len(word) > 1 and word not in stop_words and not word.isdigit():
                keywords.add(word)
        
        return keywords
    
    def _extract_simple_relations(self, text: str) -> List[Dict]:
        """提取简单的主谓宾关系"""
        relations = []
        
        # 简单的关系模式匹配
        patterns = [
            r'([^，。！？]+?)负责([^，。！？]+)',
            r'([^，。！？]+?)管理([^，。！？]+)',
            r'([^，。！？]+?)审批([^，。！？]+)',
            r'([^，。！？]+?)发布([^，。！？]+)',
            r'([^，。！？]+?)适用于([^，。！？]+)',
            r'([^，。！？]+?)要求([^，。！？]+)'
        ]
        
        predicate_map = {
            '负责': 'RESPONSIBLE_FOR',
            '管理': 'MANAGES',
            '审批': 'APPROVES',
            '发布': 'PUBLISHES',
            '适用于': 'APPLIES_TO',
            '要求': 'REQUIRES'
        }
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 2:
                    subject = match[0].strip()
                    object_entity = match[1].strip()
                    
                    # 确定谓语
                    predicate = None
                    for key, value in predicate_map.items():
                        if key in pattern:
                            predicate = value
                            break
                    
                    if predicate and subject and object_entity:
                        relations.append({
                            'subject': subject,
                            'predicate': predicate,
                            'object': object_entity
                        })
        
        return relations
    
    def _verify_relation_in_graph(self, subject: str, object_entity: str, predicate: str) -> bool:
        """在图谱中验证关系是否存在"""
        try:
            # 使用图谱查询引擎验证关系
            verification_results = self.graph_query.verify_entity_relations(
                [subject, object_entity], 
                [predicate]
            )
            
            # 检查是否找到匹配的关系
            for result in verification_results:
                if result.get('verified', False):
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"图谱关系验证失败: {e}")
            return False
    
    def _determine_risk_level(self, confidence: float) -> str:
        """确定风险等级"""
        if confidence >= 0.8:
            return 'low'
        elif confidence >= 0.5:
            return 'medium'
        else:
            return 'high'
    
    def _generate_warnings(self, entity_score: float, relation_score: float, 
                          content_score: float, coherence_score: float) -> List[str]:
        """生成警告信息"""
        warnings = []
        
        if entity_score < 0.5:
            warnings.append("答案中包含未经验证的实体信息")
        
        if relation_score < 0.4:
            warnings.append("答案中的关系描述可能不准确")
        
        if content_score < 0.3:
            warnings.append("答案内容与检索文档相关性较低")
        
        if coherence_score < 0.4:
            warnings.append("答案的逻辑连贯性有待改善")
        
        # 如果所有分数都较低，给出综合警告
        if all(score < 0.5 for score in [entity_score, relation_score, content_score, coherence_score]):
            warnings.append("⚠️ 答案可信度较低，建议谨慎对待")
        
        return warnings
    
    def generate_confidence_explanation(self, detection_result: Dict) -> str:
        """生成可信度说明"""
        confidence = detection_result['confidence']
        scores = detection_result['detailed_scores']
        
        explanation_parts = []
        
        # 总体评价
        if confidence >= 0.8:
            explanation_parts.append("答案具有较高可信度")
        elif confidence >= 0.5:
            explanation_parts.append("答案具有中等可信度")
        else:
            explanation_parts.append("答案可信度较低")
        
        # 详细分析
        if scores.get('entity_consistency', 0) >= 0.7:
            explanation_parts.append("实体信息已验证")
        
        if scores.get('relation_verification', 0) >= 0.6:
            explanation_parts.append("关系描述基本准确")
        
        if scores.get('content_overlap', 0) >= 0.6:
            explanation_parts.append("内容与文档资料吻合")
        
        return "，".join(explanation_parts) + "。"


def test_hallucination_detector():
    """测试幻觉检测功能"""
    logging.basicConfig(level=logging.INFO)
    
    # 这里需要实际的图谱查询引擎和实体提取器实例
    # 在实际使用中，这些会从其他模块导入
    print("幻觉检测器测试需要与其他模块集成才能运行")
    print("请在完整的GraphRAG系统中进行测试")


if __name__ == "__main__":
    test_hallucination_detector()