import os
import json
from neo4j import GraphDatabase
import dotenv
import re
import uuid
import hashlib
import requests
from collections import defaultdict
import traceback

# 加载环境变量
dotenv.load_dotenv()

# Neo4j连接信息
uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

# 创建Neo4j驱动程序
driver = GraphDatabase.driver(uri, auth=(username, password)) if uri and username and password else None

# 结果收集器
class ResultCollector:
    def __init__(self):
        self.policies = []
        self.organizations = []
        self.sections = []
        self.entities = defaultdict(list)
        self.relations = []
        self.summary = {
            "policies": 0,
            "organizations": 0,
            "sections": 0,
            "entities": 0,
            "unique_entities": 0,
            "relations": 0
        }
        self.entity_resolver = EntityResolver()
    
    def add_policy(self, policy_id, title):
        self.policies.append({"policy_id": policy_id, "title": title})
        self.summary["policies"] += 1
    
    def add_organization(self, org_name):
        self.organizations.append(org_name)
        self.summary["organizations"] += 1
    
    def add_section(self, section_id, title):
        self.sections.append({"section_id": section_id, "title": title})
        self.summary["sections"] += 1
    
    def add_entity(self, entity_data, source_type, source_id):
        global_id = self.entity_resolver.resolve_entity(entity_data)
        if not global_id:
            return None
            
        entity_info = {
            "global_id": global_id,
            "name": entity_data['name'],
            "type": entity_data.get('type', '未知类型'),
            "source_type": source_type,
            "source_id": source_id
        }
        
        # 仅在新实体时计数
        if global_id not in self.entities:
            self.summary["unique_entities"] += 1
            
        self.entities[global_id].append(entity_info)
        self.summary["entities"] += 1
        return global_id
    
    def add_relation(self, source_id, target_id, predicate, source_type):
        # 规范化关系类型
        rel_type = sanitize_relation_type(predicate)
        
        self.relations.append({
            "source": source_id,
            "target": target_id,
            "type": rel_type,
            "source_type": source_type
        })
        self.summary["relations"] += 1
    
    def print_results(self):
        print("\n" + "="*50)
        print("数据处理结果摘要")
        print("="*50)
        print(f"政策数量: {self.summary['policies']}")
        print(f"组织机构: {self.summary['organizations']}")
        print(f"章节数量: {self.summary['sections']}")
        print(f"实体提及数量: {self.summary['entities']} (去重后唯一实体: {self.summary['unique_entities']})")
        print(f"关系数量: {self.summary['relations']}")
        
        if self.summary['unique_entities'] > 0:
            print("\n关键实体列表 (前10个):")
            for i, (global_id, entity_list) in enumerate(list(self.entities.items())[:10]):
                main_entity = entity_list[0]
                print(f" {i+1}. {main_entity['name']} ({main_entity['type']}) [ID: {global_id}]")
                print(f"    来源: {len(entity_list)}处提及")
                sources = ", ".join(set([e['source_type'] for e in entity_list]))
                print(f"    出现位置: {sources}")
                
        if self.relations:
            print("\n关键关系列表 (前10个):")
            for i, rel in enumerate(self.relations[:10]):
                source_entity = self.entities.get(rel['source'], [{}])
                source_name = source_entity[0].get('name', '未知') if source_entity else "未知"
                
                target_entity = self.entities.get(rel['target'], [{}])
                target_name = target_entity[0].get('name', '未知') if target_entity else "未知"
                
                print(f" {i+1}. {source_name} --[{rel['type']}]-> {target_name} (来源: {rel['source_type']})")
        
        print("\n" + "="*50)
        print("数据已成功存储到Neo4j数据库")
        print("="*50)

# 实体解析器类 - 实现实体去重机制
class EntityResolver:
    """实体归一化处理器，用于实体去重"""
    def __init__(self):
        # {别名: 全局ID} 的映射
        self.alias_to_global_id = {}
        # {全局ID: 实体信息} 的映射
        self.global_entities = {}
    
    def generate_global_id(self, name, aliases):
        """为实体生成全局唯一ID"""
        # 创建实体标识符 - 使用名称和别名的哈希值
        unique_str = name + "".join(sorted(aliases))
        return f"ENT_{hashlib.md5(unique_str.encode()).hexdigest()[:8]}"
    
    def resolve_entity(self, entity):
        """解析实体，返回全局ID，更新别名映射"""
        name = entity.get('name', '').strip()
        if not name:
            return None
        
        # 获取所有别名（包括名称本身）
        aliases = set([name.lower()])
        for alias in entity.get('aliases', []):
            if isinstance(alias, str) and alias.strip():
                aliases.add(alias.lower().strip())
        
        # 检查现有别名映射
        for alias in aliases:
            if alias in self.alias_to_global_id:
                # 已有映射，返回现有全局ID
                global_id = self.alias_to_global_id[alias]
                
                # 更新全局实体的别名集合
                if global_id in self.global_entities:
                    self.global_entities[global_id]['aliases'].update(aliases)
                
                # 更新所有别名的映射
                for a in aliases:
                    self.alias_to_global_id[a] = global_id
                
                return global_id
        
        # 新实体 - 生成全局ID
        global_id = self.generate_global_id(name, aliases)
        
        # 存储实体信息
        self.global_entities[global_id] = {
            'name': name,
            'type': entity.get('type', '未知类型'),
            'aliases': aliases
        }
        
        # 更新映射
        for alias in aliases:
            self.alias_to_global_id[alias] = global_id
        
        return global_id

