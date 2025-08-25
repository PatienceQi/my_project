#scripts/policy_qa_demo.py
import os
import requests
from neo4j import GraphDatabase
import dotenv

dotenv.load_dotenv()

# 获取Ollama服务配置
llm_binding = os.getenv("LLM_BINDING")
llm_model = os.getenv("LLM_MODEL")
llm_host = os.getenv("LLM_BINDING_HOST")

# 强制设置远程配置
os.environ['OLLAMA_HOST'] = llm_host
os.environ['OLLAMA_BASE_URL'] = llm_host
os.environ['OLLAMA_NO_SERVE'] = '1'
os.environ['OLLAMA_ORIGINS'] = '*'

# 获取Neo4j连接信息
uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

# 创建Neo4j驱动程序
driver = GraphDatabase.driver(uri, auth=(username, password))

def call_ollama_chat(messages):
    """使用HTTP API调用Ollama聊天接口"""
    url = f"{llm_host}/api/chat"
    payload = {
        "model": llm_model,
        "messages": messages,
        "stream": False
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=600)
        response.raise_for_status()
        result = response.json()
        return result['message']['content']
    except Exception as e:
        print(f"Ollama API调用失败: {e}")
        return "抱歉，无法获取回答，请稍后再试。"

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
    response = call_ollama_chat([
        {
            "role": "user",
            "content": prompt
        }
    ])
    return response

if __name__ == "__main__":
    print("欢迎使用政策法规问答系统Demo！")
    while True:
        question = input("请输入您的问题（输入'exit'退出）：")
        if question.lower() == 'exit':
            break
        answer = get_policy_answer(question)
        print("回答：", answer)
    driver.close()