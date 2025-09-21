# EARAG-Eval API接口文档

## 📋 接口概述

本文档详细描述了EARAG-Eval多维度评估算法的API接口，包括请求参数、响应格式、使用示例和错误处理等信息。

## 🌐 基础信息

- **基础URL**: `http://localhost:5000`
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

## 🔑 核心API接口

### 1. 带EARAG-Eval评估的问答接口

#### 接口信息
- **URL**: `/api/ask/evaluated`
- **方法**: `POST`
- **功能**: 执行GraphRAG问答并进行EARAG-Eval多维度质量评估
- **认证**: 无需认证

#### 请求格式

```json
{
    "question": "华侨经济文化合作试验区的税收优惠政策有哪些？",
    "use_graph": true,
    "session_id": "optional_session_id_123"
}
```

#### 请求参数说明

| 参数名 | 类型 | 必填 | 描述 | 默认值 | 示例 |
|--------|------|------|------|--------|------|
| `question` | string | ✅ | 用户问题，长度限制1-1000字符 | - | "华侨经济文化合作试验区的税收优惠政策有哪些？" |
| `use_graph` | boolean | ❌ | 是否使用GraphRAG增强模式 | `true` | `true` |
| `session_id` | string | ❌ | 会话ID，用于多轮对话上下文 | - | "session_123456789" |

#### 响应格式

```json
{
    "answer": "华侨经济文化合作试验区在税收方面提供以下优惠政策：\n\n1. **企业所得税优惠**：符合条件的高新技术企业可享受15%的优惠税率...",
    "quality_score": 0.85,
    "quality_level": "优秀",
    "quality_warning": false,
    "evaluation_diagnosis": "整体评分: 0.850 (优秀) - 答案质量高，可以直接使用",
    "earag_evaluation": {
        "overall_score": 0.85,
        "quality_level": "优秀",
        "dimension_scores": {
            "entity_coverage": 0.9,
            "faithfulness": 0.8,
            "relevancy": 0.85,
            "sufficiency": 0.9,
            "hallucination": 0.15
        },
        "diagnosis": "整体评分: 0.850 (优秀) - 答案质量高，可以直接使用",
        "entity_analysis": {
            "question_entities": ["华侨经济文化合作试验区", "税收优惠政策"],
            "answer_entities": ["华侨经济文化合作试验区", "企业所得税", "增值税", "个人所得税"],
            "context_entities": ["华侨经济文化合作试验区", "优惠政策", "税收"],
            "missing_entities": [],
            "unverified_entities": []
        },
        "detailed_analysis": {
            "entity_coverage": {
                "score": 0.9,
                "diagnosis": []
            },
            "faithfulness": {
                "score": 0.8,
                "diagnosis": []
            },
            "relevancy": {
                "score": 0.85,
                "diagnosis": []
            },
            "sufficiency": {
                "score": 0.9,
                "diagnosis": []
            },
            "hallucination": {
                "score": 0.15,
                "diagnosis": []
            },
            "overall": {
                "score": 0.85,
                "quality_level": "优秀",
                "quality_description": "答案质量高，可以直接使用",
                "diagnosis": "整体评分: 0.850 (优秀) - 答案质量高，可以直接使用",
                "recommendations": [],
                "weights_used": {
                    "entity_coverage": 0.30,
                    "faithfulness": 0.25,
                    "relevancy": 0.15,
                    "sufficiency": 0.15,
                    "hallucination": -0.15
                }
            }
        },
        "processing_time": 2.34,
        "algorithm_version": "EARAG-Eval-1.0"
    },
    "traditional_confidence": {
        "confidence": 0.82,
        "risk_level": "low",
        "is_reliable": true,
        "warnings": [],
        "detailed_scores": {
            "entity_consistency": 0.85,
            "relation_verification": 0.8,
            "content_overlap": 0.9,
            "semantic_coherence": 0.75
        }
    },
    "sources": [
        {
            "type": "document",
            "title": "华侨经济文化合作试验区税收政策文件",
            "relevance": 0.92,
            "snippet": "企业所得税方面，符合条件的企业可享受15%的优惠税率..."
        },
        {
            "type": "graph_entity",
            "name": "华侨经济文化合作试验区",
            "type": "POLICY_ZONE",
            "relations": ["享受税收优惠", "促进华侨投资"]
        }
    ],
    "processing_time": 2.34,
    "question_entities": ["华侨经济文化合作试验区", "税收优惠政策"],
    "graph_enhanced": true,
    "session_id": "session_123456789",
    "recommendations": []
}
```

#### 响应参数说明

