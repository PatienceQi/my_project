"""
实体关系提取模块 - 基于Ollama的智能实体识别和关系提取
支持从政策文档中提取实体、关系，并构建知识图谱
"""

import os
import json
import logging
import re
from typing import List, Dict, Tuple, Optional
import requests
from dotenv import load_dotenv

# 导入错误处理模块
from backend.ollama_error_handler import (
    OllamaClientWithFallback, 
    ensure_remote_ollama_config,
    ollama_retry
)

# 加载环境变量
load_dotenv()

class EntityExtractor:
    """实体关系提取器 - 基于Ollama"""
    
    def __init__(self):
        """初始化实体提取器"""
        # 关键修复：强制设置远程Ollama配置，防止连接本地服务
        self._force_remote_ollama_config()
        
        # 初始化配置参数
        self.ollama_host = self._get_verified_ollama_host()
        self.model_name = os.getenv('LLM_MODEL', 'llama3.2:latest')
        self.confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', 0.4))
        
        # 初始化错误处理客户端
        self.ollama_client = OllamaClientWithFallback()
        
        # 验证远程连接
        self._validate_remote_connection()
        
        logging.info(f"实体提取器初始化成功 - Ollama: {self.ollama_host}, 模型: {self.model_name}")
        logging.info(f"已集成错误处理和回退机制")
    
    def _force_remote_ollama_config(self):
        """强制设置远程Ollama配置"""
        remote_host = 'http://120.232.79.82:11434'
        
        # 设置所有可能影响Ollama连接的环境变量
        config_vars = {
            'OLLAMA_HOST': remote_host,
            'OLLAMA_BASE_URL': remote_host,
            'LLM_BINDING_HOST': remote_host,
            'OLLAMA_NO_SERVE': '1',
            'OLLAMA_ORIGINS': '*',
            'OLLAMA_KEEP_ALIVE': '5m'
        }
        
        for key, value in config_vars.items():
            old_value = os.environ.get(key)
            os.environ[key] = value
            if old_value != value:
                logging.info(f"环境变量修正: {key} = {value} (原值: {old_value})")
    
    def _get_verified_ollama_host(self) -> str:
        """获取并验证Ollama主机地址"""
        host = os.getenv('LLM_BINDING_HOST', 'http://120.232.79.82:11434')
        
        # 确保主机地址格式正确
        if not host.startswith('http'):
            host = f"http://{host}"
        
        # 验证是否为远程地址
        if '127.0.0.1' in host or 'localhost' in host:
            logging.warning(f"检测到本地地址 {host}，强制使用远程服务")
            host = 'http://120.232.79.82:11434'
            os.environ['LLM_BINDING_HOST'] = host
        
        return host
    
    def _validate_remote_connection(self):
        """验证远程Ollama连接"""
        try:
            # 测试基本连接
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                
                # 检查目标模型是否可用
                model_available = any(self.model_name in name for name in model_names)
                
                if model_available:
                    logging.info(f"✅ 远程Ollama连接验证成功，模型 {self.model_name} 可用")
                else:
                    logging.warning(f"⚠️  模型 {self.model_name} 不可用，可用模型: {model_names}")
            else:
                logging.error(f"❌ 远程Ollama服务响应异常: {response.status_code}")
                
        except Exception as e:
            logging.error(f"❌ 远程Ollama连接验证失败: {e}")
            raise ConnectionError(f"无法连接到远程Ollama服务 {self.ollama_host}: {e}")
    
    def extract_entities(self, text: str) -> List[Dict]:
        """从文本中提取实体"""
        prompt = self._build_entity_extraction_prompt(text)
        
        try:
            response = self._call_ollama(prompt)
            entities = self._parse_entity_response(response)
            
            # 过滤低置信度实体
            filtered_entities = [
                entity for entity in entities 
                if entity.get('confidence', 0) >= self.confidence_threshold
            ]
            
            logging.info(f"提取到 {len(filtered_entities)} 个高置信度实体")
            return filtered_entities
            
        except Exception as e:
            logging.error(f"实体提取失败: {e}")
            return []
    
    def extract_relations(self, text: str, entities: List[Dict]) -> List[Dict]:
        """从文本中提取实体关系"""
        if len(entities) < 2:
            return []
        
        prompt = self._build_relation_extraction_prompt(text, entities)
        
        try:
            response = self._call_ollama(prompt)
            relations = self._parse_relation_response(response)
            
            # 验证关系的实体是否存在
            entity_names = {entity['text'].lower() for entity in entities}
            validated_relations = []
            
            for relation in relations:
                source_valid = relation.get('source', '').lower() in entity_names
                target_valid = relation.get('target', '').lower() in entity_names
                
                if source_valid and target_valid:
                    validated_relations.append(relation)
            
            logging.info(f"提取到 {len(validated_relations)} 个有效关系")
            return validated_relations
            
        except Exception as e:
            logging.error(f"关系提取失败: {e}")
            return []
    
    def extract_entities_from_question(self, question: str) -> List[str]:
        """从问题中提取关键实体"""
        prompt = f"""
        请从以下问题中提取关键实体（人名、机构名、地名、政策术语等），以JSON格式返回：

        问题：{question}

        只返回JSON格式，例如：
        {{
            "entities": ["实体1", "实体2", "实体3"]
        }}
        """
        
        try:
            response = self._call_ollama(prompt)
            entities_data = self._parse_json_response(response)
            
            if isinstance(entities_data, dict) and 'entities' in entities_data:
                entities = entities_data['entities']
                logging.info(f"从问题中提取到 {len(entities)} 个实体")
                return entities
            
            return []
            
        except Exception as e:
            logging.error(f"问题实体提取失败: {e}")
            return []
    
    def _build_entity_extraction_prompt(self, text: str) -> str:
        """构建实体提取提示"""
        prompt = f"""
        你是一个专业的政策文档分析专家。请从以下政策文本中提取关键实体，按照指定格式返回JSON：

        文本：{text[:1000]}...

        请提取以下类型的实体：
        - 组织机构(ORG)：政府部门、企业、事业单位、社会团体等
        - 政策概念(CONCEPT)：政策术语、专业概念、业务术语等  
        - 地理位置(LOCATION)：国家、省市、区域、具体地点等
        - 时间信息(TIME)：日期、期限、时间段等
        - 人员角色(PERSON)：职位、岗位、人员类别等
        - 法规条款(REGULATION)：法律条文、政策条款、规定等

        输出要求：
        1. 只返回JSON格式，不要其他解释
        2. 每个实体包含text（实体文本）、label（类型）、confidence（置信度0-1）
        3. 置信度基于实体在文本中的重要性和明确性

        输出格式：
        {{
            "entities": [
                {{"text": "实体名称", "label": "ORG", "confidence": 0.9}},
                {{"text": "另一个实体", "label": "CONCEPT", "confidence": 0.8}}
            ]
        }}
        """
        
        return prompt
    
    def _build_relation_extraction_prompt(self, text: str, entities: List[Dict]) -> str:
        """构建关系提取提示"""
        entity_list = [entity['text'] for entity in entities]
        
        prompt = f"""
        你是一个专业的政策文档分析专家。请分析以下文本中实体间的关系：

        文本：{text[:1000]}...

        已识别实体：{', '.join(entity_list)}

        请识别以下类型的关系：
        - 发布(PUBLISHES)：机构发布政策
        - 适用于(APPLIES_TO)：政策适用于某对象
        - 管理(MANAGES)：机构管理某事务
        - 要求(REQUIRES)：政策要求某行为
        - 包含(CONTAINS)：文档包含某内容
        - 负责(RESPONSIBLE_FOR)：机构负责某事务
        - 审批(APPROVES)：机构审批某事项
        - 监督(SUPERVISES)：机构监督某活动

        输出要求：
        1. 只返回JSON格式
        2. 只提取确实存在的关系
        3. source和target必须是已识别的实体

        输出格式：
        {{
            "relations": [
                {{"source": "实体1", "target": "实体2", "relation": "PUBLISHES", "confidence": 0.9}},
                {{"source": "实体2", "target": "实体3", "relation": "APPLIES_TO", "confidence": 0.8}}
            ]
        }}
        """
        
        return prompt
    
    def _call_ollama(self, prompt: str) -> str:
        """调用Ollama API，使用错误处理和回退机制"""
        # 关键修复：在每次调用前验证不会连接本地服务
        current_host = self.ollama_client.current_host
        if 'localhost' in current_host or '127.0.0.1' in current_host:
            logging.error(f"检测到本地地址: {current_host}，强制重置为远程服务")
            ensure_remote_ollama_config()
            # 重新创建客户端以应用新配置
            self.ollama_client = OllamaClientWithFallback()
            # 再次验证
            current_host = self.ollama_client.current_host
            if 'localhost' in current_host or '127.0.0.1' in current_host:
                # 如果还是本地地址，直接强制使用远程地址
                logging.error(f"错误处理客户端仍返回本地地址: {current_host}")
                raise ConnectionError("配置已损坏，无法连接远程服务")
        
        try:
            # 使用错误处理客户端调用文本生成
            response = self.ollama_client.generate_text(
                model=self.model_name,
                prompt=prompt,
                temperature=0.1,
                top_p=0.9,
                top_k=40
            )
            
            logging.debug(f"成功Ollama API调用 - 使用主机: {self.ollama_client.current_host}")
            return response
            
        except Exception as e:
            # 记录详细错误信息
            error_msg = f"Ollama API调用失败 - 主机: {self.ollama_client.current_host}, 错误: {e}"
            logging.error(error_msg)
            
            # 检查是否是本地连接错误
            if '127.0.0.1' in str(e) or 'localhost' in str(e):
                logging.error("❌ 检测到尝试连接本地服务！配置已损坏")
                # 强制重置为远程配置
                ensure_remote_ollama_config()
                
            raise
    
    def _parse_entity_response(self, response: str) -> List[Dict]:
        """解析实体提取响应"""
        try:
            # 清理响应文本
            response = response.strip()
            
            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                
                if 'entities' in data and isinstance(data['entities'], list):
                    entities = []
                    for entity in data['entities']:
                        if isinstance(entity, dict) and 'text' in entity and 'label' in entity:
                            # 确保置信度存在
                            if 'confidence' not in entity:
                                entity['confidence'] = 0.5
                            entities.append(entity)
                    
                    return entities
            
            logging.warning("无法解析实体响应，返回空列表")
            return []
            
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"实体响应解析失败: {e}")
            return []
    
    def _parse_relation_response(self, response: str) -> List[Dict]:
        """解析关系提取响应"""
        try:
            # 清理响应文本
            response = response.strip()
            
            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                
                if 'relations' in data and isinstance(data['relations'], list):
                    relations = []
                    for relation in data['relations']:
                        if (isinstance(relation, dict) and 
                            'source' in relation and 
                            'target' in relation and 
                            'relation' in relation):
                            
                            # 确保置信度存在
                            if 'confidence' not in relation:
                                relation['confidence'] = 0.5
                            relations.append(relation)
                    
                    return relations
            
            logging.warning("无法解析关系响应，返回空列表")
            return []
            
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"关系响应解析失败: {e}")
            return []
    
    def _parse_json_response(self, response: str) -> Dict:
        """解析通用JSON响应"""
        try:
            # 清理响应文本
            response = response.strip()
            
            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            
            return {}
            
        except json.JSONDecodeError as e:
            logging.error(f"JSON响应解析失败: {e}")
            return {}
    
    def extract_all_from_document(self, document: Dict) -> Dict:
        """从完整文档中提取所有实体和关系"""
        # 提取文档文本
        text = self._extract_document_text(document)
        
        if not text:
            return {'entities': [], 'relations': []}
        
        # 提取实体
        entities = self.extract_entities(text)
        
        # 提取关系
        relations = self.extract_relations(text, entities)
        
        result = {
            'entities': entities,
            'relations': relations,
            'document_id': document.get('id', 'unknown'),
            'document_title': document.get('title', '未知标题')
        }
        
        logging.info(f"文档 {result['document_title']} 提取完成: {len(entities)}个实体, {len(relations)}个关系")
        return result
    
    def _extract_document_text(self, document: Dict) -> str:
        """从文档字典中提取文本内容"""
        text_parts = []
        
        # 添加标题
        if 'title' in document:
            text_parts.append(document['title'])
        
        # 添加正文内容
        if 'content' in document:
            text_parts.append(document['content'])
        elif 'text' in document:
            text_parts.append(document['text'])
        
        # 添加章节内容
        if 'sections' in document:
            for section in document['sections']:
                if isinstance(section, dict):
                    if 'title' in section:
                        text_parts.append(section['title'])
                    if 'content' in section:
                        text_parts.append(section['content'])
                elif isinstance(section, str):
                    text_parts.append(section)
        
        return '\n'.join(text_parts)
    
    def batch_extract(self, documents: List[Dict]) -> List[Dict]:
        """批量提取多个文档的实体和关系"""
        results = []
        
        for i, document in enumerate(documents):
            logging.info(f"正在处理文档 {i+1}/{len(documents)}: {document.get('title', 'unknown')}")
            
            try:
                result = self.extract_all_from_document(document)
                results.append(result)
                
            except Exception as e:
                logging.error(f"文档 {i+1} 处理失败: {e}")
                results.append({
                    'entities': [],
                    'relations': [],
                    'document_id': document.get('id', f'doc_{i}'),
                    'document_title': document.get('title', '处理失败'),
                    'error': str(e)
                })
        
        logging.info(f"批量提取完成，共处理 {len(documents)} 个文档")
        return results


