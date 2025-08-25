#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政策法规RAG问答系统 - 连接验证脚本

快速诊断前后端连接问题和系统状态
"""

import os
import sys
import time
import requests
import json
from datetime import datetime

def print_header(title):
    """打印标题"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def print_result(test_name, success, message="", details=None):
    """打印测试结果"""
    status = "✅ 通过" if success else "❌ 失败"
    print(f"{status} {test_name}")
    if message:
        print(f"   {message}")
    if details:
        print(f"   详情: {details}")

def test_server_connection():
    """测试服务器基础连接"""
    print_header("1. 服务器连接测试")
    
    base_url = "http://127.0.0.1:5000"
    
    # 测试ping端点
    try:
        response = requests.get(f"{base_url}/ping", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_result("Ping端点", True, f"响应时间: {response.elapsed.total_seconds():.3f}s")
            print(f"   服务器时间: {data.get('timestamp', 'N/A')}")
        else:
            print_result("Ping端点", False, f"HTTP {response.status_code}")
    except requests.exceptions.ConnectionError:
        print_result("Ping端点", False, "无法连接到服务器 - 请确保后端正在运行")
        return False
    except Exception as e:
        print_result("Ping端点", False, f"请求异常: {str(e)}")
        return False
    
    return True

def test_cors_configuration():
    """测试CORS配置"""
    print_header("2. CORS配置测试")
    
    base_url = "http://127.0.0.1:5000"
    
    # 模拟不同来源的请求
    test_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000", 
        "http://127.0.0.1:5000",
        "null",  # file:// 协议
    ]
    
    for origin in test_origins:
        try:
            headers = {"Origin": origin} if origin != "null" else {}
            response = requests.get(f"{base_url}/ping", headers=headers, timeout=5)
            
            cors_headers = {
                "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            }
            
            print_result(f"来源 {origin}", response.status_code == 200, 
                        f"CORS头: {cors_headers['Access-Control-Allow-Origin']}")
                        
        except Exception as e:
            print_result(f"来源 {origin}", False, f"测试失败: {str(e)}")

def test_api_endpoints():
    """测试API端点"""
    print_header("3. API端点测试")
    
    base_url = "http://127.0.0.1:5000"
    
    # 健康检查
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_result("健康检查", True, f"系统状态: {data.get('status', 'unknown')}")
            
            # 显示连接状态
            if 'checks' in data:
                checks = data['checks']
                for check_name, check_data in checks.items():
                    status = check_data.get('status', 'unknown')
                    print(f"   {check_name}: {status}")
        else:
            print_result("健康检查", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("健康检查", False, f"请求失败: {str(e)}")
    
    # 系统状态
    try:
        response = requests.get(f"{base_url}/api/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_result("系统状态", True, "状态详情获取成功")
            
            # 显示连接详情
            if 'connections' in data:
                conn = data['connections']
                print(f"   连接初始化: {conn.get('initialized', False)}")
                if 'neo4j' in conn:
                    print(f"   Neo4j: 已配置")
                if 'ollama' in conn:
                    print(f"   Ollama: 已配置")
        else:
            print_result("系统状态", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("系统状态", False, f"请求失败: {str(e)}")

def test_session_creation():
    """测试会话创建"""
    print_header("4. 会话管理测试")
    
    base_url = "http://127.0.0.1:5000"
    
    try:
        response = requests.post(f"{base_url}/api/session/create", 
                               headers={"Content-Type": "application/json"},
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            print_result("会话创建", True, f"会话ID: {session_id[:8]}...")
            return session_id
        else:
            print_result("会话创建", False, f"HTTP {response.status_code}")
            return None
    except Exception as e:
        print_result("会话创建", False, f"请求失败: {str(e)}")
        return None

def test_question_answer(session_id=None):
    """测试问答功能"""
    print_header("5. 问答功能测试")
    
    base_url = "http://127.0.0.1:5000"
    
    test_questions = [
        "你好，系统工作正常吗？",
        "测试问题",
    ]
    
    for question in test_questions:
        try:
            payload = {"question": question}
            if session_id:
                payload["session_id"] = session_id
            
            print(f"\n测试问题: {question}")
            
            response = requests.post(f"{base_url}/api/ask",
                                   json=payload,
                                   headers={"Content-Type": "application/json"},
                                   timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', '')
                entities = data.get('entities', [])
                
                print_result("问答请求", True, f"回答长度: {len(answer)} 字符")
                print(f"   实体数量: {len(entities)}")
                if answer:
                    # 显示答案前100字符
                    preview = answer[:100] + "..." if len(answer) > 100 else answer
                    print(f"   回答预览: {preview}")
                    
            else:
                print_result("问答请求", False, f"HTTP {response.status_code}")
                if response.text:
                    print(f"   错误信息: {response.text}")
                    
        except Exception as e:
            print_result("问答请求", False, f"请求失败: {str(e)}")

def test_frontend_access():
    """测试前端文件访问"""
    print_header("6. 前端文件检查")
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    frontend_files = {
        "主页面": os.path.join(project_root, "frontend", "index.html"),
        "诊断页面": os.path.join(project_root, "frontend", "diagnostic.html"),
    }
    
    for name, file_path in frontend_files.items():
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print_result(f"{name}", True, f"文件大小: {file_size} 字节")
            print(f"   路径: file://{file_path}")
        else:
            print_result(f"{name}", False, f"文件不存在: {file_path}")

def generate_diagnostic_report():
    """生成诊断报告"""
    print_header("诊断完成")
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "system_info": {
            "python_version": sys.version,
            "platform": sys.platform,
            "cwd": os.getcwd(),
        },
        "recommendations": []
    }
    
    print("🔍 诊断报告:")
    print(f"   时间: {report['timestamp']}")
    print(f"   Python版本: {sys.version.split()[0]}")
    print(f"   工作目录: {os.getcwd()}")
    
    print("\n💡 建议:")
    print("   1. 如果连接失败，请确保后端服务正在运行：")
    print("      python start_server.py")
    print("   2. 如果CORS错误，请检查前端是否使用正确的URL")
    print("   3. 如果API错误，请检查健康状态：http://127.0.0.1:5000/health")
    print("   4. 可以使用诊断页面进行详细测试：frontend/diagnostic.html")

def main():
    """主函数"""
    print_header("政策法规RAG问答系统 - 连接诊断工具")
    print("开始全面系统检查...")
    
    # 依次执行测试
    if not test_server_connection():
        print("\n❌ 服务器连接失败，无法继续其他测试")
        print("\n请确保后端服务正在运行：")
        print("   python start_server.py")
        return
    
    test_cors_configuration()
    test_api_endpoints()
    
    session_id = test_session_creation()
    test_question_answer(session_id)
    
    test_frontend_access()
    generate_diagnostic_report()
    
    print("\n🎉 诊断完成！")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 诊断被中断")
    except Exception as e:
        print(f"\n❌ 诊断过程中出现错误: {e}")