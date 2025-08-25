# 政策法规问答系统Demo

## 项目概述
本项目是一个轻量级的政策法规问答系统Demo，结合外部大模型API和Neo4j图数据库，支持多模态查询、实体关系展示和答案溯源功能。

# 项目说明

这是一个用于政策法规查询和问答的系统，集成了Neo4j图数据库和Ollama大模型服务。

## 环境配置步骤

为了快速配置项目环境，请按照以下步骤操作：

1. **克隆项目**：如果您还没有克隆项目，请使用以下命令克隆项目到本地：
   ```bash
   git clone https://github.com/PatienceQi/my_project.git
   cd my_project
   ```

2. **设置Python虚拟环境**：
   - 使用conda创建Python 3.12环境：
     ```bash
     conda create -n rag python=3.12
     conda activate rag
     ```
   - 如果没有conda，可以从[Python官网](https://www.python.org/downloads/)安装Python 3.12。
   ```bash
   git clone https://github.com/PatienceQi/my_project.git
   cd my_project
   ```

3. **安装依赖**：在项目根目录下，运行以下命令安装所需依赖包：
   ```bash
   pip install -r requirements.txt
   ```
   这将安装`neo4j`、`dotenv`、`requests`、`flask`和`flask-cors`等必要包。
   
4. **配置环境变量**：在项目根目录下创建一个`.env`文件，并根据您的实际环境配置以下变量：
   ```bash
   NEO4J_URI=neo4j://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=password
   LLM_BINDING=ollama
   LLM_MODEL=llama3.2:latest
   LLM_BINDING_HOST=http://120.232.79.82:11434
   ```
   确保`LLM_BINDING_HOST`指向可用的Ollama服务地址。

5. **启动Neo4j数据库**：

   Neo4j是本项目的核心图数据库，支持政策法规的实体关系存储和查询。以下提供两种安装配置方式：

   ### 5.1 Neo4j Desktop版本（推荐新手使用）

   **系统要求**：
   - 操作系统：Windows 10+、macOS 10.14+、Linux（Ubuntu 18.04+）  
   - Java版本：JDK 11或JDK 17
   - 内存：至少4GB RAM（推荐8GB+）
   - 磁盘空间：至少2GB可用空间

   **安装步骤**：
   1. **下载Neo4j Desktop**：
      - 访问 [https://neo4j.com/download/](https://neo4j.com/download/)
      - 选择"Neo4j Desktop"版本
      - 填写邮箱获取激活码
      - 下载并安装桌面应用程序

   2. **首次配置**：
      - 启动Neo4j Desktop应用
      - 输入邮箱收到的激活码
      - 创建新项目，项目名称：`政策法规RAG系统`

   3. **创建数据库**：
      - 点击"Add" → "Local DBMS"
      - 数据库名称：`policy-rag-db`
      - 密码：设置为`.env`文件中的`NEO4J_PASSWORD`值
      - 版本：选择5.14.1或最新稳定版
      - 点击"Create"创建数据库

   4. **高级配置**（可选）：
      ```
      初始堆大小：512m
      最大堆大小：2g
      页面缓存：1g
      ```

   5. **启动数据库**：
      - 在项目面板中找到创建的数据库
      - 点击"Start"按钮启动数据库
      - 等待状态变为"Active"（绿色圆点）
      - 连接地址将显示为：`bolt://localhost:7687`

   6. **验证连接**：
      - 点击"Open"按钮打开Neo4j Browser
      - 或在浏览器中访问：`http://localhost:7474`
      - 使用配置的用户名和密码登录
      - 执行测试查询：`MATCH (n) RETURN count(n)`

   ### 5.2 Neo4j命令行版本（适合服务器部署）

   **下载安装**：
   ```bash
   # Linux/macOS
   curl -O https://dist.neo4j.org/neo4j-community-5.14.1-unix.tar.gz
   tar -xzf neo4j-community-5.14.1-unix.tar.gz
   cd neo4j-community-5.14.1

   # Windows
   # 下载neo4j-community-5.14.1-windows.zip并解压到指定目录
   ```

   **环境变量配置**：
   ```bash
   # Linux/macOS
   export NEO4J_HOME=/path/to/neo4j-community-5.14.1
   export PATH=$NEO4J_HOME/bin:$PATH

   # Windows
   set NEO4J_HOME=C:\neo4j-community-5.14.1
   set PATH=%NEO4J_HOME%\bin;%PATH%
   ```

   **配置文件调整**：
   编辑`$NEO4J_HOME/conf/neo4j.conf`文件：
   ```properties
   # 网络配置
   server.default_listen_address=0.0.0.0
   server.bolt.listen_address=:7687
   server.http.listen_address=:7474

   # 内存配置
   server.memory.heap.initial_size=512m
   server.memory.heap.max_size=2g
   server.memory.pagecache.size=1g

   # 认证配置
   dbms.security.auth_enabled=true
   ```

   **设置初始密码**：
   ```bash
   # 重置密码为环境变量中配置的密码
   neo4j-admin dbms set-initial-password "password"
   ```

   **启动命令**：
   ```bash
   # 启动数据库
   neo4j start

   # 检查状态
   neo4j status

   # 停止数据库（如需要）
   neo4j stop

   # 重启数据库
   neo4j restart

   # 控制台模式启动（调试用）
   neo4j console
   ```

   **使用Cypher Shell验证**：
   ```bash
   # 连接到数据库
   cypher-shell -a bolt://localhost:7687 -u neo4j -p password

   # 执行测试查询
   neo4j> MATCH (n) RETURN count(n);
   ```

   ### 5.3 验证数据库连接
   
   运行项目提供的连接测试脚本：
   ```bash
   python scripts/test_neo4j_connection.py
   ```
   
   如果连接成功，将显示"✅ Neo4j连接成功"的消息。

   ### 5.4 常见问题排除

   | 问题 | 症状 | 解决方案 |
   |------|------|----------|
   | 端口冲突 | 启动失败，7687/7474端口被占用 | 修改配置文件中的端口号或停止占用端口的程序 |
   | 内存不足 | 启动缓慢或崩溃 | 调整heap和pagecache大小配置 |
   | 权限问题 | 无法创建数据库文件 | 检查数据目录权限，使用管理员权限启动 |
   | Java版本错误 | 启动报错Java相关异常 | 安装JDK 11或17，设置JAVA_HOME环境变量 |
   | 连接超时 | Python脚本无法连接 | 检查防火墙设置，确认数据库已启动 |

   **查看日志**：
   ```bash
   # Neo4j Desktop：在图形界面中查看日志选项卡
   # 命令行版本：
   tail -f $NEO4J_HOME/logs/neo4j.log
   ```

6. **启动Ollama服务**：如果您使用的是本地Ollama服务，确保其已启动并在`LLM_BINDING_HOST`指定的地址上可用。您可以使用以下命令启动Ollama服务：
   ```bash
   ollama serve
   ```
   如果使用远程服务，请确保网络连接正常。

7. **导入数据**：运行以下脚本将政策数据导入Neo4j数据库：
   ```bash
   python scripts/import_policy_data_fixed.py --directory database/
   ```
   该脚本会读取`database`目录下的JSON文件，并将数据导入Neo4j，同时调用大模型服务进行实体识别和关系抽取。

8. **启动后端服务**：启动 Flask 后端服务以处理API请求：
   ```bash
   python backend/api_server.py
   ```
   确保后端服务运行在默认的`http://127.0.0.1:5000`地址，或根据需要修改配置。

9. **启动前端应用**：进入`frontend`目录，安装依赖并启动前端应用：
   ```bash
   cd frontend
   npm install
   npm start
   ```
   前端应用将在浏览器中自动打开，通常运行在`http://localhost:3000`。

10. **测试连接**：运行以下测试脚本以验证各项服务的连接性：
    ```bash
    python scripts/test_neo4j_connection.py
    python scripts/test_ollama_connection.py
    python scripts/test_backend_response.py
    ```

## 项目结构

- `backend/`：包含后端API服务代码。
- `database/`：包含政策法规数据文件（JSON格式）。
- `frontend/`：包含前端用户界面代码。
- `scripts/`：包含数据导入和测试脚本，详见目录中的README.md文件。

## 使用说明

- 访问前端应用，通过用户界面查询政策法规信息。
- 导入数据集后，可以扩展Neo4j查询语句，支持更复杂的政策法规查询。

如果在配置过程中遇到问题，请检查日志输出，或联系项目维护者获取帮助。
- **模块未找到错误**：如果运行脚本时出现`ModuleNotFoundError`，请确保已安装相关库。可以通过`pip install <库名>`命令解决。
- **连接超时或网络问题**：如果连接远程ollama服务时出现超时或网络错误，请检查网络连接是否稳定，并确认`LLM_BINDING_HOST`地址是否正确。
- **Neo4j连接错误**：如果连接Neo4j数据库时出现错误，请检查`NEO4J_URI`、`NEO4J_USERNAME`和`NEO4J_PASSWORD`是否正确配置。

## 后续维护

- 定期更新环境变量中的API密钥和数据库密码，确保安全。
- 根据需求说明书和项目设计方案，逐步完善Demo功能，包括多模态数据处理模块和数据集导入。
- 导入数据集后，可以扩展Neo4j查询语句，支持更复杂的政策法规查询。