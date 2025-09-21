# RAG架构实现

<cite>
**本文档引用的文件**   
- [api_server.py](file://backend/api_server.py#L1-L120) - *已更新，集成GraphRAG引擎*
- [graphrag_engine.py](file://backend/graphrag_engine.py#L1-L485) - *新增的GraphRAG核心引擎*
- [vector_retrieval.py](file://backend/vector_retrieval.py#L1-L433) - *向量检索组件*
- [graph_query.py](file://backend/graph_query.py#L1-L430) - *图谱查询组件*
- [entity_extractor.py](file://backend/entity_extractor.py#L1-L491) - *实体提取组件*
- [hallucination_detector.py](file://backend/hallucination_detector.py#L1-L434) - *幻觉检测组件*
- [import_policy_data.py](file://scripts/import_policy_data.py#L1-L574)
- [华侨经济文化合作试验区.json](file://database/华侨经济文化合作试验区.json)
- [test_ollama_connection.py](file://scripts/test_ollama_connection.py#L1-L25)
- [README.md](file://README.md#L1-L253)
- [政策法规RAG问答系统操作手册.md](file://政策法规RAG问答系统操作手册.md#L1-L130)
- [软件著作权申请.md](file://软件著作权申请.md#L1-L191)
- [index.html](file://frontend/index.html#L1-L254)
</cite>

## 更新摘要
**变更内容**   
- 将原有的单一RAG架构升级为混合式GraphRAG架构
- 新增`graphrag_engine.py`作为核心引擎，整合向量检索、图谱查询、实体提取和幻觉检测四大组件
- 更新`api_server.py`以支持GraphRAG引擎的初始化和调用
- 增加可信度评估和风险等级判断功能
- 更新系统架构图和数据流转流程

**新增章节**   
- GraphRAG引擎架构设计
- 组件协同工作机制
- 上下文增强构建机制
- 幻觉检测与可信度评估

**已弃用内容**   
- 原有的单一RAG流程描述
- 独立的Cypher查询实现
- 简单的上下文拼接逻辑

**来源跟踪系统更新**   
- 新增对`graphrag_engine.py`、`vector_retrieval.py`等核心组件的引用
- 更新文件状态标记，标注已更新和新增的文件

## 目录
1. [项目概述](#项目概述)
2. [核心组件分析](#核心组件分析)
3. [GraphRAG引擎架构设计](#graphrag引擎架构设计)
4. [组件协同工作机制](#组件协同工作机制)
5. [上下文增强构建机制](#上下文增强构建机制)
6. [幻觉检测与可信度评估](#幻觉检测与可信度评估)
7. [数据导入与图数据库构建](#数据导入与图数据库构建)
8. [系统架构图](#系统架构图)
9. [技术决策分析](#技术决策分析)

## 项目概述

本项目是一个轻量级的政策法规问答系统，采用检索增强生成（RAG）架构，结合Neo4j图数据库和Ollama大模型服务，实现对政策法规文档的智能查询与问答。系统支持多模态查询、实体关系展示和答案溯源功能，旨在解决传统政策法规查询中信息分散、检索效率低的问题。

系统采用前后端分离架构：
- **前端**：基于HTML/CSS/JavaScript实现用户交互界面
- **后端**：基于Python Flask框架提供API服务
- **数据库**：使用Neo4j图数据库存储结构化的政策法规数据
- **大模型**：通过Ollama与本地大模型（如llama3.2）进行交互

用户通过前端界面输入自然语言问题，后端服务接收请求后，首先在Neo4j图数据库中进行语义相似度检索，获取相关上下文信息，然后将上下文与问题拼接成提示词（prompt），调用Ollama API生成自然语言回答，并添加引用溯源信息后返回给前端。

**Section sources**
- [README.md](file://README.md#L1-L253)
- [政策法规RAG问答系统操作手册.md](file://政策法规RAG问答系统操作手册.md#L1-L130)

## 核心组件分析

### 后端API服务

后端核心文件`api_server.py`实现了Flask应用，提供`/api/ask`接口接收用户提问。

```python
@app.route('/api/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '')
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    result = get_policy_answer(question)
    return jsonify(result)
```

该接口接收JSON格式的请求体，提取`question`字段，调用`get_policy_answer`函数处理，并返回JSON响应。

**Section sources**
- [api_server.py](file://backend/api_server.py#L109-L120)

### 与Ollama大模型交互

系统通过`ollama`库与本地大模型进行交互。在`api_server.py`中配置Ollama客户端：

```python
LLM_BINDING_HOST = os.getenv("LLM_BINDING_HOST", "")
if LLM_BINDING_HOST:
    client = ollama.Client(host=LLM_BINDING_HOST)
else:
    client = ollama.Client()
```

调用大模型生成回答的代码如下：

```python
response = client.chat(model=LLM_MODEL, messages=[
    {
        "role": "user",
        "content": prompt
    }
])
```

系统还提供了独立的连接测试脚本`test_ollama_connection.py`，用于验证Ollama服务的可用性。

**Section sources**
- [api_server.py](file://backend/api_server.py#L15-L24)
- [test_ollama_connection.py](file://scripts/test_ollama_connection.py#L1-L25)

### Neo4j图数据库检索

系统使用Cypher查询语言在Neo4j中进行内容检索。`query_neo4j`函数实现了基于节点层级（政策→章节→子章节）的检索逻辑：

``mermaid
flowchart TD
A[用户提问] --> B{查询文本}
B --> C[匹配政策标题]
B --> D[匹配章节标题]
B --> E[匹配子章节标题]
C --> F[返回政策节点]
D --> G[返回章节节点]
E --> H[返回子章节节点]
F --> I[构建上下文]
G --> I
H --> I
I --> J[生成回答]
```

**Diagram sources**
- [api_server.py](file://backend/api_server.py#L46-L71)

**Section sources**
- [api_server.py](file://backend/api_server.py#L33-L44)

## GraphRAG引擎架构设计

### GraphRAG核心引擎

系统已从原有的单一RAG架构升级为混合式GraphRAG架构，核心是`graphrag_engine.py`文件中实现的`GraphRAGEngine`类。该引擎整合了向量检索、图谱查询、实体提取和幻觉检测四大组件，提供统一的问答接口。

```python
class GraphRAGEngine:
    """GraphRAG引擎 - 图谱增强的检索生成系统"""
    
    def __init__(self):
        """初始化GraphRAG引擎"""
        self._force_remote_ollama_config()
        self._initialize_components()
```

**Section sources**
- [graphrag_engine.py](file://backend/graphrag_engine.py#L20-L54) - *GraphRAG引擎初始化*

### 组件依赖关系

GraphRAG引擎通过依赖注入的方式集成各个组件，确保系统模块化和可维护性。

```python
from backend.vector_retrieval import VectorRetriever
from backend.graph_query import GraphQueryEngine
from backend.entity_extractor import EntityExtractor
from backend.hallucination_detector import HallucinationDetector
```

各组件职责明确：
- `VectorRetriever`：负责基于Chroma的语义检索
- `GraphQueryEngine`：负责基于Neo4j的知识图谱查询
- `EntityExtractor`：负责从文本中提取实体和关系
- `HallucinationDetector`：负责答案可信度评估

**Section sources**
- [graphrag_engine.py](file://backend/graphrag_engine.py#L0-L18) - *组件导入与依赖*

### 引擎初始化流程

GraphRAG引擎的初始化流程确保所有组件正确配置并连接到远程服务。

```python
def _initialize_components(self):
    """初始化所有组件"""
    self.vector_retriever = VectorRetriever()
    self.graph_query_engine = GraphQueryEngine()
    self.entity_extractor = EntityExtractor()
    self.hallucination_detector = HallucinationDetector(
        self.graph_query_engine, 
        self.entity_extractor
    )
```

**Section sources**
- [graphrag_engine.py](file://backend/graphrag_engine.py#L54-L70) - *组件初始化*

## 组件协同工作机制

### 问答处理主流程

`answer_question`方法是GraphRAG引擎的核心，实现了从问题接收到答案生成的完整流程。

```python
def answer_question(self, question: str, use_graph: bool = True, 
                   return_confidence: bool = True) -> Dict:
    # 1. 实体提取
    question_entities = self.entity_extractor.extract_entities_from_question(question)
    
    # 2. 并行检索
    vector_results = self.vector_retriever.search(question, top_k=5)
    graph_context = self._query_graph_context(question_entities)
    
    # 3. 构建增强上下文
    enhanced_context = self._build_enhanced_context(
        question, question_entities, vector_results, graph_context
    )
    
    # 4. 生成答案
    answer = self._generate_answer(question, enhanced_context)
    
    # 5. 幻觉检测
    confidence_info = self.hallucination_detector.detect_hallucination(
        answer, question, vector_results, graph_context
    )
```

**Section sources**
- [graphrag_engine.py](file://backend/graphrag_engine.py#L72-L188) - *问答主流程*

### 图谱上下文查询

图谱查询利用Neo4j的图遍历能力，获取问题中实体的相关信息。

```python
def _query_graph_context(self, question_entities: List[str]) -> Dict:
    graph_context = {
        'entities': [],
        'policies': [],
        'relationships': []
    }
    
    # 查询相关实体
    entities = self.graph_query_engine.query_entities_by_name(question_entities)
    graph_context['entities'] = entities
    
    # 查询相关政策
    policies = self.graph_query_engine.query_policies_by_entities(question_entities)
    graph_context['policies'] = policies
    
    # 查询实体关系网络
    if question_entities:
        main_entity = question_entities[0]
        relationships = self.graph_query_engine.query_entity_relationships(main_entity)
        graph_context['relationships'] = relationships
    
    return graph_context
```

**Section sources**
- [graphrag_engine.py](file://backend/graphrag_engine.py#L189-L217) - *图谱上下文查询*

### API服务器集成

`api_server.py`中实现了GraphRAG引擎的全局实例化和接口调用。

```python
# GraphRAG引擎实例（全局）
graphrag_engine = None

def initialize_graphrag():
    """初始化GraphRAG引擎"""
    global graphrag_engine
    try:
        graphrag_engine = GraphRAGEngine()
        logger.info("GraphRAG引擎初始化成功")
    except Exception as e:
        logger.error(f"GraphRAG引擎初始化失败: {e}")
```

**Section sources**
- [api_server.py](file://backend/api_server.py#L90-L114) - *引擎初始化*

## 上下文增强构建机制

### 增强上下文构建

`_build_enhanced_context`方法将向量检索结果和图谱查询结果融合，构建更丰富的上下文。

```python
def _build_enhanced_context(self, question: str, question_entities: List[str], 
                           vector_results: List[Dict], graph_context: Dict) -> str:
    context_parts = []
    
    # 添加问题信息
    context_parts.append(f"用户问题: {question}")
    
    if question_entities:
        context_parts.append(f"问题中的关键实体: {', '.join(question_entities)}")
    
    # 添加向量检索结果
    if vector_results:
        context_parts.append("\n=== 相关文档内容 ===")
        for i, result in enumerate(vector_results[:3], 1):
            context_parts.append(f"文档{i} (相似度: {result['similarity']:.3f}):")
            context_parts.append(result['document'][:300] + "...")
            metadata = result.get('metadata', {})
            if 'title' in metadata:
                context_parts.append(f"标题: {metadata['title']}")
    
    # 添加图谱信息
    if graph_context:
        # 添加相关实体信息
        entities = graph_context.get('entities', [])
        if entities:
            context_parts.append("\n=== 相关实体信息 ===")
            for entity in entities[:3]:
                context_parts.append(f"实体: {entity.get('name', 'unknown')} (类型: {entity.get('type', 'unknown')})")
                relations = entity.get('relations', [])
                if relations:
                    rel_texts = [f"{r['relation']}→{r['target']}" for r in relations[:3]]
                    context_parts.append(f"关系: {', '.join(rel_texts)}")
        
        # 添加相关政策信息
        policies = graph_context.get('policies', [])
        if policies:
            context_parts.append("\n=== 相关政策信息 ===")
            for policy in policies[:2]:
                context_parts.append(f"政策: {policy.get('title', 'unknown')}")
                if 'issuing_agency' in policy:
                    context_parts.append(f"发布机构: {policy['issuing_agency']}")
                if 'related_entities' in policy:
                    context_parts.append(f"涉及实体: {', '.join(policy['related_entities'][:5])}")
    
    enhanced_context = "\n".join(context_parts)
    return enhanced_context
```

**Section sources**
- [graphrag_engine.py](file://backend/graphrag_engine.py#L218-L275) - *上下文构建逻辑*

### 最终提示词示例

构建的增强上下文最终作为提示词输入给大模型。

```
用户问题: 华侨经济文化合作试验区的管理机构是什么？

问题中的关键实体: 华侨经济文化合作试验区

=== 相关文档内容 ===
文档1 (相似度: 0.945):
华侨经济文化合作试验区深汕数字科创产业园运营管理办法...
标题: 华侨经济文化合作试验区深汕数字科创产业园运营管理办法

=== 相关实体信息 ===
实体: 华侨经济文化合作试验区 (类型: LOCATION)
关系: MANAGES→深汕数字科创产业园

=== 相关政策信息 ===
政策: 华侨经济文化合作试验区深汕数字科创产业园运营管理办法
发布机构: 汕头市东海岸投资建设有限公司
涉及实体: 华侨经济文化合作试验区, 深汕数字科创产业园
```

## 幻觉检测与可信度评估

### 幻觉检测器实现

`HallucinationDetector`类实现了多维度的答案可信度评估。

```python
class HallucinationDetector:
    """幻觉检测器 - 基于知识图谱验证"""
    
    def __init__(self, graph_query_engine, entity_extractor):
        self.graph_query = graph_query_engine
        self.entity_extractor = entity_extractor
        self.hallucination_threshold = float(os.getenv('HALLUCINATION_THRESHOLD', 0.7))
        
        # 权重配置
        self.weights = {
            'entity_consistency': 0.4,
            'relation_verification': 0.3,
            'content_overlap': 0.2,
            'semantic_coherence': 0.1
        }
```

**Section sources**
- [hallucination_detector.py](file://backend/hallucination_detector.py#L20-L40) - *幻觉检测器初始化*

### 多维度检测机制

幻觉检测器从四个维度评估答案质量：

```python
def detect_hallucination(self, answer: str, question: str, retrieved_docs: List[Dict], 
                       graph_context: Dict) -> Dict:
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
```

**Section sources**
- [hallucination_detector.py](file://backend/hallucination_detector.py#L41-L90) - *多维度检测逻辑*

### 可信度评分与风险等级

系统根据综合得分确定风险等级并生成警告信息。

```python
def _determine_risk_level(self, confidence: float) -> str:
    if confidence >= 0.8:
        return 'low'
    elif confidence >= 0.5:
        return 'medium'
    else:
        return 'high'

def _generate_warnings(self, entity_score: float, relation_score: float, 
                      content_score: float, coherence_score: float) -> List[str]:
    warnings = []
    if entity_score < 0.5:
        warnings.append("答案中包含未经验证的实体信息")
    if relation_score < 0.4:
        warnings.append("答案中的关系描述可能不准确")
    if content_score < 0.3:
        warnings.append("答案内容与检索文档相关性较低")
    if coherence_score < 0.4:
        warnings.append("答案的逻辑连贯性有待改善")
    return warnings
```

**Section sources**
- [hallucination_detector.py](file://backend/hallucination_detector.py#L290-L330) - *风险等级判断*

## 数据导入与图数据库构建

### 原始数据结构

原始政策法规数据存储在`database/华侨经济文化合作试验区.json`文件中，其结构为：

```json
{
  "title": "政策标题",
  "chapters": [
    {
      "title": "总则",
      "number": "第一章",
      "articles": [
        {
          "number": "第一条",
          "content": "具体内容..."
        }
      ]
    }
  ]
}
```

数据按"政策→章节→条款"的层级组织，与图数据库的节点层级设计完全对应。

**Section sources**
- [华侨经济文化合作试验区.json](file://database/华侨经济文化合作试验区.json#L1-L111)

### 图数据库节点与关系构建

`import_policy_data.py`脚本负责将JSON数据解析并导入Neo4j数据库。其核心逻辑包括：

1. **创建政策节点**：
```python
query = (
    "MERGE (p:Policy {policy_id: $policy_id}) "
    "SET p.title = $title, "
    "    p.publish_date = $publish_date, "
    "    p.publish_agency = $publish_agency, "
    "    p.doc_number = $doc_number "
)
```

2. **创建章节节点并建立关系**：
```python
section_query = (
    "MERGE (s:Section {section_id: $section_id}) "
    "SET s.title = $title, "
    "    s.content = $content "
    "MERGE (p:Policy {policy_id: $policy_id}) "
    "MERGE (s)-[:BELONGS_TO]->(p) "
)
```

3. **创建机构节点并建立发布关系**：
```python
org_query = (
    "MERGE (o:Organization {name: $org_name}) "
    "MERGE (p:Policy {policy_id: $policy_id}) "
    "MERGE (o)-[:PUBLISHES]->(p) "
)
```

系统构建了以下主要节点类型和关系：
- **节点类型**：Policy（政策）、Section（章节）、SubSection（子章节）、Organization（机构）
- **关系类型**：BELONGS_TO（属于）、PUBLISHES（发布）、ISSUED_BY（由...发布）

``mermaid
erDiagram
Policy ||--o{ Section : "包含"
Section ||--o{ SubSection : "包含"
Organization ||--o{ Policy : "发布"
Policy ||--o{ Organization : "由...发布"
Policy {
string policy_id PK
string title
string publish_date
string publish_agency
string doc_number
}
Section {
string section_id PK
string title
string content
}
SubSection {
string sub_section_id PK
string title
string content
}
Organization {
string name PK
}
```

**Diagram sources**
- [import_policy_data.py](file://scripts/import_policy_data.py#L314-L417)

**Section sources**
- [import_policy_data.py](file://scripts/import_policy_data.py#L1-L574)

## 系统架构图

``mermaid
graph TB
subgraph "前端"
UI[用户界面]
UI --> API
end
subgraph "后端"
API[API Server]
API --> Neo4j
API --> Ollama
API --> GraphRAG[GraphRAG引擎]
end
subgraph "数据库"
Neo4j[(Neo4j图数据库)]
end
subgraph "大模型"
Ollama[(Ollama大模型)]
end
subgraph "GraphRAG组件"
GraphRAG --> Vector[向量检索]
GraphRAG --> Graph[图谱查询]
GraphRAG --> Entity[实体提取]
GraphRAG --> Hallucination[幻觉检测]
end
UI --> API
API --> Neo4j
API --> Ollama
API --> GraphRAG
GraphRAG --> Neo4j
GraphRAG --> Ollama
Neo4j --> API
Ollama --> API
API --> UI
style UI fill:#f9f,stroke:#333
style API fill:#bbf,stroke:#333
style Neo4j fill:#f96,stroke:#333
style Ollama fill:#6f9,stroke:#333
style GraphRAG fill:#9cf,stroke:#333
```

**Diagram sources**
- [README.md](file://README.md#L1-L253)
- [api_server.py](file://backend/api_server.py#L1-L120)
- [graphrag_engine.py](file://backend/graphrag_engine.py#L1-L485)

## 技术决策分析

### 为何采用轻量级RAG而非微调模型

本项目选择轻量级RAG架构而非微调大模型，主要基于以下技术决策考量：

1. **成本效益**：微调大模型需要大量计算资源和标注数据，而RAG架构只需将现有政策法规数据导入图数据库，成本更低。

2. **数据更新便捷性**：当有新政策发布时，只需将新数据导入Neo4j即可，无需重新训练模型。RAG架构实现了知识库与模型的解耦。

3. **答案可解释性**：RAG架构能够提供明确的引用溯源，回答中可以明确指出信息来源的政策标题和具体条款，增强了回答的可信度。

4. **避免模型幻觉**：通过检索真实存在的政策法规内容作为上下文，可以有效减少大模型生成虚构内容（幻觉）的风险。

5. **技术成熟度**：Neo4j图数据库在处理结构化关系数据方面技术成熟，而Ollama使得本地部署和调用大模型变得简单，两者结合形成了稳定可靠的技术栈。

6. **扩展性**：未来可以轻松扩展为混合检索模式，例如在现有关键词匹配基础上，集成文本嵌入模型实现语义向量检索。

正如`软件著作权申请.md`中所述："结合图数据库和大模型技术，实现政策法规的结构化查询和语义化问答"，这一架构创新点正是本系统的核心价值所在。

**Section sources**
- [软件著作权申请.md](file://软件著作权申请.md#L1-L191)
- [README.md](file://README.md#L1-L253)