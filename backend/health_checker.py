"""
政策法规RAG问答系统 - 健康检查模块

提供系统健康状态监控和检查功能
"""

import psutil
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.connections import get_connection_manager
from backend.session_manager import get_conversation_manager

# GraphRAG诊断相关导入
try:
    from backend.graphrag_diagnostic import GraphRAGDiagnostic, DiagnosticLevel
    GRAPHRAG_DIAGNOSTIC_AVAILABLE = True
except ImportError:
    GRAPHRAG_DIAGNOSTIC_AVAILABLE = False


class HealthChecker:
    """系统健康检查器"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.check_history: List[Dict[str, Any]] = []
        self.max_history = 100
        
        # 初始化GraphRAG诊断器
        self.graphrag_diagnostic = None
        if GRAPHRAG_DIAGNOSTIC_AVAILABLE:
            try:
                self.graphrag_diagnostic = GraphRAGDiagnostic()
            except Exception as e:
                import logging
                logging.warning(f"GraphRAG诊断器初始化失败: {e}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统整体健康状态"""
        check_time = datetime.now()
        
        # 基础系统信息
        health_data = {
            "timestamp": check_time.isoformat(),
            "uptime_seconds": (check_time - self.start_time).total_seconds(),
            "status": "healthy",
            "checks": {}
        }
        
        # 检查各个组件
        try:
            # 连接状态检查
            connection_health = self._check_connections()
            health_data["checks"]["connections"] = connection_health
            
            # 会话管理器状态
            session_health = self._check_session_manager()
            health_data["checks"]["sessions"] = session_health
            
            # 系统资源检查
            resource_health = self._check_system_resources()
            health_data["checks"]["system_resources"] = resource_health
            
            # 判断整体状态
            all_healthy = all(
                check.get("status") == "healthy" 
                for check in health_data["checks"].values()
            )
            
            health_data["status"] = "healthy" if all_healthy else "unhealthy"
            
        except Exception as e:
            health_data["status"] = "error"
            health_data["error"] = str(e)
        
        # 保存检查历史
        self._save_check_history(health_data)
        
        return health_data
    
    def _check_connections(self) -> Dict[str, Any]:
        """检查连接状态"""
        connection_manager = get_connection_manager()
        
        try:
            if not connection_manager._initialized:
                return {
                    "status": "unhealthy",
                    "message": "连接管理器未初始化",
                    "details": {}
                }
            
            health_status = connection_manager.is_healthy()
            
            details = {
                "neo4j": {
                    "healthy": health_status.get("neo4j", False),
                    "message": "Neo4j数据库连接正常" if health_status.get("neo4j") else "Neo4j数据库连接异常"
                },
                "ollama": {
                    "healthy": health_status.get("ollama", False),
                    "message": "Ollama服务连接正常" if health_status.get("ollama") else "Ollama服务连接异常"
                }
            }
            
            all_connections_healthy = all(health_status.values())
            
            return {
                "status": "healthy" if all_connections_healthy else "unhealthy",
                "message": "所有连接正常" if all_connections_healthy else "部分连接异常",
                "details": details
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"连接检查失败: {str(e)}",
                "details": {}
            }
    
    def _check_session_manager(self) -> Dict[str, Any]:
        """检查会话管理器状态"""
        try:
            session_manager = get_conversation_manager()
            stats = session_manager.get_statistics()
            
            # 检查会话数量是否过多
            session_usage = stats["total_sessions"] / stats["max_sessions"]
            
            status = "healthy"
            message = "会话管理器运行正常"
            
            if session_usage > 0.9:
                status = "warning"
                message = "会话数量接近上限"
            elif session_usage > 0.95:
                status = "unhealthy"
                message = "会话数量过多"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "total_sessions": stats["total_sessions"],
                    "active_sessions": stats["active_sessions"],
                    "session_usage_ratio": round(session_usage, 2),
                    "total_messages": stats["total_messages"]
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"会话管理器检查失败: {str(e)}",
                "details": {}
            }
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """检查系统资源使用情况"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 评估状态
            status = "healthy"
            warnings = []
            
            if cpu_percent > 80:
                status = "warning"
                warnings.append("CPU使用率过高")
            
            if memory_percent > 85:
                status = "warning" if status == "healthy" else "unhealthy"
                warnings.append("内存使用率过高")
            
            if disk_percent > 90:
                status = "warning" if status == "healthy" else "unhealthy"
                warnings.append("磁盘使用率过高")
            
            return {
                "status": status,
                "message": "系统资源正常" if status == "healthy" else f"资源警告: {', '.join(warnings)}",
                "details": {
                    "cpu_percent": round(cpu_percent, 1),
                    "memory_percent": round(memory_percent, 1),
                    "disk_percent": round(disk_percent, 1),
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_free_gb": round(disk.free / (1024**3), 2)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"系统资源检查失败: {str(e)}",
                "details": {}
            }
    
    def _save_check_history(self, health_data: Dict[str, Any]):
        """保存健康检查历史"""
        # 只保留关键信息以节省内存
        history_entry = {
            "timestamp": health_data["timestamp"],
            "status": health_data["status"],
            "uptime_seconds": health_data["uptime_seconds"]
        }
        
        # 添加各组件状态
        if "checks" in health_data:
            history_entry["component_status"] = {
                component: check.get("status", "unknown")
                for component, check in health_data["checks"].items()
            }
        
        self.check_history.append(history_entry)
        
        # 保持历史记录在限制范围内
        if len(self.check_history) > self.max_history:
            self.check_history = self.check_history[-self.max_history:]
    
    def get_health_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取健康检查历史"""
        return self.check_history[-limit:]
    
    def get_uptime_info(self) -> Dict[str, Any]:
        """获取系统运行时间信息"""
        now = datetime.now()
        uptime = now - self.start_time
        
        return {
            "start_time": self.start_time.isoformat(),
            "current_time": now.isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": str(uptime).split('.')[0],  # 去掉微秒
            "total_health_checks": len(self.check_history)
        }
    
    def get_connection_details(self) -> Dict[str, Any]:
        """获取连接详细信息"""
        try:
            connection_manager = get_connection_manager()
            return connection_manager.get_status()
        except Exception as e:
            return {
                "error": f"获取连接信息失败: {str(e)}",
                "initialized": False
            }
    
    def perform_deep_check(self) -> Dict[str, Any]:
        """执行深度健康检查"""
        deep_check = self.get_system_health()
        
        # 添加额外的深度检查项
        try:
            # 测试数据库查询
            connection_manager = get_connection_manager()
            if connection_manager.neo4j:
                start_time = time.time()
                test_result = connection_manager.neo4j.execute_query("RETURN 1 as test")
                query_time = time.time() - start_time
                
                deep_check["checks"]["database_performance"] = {
                    "status": "healthy" if test_result and query_time < 5 else "warning",
                    "query_time_seconds": round(query_time, 3),
                    "message": f"数据库查询耗时 {query_time:.3f} 秒"
                }
            
            # 测试LLM服务响应
            if connection_manager.ollama:
                start_time = time.time()
                models = connection_manager.ollama.get_available_models()
                llm_response_time = time.time() - start_time
                
                deep_check["checks"]["llm_service_performance"] = {
                    "status": "healthy" if llm_response_time < 10 else "warning",
                    "response_time_seconds": round(llm_response_time, 3),
                    "available_models": len(models),
                    "message": f"LLM服务响应耗时 {llm_response_time:.3f} 秒"
                }
            
        except Exception as e:
            deep_check["checks"]["performance_test"] = {
                "status": "error",
                "message": f"性能测试失败: {str(e)}"
            }
        
        return deep_check
    
    def get_graphrag_diagnosis(self, level: str = "basic", components: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取GraphRAG诊断结果"""
        if not self.graphrag_diagnostic:
            return {
                "status": "unavailable",
                "message": "GraphRAG诊断功能不可用",
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # 转换诊断级别
            diagnostic_level = DiagnosticLevel.BASIC
            if level.lower() == "full":
                diagnostic_level = DiagnosticLevel.FULL
            elif level.lower() == "repair":
                diagnostic_level = DiagnosticLevel.REPAIR
            
            # 执行GraphRAG诊断
            diagnosis_result = self.graphrag_diagnostic.diagnose_system(
                level=diagnostic_level,
                components=components
            )
            
            return diagnosis_result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"GraphRAG诊断失败: {str(e)}",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_quick_graphrag_status(self) -> Dict[str, Any]:
        """获取快速GraphRAG状态检查"""
        if not self.graphrag_diagnostic:
            return {
                "graphrag_available": False,
                "status": "unavailable",
                "message": "GraphRAG诊断功能不可用"
            }
        
        try:
            quick_status = self.graphrag_diagnostic.get_quick_status()
            return {
                "graphrag_available": True,
                **quick_status
            }
        except Exception as e:
            return {
                "graphrag_available": False,
                "status": "error",
                "message": f"快速检查失败: {str(e)}",
                "error": str(e)
            }
    
    def get_comprehensive_health_report(self) -> Dict[str, Any]:
        """获取综合健康报告（包含GraphRAG诊断）"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "report_type": "comprehensive",
            "basic_health": self.get_system_health(),
            "deep_check": self.perform_deep_check(),
            "graphrag_diagnosis": None,
            "overall_assessment": {}
        }
        
        # 添加GraphRAG诊断
        if self.graphrag_diagnostic:
            report["graphrag_diagnosis"] = self.get_graphrag_diagnosis("full")
        
        # 生成整体评估
        all_statuses = []
        
        # 收集基本健康状态
        basic_status = report["basic_health"].get("status", "unknown")
        all_statuses.append(basic_status)
        
        # 收集深度检查状态
        deep_status = report["deep_check"].get("status", "unknown")
        all_statuses.append(deep_status)
        
        # 收集GraphRAG诊断状态
        if report["graphrag_diagnosis"]:
            graphrag_status = report["graphrag_diagnosis"].get("overall_status", "unknown")
            all_statuses.append(graphrag_status)
        
        # 确定整体状态
        if "error" in all_statuses or "unhealthy" in all_statuses:
            overall_status = "critical"
        elif "warning" in all_statuses:
            overall_status = "degraded"
        elif "healthy" in all_statuses:
            overall_status = "healthy"
        else:
            overall_status = "unknown"
        
        # 生成评估结果
        report["overall_assessment"] = {
            "status": overall_status,
            "component_count": len(all_statuses),
            "status_distribution": {
                status: all_statuses.count(status) for status in set(all_statuses)
            },
            "graphrag_available": self.graphrag_diagnostic is not None
        }
        
        return report