| 参数名 | 类型 | 描述 |
|--------|------|------|
| `answer` | string | RAG系统生成的答案内容 |
| `quality_score` | number | EARAG-Eval整体质量评分 (0-1) |
| `quality_level` | string | 质量等级: "优秀"/"良好"/"一般"/"较差" |
| `quality_warning` | boolean | 是否需要质量警告 (评分<0.7时为true) |
| `evaluation_diagnosis` | string | 综合诊断信息 |
| `earag_evaluation` | object | 详细的EARAG-Eval评估结果 |
| `earag_evaluation.overall_score` | number | 整体评分 (0-1) |
| `earag_evaluation.dimension_scores` | object | 各维度评分 |
| `earag_evaluation.dimension_scores.entity_coverage` | number | 实体覆盖率 (0-1) |
| `earag_evaluation.dimension_scores.faithfulness` | number | 事实忠实度 (0-1) |
| `earag_evaluation.dimension_scores.relevancy` | number | 答案相关性 (0-1) |
| `earag_evaluation.dimension_scores.sufficiency` | number | 上下文充分性 (0-1) |
| `earag_evaluation.dimension_scores.hallucination` | number | 幻觉率 (0-1，越低越好) |
| `earag_evaluation.entity_analysis` | object | 实体分析结果 |
| `earag_evaluation.detailed_analysis` | object | 各维度详细分析 |
| `traditional_confidence` | object | 传统幻觉检测结果 (用于对比) |
| `sources` | array | 答案来源信息 |
| `processing_time` | number | 处理耗时 (秒) |
| `recommendations` | array | 改进建议 (质量较低时提供) |

#### 质量等级说明

| 等级 | 评分范围 | 描述 | 建议 |
|------|----------|------|------|
| 优秀 | 0.8-1.0 | 答案质量高，实体覆盖完整，事实准确 | 可直接使用 |
| 良好 | 0.7-0.8 | 答案质量较好，可能有轻微不足 | 建议优化后使用 |
| 一般 | 0.6-0.7 | 答案质量一般，存在明显问题 | 需要改进 |
| 较差 | 0.0-0.6 | 答案质量差，不建议使用 | 建议重新生成 |

#### 使用示例

**cURL 请求示例:**
```bash
curl -X POST http://localhost:5000/api/ask/evaluated \
  -H "Content-Type: application/json" \
  -d '{
    "question": "华侨经济文化合作试验区的税收优惠政策有哪些？",
    "use_graph": true,
    "session_id": "demo_session_001"
  }'
```

**JavaScript 请求示例:**
```javascript
const response = await fetch('http://localhost:5000/api/ask/evaluated', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        question: '华侨经济文化合作试验区的税收优惠政策有哪些？',
        use_graph: true,
        session_id: 'demo_session_001'
    })
});

const result = await response.json();
console.log('质量评分:', result.quality_score);
console.log('答案:', result.answer);
```

**Python 请求示例:**
```python
import requests
import json

url = "http://localhost:5000/api/ask/evaluated"
payload = {
    "question": "华侨经济文化合作试验区的税收优惠政策有哪些？",
    "use_graph": True,
    "session_id": "demo_session_001"
}

response = requests.post(url, json=payload)
result = response.json()

print(f"质量评分: {result['quality_score']}")
print(f"质量等级: {result['quality_level']}")
print(f"答案: {result['answer']}")
```

## 🔗 其他相关接口

### 2. 传统GraphRAG问答接口 (无评估)

#### 接口信息
- **URL**: `/api/ask/enhanced`
- **方法**: `POST`
- **功能**: 执行GraphRAG问答，不进行EARAG-Eval评估

#### 请求格式
```json
{
    "question": "华侨经济文化合作试验区的税收优惠政策有哪些？",
    "use_graph": true,
    "return_confidence": true,
    "session_id": "optional_session_id"
}
```

### 3. 标准RAG问答接口

#### 接口信息
- **URL**: `/api/ask`
- **方法**: `POST`
- **功能**: 执行传统RAG问答

#### 请求格式
```json
{
    "question": "华侨经济文化合作试验区的税收优惠政策有哪些？",
    "session_id": "optional_session_id"
}
```

### 4. 实体分析接口

#### 接口信息
- **URL**: `/api/graph/analyze`
- **方法**: `POST`
- **功能**: 分析文本中的实体和关系

#### 请求格式
```json
{
    "text": "华侨经济文化合作试验区享受税收优惠政策",
    "extract_entities": true,
    "extract_relations": true
}
```

### 5. 系统状态接口

#### 接口信息
- **URL**: `/api/system/stats`
- **方法**: `GET`
- **功能**: 获取系统状态和统计信息

## ❌ 错误处理

### HTTP状态码

| 状态码 | 描述 | 场景 |
|--------|------|------|
| 200 | 成功 | 请求处理成功 |
| 400 | 请求错误 | 参数验证失败、格式错误 |
| 500 | 服务器错误 | 系统内部错误 |
| 503 | 服务不可用 | GraphRAG或EARAG-Eval服务不可用 |

### 错误响应格式

```json
{
    "error": "ValidationError",
    "message": "问题内容不能为空",
    "field": "question",
    "value": "",
    "timestamp": "2025-09-13T10:30:00Z",
    "request_id": "req_123456789"
}
```

