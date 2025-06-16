# 政策法规问答系统Demo

## 项目概述
本项目是一个轻量级的政策法规问答系统Demo，结合外部大模型API和Neo4j图数据库，支持多模态查询、实体关系展示和答案溯源功能。

# 项目说明

这是一个用于政策法规查询和问答的系统，集成了Neo4j图数据库和Ollama大模型服务。

## 环境配置步骤

为了快速配置项目环境，请按照以下步骤操作：

1. **安装Python**：确保您已经安装了Python 3.8或更高版本。您可以从[Python官网](https://www.python.org/downloads/)下载并安装。

2. **克隆项目**：如果您还没有克隆项目，请使用以下命令克隆项目到本地：
   ```bash
   git clone <项目地址>
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

5. **启动Neo4j数据库**：确保Neo4j数据库已安装并启动。如果您使用的是Neo4j Desktop，打开应用并启动数据库。如果是命令行版本，可以使用以下命令：
   ```bash
   neo4j start
   ```
   验证数据库是否在`NEO4J_URI`指定的地址上运行。

6. **启动Ollama服务**：如果您使用的是本地Ollama服务，确保其已启动并在`LLM_BINDING_HOST`指定的地址上可用。您可以使用以下命令启动Ollama服务：
   ```bash
   ollama serve
   ```
   如果使用远程服务，请确保网络连接正常。

7. **导入数据**：运行以下脚本将政策数据导入Neo4j数据库：
   ```bash
   python scripts/import_policy_data.py
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