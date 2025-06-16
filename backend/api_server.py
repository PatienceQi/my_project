from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import ollama
from neo4j import GraphDatabase
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)

# Ollama配置
from neo4j import GraphDatabase
LLM_BINDING = os.getenv("LLM_BINDING")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral:latest")
LLM_BINDING_API_KEY = os.getenv("LLM_BINDING_API_KEY", "")
LLM_BINDING_HOST = os.getenv("LLM_BINDING_HOST", "")

if LLM_BINDING_HOST:
    client = ollama.Client(host=LLM_BINDING_HOST)
else:
    client = ollama.Client()

# Neo4j配置
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def query_neo4j(tx, query_text):
    query = (
        "MATCH (p:Policy) "
        "OPTIONAL MATCH (p)-[:HAS_SECTION]->(s:Section) "
        "OPTIONAL MATCH (s)-[:CONTAINS]->(sub:SubSection) "
        "OPTIONAL MATCH (p)-[:ISSUED_BY]->(a:Agency) "
        "WHERE p.title CONTAINS $query_text OR s.title CONTAINS $query_text OR sub.title CONTAINS $query_text "
        "RETURN p.title as policy_title, p.publish_agency as agency, s.title as section_title, s.content as section_content, sub.title as sub_title, sub.content as sub_content, a.name as agency_name "
        "LIMIT 5"
    )
    result = tx.run(query, query_text=query_text).data()
    return result

def get_policy_answer(question):
    try:
        with driver.session() as session:
            neo4j_results = session.read_transaction(query_neo4j, question)
            if neo4j_results:
                context = ""
                results = []
                for record in neo4j_results:
                    policy_title = record.get('policy_title', '未知政策')
                    section_title = record.get('section_title', '')
                    section_content = record.get('section_content', '内容暂无')
                    sub_title = record.get('sub_title', '')
                    sub_content = record.get('sub_content', '内容暂无')
                    agency_name = record.get('agency_name', '未知机构')
                    
                    context += f"政策标题: {policy_title}\n"
                    if section_title:
                        context += f"章节标题: {section_title}\n"
                        context += f"章节内容: {section_content}\n"
                    if sub_title:
                        context += f"条款标题: {sub_title}\n"
                        context += f"条款内容: {sub_content}\n"
                    context += f"发布机构: {agency_name}\n\n"
                    
                    content_to_display = sub_content if sub_content != '内容暂无' else section_content
                    results.append({
                        "policy_title": policy_title,
                        "section_title": section_title if section_title else sub_title,
                        "content": content_to_display,
                        "agency": agency_name,
                        "relation": "发布单位"
                    })
                
                prompt = (
                    f"你是一个政策法规专家。请根据以下信息回答用户的问题：\n\n"
                    f"{context}\n"
                    f"用户的问题是：{question}\n"
                    f"请用简洁、准确的语言回答，并在回答中引用政策标题和具体章节或条款。"
                )

                response = client.chat(model=LLM_MODEL, messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ])

                return {
                    "answer": response['message']['content'],
                    "entities": results
                }
            else:
                return {
                    "answer": "抱歉，我没有找到与您的问题相关的政策法规信息。",
                    "entities": []
                }
    except Exception as e:
        return {
            "answer": f"查询过程中出现错误: {str(e)}",
            "entities": []
        }

@app.route('/api/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '')
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    result = get_policy_answer(question)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)