# 关系类型规范化函数
def sanitize_relation_type(predicate):
    """规范化关系类型名称"""
    if not predicate:
        return "RELATED_TO"
    
    # 移除特殊字符和空格，保留字母、数字和下划线
    rel_type = re.sub(r'[^\w]', '_', predicate.strip())
    
    # 转换为首字母大写的驼峰命名
    rel_type = rel_type[0].upper() + rel_type[1:] if rel_type else "RELATED_TO"
    
    return rel_type

# 大模型调用函数 - 可接收自定义prompt
def call_large_language_model(text, custom_prompt=None):
    """
    调用大模型服务进行实体识别和关系抽取
    :param text: 要处理的文本
    :param custom_prompt: 自定义的prompt指令
    :return: 大模型返回的响应
    """
    # 确保文本长度不超过模型限制
    max_length = 2000  # 可以调整此值以适应不同模型
    if len(text) > max_length:
        print(f"警告: 文本长度({len(text)}字符)超过最大限制({max_length})，进行截断")
        text = text[:max_length]
    
    # 使用自定义prompt或默认prompt
    if custom_prompt:
        prompt = custom_prompt
    else:
        prompt = (
            "请从以下文本中识别所有提到的实体、实体间的直接关系，并为每个识别出的实体生成一个描述性的别名列表（包含其在文本中出现的所有形式：全名、缩写、昵称、指代词等）。\n"
            "任务仅需关注提供的当前文本块内容，不需要回忆或推测块外的信息。\n"
            "请以机器可解析的JSON格式输出结果。\n"
        )
    
    full_prompt = f"{prompt}\n文本内容:\n{text}"
    print(f"\n调用大模型处理文本块 (长度: {len(text)}字符)")
    
    try:
        # 构造请求数据
        payload = {
            'model': os.getenv('LLM_MODEL', 'llama3'),
            'prompt': full_prompt,
            'stream': False
        }
        
        # 发送请求到大模型服务
        api_url = os.getenv('LLM_API_URL', 'http://120.232.79.82:11434') + '/api/generate'
        response = requests.post(api_url, json=payload, timeout=120)
        response.raise_for_status()  # 抛出HTTP错误
        
        # 解析响应
        result = response.json()
        response_text = result.get('response', '')
        
        # 打印摘要
        print(f"大模型返回结果摘要 (长度: {len(response_text)}字符)")
        if response_text:
            # 尝试解析JSON输出摘要
            try:
                data = json.loads(response_text)
                entities_count = len(data.get("entities", []))
                relations_count = len(data.get("relations", []))
                print(f"  提取到实体: {entities_count}个, 关系: {relations_count}个")
            except Exception as e:
                # 解析失败时打印前100个字符
                preview = response_text[:100].replace('\n', ' ')
                print(f"  解析结果失败: {e}")
                print(f"  返回内容预览: {preview}...")
        
        return response_text
    except Exception as e:
        print(f"调用大模型服务时出错：{e}")
        return ''

# 实体和关系提取函数 - 使用专门prompt
def extract_entities_and_relations(text, result_collector=None):
    """
    从文本中提取实体和关系
    :param text: 要处理的文本
    :return: (entities, relations) 元组
    """
    # 专用prompt确保大模型输出格式一致
    prompt = """
    请从政策法规文本中提取以下信息：
    1. 实体包括：政策名称、条款编号、机构名称、日期等
    2. 关系包括：政策发布机构、条款归属政策等
    
    输出要求（严格的JSON格式）：
    {
      "entities": [
        {
          "name": "实体名称",
          "type": "实体类型",
          "aliases": ["别名1", "别名2"]
        }
      ],
      "relations": [
        {
          "source": "源实体名称",
          "target": "目标实体名称",
          "predicate": "关系类型"
        }
      ]
    }
    
    注意事项：
    - 每个实体必须有名称和类型
    - 实体别名应包含所有出现的名称形式
    - 关系类型使用英文或中文短语描述
    - 不要包含任何额外的文本解释
    """
    
    # 调用大模型服务
    model_output = call_large_language_model(text, prompt)
    
    if model_output:
        try:
            # 解析JSON结果
            data = json.loads(model_output)
            entities = data.get("entities", [])
            relations = data.get("relations", [])
            
            # 如果有结果收集器，立即添加结果
            if result_collector:
                print(f"文本提取结果: 实体 {len(entities)}个, 关系 {len(relations)}个")
            return entities, relations
        except json.JSONDecodeError:
            print("大模型返回的JSON格式无效")
            return [], []
    return [], []

