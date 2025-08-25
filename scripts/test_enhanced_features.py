#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政策法规RAG问答系统 - 增强功能测试脚本

测试错误处理、输入验证、连接管理、会话管理和健康检查等新功能
"""

import os
import sys
import json
import time
import requests
from datetime import datetime

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入后端模块进行单元测试
try:
    from backend.exceptions import ValidationError, DatabaseError, LLMServiceError
    from backend.validators import InputValidator, SecurityChecker
    from backend.connections import ConnectionManager
    from backend.session_manager import ConversationManager
    from backend.health_checker import HealthChecker
    BACKEND_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入后端模块: {e}")
    BACKEND_MODULES_AVAILABLE = False

class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
    
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """记录测试结果"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "PASS"
        else:
            self.failed_tests += 1
            status = "FAIL"
        
        result = {
            "test_name": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        self.test_results.append(result)
        print(f"[{status}] {test_name}: {message}")
    
    def test_input_validation(self):
        """测试输入验证功能"""
        if not BACKEND_MODULES_AVAILABLE:
            self.log_test("输入验证测试", False, "后端模块不可用")
            return
        
        print("\n=== 输入验证测试 ===")
        
        # 测试正常输入
        is_valid, error, cleaned = InputValidator.validate_question("这是一个正常的问题")
        self.log_test("正常输入验证", is_valid and not error, f"结果: {is_valid}, 错误: {error}")
        
        # 测试空输入
        is_valid, error, cleaned = InputValidator.validate_question("")
        self.log_test("空输入验证", not is_valid and error, f"错误信息: {error}")
        
        # 测试过长输入
        long_text = "a" * 1001
        is_valid, error, cleaned = InputValidator.validate_question(long_text)
        self.log_test("过长输入验证", not is_valid and "超过" in error, f"错误信息: {error}")
        
        # 测试非法字符
        is_valid, error, cleaned = InputValidator.validate_question("包含<script>的问题")
        self.log_test("非法字符验证", not is_valid and error, f"错误信息: {error}")
        
        # 测试会话ID验证
        is_valid, error = InputValidator.validate_session_id("123e4567-e89b-12d3-a456-426614174000")
        self.log_test("正确会话ID验证", is_valid and not error, f"结果: {is_valid}")
        
        is_valid, error = InputValidator.validate_session_id("invalid-session-id")
        self.log_test("错误会话ID验证", not is_valid and error, f"错误信息: {error}")
    
    def test_error_handling(self):
        """测试错误处理功能"""
        if not BACKEND_MODULES_AVAILABLE:
            self.log_test("错误处理测试", False, "后端模块不可用")
            return
        
        print("\n=== 错误处理测试 ===")
        
        # 测试各种异常类型
        try:
            error = ValidationError("测试验证错误", "test_field", "test_value")
            error_dict = error.to_dict()
            self.log_test("ValidationError测试", 
                         error_dict["error_code"] == "VALIDATION_ERROR", 
                         f"错误代码: {error_dict['error_code']}")
        except Exception as e:
            self.log_test("ValidationError测试", False, f"异常: {str(e)}")
        
        try:
            error = DatabaseError("测试数据库错误", "test_operation")
            error_dict = error.to_dict()
            self.log_test("DatabaseError测试", 
                         error_dict["error_code"] == "DATABASE_ERROR", 
                         f"错误代码: {error_dict['error_code']}")
        except Exception as e:
            self.log_test("DatabaseError测试", False, f"异常: {str(e)}")
        
        try:
            error = LLMServiceError("测试LLM错误", "test_model")
            error_dict = error.to_dict()
            self.log_test("LLMServiceError测试", 
                         error_dict["error_code"] == "LLM_SERVICE_ERROR", 
                         f"错误代码: {error_dict['error_code']}")
        except Exception as e:
            self.log_test("LLMServiceError测试", False, f"异常: {str(e)}")
    
    def test_session_management(self):
        """测试会话管理功能"""
        if not BACKEND_MODULES_AVAILABLE:
            self.log_test("会话管理测试", False, "后端模块不可用")
            return
        
        print("\n=== 会话管理测试 ===")
        
        try:
            manager = ConversationManager()
            
            # 创建会话
            session_id = manager.create_session()
            self.log_test("会话创建", bool(session_id), f"会话ID: {session_id[:8]}...")
            
            # 添加消息
            success = manager.add_message_to_session(session_id, "user", "测试问题")
            self.log_test("添加用户消息", success, "消息添加成功")
            
            success = manager.add_message_to_session(session_id, "assistant", "测试回答")
            self.log_test("添加助手消息", success, "消息添加成功")
            
            # 获取会话摘要
            summary = manager.get_session_summary(session_id)
            self.log_test("获取会话摘要", 
                         summary and summary["total_messages"] == 2, 
                         f"消息数量: {summary['total_messages'] if summary else 0}")
            
            # 获取上下文
            context = manager.get_context_for_question(session_id, "新问题")
            self.log_test("生成上下文问题", 
                         "测试问题" in context, 
                         f"上下文长度: {len(context)}")
            
            # 获取统计信息
            stats = manager.get_statistics()
            self.log_test("获取统计信息", 
                         stats["active_sessions"] >= 1, 
                         f"活跃会话数: {stats['active_sessions']}")
        
        except Exception as e:
            self.log_test("会话管理测试", False, f"异常: {str(e)}")
    
    def test_health_endpoints(self):
        """测试健康检查端点"""
        print("\n=== 健康检查端点测试 ===")
        
        endpoints = [
            ("/health", "基础健康检查"),
            ("/health/deep", "深度健康检查"),
            ("/api/uptime", "运行时间查询"),
            ("/api/status", "系统状态查询")
        ]
        
        for endpoint, description in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                success = response.status_code in [200, 503]  # 503也是有效响应
                
                if success:
                    try:
                        data = response.json()
                        self.log_test(description, True, f"状态码: {response.status_code}, 有数据返回")
                    except:
                        self.log_test(description, False, f"状态码: {response.status_code}, 但无法解析JSON")
                else:
                    self.log_test(description, False, f"状态码: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.log_test(description, False, f"请求失败: {str(e)}")
    
    def test_session_api_endpoints(self):
        """测试会话管理API端点"""
        print("\n=== 会话管理API测试 ===")
        
        session_id = None
        
        # 测试创建会话
        try:
            response = requests.post(f"{self.base_url}/api/session/create", timeout=10)
            if response.status_code == 200:
                data = response.json()
                session_id = data.get("session_id")
                self.log_test("创建会话API", bool(session_id), f"会话ID: {session_id[:8] if session_id else 'None'}...")
            else:
                self.log_test("创建会话API", False, f"状态码: {response.status_code}")
        except Exception as e:
            self.log_test("创建会话API", False, f"请求失败: {str(e)}")
        
        # 测试会话摘要
        if session_id:
            try:
                response = requests.get(f"{self.base_url}/api/session/{session_id}/summary", timeout=10)
                success = response.status_code in [200, 404]  # 新会话可能返回404
                self.log_test("会话摘要API", success, f"状态码: {response.status_code}")
            except Exception as e:
                self.log_test("会话摘要API", False, f"请求失败: {str(e)}")
        
        # 测试列出会话
        try:
            response = requests.get(f"{self.base_url}/api/sessions", timeout=10)
            success = response.status_code == 200
            if success:
                data = response.json()
                count = data.get("count", 0)
                self.log_test("列出会话API", True, f"会话数量: {count}")
            else:
                self.log_test("列出会话API", False, f"状态码: {response.status_code}")
        except Exception as e:
            self.log_test("列出会话API", False, f"请求失败: {str(e)}")
    
    def test_enhanced_ask_api(self):
        """测试增强的问答API"""
        print("\n=== 增强问答API测试 ===")
        
        # 测试输入验证
        test_cases = [
            ({}, "空请求体", False),
            ({"question": ""}, "空问题", False),
            ({"question": "a" * 1001}, "过长问题", False),
            ({"question": "包含<script>标签的问题"}, "非法字符", False),
            ({"question": "正常问题"}, "正常问题", True),
            ({"question": "带会话ID的问题", "session_id": "invalid-id"}, "无效会话ID", False),
        ]
        
        for request_data, description, should_succeed in test_cases:
            try:
                response = requests.post(
                    f"{self.base_url}/api/ask", 
                    json=request_data,
                    timeout=30
                )
                
                if should_succeed:
                    success = response.status_code == 200
                    message = f"状态码: {response.status_code}"
                    if success:
                        try:
                            data = response.json()
                            message += f", 有答案: {'answer' in data}"
                        except:
                            success = False
                            message += ", 无法解析响应"
                else:
                    success = response.status_code == 400
                    message = f"状态码: {response.status_code}"
                
                self.log_test(f"问答API - {description}", success, message)
                
            except Exception as e:
                self.log_test(f"问答API - {description}", False, f"请求失败: {str(e)}")
    
    def test_connection_recovery(self):
        """测试连接恢复能力"""
        print("\n=== 连接恢复测试 ===")
        
        # 多次健康检查，测试稳定性
        success_count = 0
        total_checks = 5
        
        for i in range(total_checks):
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code in [200, 503]:
                    success_count += 1
                time.sleep(1)
            except:
                pass
        
        stability_ratio = success_count / total_checks
        self.log_test("连接稳定性测试", 
                     stability_ratio >= 0.8, 
                     f"成功率: {stability_ratio*100:.1f}% ({success_count}/{total_checks})")
    
    def run_all_tests(self):
        """运行所有测试"""
        print(f"开始测试政策法规RAG问答系统增强功能")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"目标服务器: {self.base_url}")
        
        # 运行各项测试
        self.test_input_validation()
        self.test_error_handling()
        self.test_session_management()
        self.test_health_endpoints()
        self.test_session_api_endpoints()
        self.test_enhanced_ask_api()
        self.test_connection_recovery()
        
        # 输出测试总结
        print(f"\n{'='*60}")
        print(f"测试总结")
        print(f"{'='*60}")
        print(f"总测试数: {self.total_tests}")
        print(f"通过: {self.passed_tests}")
        print(f"失败: {self.failed_tests}")
        print(f"通过率: {(self.passed_tests/self.total_tests*100):.1f}%")
        
        # 显示失败的测试
        failed_tests = [test for test in self.test_results if test["status"] == "FAIL"]
        if failed_tests:
            print(f"\n失败的测试:")
            for test in failed_tests:
                print(f"  - {test['test_name']}: {test['message']}")
        
        # 保存测试结果
        self.save_test_results()
        
        return self.failed_tests == 0
    
    def save_test_results(self):
        """保存测试结果到文件"""
        result_file = "test_results_enhanced_features.json"
        
        test_report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "pass_rate": round(self.passed_tests/self.total_tests*100, 1) if self.total_tests > 0 else 0
            },
            "details": self.test_results
        }
        
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(test_report, f, ensure_ascii=False, indent=2)
            print(f"\n测试结果已保存到: {result_file}")
        except Exception as e:
            print(f"保存测试结果失败: {str(e)}")


def main():
    """主函数"""
    print("政策法规RAG问答系统 - 增强功能测试")
    print("=" * 60)
    
    # 检查服务器是否运行
    test_runner = TestRunner()
    
    try:
        response = requests.get(f"{test_runner.base_url}/health", timeout=5)
        print(f"✓ 服务器响应正常 (状态码: {response.status_code})")
    except requests.exceptions.RequestException:
        print("✗ 警告: 无法连接到服务器，部分测试可能失败")
        print(f"  请确保服务器在 {test_runner.base_url} 运行")
    
    # 运行测试
    success = test_runner.run_all_tests()
    
    # 根据测试结果设置退出代码
    if success:
        print("\n🎉 所有测试通过!")
        exit(0)
    else:
        print("\n❌ 部分测试失败，请检查系统配置")
        exit(1)


if __name__ == "__main__":
    main()