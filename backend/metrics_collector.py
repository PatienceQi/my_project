"""
政策法规RAG问答系统 - 监控指标收集模块

提供系统性能、资源使用和业务指标的收集功能
"""

import time
import psutil
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from backend.connections import get_connection_manager
from backend.session_manager import get_conversation_manager

try:
    from backend.graphrag_engine import GraphRAGEngine
    GRAPHRAG_AVAILABLE = True
except ImportError:
    GRAPHRAG_AVAILABLE = False

# 全局指标收集器实例
_metrics_collector = None


class MetricsCollector:
    """监控指标收集器"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.start_time = datetime.now()
        
        # 指标存储
        self.system_metrics = deque(maxlen=max_history)
        self.api_metrics = defaultdict(lambda: deque(maxlen=max_history))
        self.business_metrics = defaultdict(lambda: deque(maxlen=max_history))
        
        # 请求计数器
        self.request_counter = defaultdict(int)
        self.error_counter = defaultdict(int)
        
        # 性能计时器
        self.performance_timers = {}
        
        # 启动后台收集线程
        self._start_background_collection()
    
    def _start_background_collection(self):
        """启动后台指标收集"""
        def collect_system_metrics():
            while True:
                try:
                    metrics = self._collect_system_metrics()
                    self.system_metrics.append({
                        "timestamp": datetime.now().isoformat(),
                        "metrics": metrics
                    })
                    time.sleep(60)  # 每分钟收集一次
                except Exception as e:
                    print(f"后台指标收集出错: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=collect_system_metrics, daemon=True)
        thread.start()
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统级指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            
            # 网络IO
            net_io = psutil.net_io_counters()
            
            return {
                "cpu_percent": round(cpu_percent, 2),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_percent": round(memory.percent, 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_percent": round(disk.percent, 2),
                "network_bytes_sent": net_io.bytes_sent,
                "network_bytes_recv": net_io.bytes_recv
            }
        except Exception as e:
            return {"error": f"系统指标收集失败: {str(e)}"}
    
    def start_timer(self, timer_name: str) -> str:
        """开始计时器"""
        timer_id = f"{timer_name}_{datetime.now().timestamp()}"
        self.performance_timers[timer_id] = {
            "name": timer_name,
            "start_time": time.time()
        }
        return timer_id
    
    def stop_timer(self, timer_id: str) -> Optional[float]:
        """停止计时器并返回耗时"""
        if timer_id in self.performance_timers:
            timer = self.performance_timers.pop(timer_id)
            elapsed_time = time.time() - timer["start_time"]
            return elapsed_time
        return None
    
    def record_api_request(self, endpoint: str, method: str, status_code: int, 
                          response_time: float, request_size: int = 0, 
                          response_size: int = 0):
        """记录API请求指标"""
        self.request_counter[endpoint] += 1
        
        if status_code >= 400:
            self.error_counter[endpoint] += 1
        
        metric = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "status_code": status_code,
            "response_time_ms": round(response_time * 1000, 2),
            "request_size_bytes": request_size,
            "response_size_bytes": response_size
        }
        
        self.api_metrics[endpoint].append(metric)
    
    def record_business_metric(self, metric_name: str, value: Any, 
                              tags: Optional[Dict[str, str]] = None):
        """记录业务指标"""
        metric = {
            "timestamp": datetime.now().isoformat(),
            "value": value,
            "tags": tags or {}
        }
        
        self.business_metrics[metric_name].append(metric)
    
    def record_question_processing(self, question_length: int, answer_length: int, 
                                 processing_time: float, method: str = "traditional",
                                 confidence: Optional[float] = None,
                                 entities_count: Optional[int] = None):
        """记录问题处理指标"""
        self.record_business_metric("question_processing", {
            "question_length": question_length,
            "answer_length": answer_length,
            "processing_time": processing_time,
            "method": method,
            "confidence": confidence,
            "entities_count": entities_count
        }, {"method": method})
    
    def get_system_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取系统指标历史"""
        return list(self.system_metrics)[-limit:]
    
    def get_api_metrics(self, endpoint: Optional[str] = None, limit: int = 100) -> Dict[str, List]:
        """获取API指标"""
        if endpoint:
            return {endpoint: list(self.api_metrics[endpoint])[-limit:]}
        else:
            return {ep: list(metrics)[-limit:] for ep, metrics in self.api_metrics.items()}
    
    def get_business_metrics(self, metric_name: Optional[str] = None, limit: int = 100) -> Dict[str, List]:
        """获取业务指标"""
        if metric_name:
            return {metric_name: list(self.business_metrics[metric_name])[-limit:]}
        else:
            return {name: list(metrics)[-limit:] for name, metrics in self.business_metrics.items()}
    
    def get_request_summary(self) -> Dict[str, Any]:
        """获取请求摘要"""
        total_requests = sum(self.request_counter.values())
        total_errors = sum(self.error_counter.values())
        
        # 计算错误率
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        # 计算各端点的平均响应时间
        endpoint_avg_times = {}
        for endpoint, metrics in self.api_metrics.items():
            if metrics:
                avg_time = sum(m["response_time_ms"] for m in metrics) / len(metrics)
                endpoint_avg_times[endpoint] = round(avg_time, 2)
        
        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate_percent": round(error_rate, 2),
            "requests_by_endpoint": dict(self.request_counter),
            "errors_by_endpoint": dict(self.error_counter),
            "average_response_times_ms": endpoint_avg_times
        }
    
    def get_system_uptime(self) -> Dict[str, Any]:
        """获取系统运行时间"""
        uptime = datetime.now() - self.start_time
        return {
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": str(uptime).split('.')[0]
        }
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """获取综合指标报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "system_uptime": self.get_system_uptime(),
            "request_summary": self.get_request_summary(),
            "system_metrics_latest": dict(self.system_metrics[-1]) if self.system_metrics else {},
            "business_metrics_summary": {}
        }
        
        # 生成业务指标摘要
        for metric_name, metrics in self.business_metrics.items():
            if metrics:
                latest_value = metrics[-1]["value"]
                report["business_metrics_summary"][metric_name] = {
                    "latest": latest_value,
                    "count": len(metrics)
                }
        
        # 删除GraphRAG特定指标收集，避免创建新引擎实例导致资源冲突
        # 修复：不再在指标收集中创建GraphRAG引擎实例
        # GraphRAG统计信息应通过专门的API端点获取
        
        # 添加连接状态
        try:
            connection_manager = get_connection_manager()
            report["connection_status"] = connection_manager.get_status()
        except Exception as e:
            report["connection_status"] = {"error": f"获取连接状态失败: {str(e)}"}
        
        # 添加会话统计
        try:
            session_manager = get_conversation_manager()
            report["session_stats"] = session_manager.get_statistics()
        except Exception as e:
            report["session_stats"] = {"error": f"获取会话统计失败: {str(e)}"}
        
        return report


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def create_metrics_endpoints():
    """创建监控指标相关的Flask路由"""
    from flask import jsonify, request
    
    def metrics_system():
        """系统指标端点"""
        try:
            collector = get_metrics_collector()
            limit = int(request.args.get('limit', 50))
            metrics = collector.get_system_metrics(limit)
            return jsonify({
                "status": "success",
                "metrics": metrics,
                "count": len(metrics)
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"获取系统指标失败: {str(e)}"
            }), 500
    
    def metrics_api():
        """API指标端点"""
        try:
            collector = get_metrics_collector()
            endpoint = request.args.get('endpoint')
            limit = int(request.args.get('limit', 50))
            metrics = collector.get_api_metrics(endpoint, limit)
            return jsonify({
                "status": "success",
                "metrics": metrics
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"获取API指标失败: {str(e)}"
            }), 500
    
    def metrics_business():
        """业务指标端点"""
        try:
            collector = get_metrics_collector()
            metric_name = request.args.get('metric')
            limit = int(request.args.get('limit', 50))
            metrics = collector.get_business_metrics(metric_name, limit)
            return jsonify({
                "status": "success",
                "metrics": metrics
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"获取业务指标失败: {str(e)}"
            }), 500
    
    def metrics_summary():
        """指标摘要端点"""
        try:
            collector = get_metrics_collector()
            summary = collector.get_request_summary()
            return jsonify({
                "status": "success",
                "summary": summary
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"获取指标摘要失败: {str(e)}"
            }), 500
    
    def metrics_comprehensive():
        """综合指标报告端点"""
        try:
            collector = get_metrics_collector()
            report = collector.get_comprehensive_metrics()
            return jsonify({
                "status": "success",
                "report": report
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"获取综合指标报告失败: {str(e)}"
            }), 500
    
    return {
        'metrics_system': metrics_system,
        'metrics_api': metrics_api,
        'metrics_business': metrics_business,
        'metrics_summary': metrics_summary,
        'metrics_comprehensive': metrics_comprehensive
    }