# 创建政策节点和相关实体关系
def create_policy_nodes(tx, policy_data, result_collector):
    """
    创建政策节点、相关实体和关系
    :param tx: Neo4j事务
    :param policy_data: 政策数据字典
    :param result_collector: 结果收集器
    """
    # 修复：直接使用policy_data字典
    if not isinstance(policy_data, dict):
        print("无效的政策数据格式")
        return
    
    # 获取政策基本信息
    policy_title = policy_data.get('title', '未知政策标题')
    policy_id = f"POL_{hashlib.md5(policy_title.encode()).hexdigest()[:8]}"
    publish_agency = policy_data.get('publish_agency', '未知发布机构')
    publish_date = policy_data.get('publish_date', '未知发布日期')
    doc_number = policy_data.get('doc_number', '无文号')
    
    # 添加政策到结果收集器
    result_collector.add_policy(policy_id, policy_title)
    print(f"\n开始处理政策: {policy_title} [ID: {policy_id}]")
    
    # 创建政策节点
    query = (
        "MERGE (p:Policy {policy_id: $policy_id}) "
        "SET p.title = $title, "
        "    p.publish_date = $publish_date, "
        "    p.publish_agency = $publish_agency, "
        "    p.doc_number = $doc_number "
    )
    params = {
        'policy_id': policy_id,
        'title': policy_title,
        'publish_date': publish_date,
        'publish_agency': publish_agency,
        'doc_number': doc_number
    }
    
    try:
        tx.run(query, **params)
    except Exception as e:
        print(f"创建政策节点时出错: {e}")
        traceback.print_exc()
    
    # 创建机构节点并建立关系
    if publish_agency and publish_agency != '未知发布机构':
        result_collector.add_organization(publish_agency)
        org_query = (
            "MERGE (o:Organization {name: $org_name}) "
            "MERGE (p:Policy {policy_id: $policy_id}) "
            "MERGE (o)-[:PUBLISHES]->(p) "
        )
        org_params = {
            'org_name': publish_agency,
            'policy_id': policy_id
        }
        try:
            tx.run(org_query, **org_params)
        except Exception as e:
            print(f"创建机构关系时出错: {e}")
    
    # 处理通知正文
    notification_body = policy_data.get('notification_body', '')
    if notification_body:
        print(f"\n处理通知正文 (长度: {len(notification_body)}字符)")
        entities, relations = extract_entities_and_relations(notification_body, result_collector)
        process_entities(entities, tx, result_collector, "Policy", policy_id, policy_id)
        process_relations(relations, tx, result_collector, "Policy")
    
    # 处理主文部分
    main_body = policy_data.get('main_body', [])
    print(f"\n处理主文部分: {len(main_body)}个章节")
    for section in main_body:
        section_title = section.get('section_title', '未知章节标题')
        section_content = section.get('content', '')
        section_id = f"{policy_id}_section_{hashlib.md5(section_title.encode()).hexdigest()[:6]}"
        
        # 添加到结果收集器
        result_collector.add_section(section_id, section_title)
        
        # 创建章节节点并连接到政策
        section_query = (
            "MERGE (s:Section {section_id: $section_id}) "
            "SET s.title = $title, "
            "    s.content = $content "
            "MERGE (p:Policy {policy_id: $policy_id}) "
            "MERGE (s)-[:BELONGS_TO]->(p) "
        )
        section_params = {
            'section_id': section_id,
            'title': section_title,
            'content': section_content,
            'policy_id': policy_id
        }
        try:
            tx.run(section_query, **section_params)
        except Exception as e:
            print(f"创建章节节点时出错: {e}")
        
        # 处理章节内容
        if section_content:
            print(f"  处理章节内容: {section_title} (长度: {len(section_content)}字符)")
            entities, relations = extract_entities_and_relations(section_content, result_collector)
            process_entities(entities, tx, result_collector, "Section", section_id, policy_id)
            process_relations(relations, tx, result_collector, "Section")
    
    # 处理结尾部分
    ending = policy_data.get('ending', '')
    if ending:
        print(f"\n处理结尾部分 (长度: {len(ending)}字符)")
        entities, relations = extract_entities_and_relations(ending, result_collector)
        process_entities(entities, tx, result_collector, "PolicyEnding", policy_id, policy_id)
        process_relations(relations, tx, result_collector, "PolicyEnding")
    
    # 处理抄送部分
    cc = policy_data.get('cc', '')
    if cc:
        print(f"\n处理抄送部分 (长度: {len(cc)}字符)")
        # 提取抄送机构
        organizations = re.findall(r'[^\s，。；、]+', cc)
        for org in organizations:
            if org:
                org_name = org.strip()
                result_collector.add_organization(org_name)
                # 创建机构节点并连接到政策
                cc_query = (
                    "MERGE (o:Organization {name: $org_name}) "
                    "MERGE (p:Policy {policy_id: $policy_id}) "
                    "MERGE (o)-[:CC]->(p) "
                )
                cc_params = {
                    'org_name': org_name,
                    'policy_id': policy_id
                }
                try:
                    tx.run(cc_query, **cc_params)
                except Exception as e:
                    print(f"创建抄送关系时出错: {e}")

