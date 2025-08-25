"""
GraphRAG实验评估脚本
支持对比实验、性能评估和结果分析
"""

import os
import sys
import json
import time
import logging
from typing import List, Dict, Any
from pathlib import Path
import statistics
from datetime import datetime

# 添加backend目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from backend.graphrag_engine import GraphRAGEngine
    from backend.api_server import generate_policy_answer
    GRAPHRAG_AVAILABLE = True
except ImportError as e:
    print(f"GraphRAG模块不可用: {e}")
    GRAPHRAG_AVAILABLE = False

class ExperimentEvaluator:
    """实验评估器"""
    
    def __init__(self):
        self.results_dir = Path("evaluation_results")
        self.results_dir.mkdir(exist_ok=True)
        
        self.graphrag_engine = None
        if GRAPHRAG_AVAILABLE:
            try:
                self.graphrag_engine = GraphRAGEngine()
                logging.info("GraphRAG引擎初始化成功")
            except Exception as e:
                logging.error(f"GraphRAG引擎初始化失败: {e}")
        
        # 测试问题集
        self.test_questions = [
            {
                "id": "Q001",
                "question": "华侨经济文化合作试验区的管理机构是什么？",
                "category": "机构查询",
                "expected_entities": ["华侨经济文化合作试验区", "管理委员会"]
            },
            {
                "id": "Q002", 
                "question": "中小企业有哪些税收优惠政策？",
                "category": "政策查询",
                "expected_entities": ["中小企业", "税收优惠"]
            },
            {
                "id": "Q003",
                "question": "投资项目需要哪些审批程序？",
                "category": "流程查询", 
                "expected_entities": ["投资项目", "审批程序"]
            },
            {
                "id": "Q004",
                "question": "试验区内企业的注册条件是什么？",
                "category": "条件查询",
                "expected_entities": ["试验区", "企业注册", "条件"]
            },
            {
                "id": "Q005",
                "question": "政策法规的发布机构有哪些？",
                "category": "机构查询",
                "expected_entities": ["政策法规", "发布机构"]
            }
        ]
        
        logging.info("实验评估器初始化完成")
    
    def evaluate_single_question(self, question_data: Dict, method: str) -> Dict:
        """评估单个问题"""
        question = question_data["question"]
        start_time = time.time()
        
        try:
            if method == "graphrag" and self.graphrag_engine:
                result = self.graphrag_engine.answer_question(
                    question, use_graph=True, return_confidence=True
                )
                answer = result["answer"]
                confidence = result.get("confidence", 0)
                warnings = result.get("warnings", [])
                entities = result.get("question_entities", [])
                sources_count = len(result.get("sources", []))
                
            elif method == "traditional":
                result = generate_policy_answer(question)
                answer = result["answer"]
                confidence = None
                warnings = []
                entities = result.get("entities", [])
                sources_count = 0
                
            else:
                raise ValueError(f"不支持的方法: {method}")
            
            processing_time = time.time() - start_time
            
            # 评估指标
            evaluation = {
                "question_id": question_data["id"],
                "question": question,
                "method": method,
                "answer": answer,
                "answer_length": len(answer),
                "processing_time": round(processing_time, 3),
                "confidence": confidence,
                "warnings_count": len(warnings),
                "warnings": warnings,
                "extracted_entities": entities,
                "entities_count": len(entities),
                "sources_count": sources_count,
                "timestamp": datetime.now().isoformat()
            }
            
            # 实体匹配评估
            expected_entities = question_data.get("expected_entities", [])
            if expected_entities:
                matched_entities = 0
                for expected in expected_entities:
                    for extracted in entities:
                        if expected.lower() in extracted.lower() or extracted.lower() in expected.lower():
                            matched_entities += 1
                            break
                
                evaluation["entity_recall"] = matched_entities / len(expected_entities) if expected_entities else 0
                evaluation["entity_precision"] = matched_entities / len(entities) if entities else 0
            
            return evaluation
            
        except Exception as e:
            logging.error(f"评估失败 {method}: {e}")
            return {
                "question_id": question_data["id"],
                "question": question,
                "method": method,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
    
    def run_comparison_experiment(self) -> Dict:
        """运行对比实验"""
        logging.info("开始对比实验...")
        
        results = {
            "experiment_info": {
                "start_time": datetime.now().isoformat(),
                "questions_count": len(self.test_questions),
                "methods": ["traditional", "graphrag"] if GRAPHRAG_AVAILABLE else ["traditional"]
            },
            "results": []
        }
        
        for i, question_data in enumerate(self.test_questions):
            logging.info(f"评估问题 {i+1}/{len(self.test_questions)}: {question_data['id']}")
            
            question_results = {
                "question_data": question_data,
                "evaluations": {}
            }
            
            # 传统RAG评估
            traditional_result = self.evaluate_single_question(question_data, "traditional")
            question_results["evaluations"]["traditional"] = traditional_result
            
            # GraphRAG评估（如果可用）
            if GRAPHRAG_AVAILABLE and self.graphrag_engine:
                graphrag_result = self.evaluate_single_question(question_data, "graphrag")
                question_results["evaluations"]["graphrag"] = graphrag_result
                
                # 对比分析
                comparison = self._compare_results(traditional_result, graphrag_result)
                question_results["comparison"] = comparison
            
            results["results"].append(question_results)
            
            # 短暂延迟避免过载
            time.sleep(1)
        
        results["experiment_info"]["end_time"] = datetime.now().isoformat()
        results["summary"] = self._generate_summary(results)
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"comparison_experiment_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logging.info(f"实验结果已保存: {results_file}")
        return results
    
    def _compare_results(self, traditional: Dict, graphrag: Dict) -> Dict:
        """对比两种方法的结果"""
        comparison = {}
        
        # 处理时间对比
        if "processing_time" in traditional and "processing_time" in graphrag:
            comparison["time_difference"] = graphrag["processing_time"] - traditional["processing_time"]
            comparison["graphrag_faster"] = comparison["time_difference"] < 0
        
        # 答案长度对比
        if "answer_length" in traditional and "answer_length" in graphrag:
            comparison["length_difference"] = graphrag["answer_length"] - traditional["answer_length"]
            comparison["graphrag_more_detailed"] = comparison["length_difference"] > 0
        
        # 实体数量对比
        if "entities_count" in traditional and "entities_count" in graphrag:
            comparison["entities_difference"] = graphrag["entities_count"] - traditional["entities_count"]
            comparison["graphrag_more_entities"] = comparison["entities_difference"] > 0
        
        # 可信度信息
        comparison["graphrag_has_confidence"] = "confidence" in graphrag and graphrag["confidence"] is not None
        if comparison["graphrag_has_confidence"]:
            comparison["confidence_score"] = graphrag["confidence"]
            comparison["high_confidence"] = graphrag["confidence"] >= 0.7
        
        # 警告信息
        comparison["graphrag_has_warnings"] = graphrag.get("warnings_count", 0) > 0
        
        return comparison
    
    def _generate_summary(self, results: Dict) -> Dict:
        """生成实验摘要"""
        summary = {
            "total_questions": len(results["results"]),
            "methods_evaluated": [],
            "average_metrics": {}
        }
        
        # 收集所有评估结果
        traditional_results = []
        graphrag_results = []
        
        for result in results["results"]:
            if "traditional" in result["evaluations"]:
                eval_result = result["evaluations"]["traditional"]
                if "error" not in eval_result:
                    traditional_results.append(eval_result)
                    summary["methods_evaluated"].append("traditional")
            
            if "graphrag" in result["evaluations"]:
                eval_result = result["evaluations"]["graphrag"]
                if "error" not in eval_result:
                    graphrag_results.append(eval_result)
                    summary["methods_evaluated"].append("graphrag")
        
        summary["methods_evaluated"] = list(set(summary["methods_evaluated"]))
        
        # 计算平均指标
        if traditional_results:
            summary["average_metrics"]["traditional"] = self._calculate_average_metrics(traditional_results)
        
        if graphrag_results:
            summary["average_metrics"]["graphrag"] = self._calculate_average_metrics(graphrag_results)
        
        # 对比摘要
        if traditional_results and graphrag_results:
            summary["comparison_summary"] = self._generate_comparison_summary(results)
        
        return summary
    
    def _calculate_average_metrics(self, results: List[Dict]) -> Dict:
        """计算平均指标"""
        metrics = {}
        
        # 处理时间
        times = [r["processing_time"] for r in results if "processing_time" in r]
        if times:
            metrics["avg_processing_time"] = round(statistics.mean(times), 3)
            metrics["max_processing_time"] = round(max(times), 3)
            metrics["min_processing_time"] = round(min(times), 3)
        
        # 答案长度
        lengths = [r["answer_length"] for r in results if "answer_length" in r]
        if lengths:
            metrics["avg_answer_length"] = round(statistics.mean(lengths), 1)
        
        # 实体数量
        entity_counts = [r["entities_count"] for r in results if "entities_count" in r]
        if entity_counts:
            metrics["avg_entities_count"] = round(statistics.mean(entity_counts), 1)
        
        # 可信度（仅GraphRAG）
        confidences = [r["confidence"] for r in results if "confidence" in r and r["confidence"] is not None]
        if confidences:
            metrics["avg_confidence"] = round(statistics.mean(confidences), 3)
            metrics["high_confidence_ratio"] = round(sum(1 for c in confidences if c >= 0.7) / len(confidences), 3)
        
        # 实体匹配（如果有）
        entity_recalls = [r["entity_recall"] for r in results if "entity_recall" in r]
        if entity_recalls:
            metrics["avg_entity_recall"] = round(statistics.mean(entity_recalls), 3)
        
        return metrics
    
    def _generate_comparison_summary(self, results: Dict) -> Dict:
        """生成对比摘要"""
        comparisons = [r["comparison"] for r in results["results"] if "comparison" in r]
        
        if not comparisons:
            return {}
        
        summary = {}
        
        # 时间对比
        faster_count = sum(1 for c in comparisons if c.get("graphrag_faster", False))
        summary["graphrag_faster_ratio"] = round(faster_count / len(comparisons), 3)
        
        # 详细程度对比
        detailed_count = sum(1 for c in comparisons if c.get("graphrag_more_detailed", False))
        summary["graphrag_more_detailed_ratio"] = round(detailed_count / len(comparisons), 3)
        
        # 实体提取对比
        more_entities_count = sum(1 for c in comparisons if c.get("graphrag_more_entities", False))
        summary["graphrag_more_entities_ratio"] = round(more_entities_count / len(comparisons), 3)
        
        # 高可信度比例
        high_confidence_count = sum(1 for c in comparisons if c.get("high_confidence", False))
        summary["high_confidence_ratio"] = round(high_confidence_count / len(comparisons), 3)
        
        # 有警告的比例
        warnings_count = sum(1 for c in comparisons if c.get("graphrag_has_warnings", False))
        summary["warnings_ratio"] = round(warnings_count / len(comparisons), 3)
        
        return summary
    
    def generate_report(self, results: Dict) -> str:
        """生成实验报告"""
        report = []
        report.append("# GraphRAG实验评估报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 实验概况
        info = results["experiment_info"]
        report.append("## 实验概况")
        report.append(f"- 测试问题数量: {info['questions_count']}")
        report.append(f"- 评估方法: {', '.join(info['methods'])}")
        report.append(f"- 开始时间: {info['start_time']}")
        report.append(f"- 结束时间: {info['end_time']}")
        report.append("")
        
        # 摘要统计
        summary = results["summary"]
        report.append("## 性能摘要")
        
        if "traditional" in summary["average_metrics"]:
            trad_metrics = summary["average_metrics"]["traditional"]
            report.append("### 传统RAG")
            report.append(f"- 平均处理时间: {trad_metrics.get('avg_processing_time', 'N/A')}秒")
            report.append(f"- 平均答案长度: {trad_metrics.get('avg_answer_length', 'N/A')}字符")
            report.append(f"- 平均实体数量: {trad_metrics.get('avg_entities_count', 'N/A')}")
            report.append("")
        
        if "graphrag" in summary["average_metrics"]:
            graph_metrics = summary["average_metrics"]["graphrag"]
            report.append("### GraphRAG")
            report.append(f"- 平均处理时间: {graph_metrics.get('avg_processing_time', 'N/A')}秒")
            report.append(f"- 平均答案长度: {graph_metrics.get('avg_answer_length', 'N/A')}字符")
            report.append(f"- 平均实体数量: {graph_metrics.get('avg_entities_count', 'N/A')}")
            report.append(f"- 平均可信度: {graph_metrics.get('avg_confidence', 'N/A')}")
            report.append(f"- 高可信度比例: {graph_metrics.get('high_confidence_ratio', 'N/A')}")
            report.append("")
        
        # 对比分析
        if "comparison_summary" in summary:
            comp = summary["comparison_summary"]
            report.append("## 对比分析")
            report.append(f"- GraphRAG更快的比例: {comp.get('graphrag_faster_ratio', 'N/A')}")
            report.append(f"- GraphRAG更详细的比例: {comp.get('graphrag_more_detailed_ratio', 'N/A')}")
            report.append(f"- GraphRAG提取更多实体的比例: {comp.get('graphrag_more_entities_ratio', 'N/A')}")
            report.append(f"- 高可信度答案比例: {comp.get('high_confidence_ratio', 'N/A')}")
            report.append(f"- 产生警告的比例: {comp.get('warnings_ratio', 'N/A')}")
            report.append("")
        
        # 详细结果
        report.append("## 详细结果")
        for i, result in enumerate(results["results"], 1):
            question_data = result["question_data"]
            report.append(f"### 问题 {i}: {question_data['question']}")
            report.append(f"类别: {question_data['category']}")
            
            for method, evaluation in result["evaluations"].items():
                if "error" in evaluation:
                    report.append(f"**{method.upper()}**: 评估失败 - {evaluation['error']}")
                else:
                    report.append(f"**{method.upper()}**:")
                    report.append(f"- 处理时间: {evaluation.get('processing_time', 'N/A')}秒")
                    report.append(f"- 答案长度: {evaluation.get('answer_length', 'N/A')}字符")
                    if method == "graphrag":
                        report.append(f"- 可信度: {evaluation.get('confidence', 'N/A')}")
                        if evaluation.get('warnings'):
                            report.append(f"- 警告: {', '.join(evaluation['warnings'])}")
            
            report.append("")
        
        return "\n".join(report)
    
    def close(self):
        """关闭资源"""
        try:
            if self.graphrag_engine:
                self.graphrag_engine.close()
        except Exception as e:
            logging.error(f"关闭GraphRAG引擎失败: {e}")


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("GraphRAG实验评估系统")
    print("=" * 40)
    
    evaluator = ExperimentEvaluator()
    
    try:
        # 运行对比实验
        print("开始运行对比实验...")
        results = evaluator.run_comparison_experiment()
        
        # 生成报告
        print("生成实验报告...")
        report = evaluator.generate_report(results)
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = evaluator.results_dir / f"experiment_report_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"实验报告已保存: {report_file}")
        print("\n" + "="*40)
        print("实验摘要:")
        print(report.split("## 详细结果")[0])
        
    except Exception as e:
        logging.error(f"实验执行失败: {e}")
        print(f"实验失败: {e}")
        
    finally:
        evaluator.close()


if __name__ == "__main__":
    main()