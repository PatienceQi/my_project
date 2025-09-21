# Neo4j 图数据库集成

<cite>
**本文档引用的文件**   
- [import_policy_data.py](file://scripts\import_policy_data.py) - *已更新，包含Neo4j驱动初始化和数据导入逻辑*
- [test_neo4j_connection.py](file://scripts\test_neo4j_connection.py) - *已更新，连接测试逻辑*
- [api_server.py](file://backend\api_server.py) - *已更新，包含连接管理器初始化*
- [connections.py](file://backend\connections.py) - *新增，包含Neo4jConnectionManager和统一连接管理器*
- [graph_query.py](file://backend\graph_query.py) - *新增，包含图谱查询引擎和max_hops参数验证*
- [test_graph_query_fix.py](file://scripts\test_graph_query_fix.py) - *新增，图查询修复验证测试*
- [README.md](file://README.md)
</cite>

## 更新摘要
**变更内容**   
- 更新了环境变量与驱动初始化部分，反映新的连接管理器架构
- 新增了会话管理与连接池配置章节，详细说明Neo4jConnectionManager
- 更新了异常处理与会话管理部分，包含新的健康检查机制
- 新增了图谱查询参数验证章节，说明max_hops参数验证逻辑
- 更新了基于实体和关键词的语义检索部分，反映新的查询执行方式
- 更新了Neo4j连接状态验证部分，包含新的测试脚本

**文档来源更新**   
- 新增了connections.py和graph_query.py作为核心引用文件
- 更新了所有受影响文件的引用状态

## 目录
1. [Neo4j 图数据库集成](#neo4j-图数据库集成)
2. [环境变量与驱动初始化](#环境变量与驱动初始化)
3. [图模型设计逻辑](#图模型设计逻辑)
4. [批量导入政策数据](#批量导入政策数据)
5. [基于实体和关键词的语义检索](#基于实体和关键词的语义检索)
6. [Neo4j 连接状态验证](#neo4j-连接状态验证)
7. [异常处理与会话管理](#异常处理与会话管理)
8. [索引优化建议](#索引优化建议)
9. [会话管理与连接池配置](#会话管理与连接池配置)
10. [图谱查询参数验证](#图谱查询参数验证)

## 环境变量与驱动初始化

本系统通过环境变量加载 Neo4j 数据库的连接信息，确保配置的灵活性和安全性。在项目根目录下创建 `.env` 文件，并配置以下变量：

```bash
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_MAX_POOL_SIZE=10
NEO4J_CONNECTION_TIMEOUT=600
```

系统采用分层的连接管理架构。核心是 `Neo4jConnectionManager` 类，它封装了驱动初始化、连接池管理、健康检查等核心功能。该类在 `backend/connections.py` 中定义，并通过 `ConnectionManager` 统一管理器进行实例化。

在 `api_server.py` 中，系统通过以下代码初始化连接：

```python
def initialize_connections():
    """初始化数据库和LLM连接"""
    try:
        neo4j_config = {
            'uri': os.getenv('NEO4J_URI', 'neo4j://localhost:7687'),
            'username': os.getenv('NEO4J_USERNAME', 'neo4j'),
            'password': os.getenv('NEO4J_PASSWORD', 'password'),
            'max_pool_size': int(os.getenv('NEO4J_MAX_POOL_SIZE', '10')),
            'connection_timeout': int(os.getenv('NEO4J_CONNECTION_TIMEOUT', '30'))
        }
        
        # 初始化连接管理器
        connection_manager.initialize(neo4j_config, ollama_config, strict_mode=False)
```

此架构将连接管理与业务逻辑分离，提高了系统的可维护性和可测试性。

**更新** 现在使用统一的 `ConnectionManager` 进行连接管理，而非直接创建驱动实例。

**Section sources**
- [connections.py](file://backend\connections.py#L20-L161) - *新增，Neo4jConnectionManager实现*
- [api_server.py](file://backend\api_server.py#L116-L145) - *已更新，连接初始化逻辑*
- [import_policy_data.py](file://scripts\import_policy_data.py#L41-L43) - *已更新，环境变量加载*

## 图模型设计逻辑

系统采用图数据库模型来表示政策法规及其相关实体。核心节点标签包括 `Policy`（政策）、`Section`（章节）、`SubSection`（子章节）和 `Agency`（机构）。节点间的关系通过特定的关系类型连接，形成一个语义丰富的知识图谱。

### 节点标签
- **Policy**: 表示一个完整的政策法规，包含属性如 `policy_id`、`title`、`publish_date`、`publish_agency` 和 `doc_number`。
- **Section**: 表示政策中的章节，包含 `section_id`、`title` 和 `content`。
- **SubSection**: 表示章节下的子条款，结构与 `Section` 类似。
- **Agency**: 表示发布政策的机构，包含 `name` 属性。

### 关系类型
- **BELONGS_TO**: 表示 `Section` 或 `SubSection` 属于某个 `Policy`。
- **ISSUED_BY**: 表示 `Policy` 由某个 `Agency` 发布。
- **PUBLISHES**: 与 `ISSUED_BY` 互为反向关系，表示 `Agency` 发布了某个 `Policy`。
- **CC**: 表示抄送关系，即某个 `Organization` 被抄送至 `Policy`。
- **MENTIONED_IN**: 表示 `Entity` 在 `Policy` 中被提及。
- **RELATED_TO**: 默认关系类型，用于连接通过大模型提取的实体间关系。

该设计逻辑支持高效的层级查询和语义检索，例如通过 `MATCH (p:Policy)-[:HAS_SECTION]->(s:Section)` 查询政策的所有章节。

**Section sources**
- [import_policy_data.py](file://scripts\import_policy_data.py#L314-L349)
- [import_policy_data.py](file://scripts\import_policy_data.py#L383-L417)

## 批量导入政策数据

`import_policy_data.py` 脚本负责将 JSON 格式的政策法规数据批量导入 Neo4j 数据库。该过程包括读取 JSON 文件、解析数据、创建节点和关系。

### 数据导入流程
1. **读取 JSON 文件**: 脚本从 `database` 目录下读取指定的 JSON 文件。
2. **创建事务**: 使用 `driver.session()` 创建会话，并在事务中执行写操作。
3. **创建节点**: 通过 Cypher 查询创建 `Policy`、`Section` 等节点。
4. **建立关系**: 使用 `MERGE` 语句确保节点和关系的唯一性。

### 核心代码示例
```python
def create_policy_node(self, tx, policy_data: Dict) -> str:
    """创建政策节点"""
    title = policy_data.get('title', '未知政策')
    policy_id = self.generate_id(title, "POL")
    
    query = """
    MERGE (p:Policy {policy_id: $policy_id})
    SET p.title = $title,
        p.doc_number = $doc_number,
        p.publish_agency = $publish_agency,
        p.publish_date = $publish_date
    RETURN p.policy_id as policy_id
    """
    
    params = {
        'policy_id': policy_id,
        'title': title,
        'doc_number': policy_data.get('doc_number', ''),
        'publish_agency': policy_data.get('publish_agency', ''),
        'publish_date': policy_data.get('publish_date', '')
    }
    
    result = tx.run(query, **params)
    record = result.single()
    return policy_id
```

此脚本还调用大模型服务进行实体识别和关系抽取，进一步丰富图数据库中的信息。

**Section sources**
- [import_policy_data.py](file://scripts\import_policy_data.py#L314-L444)

## 基于实体和关键词的语义检索

`api_server.py` 脚本通过 Cypher 查询实现基于实体和关键词的语义检索。当用户提出问题时，后端服务在 Neo4j 数据库中搜索相关节点和关系，返回上下文信息供大模型生成答案。

### 检索逻辑
1. **构建查询**: 使用 `MATCH` 语句查找包含关键词的 `Policy`、`Section` 或 `SubSection` 节点。
2. **关联机构**: 通过 `OPTIONAL MATCH` 获取政策的发布机构。
3. **返回结果**: 返回政策标题、章节内容、发布机构等信息。

### Cypher 查询示例
```python
def query_policy_knowledge(question: str) -> list:
    """
    查询政策法规知识图谱
    """
    try:
        query = (
            "MATCH (p:Policy) "
            "OPTIONAL MATCH (p)-[:HAS_SECTION]->(s:Section) "
            "OPTIONAL MATCH (s)-[:CONTAINS]->(sub:SubSection) "
            "OPTIONAL MATCH (p)-[:ISSUED_BY]->(a:Agency) "
            "WHERE p.title CONTAINS $query_text OR s.title CONTAINS $query_text OR sub.title CONTAINS $query_text "
            "RETURN p.title as policy_title, p.publish_agency as agency, s.title as section_title, s.content as section_content, sub.title as sub_title, sub.content as sub_content, a.name as agency_name "
            "LIMIT 5"
        )
        
        results = connection_manager.neo4j.execute_query(query, {'query_text': question})
        return results
    except Exception as e:
        logger.error(f"Neo4j查询失败: {str(e)}")
        raise DatabaseError(f"数据库查询失败: {str(e)}", "policy_query")
```

现在通过 `connection_manager.neo4j.execute_query()` 方法执行查询，该方法封装了会话管理和异常处理。

**更新** 查询执行方式已更新为使用 `ConnectionManager` 的 `execute_query` 方法。

**Section sources**
- [api_server.py](file://backend\api_server.py#L46-L71) - *已更新，查询执行逻辑*
- [connections.py](file://backend\connections.py#L101-L130) - *新增，execute_query方法实现*
- [软件著作权申请.md](file://软件著作权申请.md#L138-L187)

## Neo4j 连接状态验证

`test_neo4j_connection.py` 脚本用于验证 Neo4j 服务的连接状态。该脚本尝试创建驱动程序并执行简单的连接测试。

### 验证流程
1. **加载环境变量**: 读取 `NEO4J_URI`、`NEO4J_USERNAME` 和 `NEO4J_PASSWORD`。
2. **创建驱动**: 使用 `GraphDatabase.driver()` 创建连接。
3. **测试连接**: 如果连接成功，打印成功消息；否则捕获异常并打印错误信息。

### 代码示例
```python
def create_driver():
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        print("Connection to Neo4j successful!")
        return driver
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        return None

# 测试连接
driver = create_driver()
if driver:
    driver.close()
```

此外，系统还提供了 `test_graph_query_fix.py` 脚本，用于验证图查询功能的正确性，包括参数验证和查询语法测试。

**更新** 新增了 `test_graph_query_fix.py` 脚本用于更全面的测试。

**Section sources**
- [test_neo4j_connection.py](file://scripts\test_neo4j_connection.py#L0-L24) - *已更新，连接测试逻辑*
- [test_graph_query_fix.py](file://scripts\test_graph_query_fix.py#L0-L180) - *新增，图查询修复验证测试*

## 异常处理与会话管理

系统在与 Neo4j 交互时实现了完善的异常处理和会话管理机制。

### 异常处理
- **通用异常**: 使用 `try-except` 捕获所有异常，避免程序因单个错误而崩溃。
- **具体异常**: 通过自定义异常类（如 `DatabaseError`）提供更详细的错误信息。

### 会话管理
- **自动管理**: 使用 `with` 语句确保会话在使用后自动关闭。
- **事务执行**: 使用 `execute_query` 方法执行查询，保证数据一致性。

```python
def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> list:
    """
    执行Cypher查询
    """
    try:
        with self.get_session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    except Exception as e:
        raise DatabaseError(f"查询执行失败: {str(e)}", "query_execution")
```

**更新** 会话管理已集成到 `Neo4jConnectionManager` 中，提供了更完善的资源管理。

**Section sources**
- [connections.py](file://backend\connections.py#L101-L130) - *新增，execute_query方法*
- [connections.py](file://backend\connections.py#L70-L90) - *新增，get_session上下文管理器*
- [api_server.py](file://backend\api_server.py#L45-L70)

## 索引优化建议

为提升查询性能，建议在 Neo4j 中为常用查询字段创建索引。

### 推荐索引
- **Policy 节点**: 为 `policy_id` 和 `title` 创建索引。
  ```cypher
  CREATE INDEX FOR (p:Policy) ON (p.policy_id);
  CREATE INDEX FOR (p:Policy) ON (p.title);
  ```
- **Section 节点**: 为 `section_id` 和 `title` 创建索引。
  ```cypher
  CREATE INDEX FOR (s:Section) ON (s.section_id);
  CREATE INDEX FOR (s:Section) ON (s.title);
  ```
- **Agency 节点**: 为 `name` 创建索引。
  ```cypher
  CREATE INDEX FOR (a:Agency) ON (a.name);
  ```

这些索引将显著加快基于 ID 或标题的查询速度，特别是在处理大量政策法规数据时。

**Section sources**
- [import_policy_data.py](file://scripts\import_policy_data.py#L314-L349)
- [import_policy_data.py](file://scripts\import_policy_data.py#L383-L417)

## 会话管理与连接池配置

系统通过 `Neo4jConnectionManager` 类实现了高级的会话管理和连接池配置。该类在 `backend/connections.py` 中定义，提供了以下核心功能：

### 连接池配置
- **最大连接池大小**: 通过 `max_pool_size` 参数配置，默认为10。
- **连接超时**: 通过 `connection_timeout` 参数配置，默认为600秒。
- **事务重试时间**: 设置为30秒，确保在网络波动时的可靠性。

### 健康检查机制
- **缓存机制**: 健康检查结果缓存1分钟，避免频繁检查。
- **主动检查**: 通过执行 `RETURN 1 as health_check` 查询来验证连接状态。

### 核心代码示例
```python
class Neo4jConnectionManager:
    """Neo4j连接池管理器"""
    
    def __init__(self, uri: str, auth: tuple, max_pool_size: int = 10, 
                 connection_timeout: int = 30):
        self.uri = uri
        self.auth = auth
        self.max_pool_size = max_pool_size
        self.connection_timeout = connection_timeout
        self._driver = None
        
        self._initialize_driver()
    
    def _initialize_driver(self):
        """初始化Neo4j驱动"""
        try:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=self.auth,
                max_connection_pool_size=self.max_pool_size,
                connection_timeout=self.connection_timeout,
                max_transaction_retry_time=30
            )
        except Exception as e:
            raise ConfigurationError(f"Neo4j连接初始化失败: {str(e)}", "neo4j_connection")
```

此设计确保了连接的高效复用和系统的稳定性。

**Section sources**
- [connections.py](file://backend\connections.py#L20-L161) - *新增，Neo4jConnectionManager完整实现*

## 图谱查询参数验证

`graph_query.py` 文件中的 `GraphQueryEngine` 类实现了对图谱查询参数的验证机制，特别是对 `max_hops` 参数的验证。

### max_hops参数验证
- **类型验证**: 确保参数为整数类型。
- **范围验证**: 将参数限制在1-10之间，防止过长的路径查询影响性能。
- **默认值**: 对于无效输入，返回默认值2。

### 核心代码示例
```python
def _validate_max_hops(self, max_hops: int) -> int:
    """验证并修正max_hops参数"""
    if not isinstance(max_hops, int):
        logging.warning(f"max_hops参数类型错误: {type(max_hops)}, 使用默认值2")
        return 2
    
    if max_hops < 1:
        logging.warning(f"max_hops过小: {max_hops}, 修正为1")
        return 1
    
    if max_hops > 10:
        logging.warning(f"max_hops过大: {max_hops}, 修正为10")
        return 10
    
    return max_hops
```

该验证机制在 `query_entity_relationships` 方法中被调用，确保了查询的安全性和性能。

**Section sources**
- [graph_query.py](file://backend\graph_query.py#L0-L52) - *新增，GraphQueryEngine初始化和参数验证*
- [graph_query.py](file://backend\graph_query.py#L150-L200) - *新增，query_entity_relationships方法*
- [test_graph_query_fix.py](file://scripts\test_graph_query_fix.py#L0-L180) - *新增，参数验证测试*