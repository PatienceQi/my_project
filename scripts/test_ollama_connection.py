import os
import ollama

# Read environment variables
LLM_BINDING = os.getenv('LLM_BINDING', 'ollama')
LLM_MODEL = os.getenv('LLM_MODEL', 'llama3.2:latest')
LLM_BINDING_API_KEY = os.getenv('LLM_BINDING_API_KEY', 'your_api_key')
LLM_BINDING_HOST = os.getenv('LLM_BINDING_HOST', 'http://120.232.79.82:11434')

# Configure ollama client
client = ollama.Client(host=LLM_BINDING_HOST)

# Test connection to ollama service
try:
    response = client.chat(model=LLM_MODEL, messages=[
        {
            'role': 'user',
            'content': 'Hello, can you respond to me?'
        }
    ])
    print('Connection successful! Response from ollama:')
    print(response['message']['content'])
except Exception as e:
    print('Error connecting to ollama service:')
    print(e)