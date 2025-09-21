# API接口文档

<cite>
**本文档引用的文件**  
- [api_server.py](file://backend/api_server.py#L1-L877) - *更新了GraphRAG增强API*
- [hallucination_detector.py](file://backend/hallucination_detector.py#L1-L434) - *新增幻觉检测器实现*
- [graphrag_engine.py](file://backend/graphrag_engine.py#L1-L500) - *GraphRAG引擎核心逻辑*
- [index_graphrag.html](file://frontend/index_graphrag.html#L1-L823) - *GraphRAG前端界面*
- [test_enhanced_features.py](file://scripts/test_enhanced_features.py#L1-L300) - *增强功能测试*
</cite>

## 更新摘要
**变更内容**   
- 在`/api/ask/enhanced`端点中新增了可信度、风险等级等响应字段
- 增加了对GraphRAG增强问答API的详细说明
- 更新了响应结构定义，包含confidence、risk_level等新字段
- 新增了GraphRAG前端调用示例
- 添加了幻觉检测机制的技术说明

## 目录
1. [简介](#简介)
2. [API端点说明](#api端点说明)
3. [请求与响应结构](#请求与响应结构)
4. [状态码说明](#状态码说明)
5. [调用示例](#调用示例)
6. [性能与延迟](#性能与延迟)
7. [安全与部署说明](#安全与部署说明)

## 简介
本系统是一个基于RAG（检索增强生成）架构的政策法规智能问答系统，旨在通过自然语言查询为用户提供精准的政策法规解答。系统后端采用Flask构建RESTful API，结合Ollama大语言模型与Neo4j图数据库，实现对结构化政策数据的语义检索与智能生成。前端为单页Web应用，用户可通过浏览器进行交互式问答。

系统核心流程为：用户提问 → 后端从Neo4j中检索相关法规条文 → 将上下文注入提示词 → 调用Ollama模型生成回答 → 返回结构化响应。本API文档详细说明系统唯一的API端点 `/api/ask` 的使用方式。

**Section sources**
- [api_server.py](file://backend/api_server.py#L1-L120)
- [index.html](file://frontend/index.html#L1-L254)

## API端点说明
该系统提供一个RESTful API端点，用于接收用户问题并返回基于政策法规知识库的智能回答。

- **HTTP方法**: `POST`
- **请求URL**: `/api/ask`
- **功能描述**: 接收用户输入的自然语言问题，从政策法规数据库中检索相关信息，并利用大语言模型生成准确、可溯源的回答。

该端点是系统前后端交互的核心，被前端Web界面和测试脚本共同调用。此外，系统还提供了`/api/ask/enhanced`端点，支持GraphRAG增强功能，可返回答案可信度、风险等级等评估信息。

**Section sources**
- [api_server.py](file://backend/api_server.py#L115-L119)
- [test_backend_response.py](file://scripts/test_backend_response.py#L5-L7)
- [index.html](file://frontend/index.html#L131-L132)

## 请求与响应结构

### 请求体（Request Body）
请求必须为JSON格式，包含以下字段：

```json
{
  "question": "汕华管委规第一章第一条的主要内容是什么"
}
```

**请求字段说明**:
- **question**: 字符串类型，必填。表示用户提出的问题，系统将基于此问题在政策法规库中进行语义检索。

### 响应体（Response Body）
成功响应返回JSON对象，包含以下字段：

```json
{
  "answer": "根据《华侨经济文化合作试验区深汕数字科创产业园运营管理办法》第一章第一条，该办法旨在贯彻市委、市政府决策部署，加快汕头华侨经济文化合作试验区产业发展聚集，引导和鼓励数字科创产业落户，助推产业高质量发展。",
  "entities": [
    {
      "policy_title": "华侨经济文化合作试验区深汕数字科创产业园\n\n运营管理办法",
      "section_title": "第一条",
      "content": "为贯彻市委、市政府决策部署，进一步加快汕头华 侨经济文化合作试验区（以下简称华侨试验区）产业发展聚集， 引导和鼓励数字科创产业落户华侨试验区，助推华侨试验区产 业高质量发展。根据有关法律法规，制定本办法。",
      "agency": "未知机构",
      "relation": "发布单位"
    }
  ],
  "confidence": 0.85,
  "risk_level": "low",
  "is_reliable": true,
  "warnings": [
    "答案中包含未经验证的实体信息"
  ],
  "processing_time": 2.3
}
```

**响应字段说明**:
- **answer**: 字符串类型。由大语言模型生成的最终回答文本，内容简洁、准确，并引用了具体的政策来源。
- **entities**: 对象数组。包含所有被检索到并用于生成回答的相关政策法规条目，每个条目包含政策标题、章节/条款标题、具体内容、发布机构等信息，用于回答的可溯源性。
- **confidence**: 数值类型（0-1）。表示答案的可信度评分，由幻觉检测器基于实体一致性、关系验证、内容重叠度和语义连贯性四个维度计算得出。
- **risk_level**: 字符串类型。风险等级，分为"low"（低）、"medium"（中）、"high"（高），根据可信度评分确定。
- **is_reliable**: 布尔类型。表示答案是否可靠，当可信度评分高于阈值（默认0.7）时为true。
- **warnings**: 字符串数组。包含检测到的潜在问题警告信息。
- **processing_time**: 数值类型。处理时间（秒），用于性能监控。

**Section sources**
- [api_server.py](file://backend/api_server.py#L70-L88)
- [hallucination_detector.py](file://backend/hallucination_detector.py#L79-L112)
- [index.html](file://frontend/index.html#L205-L225)

## 状态码说明
API调用可能返回以下HTTP状态码：

| 状态码 | 含义 | 说明 |
| :--- | :--- | :--- |
| **200** | OK | 请求成功。响应体包含生成的答案和引用的政策来源。 |
| **400** | Bad Request | 请求无效。通常因为请求体中缺少`question`字段或JSON格式错误。 |
| **500** | Internal Server Error | 服务器内部错误。可能由于数据库连接失败、Ollama模型调用异常等后端问题导致。 |
| **503** | Service Unavailable | 服务不可用。当GraphRAG功能不可用时返回此状态码。 |

**Section sources**
- [api_server.py](file://backend/api_server.py#L117-L118)

## 调用示例

### curl命令示例
以下是一个使用curl命令调用API的示例：

```bash
curl -X POST http://127.0.0.1:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "入驻深汕数字科创产业园需要满足哪些条件？"}'
```

### Postman请求示例
在Postman中配置请求：
- **Method**: `POST`
- **URL**: `http://127.0.0.1:5000/api/ask`
- **Body** (选择`raw`和`JSON`):
```json
{
  "question": "产业园的退出机制有哪些？"
}
```

### 前端JavaScript调用示例
前端通过`fetch` API调用后端服务：

```javascript
const response = await fetch('http://127.0.0.1:5000/api/ask', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question: '您的问题' }),
});
const data = await response.json();
console.log(data.answer); // 输出回答
```

### GraphRAG增强API调用示例
使用GraphRAG增强API获取可信度评估：

```javascript
const response = await fetch('http://127.0.0.1:5000/api/ask/enhanced', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({ 
        question: '您的问题',
        return_confidence: true
    }),
});
const data = await response.json();
console.log(`回答: ${data.answer}`);
console.log(`可信度: ${data.confidence}`);
console.log(`风险等级: ${data.risk_level}`);
```

**Section sources**
- [test_backend_response.py](file://scripts/test_backend_response.py#L5-L15)
- [index.html](file://frontend/index.html#L187-L202)
- [index_graphrag.html](file://frontend/index_graphrag.html#L487-L521)

## 性能与延迟
- **预期性能**: API的响应时间主要受Ollama大语言模型的推理速度影响。在本地部署且模型已加载的情况下，典型响应延迟在1-5秒之间。
- **影响因素**: 
  - **模型加载时间**: 首次调用时，Ollama需要加载模型到内存，此过程可能耗时较长（数十秒）。
  - **网络延迟**: 若Ollama服务部署在远程服务器，网络延迟会显著增加总响应时间。
  - **查询复杂度**: 问题越复杂，模型生成回答所需的时间可能越长。
- **优化建议**: 可通过使用更轻量级的模型（如`mistral:7b`）或在高性能GPU上运行Ollama来降低延迟。

**Section sources**
- [api_server.py](file://backend/api_server.py#L21-L24)
- [requirements.txt](file://requirements.txt#L7)

## 安全与部署说明
- **认证机制**: 该API端点**无任何认证或授权机制**。它依赖于内网部署的物理安全，仅允许受信任的内部网络访问。
- **部署场景**: 适用于内网或私有云环境，不建议直接暴露在公网。
- **环境配置**: 系统通过`.env`文件或环境变量配置关键参数，包括：
  - `LLM_MODEL`: 指定使用的Ollama模型（默认`mistral:latest`）。
  - `LLM_BINDING_HOST`: 指定Ollama服务的地址。
  - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`: 配置Neo4j数据库连接。
- **技术栈**: 基于Python 3，核心依赖包括Flask（Web框架）、Flask-CORS（跨域支持）、ollama（Ollama API客户端）和neo4j（Neo4j数据库驱动）。
- **可信度评估机制**: 系统通过`hallucination_detector.py`中的幻觉检测器计算答案可信度，综合考虑实体一致性（权重0.4）、关系验证（权重0.3）、内容重叠度（权重0.2）和语义连贯性（权重0.1）四个维度。

**Section sources**
- [api_server.py](file://backend/api_server.py#L16-L31)
- [requirements.txt](file://requirements.txt#L1-L7)
- [hallucination_detector.py](file://backend/hallucination_detector.py#L1-L434)