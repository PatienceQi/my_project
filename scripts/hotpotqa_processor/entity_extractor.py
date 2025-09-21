"""
HotpotQA实体提取器

基于Ollama大模型进行智能实体识别和关系提取。
支持从问题、答案、上下文段落中提取实体，并推断实体间关系。
"""

import json
import logging
import time
import requests
from typing import List, Dict, Any, Optional, Tuple
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class HotpotQAEntityExtractor:
    """HotpotQA实体提取器"""
    
    def __init__(self, ollama_host: str = None, model_name: str = "llama3.2:latest"):
        self.ollama_host = ollama_host or os.getenv("LLM_BINDING_HOST", "http://120.232.79.82:11434")
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)
        
        # 确保host格式正确
        if not self.ollama_host.startswith(('http://', 'https://')):
            self.ollama_host = f"http://{self.ollama_host}"
        
        # 记录连接信息
        self.logger.info(f"使用Ollama服务: {self.ollama_host}, 模型: {self.model_name}")
        
        self.session = requests.Session()
        self.session.timeout = 3000  # 50分钟超时
        
        # 统计信息
        self.stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'total_entities_extracted': 0,
            'total_relations_extracted': 0,
            'avg_extraction_time': 0.0
        }
        
        self.logger.info(f"HotpotQA实体提取器初始化完成，使用Ollama服务: {self.ollama_host}")
    
    def extract_all_from_question(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从问题数据中提取所有实体和关系
        
        Args:
            question_data: 预处理后的问题数据
            
        Returns:
            包含实体和关系的提取结果
        """
        start_time = time.time()
        self.stats['total_extractions'] += 1
        
        try:
            extraction_result = {
                'question_id': question_data['question_id'],
                'entities': [],
                'relations': [],
                'extraction_metadata': {
                    'extraction_time': 0,
                    'success': False,
                    'error_message': None
                }
            }
            
            # 从问题中提取实体
            question_entities = self.extract_entities_from_text(
                question_data['question'], 
                'question'
            )
            extraction_result['entities'].extend(question_entities)
            
            # 从答案中提取实体
            answer_entities = self.extract_entities_from_text(
                question_data['answer'], 
                'answer'
            )
            extraction_result['entities'].extend(answer_entities)
            
            # 从上下文段落中提取实体
            for paragraph in question_data['paragraphs']:
                para_entities = self.extract_entities_from_text(
                    f"{paragraph['title']} {paragraph['text']}", 
                    'context'
                )
                # 添加段落信息
                for entity in para_entities:
                    entity['source_paragraph'] = paragraph['paragraph_id']
                extraction_result['entities'].extend(para_entities)
            
            # 去重和归一化实体
            extraction_result['entities'] = self.resolve_entity_references(
                extraction_result['entities']
            )
            
            # 提取实体间关系
            if len(extraction_result['entities']) > 1:
                relations = self.extract_relations_from_context(
                    extraction_result['entities'],
                    question_data
                )
                extraction_result['relations'] = relations
            
            # 更新统计信息
            extraction_time = time.time() - start_time
            extraction_result['extraction_metadata'].update({
                'extraction_time': extraction_time,
                'success': True
            })
            
            self.stats['successful_extractions'] += 1
            self.stats['total_entities_extracted'] += len(extraction_result['entities'])
            self.stats['total_relations_extracted'] += len(extraction_result['relations'])
            self._update_avg_time(extraction_time)
            
            self.logger.info(
                f"成功提取问题 {question_data['question_id']}: "
                f"{len(extraction_result['entities'])} 个实体, "
                f"{len(extraction_result['relations'])} 个关系"
            )
            
            return extraction_result
            
        except Exception as e:
            extraction_time = time.time() - start_time
            self.stats['failed_extractions'] += 1
            
            self.logger.error(f"提取实体失败 {question_data['question_id']}: {e}")
            
            return {
                'question_id': question_data['question_id'],
                'entities': [],
                'relations': [],
                'extraction_metadata': {
                    'extraction_time': extraction_time,
                    'success': False,
                    'error_message': str(e)
                }
            }
    
    def extract_entities_from_text(self, text: str, context_type: str) -> List[Dict[str, Any]]:
        """
        从文本中提取实体
        
        Args:
            text: 输入文本
            context_type: 上下文类型 ('question', 'answer', 'context')
            
        Returns:
            实体列表
        """
        if not text or len(text.strip()) < 3:
            return []
        
        try:
            # 构建实体提取提示
            prompt = self._build_entity_extraction_prompt(text, context_type)
            
            # 调用Ollama进行实体提取
            response = self._call_ollama_for_entities(prompt)
            
            # 解析响应
            entities = self._parse_entity_response(response, context_type)
            
            return entities
            
        except Exception as e:
            self.logger.warning(f"从文本提取实体失败 ({context_type}): {e}")
            return []
    
    def _build_entity_extraction_prompt(self, text: str, context_type: str) -> str:
        """构建实体提取提示"""
        return f"""请从以下{context_type}文本中提取重要的实体。重点关注人名、地名、组织机构、时间、事件等。

文本: {text}

请以JSON格式返回提取的实体，格式如下：
{{
    "entities": [
        {{
            "name": "实体名称",
            "type": "实体类型(PERSON/LOCATION/ORGANIZATION/TIME/EVENT/CONCEPT)",
            "confidence": 0.95,
            "aliases": ["别名1", "别名2"]
        }}
    ]
}}

只返回JSON，不要添加其他解释。"""
    
    def _build_relation_extraction_prompt(self, entities: List[Dict], context: str) -> str:
        """构建关系提取提示"""
        entity_names = [entity['name'] for entity in entities]
        
        return f"""请分析以下实体在给定上下文中的关系：

实体列表: {', '.join(entity_names)}

上下文: {context}

请以JSON格式返回实体间的关系，格式如下：
{{
    "relations": [
        {{
            "source": "实体1",
            "target": "实体2", 
            "relation": "关系类型",
            "confidence": 0.85,
            "description": "关系描述"
        }}
    ]
}}

关系类型包括：LOCATED_IN, WORKS_FOR, MEMBER_OF, HAPPENED_AT, RELATED_TO, PART_OF, CAUSES等。
只返回JSON，不要添加其他解释。"""
    
    def _call_ollama_for_relations(self, prompt: str) -> str:
        """调用Ollama进行关系提取"""
        try:
            url = f"{self.ollama_host}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.7,
                    "max_tokens": 3000,  # 增加最大token数
                    "stop": ["```", "---"]  # 添加停止词
                }
            }
            
            response = self.session.post(url, json=payload, timeout=3000)
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get('response', '')
            
            # 记录响应长度用于调试
            self.logger.debug(f"Ollama关系提取响应长度: {len(response_text)}")
            
            return response_text
            
        except Exception as e:
            self.logger.error(f"调用Ollama关系提取失败: {e}")
            raise
    
    def _call_ollama_for_entities(self, prompt: str) -> str:
        """调用Ollama进行实体提取"""
        try:
            url = f"{self.ollama_host}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.8,
                    "max_tokens": 2500,  # 增加最大token数
                    "stop": ["```", "---"]  # 添加停止词
                }
            }
            
            response = self.session.post(url, json=payload, timeout=3000)
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get('response', '')
            
            # 记录响应长度用于调试
            self.logger.debug(f"Ollama实体提取响应长度: {len(response_text)}")
            
            return response_text
            
        except Exception as e:
            self.logger.error(f"调用Ollama实体提取失败: {e}")
            raise
    
    def _parse_entity_response(self, response: str, context_type: str) -> List[Dict[str, Any]]:
        """解析实体提取响应"""
        try:
            # 尝试提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                return []
            
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            entities = []
            for entity_data in data.get('entities', []):
                if isinstance(entity_data, dict) and 'name' in entity_data:
                    entity = {
                        'entity_id': f"entity_{len(entities)}_{int(time.time())}",
                        'name': entity_data['name'].strip(),
                        'entity_type': entity_data.get('type', 'CONCEPT'),
                        'confidence': float(entity_data.get('confidence', 0.8)),
                        'aliases': entity_data.get('aliases', []),
                        'source_context': context_type
                    }
                    
                    # 验证实体有效性
                    if len(entity['name']) > 1 and entity['confidence'] > 0.3:
                        entities.append(entity)
            
            return entities
            
        except json.JSONDecodeError:
            self.logger.warning(f"解析实体响应JSON失败: {response[:200]}")
            return []
        except Exception as e:
            self.logger.warning(f"解析实体响应失败: {e}")
            return []
    
    def _parse_relation_response(self, response: str) -> List[Dict[str, Any]]:
        """解析关系提取响应"""
        try:
            # 尝试提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                return []
            
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            relations = []
            for relation_data in data.get('relations', []):
                if isinstance(relation_data, dict) and all(k in relation_data for k in ['source', 'target', 'relation']):
                    relation = {
                        'relation_id': f"rel_{len(relations)}_{int(time.time())}",
                        'source': relation_data['source'].strip(),
                        'target': relation_data['target'].strip(),
                        'relation_type': relation_data['relation'].strip(),
                        'confidence': float(relation_data.get('confidence', 0.7)),
                        'description': relation_data.get('description', '')
                    }
                    
                    # 验证关系有效性
                    if (relation['source'] != relation['target'] and 
                        len(relation['source']) > 1 and 
                        len(relation['target']) > 1 and
                        relation['confidence'] > 0.3):
                        relations.append(relation)
            
            return relations
            
        except json.JSONDecodeError:
            self.logger.warning(f"解析关系响应JSON失败: {response[:200]}")
            return []
        except Exception as e:
            self.logger.warning(f"解析关系响应失败: {e}")
            return []
    
    def extract_relations_from_context(self, entities: List[Dict], question_data: Dict) -> List[Dict[str, Any]]:
        """
        从上下文中提取实体间关系
        
        Args:
            entities: 提取的实体列表
            question_data: 问题数据
            
        Returns:
            关系列表
        """
        if len(entities) < 2:
            return []
        
        try:
            # 构建上下文信息
            context_parts = [
                f"问题: {question_data['question']}",
                f"答案: {question_data['answer']}"
            ]
            
            # 添加重要段落
            for para in question_data['paragraphs'][:3]:  # 只取前3个段落
                context_parts.append(f"{para['title']}: {para['text']}")
            
            context = "\n".join(context_parts)
            
            # 构建关系提取提示
            prompt = self._build_relation_extraction_prompt(entities, context)
            
            # 调用Ollama进行关系提取
            response = self._call_ollama_for_relations(prompt)
            
            # 解析响应
            relations = self._parse_relation_response(response)
            
            return relations
            
        except Exception as e:
            self.logger.warning(f"提取关系失败: {e}")
            return []
    
    def resolve_entity_references(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析实体引用，处理同义词和缩写
        
        Args:
            entities: 原始实体列表
            
        Returns:
            去重后的实体列表
        """
        if not entities:
            return []
        
        # 按名称分组，处理相似实体
        entity_groups = {}
        
        for entity in entities:
            name = entity['name'].lower().strip()
            
            # 查找相似实体
            matched_group = None
            for group_key in entity_groups:
                if self._are_entities_similar(name, group_key):
                    matched_group = group_key
                    break
            
            if matched_group:
                # 合并到现有组
                existing = entity_groups[matched_group]
                existing['confidence'] = max(existing['confidence'], entity['confidence'])
                existing['aliases'].extend(entity.get('aliases', []))
                existing['aliases'].append(entity['name'])
                existing['aliases'] = list(set(existing['aliases']))  # 去重
            else:
                # 创建新组
                entity_groups[name] = {
                    **entity,
                    'aliases': entity.get('aliases', [])
                }
        
        return list(entity_groups.values())
    
    def _are_entities_similar(self, name1: str, name2: str) -> bool:
        """判断两个实体名称是否相似"""
        # 完全匹配
        if name1 == name2:
            return True
        
        # 缩写匹配
        if len(name1) <= 5 and name1 in name2:
            return True
        if len(name2) <= 5 and name2 in name1:
            return True
        
        # 包含关系（较长的名称包含较短的）
        if len(name1) > len(name2) and name2 in name1:
            return True
        if len(name2) > len(name1) and name1 in name2:
            return True
        
        # 编辑距离相似度
        if self._edit_distance_similarity(name1, name2) > 0.8:
            return True
        
        return False
    
    def _edit_distance_similarity(self, s1: str, s2: str) -> float:
        """计算编辑距离相似度"""
        if not s1 or not s2:
            return 0.0
        
        # 简化的编辑距离计算
        len1, len2 = len(s1), len(s2)
        if len1 == 0:
            return 0.0
        if len2 == 0:
            return 0.0
        
        # 创建距离矩阵
        d = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        for i in range(len1 + 1):
            d[i][0] = i
        for j in range(len2 + 1):
            d[0][j] = j
        
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                d[i][j] = min(
                    d[i-1][j] + 1,      # 删除
                    d[i][j-1] + 1,      # 插入
                    d[i-1][j-1] + cost  # 替换
                )
        
        max_len = max(len1, len2)
        similarity = 1 - (d[len1][len2] / max_len)
        return similarity
    
    def validate_extraction_result(self, result: Dict[str, Any]) -> bool:
        """验证提取结果的有效性"""
        try:
            # 检查基本结构
            if not isinstance(result, dict):
                return False
            
            required_keys = ['question_id', 'entities', 'relations', 'extraction_metadata']
            if not all(key in result for key in required_keys):
                return False
            
            # 检查实体格式
            entities = result['entities']
            if not isinstance(entities, list):
                return False
            
            for entity in entities:
                if not isinstance(entity, dict) or 'name' not in entity:
                    return False
            
            # 检查关系格式
            relations = result['relations']
            if not isinstance(relations, list):
                return False
            
            for relation in relations:
                if not isinstance(relation, dict):
                    return False
                if not all(key in relation for key in ['source', 'target', 'relation_type']):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _update_avg_time(self, extraction_time: float):
        """更新平均提取时间"""
        total_time = self.stats['avg_extraction_time'] * (self.stats['successful_extractions'] - 1)
        self.stats['avg_extraction_time'] = (total_time + extraction_time) / self.stats['successful_extractions']
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取提取统计信息"""
        total = self.stats['total_extractions']
        return {
            **self.stats,
            'success_rate': self.stats['successful_extractions'] / max(total, 1),
            'avg_entities_per_extraction': self.stats['total_entities_extracted'] / max(self.stats['successful_extractions'], 1),
            'avg_relations_per_extraction': self.stats['total_relations_extracted'] / max(self.stats['successful_extractions'], 1)
        }