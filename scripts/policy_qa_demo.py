import os
import ollama
from neo4j import GraphDatabase
import dotenv

dotenv.load_dotenv()

# 获取Ollama服务配置
llm_binding = os.getenv("LLM_BINDING")
llm_model = os.getenv("LLM_MODEL")
llm_host = os.getenv("LLM_BINDING_HOST")

# 获取Neo4j连接信息
uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

# 初始化Ollama客户端
client = ollama.Client(host=llm_host)

# 创建Neo4j驱动程序
driver = GraphDatabase.driver(uri, auth=(username, password))

def query_neo4j(tx, query):
    result = tx.run(query)
    return list(result)

def get_policy_answer(question):
    # 简单的示例：从Neo4j中查询相关政策信息
    with driver.session() as session:
        result = session.read_transaction(query_neo4j, "MATCH (n:Policy) RETURN n LIMIT 1")
        if result:
            policy_info = result[0]['n'].get('content', '暂无相关政策信息')
        else:
            policy_info = "暂无相关政策信息"
    
    # 使用Ollama生成回答
    prompt = f"用户问题：{question}\n相关政策信息：{policy_info}\n请根据以上信息回答用户的问题。"
    response = client.chat(model=llm_model, messages=[
        {
            "role": "user",
            "content": prompt
        }
    ])
    return response['message']['content']

if __name__ == "__main__":
    print("欢迎使用政策法规问答系统Demo！")
    while True:
        question = input("请输入您的问题（输入'exit'退出）：")
        if question.lower() == 'exit':
            break
        answer = get_policy_answer(question)
        print("回答：", answer)
    driver.close()