def test_entity_extractor():
    """测试实体提取功能"""
    logging.basicConfig(level=logging.INFO)
    
    # 创建提取器
    extractor = EntityExtractor()
    
    # 测试文本
    test_text = """
    华侨经济文化合作试验区管理委员会负责试验区的开发建设和管理工作。
    试验区内的企业享受税收优惠政策，包括企业所得税减免和增值税优惠。
    投资项目需要通过发改委审批，并接受财政部门监督。
    """
    
    print("测试文本:", test_text)
    print("\n" + "="*50)
    
    # 测试实体提取
    print("=== 实体提取测试 ===")
    entities = extractor.extract_entities(test_text)
    print(f"提取到 {len(entities)} 个实体:")
    for entity in entities:
        print(f"  {entity['text']} ({entity['label']}) - 置信度: {entity['confidence']}")
    
    # 测试关系提取
    print("\n=== 关系提取测试 ===")
    relations = extractor.extract_relations(test_text, entities)
    print(f"提取到 {len(relations)} 个关系:")
    for relation in relations:
        print(f"  {relation['source']} --{relation['relation']}--> {relation['target']} - 置信度: {relation['confidence']}")
    
    # 测试问题实体提取
    print("\n=== 问题实体提取测试 ===")
    test_question = "华侨试验区的税收优惠政策是什么？"
    question_entities = extractor.extract_entities_from_question(test_question)
    print(f"问题: {test_question}")
    print(f"提取到的实体: {question_entities}")


if __name__ == "__main__":
    test_entity_extractor()