def process_entities(entities, tx, result_collector, source_type, source_id, policy_id):
    """处理并存储实体"""
    for entity in entities:
        if 'name' not in entity or not entity['name']:
            continue
            
        # 添加到结果收集器
        entity_id = result_collector.add_entity(entity, source_type, source_id)
        if not entity_id:
            continue
            
        # 获取别名列表
        aliases = list(set(
            entity.get('aliases', []) + [entity['name']]
        ))
        
        # 创建实体节点或更新现有节点
        entity_query = (
            "MERGE (e:Entity {global_id: $global_id}) "
            "ON CREATE SET e.name = $name, "
            "              e.type = $type, "
            "              e.aliases = $aliases, "
            "              e.created_from = $source_type "
            "ON MATCH SET e.aliases = CASE "
            "                WHEN NOT $name IN e.aliases THEN e.aliases + $aliases "
            "                ELSE e.aliases "
            "              END "
            "MERGE (p:Policy {policy_id: $policy_id}) "
            "MERGE (e)-[:MENTIONED_IN {source: $source_type}]->(p) "
        )
        entity_params = {
            'global_id': entity_id,
            'name': entity['name'],
            'type': entity.get('type', '未知类型'),
            'aliases': aliases,
            'source_type': source_type,
            'policy_id': policy_id
        }
        
        try:
            tx.run(entity_query, **entity_params)
        except Exception as e:
            print(f"创建实体节点时出错: {e}")

def process_relations(relations, tx, result_collector, source_type):
    """处理并存储关系"""
    for relation in relations:
        source = relation.get('source', '')
        target = relation.get('target', '')
        predicate = relation.get('predicate', '')
        
        if not source or not target or not predicate:
            continue
            
        # 解析源实体和目标实体
        source_id = result_collector.entity_resolver.alias_to_global_id.get(source.lower(), None)
        target_id = result_collector.entity_resolver.alias_to_global_id.get(target.lower(), None)
        
        if source_id and target_id:
            # 添加到结果收集器
            result_collector.add_relation(source_id, target_id, predicate, source_type)
            
            # 规范化关系类型
            rel_type = sanitize_relation_type(predicate)
            
            # 创建关系
            rel_query = (
                "MATCH (s:Entity {global_id: $source_global_id}) "
                "MATCH (t:Entity {global_id: $target_global_id}) "
                f"MERGE (s)-[:{rel_type}]->(t) "
            )
            rel_params = {
                'source_global_id': source_id,
                'target_global_id': target_id
            }
            try:
                tx.run(rel_query, **rel_params)
            except Exception as e:
                print(f"创建实体关系时出错: {e}")

# 导入政策数据
def import_policy_data():
    """读取JSON文件并将数据导入Neo4j"""
    data_path = './database/[OCR]_华侨经济文化合作试验区.json'
    
    try:
        with open(data_path, 'r', encoding='utf-8') as file:
            policy_data = json.load(file)
        
        # 创建结果收集器
        result_collector = ResultCollector()
        
        if driver:
            # 将数据导入Neo4j
            with driver.session() as session:
                session.execute_write(create_policy_nodes, policy_data, result_collector)
        else:
            print("Neo4j驱动未初始化，跳过数据库写入")
        
        # 打印处理结果
        result_collector.print_results()
    except Exception as e:
        print(f"导入数据时出错：{e}")
        traceback.print_exc()

# 主程序
if __name__ == "__main__":
    print("="*50)
    print("政策数据分析处理系统")
    print("="*50)
    print("开始处理政策数据...\n")
    
    import_policy_data()
    
    if driver:
        driver.close()
        print("\nNeo4j连接已关闭")
    
    print("\n处理完成")