### 常见错误处理

#### 1. 参数验证错误 (400)
```json
{
    "error": "ValidationError",
    "message": "问题长度超过限制，请限制在1000字符内",
    "field": "question"
}
```

#### 2. 服务不可用错误 (503)
```json
{
    "error": "GraphRAG功能不可用",
    "message": "请使用 /api/ask 接口访问传统RAG功能",
    "available_endpoints": ["/api/ask"]
}
```

#### 3. EARAG-Eval评估器不可用 (503)
```json
{
    "error": "EARAG-Eval评估器不可用",
    "message": "请使用 /api/ask/enhanced 接口访问增强问答功能",
    "available_endpoints": ["/api/ask", "/api/ask/enhanced"]
}
```

#### 4. 系统内部错误 (500)
```json
{
    "error": "SystemError",
    "message": "EARAG-Eval评估失败",
    "timestamp": "2025-09-13T10:30:00Z"
}
```

## 🔧 配置信息

### EARAG-Eval评估器配置

```json
{
    "weights": {
        "entity_coverage": 0.30,
        "faithfulness": 0.25,
        "relevancy": 0.15,
        "sufficiency": 0.15,
        "hallucination": -0.15
    },
    "thresholds": {
        "entity_coverage": 0.8,
        "faithfulness": 0.7,
        "relevancy": 0.7,
        "sufficiency": 0.8,
        "hallucination": 0.2,
        "overall": 0.7
    },
    "performance": {
        "timeout_seconds": 5,
        "max_text_length": 1000,
        "parallel_workers": 4
    }
}
```

### 评估维度详解

#### 维度1: 实体覆盖率 (Entity Coverage)
- **权重**: 30% (最重要维度)
- **计算方法**: `(问题实体 ∩ 答案实体) / 问题实体总数`
- **阈值**: 0.8
- **说明**: 评估答案对问题中关键政策实体的覆盖程度

#### 维度2: 事实忠实度 (Faithfulness)
- **权重**: 25%
- **计算方法**: LLM自评估 + Neo4j知识图谱验证
- **阈值**: 0.7
- **说明**: 检验答案内容与检索上下文的事实一致性

#### 维度3: 答案相关性 (Relevancy)
- **权重**: 15%
- **计算方法**: BGE-M3嵌入向量余弦相似度
- **阈值**: 0.7
- **说明**: 评估答案与问题的语义相关性

#### 维度4: 上下文充分性 (Context Sufficiency)
- **权重**: 15%
- **计算方法**: `(问题实体 ∩ 上下文实体) / 问题实体总数`
- **阈值**: 0.8
- **说明**: 评估检索上下文信息的完整性和充分性

#### 维度5: 幻觉率 (Hallucination Rate)
- **权重**: -15% (负权重，惩罚幻觉)
- **计算方法**: `基础幻觉率 + 0.5 * 实体幻觉率`
- **阈值**: 0.2 (低于此值较好)
- **说明**: 检测答案中的虚假或不准确信息

#### 维度6: 整体评分 (Overall Score)
- **计算方法**: 加权平均 + 质量分级
- **说明**: 综合所有维度得出最终质量评分和等级

## 📊 监控与诊断

### 性能指标

- **响应时间**: 通常2-8秒 (包含LLM调用)
- **评估准确性**: 算法逻辑准确性 > 95%
- **并发支持**: 支持多个用户同时评估
- **资源消耗**: 内存使用 < 500MB

### 诊断信息

评估结果中的`diagnosis`字段提供详细的质量诊断信息：

```json
{
    "diagnosis": "整体评分: 0.650 (一般) - 答案质量一般，需要改进 | 发现问题: 实体覆盖不足，遗漏关键实体: ['投资政策']; 答案与问题相关性较低"
}
```

## 🚀 最佳实践

### 1. 请求优化
- 问题描述要清晰具体，包含关键政策实体
- 合理使用`session_id`维持多轮对话上下文
- 根据需要选择是否启用图谱增强模式

### 2. 结果解读
- 关注`quality_score`和`quality_level`判断答案可用性
- 查看`entity_analysis`了解实体覆盖情况
- 参考`recommendations`进行质量改进

### 3. 错误处理
- 实现适当的重试机制处理网络问题
- 根据错误类型提供用户友好的提示
- 监控服务可用性状态

### 4. 集成建议
- 在生产环境中使用本地LLM服务提升性能
- 实现结果缓存机制减少重复计算
- 设置合理的超时时间和错误处理

---

## 📞 技术支持

如有疑问或需要技术支持，请参考：
- [EARAG-Eval实现总结文档](./EARAG_Eval_Implementation_Summary.md)
- [项目操作手册](./政策法规RAG问答系统操作手册.md)
- [测试脚本](./scripts/test_earag_evaluator.py)
- [演示脚本](./scripts/demo_earag_evaluator.py)