# GraphRAG政策法规问答系统 - 部署与使用指南

## 项目概述

本项目是基于GraphRAG（图谱增强检索生成）技术的政策法规问答系统，集成了向量检索、知识图谱、实体关系提取和幻觉检测等先进技术，提供更准确、可信的政策法规问答服务。

### 主要特性

- 🚀 **GraphRAG增强**: 结合向量检索和知识图谱的双重检索策略
- 🧠 **智能实体提取**: 基于Ollama大模型的命名实体识别和关系提取
- 🛡️ **幻觉检测**: 多维度验证答案可信度，减少AI幻觉
- 📊 **可视化界面**: 支持可信度显示、来源追溯和对比分析
- 🔄 **双模式支持**: 传统RAG和GraphRAG模式可切换

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面      │    │   Flask API     │    │   GraphRAG引擎   │
│                 │    │                 │    │                 │
│ • GraphRAG界面  │◄──►│ • 增强API接口   │◄──►│ • 向量检索      │
│ • 可信度显示    │    │ • 对比分析      │    │ • 图谱查询      │
│ • 模式切换      │    │ • 实体分析      │    │ • 幻觉检测      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲                        ▲
                                │                        │
                                ▼                        ▼
                        ┌─────────────────┐    ┌─────────────────┐
                        │   数据存储      │    │   AI服务        │
                        │                 │    │                 │
                        │ • Neo4j图谱     │    │ • Ollama LLM    │
                        │ • Chroma向量库  │    │ • 实体提取      │
                        │ • 政策文档      │    │ • 关系提取      │
                        └─────────────────┘    └─────────────────┘
```

## 快速开始

### 方式一：简化安装（推荐用于测试）

1. **运行安装脚本**
```bash
# 在项目根目录执行
python setup_graphrag.py
```

2. **运行基础测试**
```bash
python test_graphrag_basic.py
```

### 方式二：完整安装

#### 1. 环境准备

**Python环境**
```bash
# 使用conda创建虚拟环境
conda create -n rag python=3.12
conda activate rag

# 或使用venv
python -m venv rag_env
# Windows: rag_env\Scripts\activate
# Linux/Mac: source rag_env/bin/activate
```

**安装依赖**
```bash
pip install -r requirements.txt
```

#### 2. 服务配置

**Neo4j数据库**
- 下载并安装 [Neo4j Desktop](https://neo4j.com/download/)
- 创建新数据库，记录连接信息

**Ollama服务**
- 安装 [Ollama](https://ollama.ai/)
- 拉取模型：`ollama pull llama3.2:latest`
- 启动服务：`ollama serve`

#### 3. 配置文件

编辑 `.env` 文件：
```env
# LLM配置
LLM_BINDING=ollama
LLM_MODEL=llama3.2:latest
LLM_BINDING_HOST=http://120.232.79.82:11434  # 修改为您的Ollama地址

# Neo4j配置  
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password  # 修改为您的密码

# GraphRAG配置
CHROMA_PERSIST_DIR=./data/chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2
GRAPH_RETRIEVAL_TOP_K=5
VECTOR_RETRIEVAL_TOP_K=5
CONFIDENCE_THRESHOLD=0.4
```

#### 4. 数据导入

**导入测试数据**
```bash
# 导入到Neo4j和向量数据库
python scripts/import_graphrag_data.py
```

**或使用传统导入（仅Neo4j）**
```bash
python scripts/import_policy_data.py
```

## 系统启动

### 启动API服务

```bash
# 推荐方式：使用统一启动脚本
python start_server.py

# 或直接启动
python backend/api_server.py
```

服务启动后访问：
- 传统界面：`http://127.0.0.1:5000/frontend/index.html`
- GraphRAG界面：`http://127.0.0.1:5000/frontend/index_graphrag.html`
- API文档：`http://127.0.0.1:5000/health`

### 系统测试

```bash
# 综合系统测试
python scripts/test_graphrag_system.py

# 功能测试
python scripts/test_backend_response.py

# 连接测试
python scripts/test_neo4j_connection.py
python scripts/test_ollama_connection.py
```

## API接口说明

### 传统RAG接口

**POST** `/api/ask`
```json
{
  "question": "华侨试验区的管理机构是什么？",
  "session_id": "可选会话ID"
}
```

