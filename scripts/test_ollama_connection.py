import os
import requests

# Read environment variables
LLM_BINDING = os.getenv('LLM_BINDING', 'ollama')
LLM_MODEL = os.getenv('LLM_MODEL', 'llama3.2:latest')
LLM_BINDING_API_KEY = os.getenv('LLM_BINDING_API_KEY', 'your_api_key')
LLM_BINDING_HOST = os.getenv('LLM_BINDING_HOST', 'http://120.232.79.82:11434')

# 强制设置远程配置
os.environ['OLLAMA_HOST'] = LLM_BINDING_HOST
os.environ['OLLAMA_BASE_URL'] = LLM_BINDING_HOST
os.environ['OLLAMA_NO_SERVE'] = '1'
os.environ['OLLAMA_ORIGINS'] = '*'

print(f"测试Ollama连接: {LLM_BINDING_HOST}")
print(f"使用模型: {LLM_MODEL}")

# Test connection to ollama service using HTTP API
try:
    # 使用HTTP API而不是ollama客户端
    url = f"{LLM_BINDING_HOST}/api/chat"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                'role': 'user',
                'content': 'Hello, can you respond to me?'
            }
        ],
        "stream": False
    }
    
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    print('Connection successful! Response from ollama:')
    print(result['message']['content'])
    
except Exception as e:
    print('Error connecting to ollama service:')
    print(e)