# 全局健康检查器实例
health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    """获取全局健康检查器实例"""
    return health_checker


def create_health_endpoints():
    """创建GraphRAG增强的健康检查相关的Flask路由"""
    from flask import jsonify, request
    
    def health():
        """基础健康检查端点"""
        try:
            health_data = health_checker.get_system_health()
            status_code = 200 if health_data["status"] == "healthy" else 503
            return jsonify(health_data), status_code
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"健康检查失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }), 500
    
    def health_deep():
        """深度健康检查端点"""
        try:
            health_data = health_checker.perform_deep_check()
            status_code = 200 if health_data["status"] == "healthy" else 503
            return jsonify(health_data), status_code
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"深度健康检查失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }), 500
    
    def health_graphrag():
        """GraphRAG专项诊断端点"""
        try:
            # 获取请求参数
            level = request.args.get('level', 'basic')  # basic, full, repair
            components = request.args.get('components', '').split(',') if request.args.get('components') else None
            
            # 执行诊断
            diagnosis_result = health_checker.get_graphrag_diagnosis(level, components)
            
            # 确定 HTTP 状态码
            if diagnosis_result.get("overall_status") == "healthy":
                status_code = 200
            elif diagnosis_result.get("overall_status") in ["warning", "degraded"]:
                status_code = 200  # 警告不返回503
            else:
                status_code = 503
            
            return jsonify(diagnosis_result), status_code
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"GraphRAG诊断失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }), 500
    
    def health_comprehensive():
        """综合健康报告端点"""
        try:
            comprehensive_report = health_checker.get_comprehensive_health_report()
            
            # 根据整体评估确定状态码
            overall_status = comprehensive_report.get("overall_assessment", {}).get("status", "unknown")
            if overall_status == "healthy":
                status_code = 200
            elif overall_status == "degraded":
                status_code = 200
            else:
                status_code = 503
            
            return jsonify(comprehensive_report), status_code
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"综合健康报告失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }), 500
    
    def health_quick_graphrag():
        """快速GraphRAG状态检查端点"""
        try:
            quick_status = health_checker.get_quick_graphrag_status()
            
            status_code = 200 if quick_status.get("status") == "healthy" else 503
            return jsonify(quick_status), status_code
            
        except Exception as e:
            return jsonify({
                "status": "error", 
                "message": f"快速GraphRAG检查失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }), 500
    
    def health_history():
        """健康检查历史端点"""
        try:
            limit = int(request.args.get('limit', 50))
            history = health_checker.get_health_history(limit)
            
            return jsonify({
                "status": "success",
                "history": history,
                "count": len(history),
                "limit": limit
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"获取健康检查历史失败: {str(e)}"
            }), 500
    
    def uptime():
        """系统运行时间端点"""
        try:
            uptime_info = health_checker.get_uptime_info()
            return jsonify(uptime_info)
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"获取运行时间信息失败: {str(e)}"
            }), 500
    
    def health_diagnosis_history():
        """GraphRAG诊断历史端点"""
        try:
            if not health_checker.graphrag_diagnostic:
                return jsonify({
                    "status": "unavailable",
                    "message": "GraphRAG诊断功能不可用"
                }), 503
            
            limit = int(request.args.get('limit', 20))
            diagnosis_history = health_checker.graphrag_diagnostic.get_diagnosis_history(limit)
            
            return jsonify({
                "status": "success",
                "diagnosis_history": diagnosis_history,
                "count": len(diagnosis_history),
                "limit": limit
            })
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"获取诊断历史失败: {str(e)}"
            }), 500
    
    return {
        'health': health,
        'health_deep': health_deep,
        'health_graphrag': health_graphrag,
        'health_comprehensive': health_comprehensive,
        'health_quick_graphrag': health_quick_graphrag,
        'health_history': health_history,
        'health_diagnosis_history': health_diagnosis_history,
        'uptime': uptime
    }