### GraphRAG增强接口

**POST** `/api/ask/enhanced`
```json
{
  "question": "华侨试验区的管理机构是什么？",
  "use_graph": true,
  "return_confidence": true,
  "session_id": "可选会话ID"
}
```

**响应示例**
```json
{
  "answer": "华侨经济文化合作试验区的管理机构是...",
  "confidence": 0.85,
  "risk_level": "low",
  "is_reliable": true,
  "sources": [
    {
      "type": "document",
      "title": "政策文档标题",
      "relevance": 0.9
    }
  ],
  "warnings": [],
  "processing_time": 2.3
}
```

### 实体分析接口

**POST** `/api/graph/analyze`
```json
{
  "text": "政策文本内容",
  "extract_entities": true,
  "extract_relations": true
}
```

### 对比分析接口

**POST** `/api/compare`
```json
{
  "question": "用户问题"
}
```

### 系统状态接口

**GET** `/api/system/stats`

## 实验评估

### 运行对比实验

```bash
# 执行GraphRAG vs 传统RAG对比实验
python scripts/implement_evaluation.py
```

### 查看实验结果

实验结果保存在 `evaluation_results/` 目录：
- `comparison_experiment_*.json`: 详细实验数据
- `experiment_report_*.md`: 实验报告

### 实验指标

- **准确性**: 答案质量和实体匹配度
- **可靠性**: 幻觉率和可信度评分
- **效率**: 响应时间和处理性能
- **覆盖度**: 信息完整性和来源数量

## 使用技巧

### 1. 模式选择

- **传统RAG**: 适合简单查询，响应速度快
- **GraphRAG**: 适合复杂推理，准确性更高

### 2. 可信度解读

- **0.8+**: 高可信度，信息准确可靠
- **0.5-0.8**: 中等可信度，建议核实
- **0.5-**: 低可信度，需要谨慎对待

### 3. 警告处理

- 实体未验证：答案可能包含不准确信息
- 关系不准确：逻辑推理可能有误
- 内容相关性低：答案可能偏离主题

## 故障排除

### 常见问题

**1. GraphRAG功能不可用**
- 检查Ollama服务是否运行
- 验证Neo4j连接配置
- 确认依赖包已安装

**2. 向量检索失败**
- 检查Chroma数据库目录权限
- 验证sentence-transformers安装
- 确认数据目录存在

**3. 实体提取错误**
- 检查Ollama模型是否已下载
- 验证API连接地址
- 检查网络连接

**4. 前端CORS错误**
- 检查API服务器是否运行
- 验证CORS配置
- 使用支持的浏览器

### 日志查看

```bash
# 查看API服务器日志
tail -f api_server.log

# 查看测试日志
tail -f test_graphrag.log
```

### 调试模式

设置环境变量启用详细日志：
```bash
export LOG_LEVEL=DEBUG
export EXPERIMENT_MODE=true
```

## 扩展开发

### 添加新的实体类型

1. 修改 `backend/entity_extractor.py` 中的提示模板
2. 更新图谱查询逻辑
3. 调整前端显示逻辑

### 集成新的向量模型

1. 在 `backend/vector_retrieval.py` 中添加模型支持
2. 更新配置文件选项
3. 测试兼容性

### 添加新的评估指标

1. 扩展 `scripts/implement_evaluation.py`
2. 定义新的评估函数
3. 更新报告生成逻辑

## 生产部署

### 性能优化

- 使用Gunicorn等WSGI服务器
- 启用Redis缓存
- 配置负载均衡
- 优化数据库索引

### 安全配置

- 启用HTTPS
- 配置防火墙规则
- 设置访问控制
- 定期更新依赖

### 监控告警

- 配置健康检查
- 设置性能监控
- 启用错误日志收集
- 建立告警机制

## 技术支持

### 文档资源

- [Neo4j官方文档](https://neo4j.com/docs/)
- [Ollama模型库](https://ollama.ai/library)
- [Chroma向量数据库](https://docs.trychroma.com/)
- [Flask框架文档](https://flask.palletsprojects.com/)

### 社区支持

如有技术问题，请查阅项目文档或提交Issue。

---

*最后更新: 2025-08-25*  
*版本: GraphRAG v2.0*