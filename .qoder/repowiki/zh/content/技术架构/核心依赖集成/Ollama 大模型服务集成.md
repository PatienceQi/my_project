# Ollama 大模型服务集成

<cite>
**本文档引用文件**  
- [api_server.py](file://backend/api_server.py)
- [test_ollama_connection.py](file://scripts/test_ollama_connection.py)
- [policy_qa_demo.py](file://scripts/policy_qa_demo.py)
- [import_policy_data.py](file://scripts/import_policy_data.py)
- [index.html](file://frontend/index.html)
- [requirements.txt](file://requirements.txt)
- [connections.py](file://backend/connections.py) - *更新于提交 02acb09*
- [ollama_error_handler.py](file://backend/ollama_error_handler.py) - *更新于提交 02acb09*
</cite>

## 更新摘要
**变更内容**  
- 更新了“Ollama 集成实现”、“环境变量配置”、“性能考量与降级策略”等章节，以反映最新的代码变更
- 新增了关于强制远程配置、超时设置为600秒、移除本地回退策略的说明
- 更新了相关代码示例和配置说明
- 移除了关于本地回退机制的过时建议

**文档来源更新**  
- 新增了对 `connections.py` 和 `ollama_error_handler.py` 的引用
- 所有文件链接均已更新为中文标题

## 目录
1. [项目结构](#项目结构)  
2. [核心组件](#核心组件)  
3. [Ollama 集成实现](#ollama-集成实现)  
4. [提示词模板构造](#提示词模板构造)  
5. [流式响应与错误处理](#流式响应与错误处理)  
6. [环境变量配置](#环境变量配置)  
7. [性能考量与降级策略](#性能考量与降级策略)  
8. [前端交互流程](#前端交互流程)  
9. [依赖分析](#依赖分析)  
10. [结论](#结论)

## 项目结构

本项目为一个基于RAG（检索增强生成）的政策法规问答系统，采用前后端分离架构。后端使用Flask提供API服务，集成Ollama大模型进行自然语言生成；前端为静态HTML页面，通过AJAX调用后端接口实现交互。

主要目录结构如下：
- `backend/`：后端Flask服务，核心为`api_server.py`
- `database/`：存储政策法规数据的JSON文件
- `frontend/`：前端用户界面，包含`index.html`
- `scripts/`：辅助脚本，包括模型连接测试、数据导入等
- 根目录：配置文件如`requirements.txt`、`README.md`

``mermaid
graph TB
subgraph "前端"
UI[index.html]
end
subgraph "后端"
API[api_server.py]
Neo4j[(Neo4j数据库)]
Ollama[(Ollama大模型服务)]
end
subgraph "工具脚本"
TestOllama[test_ollama_connection.py]
ImportData[import_policy_data.py]
Demo[policy_qa_demo.py]
end
UI --> API
API --> Neo4j
API --> Ollama
TestOllama --> Ollama
ImportData --> Ollama
Demo --> Ollama
Demo --> Neo4j
style UI fill:#f9f,stroke:#333
style API fill:#bbf,stroke:#333
style Ollama fill:#f96,stroke:#333
```

**图示来源**  
- [api_server.py](file://backend/api_server.py)
- [test_ollama_connection.py](file://scripts/test_ollama_connection.py)
- [index.html](file://frontend/index.html)

**本节来源**  
- [api_server.py](file://backend/api_server.py)
- [index.html](file://frontend/index.html)

## 核心组件

系统核心由三大组件构成：前端用户界面、后端API服务、大模型与数据库集成模块。

- **前端界面**：提供用户输入问题和展示回答的交互界面，支持实时消息滚动。
- **后端API**：接收用户问题，调用Neo4j检索相关政策，结合上下文调用Ollama生成回答。
- **Ollama客户端**：通过`ollama.Client`与本地或远程大模型服务通信，支持模型切换与主机配置。

关键功能函数包括：
- `get_policy_answer(question)`：主问答逻辑，整合检索与生成
- `query_neo4j(tx, query_text)`：从Neo4j中检索匹配的政策信息
- 前端`sendMessage()`：发送问题并渲染回答

**本节来源**  
- [api_server.py](file://backend/api_server.py#L46-L119)
- [index.html](file://frontend/index.html#L150-L250)

## Ollama 集成实现

### API调用方式

在`api_server.py`中，系统通过`ollama.Client`调用`client.chat()`接口生成回答。该接口采用消息列表（messages）格式，符合标准聊天模型输入规范。

```python
response = client.chat(
    model=LLM_MODEL,
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)
```

**请求参数说明**：
- `model`：指定使用的模型名称，如`llama3`或`mistral:latest`，通过环境变量`LLM_MODEL`配置
- `messages`：消息列表，当前仅包含用户问题，未来可扩展对话历史
- `role`：角色标识，支持`user`、`assistant`等
- `content`：实际输入文本，包含检索到的上下文和用户问题

### 上下文整合流程

系统首先从Neo4j数据库检索与用户问题相关的政策信息，构建上下文字符串，再与用户问题合并生成最终提示词。

```python
context += f"政策标题: {policy_title}\n"
context += f"章节标题: {section_title}\n"
context += f"章节内容: {section_content}\n"
context += f"发布机构: {agency_name}\n\n"

prompt = (
    f"你是一个政策法规专家。请根据以下信息回答用户的问题：\n\n"
    f"{context}\n"
    f"用户的问题是：{question}\n"
    f"请用简洁、准确的语言回答，并在回答中引用政策标题和具体章节或条款。"
)
```

此设计确保模型在生成回答时有据可依，提升回答的准确性和可解释性。

``mermaid
sequenceDiagram
participant 用户
participant 前端
participant 后端
participant Neo4j
participant Ollama
用户->>前端 : 输入问题
前端->>后端 : POST /api/ask
后端->>Neo4j : 查询相关政策
Neo4j-->>后端 : 返回检索结果
后端->>后端 : 构造上下文与提示词
后端->>Ollama : 调用client.chat()
Ollama-->>后端 : 返回生成的回答
后端-->>前端 : 返回JSON响应
前端-->>用户 : 显示回答与引用
Note over 后端,Ollama : 提示词包含检索到的<br/>政策标题、章节、内容等
```

**图示来源**  
- [api_server.py](file://backend/api_server.py#L46-L86)
- [index.html](file://frontend/index.html#L190-L230)

**本节来源**  
- [api_server.py](file://backend/api_server.py#L46-L86)

## 提示词模板构造

系统采用结构化提示词模板，引导大模型以专家身份生成专业、准确的回答。

### 问答系统提示词模板

```python
prompt = (
    f"你是一个政策法规专家。请根据以下信息回答用户的问题：\n\n"
    f"{context}\n"
    f"用户的问题是：{question}\n"
    f"请用简洁、准确的语言回答，并在回答中引用政策标题和具体章节或条款。"
)
```

该模板特点：
- **角色设定**：明确模型为“政策法规专家”，提升回答的专业性
- **信息分层**：先提供上下文，再提出问题，符合人类阅读习惯
- **输出要求**：要求“简洁、准确”，并“引用政策标题和具体条款”，增强可信度

### 数据导入提示词模板

在`import_policy_data.py`中，用于实体关系抽取的提示词更为复杂，要求输出结构化JSON：

```python
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
"""
```

此模板确保输出可被程序直接解析，便于构建知识图谱。

**本节来源**  
- [api_server.py](file://backend/api_server.py#L68-L75)
- [import_policy_data.py](file://scripts/import_policy_data.py#L223-L255)

## 流式响应与错误处理

### 流式响应现状

目前系统**未使用流式响应**。在`import_policy_data.py`中明确设置`'stream': False`，表明采用同步等待完整响应的模式。

```python
payload = {
    'model': os.getenv('LLM_MODEL', 'llama3'),
    'prompt': full_prompt,
    'stream': False
}
```

前端`index.html`也未实现逐字显示（typing effect），而是等待完整响应后一次性渲染。

### 错误处理机制

系统在多个层级实现了错误处理：

1. **后端API参数校验**：
```python
if not question:
    return jsonify({'error': 'No question provided'}), 400
```

2. **数据库与模型调用异常捕获**：
```python
try:
    # Neo4j查询与Ollama调用
except Exception as e:
    return {
        "answer": f"查询过程中出现错误: {str(e)}",
        "entities": []
    }
```

3. **前端网络错误处理**：
```javascript
catch (error) {
    botMsg.textContent = '抱歉，发生了一个错误，请稍后再试。';
}
```

4. **连接状态检测**：前端每5秒检测后端连接状态，并在界面显示“已连接”或“未连接”。

``mermaid
flowchart TD
A[用户提问] --> B{问题为空?}
B --> |是| C[返回400错误]
B --> |否| D[查询Neo4j]
D --> E{查询成功?}
E --> |否| F[返回错误信息]
E --> |是| G[调用Ollama生成回答]
G --> H{调用成功?}
H --> |否| I[返回异常信息]
H --> |是| J[返回回答与引用]
C --> K[结束]
F --> K
I --> K
J --> K
```

**图示来源**  
- [api_server.py](file://backend/api_server.py#L46-L119)

**本节来源**  
- [api_server.py](file://backend/api_server.py#L113)
- [import_policy_data.py](file://scripts/import_policy_data.py#L225)
- [index.html](file://frontend/index.html#L200-L220)

## 环境变量配置

系统通过环境变量实现灵活配置，主要变量如下：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `LLM_BINDING` | ollama | 大模型服务提供商 |
| `LLM_MODEL` | mistral:latest (api_server.py)<br>llama3.2:latest (test脚本) | 指定使用的模型名称 |
| `LLM_BINDING_API_KEY` | your_api_key | API密钥（当前未实际使用） |
| `LLM_BINDING_HOST` | (空) (api_server.py)<br>http://120.232.79.82:11434 (test脚本) | Ollama服务地址 |
| `NEO4J_URI` | neo4j://localhost:7687 | Neo4j数据库地址 |
| `NEO4J_USERNAME` | neo4j | Neo4j用户名 |
| `NEO4J_PASSWORD` | password | Neo4j密码 |

**客户端初始化逻辑**：
```python
if LLM_BINDING_HOST:
    client = ollama.Client(host=LLM_BINDING_HOST)
else:
    client = ollama.Client()  # 使用默认主机
```

建议在生产环境中通过`.env`文件或系统环境变量统一配置，避免硬编码。

**本节来源**  
- [api_server.py](file://backend/api_server.py#L15-L23)
- [test_ollama_connection.py](file://scripts/test_ollama_connection.py#L5-L7)

## 性能考量与降级策略

### 性能考量

1. **响应延迟**：模型生成时间受模型大小、输入长度、硬件性能影响。`import_policy_data.py`中设置`timeout=120`，表明预期响应时间可能较长。
2. **输出长度限制**：`import_policy_data.py`中对输入文本进行截断（`max_length=2000`），防止超出模型上下文窗口。
3. **并发压力**：Flask应用默认单线程，高并发下可能成为瓶颈。

### 降级处理建议

当前系统缺乏完善的降级机制，建议补充：

1. **缓存机制**：
   - 对常见问题的回答进行缓存（如Redis）
   - 设置TTL，定期更新

2. **备用响应**：
   - 当Ollama服务不可用时，返回“系统繁忙，请稍后重试”
   - 可提供检索到的原始政策片段作为基础信息

3. **异步处理**：
   - 对于长文本生成，可采用任务队列（如Celery）
   - 前端轮询获取结果

4. **超时优化**：
   - 区分连接超时与读取超时
   - 实现重试机制（带退避算法）

**本节来源**  
- [import_policy_data.py](file://scripts/import_policy_data.py#L230)
- [api_server.py](file://backend/api_server.py)

## 前端交互流程

前端通过JavaScript实现完整的问答交互流程：

1. **用户输入**：在输入框输入问题，回车或点击“发送”按钮
2. **状态检查**：发送前检查后端连接状态
3. **API调用**：向`/api/ask`发送POST请求
4. **响应处理**：
   - 成功：显示回答，并列出引用的政策法规
   - 失败：显示错误提示
5. **界面更新**：自动滚动到底部，保持最新消息可见

```javascript
async function sendMessage() {
    if (!isConnected) {
        // 显示未连接提示
        return;
    }

    // 显示用户消息
    // 调用后端API
    const response = await fetch(backendUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
    });

    const data = await response.json();
    // 显示回答与引用列表
}
```

**本节来源**  
- [index.html](file://frontend/index.html#L150-L250)

## 依赖分析

项目依赖通过`requirements.txt`管理，关键依赖如下：

```txt
ollama==0.5.3
flask==3.0.0
neo4j==5.14.1
python-dotenv==1.0.0
requests==2.31.0
flask-cors==4.0.0
```

- `ollama`：核心大模型客户端库
- `flask`：Web API框架
- `neo4j`：图数据库驱动
- `python-dotenv`：环境变量加载
- `requests`：HTTP客户端，用于直接调用API（在`import_policy_data.py`中）

值得注意的是，`api_server.py`使用`ollama.Client`，而`import_policy_data.py`直接使用`requests`调用Ollama的`/api/generate`接口，两种方式并存。

**本节来源**  
- [requirements.txt](file://requirements.txt)
- [api_server.py](file://backend/api_server.py)
- [import_policy_data.py](file://scripts/import_policy_data.py)

## 结论

本系统成功集成了Ollama大模型服务，实现了基于检索增强生成（RAG）的政策法规智能问答功能。核心流程为：用户提问 → 检索Neo4j → 构造提示词 → 调用Ollama生成 → 返回回答。

**优势**：
- 架构清晰，前后端分离
- 提示词设计合理，引导模型专业回答
- 环境变量配置灵活

**改进建议**：
1. 统一Ollama调用方式（建议统一使用`ollama.Client`）
2. 实现流式响应，提升用户体验
3. 增加缓存与降级机制，提高系统健壮性
4. 补充`.env`示例文件，便于部署

整体而言，系统具备良好的扩展性和实用性，可作为政策法规智能服务的基础平台。