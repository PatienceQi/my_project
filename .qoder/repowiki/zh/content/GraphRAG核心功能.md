# GraphRAG核心功能

<cite>
**本文档引用文件**  
- [api_server.py](file://backend/api_server.py#L0-L877)
- [graphrag_engine.py](file://backend/graphrag_engine.py)
- [entity_extractor.py](file://backend/entity_extractor.py#L0-L491)
- [graph_query.py](file://backend/graph_query.py#L0-L430)
- [hallucination_detector.py](file://backend/hallucination_detector.py#L0-L434)
- [vector_retrieval.py](file://backend/vector_retrieval.py#L0-L433)
- [connections.py](file://backend/connections.py)
- [validators.py](file://backend/validators.py)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构概览](#架构概览)
5. [详细组件分析](#详细组件分析)
6. [依赖分析](#依赖分析)
7. [性能考量](#性能考量)
8. [故障排除指南](#故障排除指南)
9. [结论](#结论)

## 简介
**GraphRAG核心功能** 是一个基于知识图谱的增强型检索增强生成（RAG）系统，专为政策法规问答场景设计。该系统结合了传统向量检索与知识图谱推理能力，通过实体识别、关系抽取和幻觉检测等技术，显著提升了问答系统的准确性、可解释性和可靠性。

系统支持两种模式：传统RAG模式和GraphRAG增强模式。在增强模式下，系统不仅返回答案，还提供置信度评分、风险等级、来源依据和潜在警告，帮助用户判断答案的可信度。整个系统采用模块化设计，各组件职责清晰，便于维护和扩展。

## 项目结构
本项目采用分层架构，主要分为前端、后端、数据和脚本四大模块。后端是GraphRAG功能的核心实现区域。

``mermaid
graph TB
subgraph "前端"
index_html["index.html"]
index_graphrag_html["index_graphrag.html"]
diagnostic_html["diagnostic.html"]
end
subgraph "后端"
api_server["api_server.py"]
graphrag_engine["graphrag_engine.py"]
entity_extractor["entity_extractor.py"]
graph_query["graph_query.py"]
hallucination_detector["hallucination_detector.py"]
vector_retrieval["vector_retrieval.py"]
connections["connections.py"]
validators["validators.py"]
end
subgraph "数据"
database["database/"]
data["data/"]
end
subgraph "脚本"
scripts["scripts/"]
setup_graphrag["setup_graphrag.py"]
start_server["start_server.py"]
end
api_server --> graphrag_engine
graphrag_engine --> entity_extractor
graphrag_engine --> graph_query
graphrag_engine --> hallucination_detector
graphrag_engine --> vector_retrieval
graphrag_engine --> connections
api_server --> connections
api_server --> validators
```

**图示来源**  
- [api_server.py](file://backend/api_server.py#L0-L877)
- [graphrag_engine.py](file://backend/graphrag_engine.py)
- [project_structure](file://.)

**本节来源**  
- [api_server.py](file://backend/api_server.py#L0-L877)
- [project_structure](file://.)

## 核心组件
GraphRAG系统由多个核心组件构成，共同实现增强型问答功能。主要组件包括：

- **GraphRAGEngine**：GraphRAG引擎主类，协调各组件工作流程。
- **EntityExtractor**：实体关系提取器，负责从文本中识别实体和关系。
- **GraphQueryEngine**：图谱查询引擎，与Neo4j数据库交互执行复杂图查询。
- **HallucinationDetector**：幻觉检测器，多维度评估答案的可信度。
- **VectorRetriever**：向量检索器，基于Chroma和Ollama实现语义搜索。
- **API Server**：提供RESTful API接口，暴露GraphRAG功能。

这些组件通过清晰的接口进行通信，形成了一个高内聚、低耦合的系统架构。

**本节来源**  
- [graphrag_engine.py](file://backend/graphrag_engine.py)
- [entity_extractor.py](file://backend/entity_extractor.py#L0-L491)
- [graph_query.py](file://backend/graph_query.py#L0-L430)
- [hallucination_detector.py](file://backend/hallucination_detector.py#L0-L434)
- [vector_retrieval.py](file://backend/vector_retrieval.py#L0-L433)

## 架构概览
GraphRAG系统采用微服务式架构，各功能模块高度解耦，通过API进行通信。系统整体架构如下图所示：

``mermaid
graph TD
Client[客户端] --> API[API服务器]
subgraph "后端服务"
API --> GEngine[GraphRAG引擎]
subgraph "数据层"
GEngine --> VRetriever[向量检索器]
GEngine --> GQuery[图谱查询引擎]
VRetriever --> Chroma[(Chroma向量数据库)]
GQuery --> Neo4j[(Neo4j图数据库)]
end
subgraph "处理层"
GEngine --> EExtractor[实体提取器]
GEngine --> HDetector[幻觉检测器]
EExtractor --> Ollama[(Ollama服务)]
HDetector --> GQuery
HDetector --> EExtractor
end
end
API --> Session[会话管理器]
API --> Health[健康检查器]
style GEngine fill:#f9f,stroke:#333
style EExtractor fill:#bbf,stroke:#333
style HDetector fill:#f96,stroke:#333
```

**图示来源**  
- [api_server.py](file://backend/api_server.py#L0-L877)
- [graphrag_engine.py](file://backend/graphrag_engine.py)
- [entity_extractor.py](file://backend/entity_extractor.py#L0-L491)
- [graph_query.py](file://backend/graph_query.py#L0-L430)
- [hallucination_detector.py](file://backend/hallucination_detector.py#L0-L434)
- [vector_retrieval.py](file://backend/vector_retrieval.py#L0-L433)

## 详细组件分析
### GraphRAG引擎分析
GraphRAG引擎是整个系统的核心协调者，负责整合向量检索、图谱查询、实体提取和幻觉检测等功能，生成高质量的增强型回答。

#### 类图
``mermaid
classDiagram
class GraphRAGEngine {
+answer_question(question : str, use_graph : bool, return_confidence : bool) Dict
+get_system_stats() Dict
-retrieve_relevant_docs(query : str) List[Dict]
-extract_context_entities(text : str) List[Dict]
-build_enhanced_context(question : str, docs : List[Dict], entities : List[Dict]) str
-generate_answer_with_llm(prompt : str) str
-evaluate_answer_reliability(answer : str, question : str, docs : List[Dict], graph_context : Dict) Dict
}
class EntityExtractor {
+extract_entities(text : str) List[Dict]
+extract_relations(text : str, entities : List[Dict]) List[Dict]
+extract_entities_from_question(question : str) List[str]
}
class GraphQueryEngine {
+query_entities_by_name(entity_names : List[str]) List[Dict]
+query_policies_by_entities(entity_names : List[str]) List[Dict]
+query_entity_relationships(entity_name : str, max_hops : int) Dict
+search_similar_policies(query_text : str) List[Dict]
+get_policy_context(policy_title : str) Dict
+verify_entity_relations(entities : List[str], relations : List[str]) List[Dict]
+get_graph_statistics() Dict
}
class HallucinationDetector {
+detect_hallucination(answer : str, question : str, retrieved_docs : List[Dict], graph_context : Dict) Dict
-check_entity_consistency(answer : str, graph_context : Dict) float
-verify_relations(answer : str, graph_context : Dict) float
-check_content_overlap(answer : str, retrieved_docs : List[Dict]) float
-check_semantic_coherence(answer : str, question : str) float
-determine_risk_level(confidence : float) str
-generate_warnings(entity_score : float, relation_score : float, content_score : float, coherence_score : float) List[str]
}
class VectorRetriever {
+add_documents(documents : List[Dict]) bool
+search(query : str, top_k : int) List[Dict]
+split_text(text : str) List[str]
}
GraphRAGEngine --> EntityExtractor : "使用"
GraphRAGEngine --> GraphQueryEngine : "使用"
GraphRAGEngine --> HallucinationDetector : "使用"
GraphRAGEngine --> VectorRetriever : "使用"
```

**图示来源**  
- [graphrag_engine.py](file://backend/graphrag_engine.py)
- [entity_extractor.py](file://backend/entity_extractor.py#L0-L491)
- [graph_query.py](file://backend/graph_query.py#L0-L430)
- [hallucination_detector.py](file://backend/hallucination_detector.py#L0-L434)
- [vector_retrieval.py](file://backend/vector_retrieval.py#L0-L433)

#### 工作流程
``mermaid
sequenceDiagram
participant Client as "客户端"
participant API as "API服务器"
participant Engine as "GraphRAG引擎"
participant Extractor as "实体提取器"
participant Retriever as "向量检索器"
participant Query as "图谱查询引擎"
participant Detector as "幻觉检测器"
participant LLM as "Ollama LLM"
Client->>API : POST /api/ask/enhanced
API->>Engine : answer_question()
Engine->>Extractor : extract_entities_from_question()
Extractor-->>Engine : 问题实体列表
Engine->>Retriever : search()
Retriever-->>Engine : 相关文档
Engine->>Query : query_entities_by_name()
Query-->>Engine : 实体信息
Engine->>Query : query_policies_by_entities()
Query-->>Engine : 政策信息
Engine->>Extractor : extract_entities()
Extractor-->>Engine : 文档实体
Engine->>Extractor : extract_relations()
Extractor-->>Engine : 实体关系
Engine->>LLM : generate_answer_with_llm()
LLM-->>Engine : 原始答案
Engine->>Detector : detect_hallucination()
Detector-->>Engine : 可信度评估
Engine-->>API : 返回增强答案
API-->>Client : JSON响应
```

**图示来源**  
- [api_server.py](file://backend/api_server.py#L0-L877)
- [graphrag_engine.py](file://backend/graphrag_engine.py)
- [entity_extractor.py](file://backend/entity_extractor.py#L0-L491)
- [graph_query.py](file://backend/graph_query.py#L0-L430)
- [hallucination_detector.py](file://backend/hallucination_detector.py#L0-L434)
- [vector_retrieval.py](file://backend/vector_retrieval.py#L0-L433)

**本节来源**  
- [graphrag_engine.py](file://backend/graphrag_engine.py)
- [api_server.py](file://backend/api_server.py#L0-L877)

### 实体提取器分析
实体提取器负责从政策文本中识别关键实体（如机构、政策、地点等）及其相互关系，为知识图谱构建提供基础数据。

#### 处理流程
``mermaid
flowchart TD
Start([开始]) --> ExtractEntities["提取实体"]
ExtractEntities --> BuildEntityPrompt["构建实体提取提示"]
BuildEntityPrompt --> CallOllama["调用Ollama API"]
CallOllama --> ParseEntityResponse["解析实体响应"]
ParseEntityResponse --> FilterByConfidence["按置信度过滤"]
FilterByConfidence --> ReturnEntities["返回实体列表"]
Start --> ExtractRelations["提取关系"]
ExtractRelations --> BuildRelationPrompt["构建关系提取提示"]
BuildRelationPrompt --> CallOllama
CallOllama --> ParseRelationResponse["解析关系响应"]
ParseRelationResponse --> ValidateRelations["验证关系有效性"]
ValidateRelations --> ReturnRelations["返回关系列表"]
style Start fill:#f9f,stroke:#333
style ReturnEntities fill:#9f9,stroke:#333
style ReturnRelations fill:#9f9,stroke:#333
```

**图示来源**  
- [entity_extractor.py](file://backend/entity_extractor.py#L0-L491)

**本节来源**  
- [entity_extractor.py](file://backend/entity_extractor.py#L0-L491)

### 图谱查询引擎分析
图谱查询引擎封装了与Neo4j数据库的交互逻辑，提供了一系列高级查询接口，支持实体查询、关系查询、路径查询等复杂操作。

#### 查询类型
``mermaid
graph TD
A[图谱查询引擎] --> B[实体查询]
A --> C[政策查询]
A --> D[关系网络查询]
A --> E[文本相似度搜索]
A --> F[上下文获取]
A --> G[关系验证]
A --> H[统计信息]
B --> B1["query_entities_by_name()"]
C --> C1["query_policies_by_entities()"]
D --> D1["query_entity_relationships()"]
E --> E1["search_similar_policies()"]
F --> F1["get_policy_context()"]
G --> G1["verify_entity_relations()"]
H --> H1["get_graph_statistics()"]
```

**图示来源**  
- [graph_query.py](file://backend/graph_query.py#L0-L430)

**本节来源**  
- [graph_query.py](file://backend/graph_query.py#L0-L430)

### 幻觉检测器分析
幻觉检测器是GraphRAG系统的核心创新点，通过多维度评估机制检测和量化答案中的潜在幻觉，确保输出的可靠性。

#### 检测维度
``mermaid
pie
title 幻觉检测权重分配
“实体一致性” : 40
“关系验证” : 30
“内容重叠” : 20
“语义连贯性” : 10
```

#### 评估流程
``mermaid
flowchart TD
Start([开始]) --> EntityCheck["实体一致性检查"]
EntityCheck --> RelationCheck["关系验证检查"]
RelationCheck --> ContentCheck["内容重叠度检查"]
ContentCheck --> CoherenceCheck["语义连贯性检查"]
CoherenceCheck --> CalculateScore["计算综合可信度"]
CalculateScore --> DetermineRisk["确定风险等级"]
DetermineRisk --> GenerateWarnings["生成警告信息"]
GenerateWarnings --> ReturnResult["返回检测结果"]
```

**图示来源**  
- [hallucination_detector.py](file://backend/hallucination_detector.py#L0-L434)

**本节来源**  
- [hallucination_detector.py](file://backend/hallucination_detector.py#L0-L434)

### 向量检索器分析
向量检索器基于Chroma向量数据库和Ollama嵌入服务，实现了高效的语义检索功能，是传统RAG模式的基础。

#### 检索流程
``mermaid
flowchart TD
Start([开始]) --> SplitText["文本分块"]
SplitText --> GetEmbeddings["获取嵌入向量"]
GetEmbeddings --> SearchSimilar["相似度搜索"]
SearchSimilar --> ReturnResults["返回结果"]
subgraph "嵌入服务"
GetEmbeddings --> Ollama["Ollama远程服务"]
GetEmbeddings --> Local["本地sentence-transformers"]
end
```

**图示来源**  
- [vector_retrieval.py](file://backend/vector_retrieval.py#L0-L433)

**本节来源**  
- [vector_retrieval.py](file://backend/vector_retrieval.py#L0-L433)

## 依赖分析
GraphRAG系统依赖于多个外部服务和库，形成了一个复杂的依赖网络。

``mermaid
graph TD
GEngine[GraphRAG引擎] --> EExtractor[实体提取器]
GEngine --> GQuery[图谱查询引擎]
GEngine --> HDetector[幻觉检测器]
GEngine --> VRetriever[向量检索器]
EExtractor --> OllamaLLM[Ollama LLM]
GQuery --> Neo4j[Neo4j数据库]
VRetriever --> Chroma[Chroma数据库]
VRetriever --> OllamaEmbed[Ollama嵌入服务]
HDetector --> GQuery
HDetector --> EExtractor
subgraph "外部服务"
OllamaLLM
OllamaEmbed
Neo4j
Chroma
end
style OllamaLLM fill:#f96,stroke:#333
style OllamaEmbed fill:#f96,stroke:#333
style Neo4j fill:#69f,stroke:#333
style Chroma fill:#69f,stroke:#333
```

**图示来源**  
- [graphrag_engine.py](file://backend/graphrag_engine.py)
- [entity_extractor.py](file://backend/entity_extractor.py#L0-L491)
- [graph_query.py](file://backend/graph_query.py#L0-L430)
- [hallucination_detector.py](file://backend/hallucination_detector.py#L0-L434)
- [vector_retrieval.py](file://backend/vector_retrieval.py#L0-L433)

**本节来源**  
- [graphrag_engine.py](file://backend/graphrag_engine.py)
- [connections.py](file://backend/connections.py)

## 性能考量
GraphRAG系统的性能受多个因素影响，主要包括：

- **Ollama服务延迟**：实体提取和答案生成依赖远程Ollama服务，网络延迟是主要性能瓶颈。
- **图谱查询复杂度**：复杂的关系查询可能涉及多跳遍历，影响响应时间。
- **向量检索规模**：向量数据库的大小直接影响检索速度。
- **文本分块策略**：分块大小和重叠度影响嵌入生成和检索效率。

系统通过以下方式优化性能：
- 使用连接池管理数据库连接
- 对LLM调用进行错误重试和回退
- 实现批量嵌入向量生成
- 设置合理的查询结果限制

## 故障排除指南
### 常见问题及解决方案
**问题**：GraphRAG功能不可用，返回503错误  
**原因**：GraphRAG模块导入失败或引擎初始化失败  
**解决方案**：检查`backend/graphrag_engine.py`文件是否存在，确认依赖库已安装

**问题**：实体提取失败，日志显示连接错误  
**原因**：尝试连接本地Ollama服务而非远程服务  
**解决方案**：检查环境变量配置，确保`LLM_BINDING_HOST`指向远程服务地址

**问题**：Neo4j连接失败  
**原因**：数据库配置错误或服务未启动  
**解决方案**：检查`.env`文件中的`NEO4J_URI`、`NEO4J_USERNAME`、`NEO4J_PASSWORD`配置

**问题**：向量检索返回空结果  
**原因**：向量数据库中无数据或嵌入模型不匹配  
**解决方案**：运行`import_policy_data.py`脚本导入数据，确认嵌入模型一致性

**问题**：幻觉检测器报错  
**原因**：缺少jieba分词库  
**解决方案**：执行`pip install jieba`安装依赖

### API错误码说明
| 错误码 | 错误类型 | 说明 |
|--------|----------|------|
| 400 | ValidationError | 请求参数验证失败 |
| 404 | SessionError | 会话不存在或已过期 |
| 500 | SystemError | 系统内部错误 |
| 503 | DatabaseError | 数据库服务不可用 |
| 503 | LLMServiceError | LLM服务调用失败 |

**本节来源**  
- [api_server.py](file://backend/api_server.py#L0-L877)
- [exceptions.py](file://backend/exceptions.py)
- [validators.py](file://backend/validators.py)

## 结论
GraphRAG核心功能通过整合知识图谱技术和传统RAG方法，构建了一个更加智能、可靠和可解释的政策法规问答系统。系统采用模块化设计，各组件职责清晰，易于维护和扩展。

核心优势包括：
- **增强的准确性**：通过知识图谱验证答案的实体和关系
- **可靠的可信度评估**：多维度幻觉检测机制量化答案风险
- **丰富的上下文信息**：返回答案的同时提供来源依据和警告信息
- **灵活的架构设计**：支持传统RAG和GraphRAG两种模式

未来可优化方向包括：
- 引入更先进的图神经网络进行关系推理
- 实现增量式知识图谱更新
- 优化向量检索与图谱查询的融合策略
- 增强多轮对话的上下文理解能力