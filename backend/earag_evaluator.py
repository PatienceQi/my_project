"""
EARAG-Eval多维度评估算法
Entity-Aware Multi-Dimensional Evaluation Algorithm

专为政策法规RAG问答系统设计的多维度评估算法，通过6个核心维度量化评估RAG生成答案的质量。
算法强调实体覆盖率在政策问答场景中的重要性，支持实时集成，响应时间控制在5秒以内。
"""

import os
import json
import logging
import time
import re
from typing import Dict, List, Set, Optional, Tuple
import numpy as np
import requests
from dotenv import load_dotenv

# 导入系统依赖
from backend.ollama_error_handler import OllamaClientWithFallback

# 加载环境变量
load_dotenv()

class EARAGEvaluator:
    """EARAG-Eval多维度评估器
    
    核心特性:
    - 实体感知评估：基于政策实体的覆盖度和准确性
    - 多维度量化：6个独立维度全面评估答案质量
    - 并行计算优化：支持独立并行的维度计算
    - 自适应阈值：针对政策领域特点调整评估标准
    - 诊断报告生成：提供详细质量分析和改进建议
    """
    
    def __init__(self):
        """初始化EARAG-Eval评估器"""
        # 配置参数
        self.ollama_host = os.getenv('LLM_BINDING_HOST', 'http://120.232.79.82:11434')
        self.model_name = os.getenv('LLM_MODEL', 'llama3.2:latest')
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'bge-m3:latest')
        
        # 政策领域权重配置（根据政策问答特点调优）
        self.weights = {
            "entity_coverage": 0.30,      # 实体覆盖率权重最高（政策实体重要）
            "faithfulness": 0.25,         # 事实忠实度权重
            "relevancy": 0.15,           # 答案相关性权重
            "sufficiency": 0.15,         # 上下文充分性权重
            "hallucination": -0.15       # 幻觉率权重（负权重，惩罚幻觉）
        }
        
        # 自适应阈值（针对政策领域特点）
        self.thresholds = {
            "entity_coverage": 0.8,       # 政策实体覆盖要求高
            "faithfulness": 0.7,          # 事实准确性要求
            "relevancy": 0.7,            # 相关性基本要求
            "sufficiency": 0.8,          # 上下文完整性要求高
            "hallucination": 0.2,        # 幻觉率容忍度低
            "overall": 0.7               # 整体质量及格线
        }
        
        # 性能配置
        self.timeout_seconds = 5          # 总评估时间限制
        self.max_text_length = 1000       # 文本截断长度
        self.parallel_workers = 4         # 并行工作线程数
        
        # 初始化组件
        self.ollama_client = OllamaClientWithFallback()
        
        # 实体类型配置（政策领域特定）
        self.policy_entity_types = {
            "政策名称", "机构组织", "地理位置", 
            "法律条款", "行业领域", "人员角色",
            "时间信息", "数值金额", "业务术语"
        }
        
        logging.info("EARAG-Eval多维度评估器初始化完成")
    
    def evaluate(self, question: str, answer: str, context: List[str], 
                graph_entities: Set[str]) -> Dict:
        """
        执行多维度评估算法
        
        Args:
            question: 用户问题字符串
            answer: RAG系统生成的答案
            context: 检索上下文列表
            graph_entities: Neo4j图谱预提取实体集
            
        Returns:
            包含所有维度评分和诊断信息的结果字典
        """
        start_time = time.time()
        
        try:
            logging.info("开始执行EARAG-Eval多维度评估")
            
            # 预处理阶段：并行实体提取
            entities_info = self._extract_entities_parallel(question, answer, context)
            
            if time.time() - start_time > self.timeout_seconds:
                return self._timeout_fallback("实体提取超时")
            
            # 评估阶段：计算6个维度
            dimension_results = self._calculate_all_dimensions(
                question, answer, context, graph_entities, entities_info
            )
            
            # 构建最终结果
            result = {
                "overall_score": dimension_results["overall"]["score"],
                "quality_level": dimension_results["overall"]["quality_level"],
                "dimension_scores": {
                    dim: result["score"] for dim, result in dimension_results.items() 
                    if dim != "overall"
                },
                "diagnosis": self._generate_comprehensive_diagnosis(dimension_results),
                "entity_analysis": {
                    "question_entities": entities_info["question_entities"],
                    "answer_entities": entities_info["answer_entities"],
                    "context_entities": entities_info["context_entities"],
                    "missing_entities": list(set(entities_info["question_entities"]) - 
                                           set(entities_info["answer_entities"])),
                    "unverified_entities": list(set(entities_info["answer_entities"]) - 
                                               graph_entities)
                },
                "detailed_analysis": {
                    dim: {"score": result["score"], "diagnosis": result["diagnosis"]}
                    for dim, result in dimension_results.items()
                },
                "processing_time": round(time.time() - start_time, 2),
                "algorithm_version": "EARAG-Eval-1.0"
            }
            
            logging.info(f"EARAG-Eval评估完成，整体评分: {result['overall_score']:.3f}")
            return result
            
        except Exception as e:
            logging.error(f"EARAG-Eval评估失败: {e}")
            return self._error_fallback(str(e))
    
    def _extract_entities_parallel(self, question: str, answer: str, 
                                 context: List[str]) -> Dict:
        """并行提取问题、答案和上下文中的实体"""
        # 简化版本：串行提取（可后续优化为并行）
        context_text = "\n".join(context[:3]) if context else ""
        
        question_entities = self._extract_entities(question, "问题")
        answer_entities = self._extract_entities(answer, "答案") 
        context_entities = self._extract_entities(context_text, "上下文")
        
        return {
            "question_entities": question_entities,
            "answer_entities": answer_entities, 
            "context_entities": context_entities
        }
    
    def _extract_entities(self, text: str, role: str) -> List[str]:
        """使用Ollama提取关键实体"""
        if not text or len(text.strip()) < 5:
            return [] if role != "问题" else ["generic_query"]
        
        # 截断过长文本
        text = text[:self.max_text_length] if len(text) > self.max_text_length else text
        
        prompt = f"""
从以下{role}文本中提取关键政策实体：
文本: {text}

实体类型：政策名称、机构组织、地理位置、法律条款、行业领域、人员角色、时间信息、数值金额、业务术语

输出格式：["实体1", "实体2", "实体3"]
只输出JSON数组，无其他内容。
"""
        
        try:
            response = self.ollama_client.call_api('generate', {
                'model': self.model_name,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.2}
            })
            # 解析JSON响应
            response_text = response.get('response', '').strip()
            cleaned_response = response_text
            
            # 尝试提取JSON数组
            if cleaned_response.startswith('[') and cleaned_response.endswith(']'):
                entities = json.loads(cleaned_response)
            else:
                # 尝试从响应中提取JSON数组
                json_match = re.search(r'\[.*?\]', cleaned_response, re.DOTALL)
                if json_match:
                    entities = json.loads(json_match.group())
                else:
                    entities = []
            
            # 过滤和清理实体
            filtered_entities = []
            for entity in entities:
                if isinstance(entity, str) and len(entity.strip()) > 1:
                    filtered_entities.append(entity.strip())
            
            return filtered_entities[:20]  # 限制实体数量
            
        except Exception as e:
            logging.warning(f"{role}实体提取失败: {e}")
            return [] if role != "问题" else ["generic_query"]
    
    def _calculate_all_dimensions(self, question: str, answer: str, context: List[str],
                                graph_entities: Set[str], entities_info: Dict) -> Dict:
        """计算所有6个维度的评分"""
        results = {}
        
        q_entities = set(entities_info["question_entities"])
        a_entities = set(entities_info["answer_entities"])
        c_entities = set(entities_info["context_entities"])
        
        # 维度1：实体覆盖率
        results["entity_coverage"] = self._calculate_entity_coverage(q_entities, a_entities)
        
        # 维度2：事实忠实度
        results["faithfulness"] = self._calculate_faithfulness(
            answer, context, a_entities, graph_entities
        )
        
        # 维度3：答案相关性
        results["relevancy"] = self._calculate_relevancy(question, answer)
        
        # 维度4：上下文充分性
        results["sufficiency"] = self._calculate_sufficiency(q_entities, c_entities)
        
        # 维度5：幻觉率
        results["hallucination"] = self._calculate_hallucination(
            results["faithfulness"]["score"], 
            results["faithfulness"].get("unmatched_ratio", 0)
        )
        
        # 维度6：整体评分
        dimension_scores = {
            "entity_coverage": results["entity_coverage"]["score"],
            "faithfulness": results["faithfulness"]["score"],
            "relevancy": results["relevancy"]["score"],
            "sufficiency": results["sufficiency"]["score"],
            "hallucination": results["hallucination"]["score"]
        }
        
        results["overall"] = self._calculate_overall_score(dimension_scores)
        
        return results
    
    def _calculate_entity_coverage(self, q_entities: Set[str], a_entities: Set[str]) -> Dict:
        """维度1：计算实体覆盖率"""
        if not q_entities:
            return {"score": 1.0, "diagnosis": [], "covered_entities": [], "missing_entities": []}
        
        covered = q_entities.intersection(a_entities)
        missing = q_entities - a_entities
        score = len(covered) / len(q_entities)
        
        diagnosis = []
        if score < self.thresholds["entity_coverage"]:
            diagnosis.append(f"实体覆盖不足，遗漏关键实体: {list(missing)}")
            diagnosis.append("建议：补充答案中缺失的政策实体信息")
        
        return {
            "score": score,
            "covered_entities": list(covered),
            "missing_entities": list(missing),
            "diagnosis": diagnosis
        }
    
    def _calculate_faithfulness(self, answer: str, context: List[str], 
                               a_entities: Set[str], graph_entities: Set[str]) -> Dict:
        """维度2：计算事实忠实度（双重验证机制）"""
        # 1. LLM自评估
        context_text = "\n".join(context[:3]) if context else ""
        llm_score = self._llm_faithfulness_assessment(answer, context_text)
        
        # 2. 知识图谱验证
        unmatched_entities = a_entities - graph_entities
        unmatched_ratio = len(unmatched_entities) / len(a_entities) if a_entities else 0
        
        # 3. 综合评分
        final_score = max(0, llm_score - 0.1 * unmatched_ratio)
        
        diagnosis = []
        if unmatched_ratio > 0.2:
            diagnosis.append(f"包含未验证实体: {list(unmatched_entities)}")
        if final_score < self.thresholds["faithfulness"]:
            diagnosis.append("事实忠实度较低，可能存在错误信息")
        
        return {
            "score": final_score,
            "llm_score": llm_score,
            "unmatched_ratio": unmatched_ratio,
            "unmatched_entities": list(unmatched_entities),
            "diagnosis": diagnosis
        }
    
    def _llm_faithfulness_assessment(self, answer: str, context: str) -> float:
        """使用LLM评估答案对上下文的忠实度"""
        if not context.strip():
            return 0.5
        
        prompt = f"""
评估答案对上下文的事实忠实度，0-1评分（0完全不符，1完全符合）：

上下文: {context[:500]}

答案: {answer[:500]}

评估标准：
- 答案内容是否基于上下文
- 是否存在与上下文矛盾的信息
- 是否添加了上下文中没有的事实

只输出0到1之间的数字分数，例如：0.8
"""
        
        try:
            response = self.ollama_client.call_api('generate', {
                'model': self.model_name,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.2}
            })
            response_text = response.get('response', '').strip()
            # 提取数字评分
            score_match = re.search(r'([0-1]\.?\d*)', response_text)
            if score_match:
                score = float(score_match.group(1))
                return max(0, min(1, score))
            else:
                return 0.5
        except Exception as e:
            logging.warning(f"LLM忠实度评估失败: {e}")
            return 0.5
    
    def _calculate_relevancy(self, question: str, answer: str) -> Dict:
        """维度3：计算答案相关性（使用嵌入相似度）"""
        try:
            # 获取问题和答案的嵌入向量
            q_embedding = self._get_embedding(question)
            a_embedding = self._get_embedding(answer)
            
            if q_embedding is None or a_embedding is None:
                return {"score": 0.5, "diagnosis": ["无法计算语义相似度"]}
            
            # 计算余弦相似度
            similarity = np.dot(q_embedding, a_embedding) / (
                np.linalg.norm(q_embedding) * np.linalg.norm(a_embedding)
            )
            similarity = max(0, float(similarity))
            
            diagnosis = []
            if similarity < self.thresholds["relevancy"]:
                diagnosis.append("答案与问题相关性较低")
                diagnosis.append("建议：确保答案直接回应问题核心需求")
            
            return {"score": similarity, "diagnosis": diagnosis}
            
        except Exception as e:
            logging.warning(f"相关性计算失败: {e}")
            return {"score": 0.5, "diagnosis": ["相关性计算失败"]}
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本嵌入向量（使用BGE-M3）"""
        if not text.strip():
            return None
        
        url = f"{self.ollama_host}/api/embed"
        payload = {
            "model": self.embedding_model,
            "input": text.strip()[:self.max_text_length]
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            embeddings = result.get('embeddings')
            
            if embeddings and len(embeddings) > 0:
                return embeddings[0]
            else:
                return None
                
        except Exception as e:
            logging.warning(f"嵌入向量获取失败: {e}")
            return None
    
    def _calculate_sufficiency(self, q_entities: Set[str], c_entities: Set[str]) -> Dict:
        """维度4：计算上下文充分性"""
        if not q_entities:
            return {"score": 1.0, "diagnosis": []}
        
        covered = q_entities.intersection(c_entities)
        uncovered = q_entities - c_entities
        score = len(covered) / len(q_entities)
        
        diagnosis = []
        if score < self.thresholds["sufficiency"]:
            diagnosis.append("上下文覆盖不足，缺少相关信息")
            diagnosis.append(f"建议检索更多关于{list(uncovered)}的信息")
        
        return {"score": score, "diagnosis": diagnosis}
    
    def _calculate_hallucination(self, faithfulness_score: float, unmatched_ratio: float) -> Dict:
        """维度5：计算幻觉率（复合检测）"""
        base_hallucination = 1 - faithfulness_score
        entity_hallucination = 0.5 * unmatched_ratio
        total_hallucination = min(1.0, base_hallucination + entity_hallucination)
        
        diagnosis = []
        if total_hallucination > self.thresholds["hallucination"]:
            diagnosis.append("检测到潜在幻觉内容")
        if total_hallucination > 0.5:
            diagnosis.append("高风险：答案可能包含虚假信息，建议重新生成")
        
        risk_level = "高风险" if total_hallucination > 0.5 else ("中风险" if total_hallucination > 0.2 else "低风险")
        
        return {
            "score": total_hallucination,
            "risk_level": risk_level,
            "base_hallucination": base_hallucination,
            "entity_hallucination": entity_hallucination,
            "diagnosis": diagnosis
        }
    
    def _calculate_overall_score(self, dimension_scores: Dict) -> Dict:
        """维度6：计算整体评分并生成质量等级"""
        # 加权计算整体评分
        overall_score = sum(
            self.weights[dim] * score for dim, score in dimension_scores.items()
        )
        overall_score = max(0, min(1, overall_score))
        
        # 确定质量等级
        if overall_score >= 0.8:
            quality_level = "优秀"
            quality_desc = "答案质量高，可以直接使用"
        elif overall_score >= 0.7:
            quality_level = "良好"  
            quality_desc = "答案质量较好，建议优化后使用"
        elif overall_score >= 0.6:
            quality_level = "一般"
            quality_desc = "答案质量一般，需要改进"
        else:
            quality_level = "较差"
            quality_desc = "答案质量差，建议重新生成"
        
        # 综合诊断
        diagnosis = f"整体评分: {overall_score:.3f} ({quality_level}) - {quality_desc}"
        
        recommendations = []
        if overall_score < self.thresholds["overall"]:
            recommendations.append("建议重新生成答案或优化检索策略")
        
        return {
            "score": overall_score,
            "quality_level": quality_level,
            "quality_description": quality_desc,
            "diagnosis": diagnosis,
            "recommendations": recommendations,
            "weights_used": self.weights.copy()
        }
    
    def _generate_comprehensive_diagnosis(self, dimension_results: Dict) -> str:
        """生成综合诊断报告"""
        diagnosis_parts = []
        
        # 整体质量
        overall = dimension_results["overall"]
        diagnosis_parts.append(overall["diagnosis"])
        
        # 各维度问题汇总
        issues = []
        for dim_name, result in dimension_results.items():
            if dim_name != "overall" and result.get("diagnosis"):
                issues.extend(result["diagnosis"])
        
        if issues:
            diagnosis_parts.append(f"发现问题: {'; '.join(issues[:5])}")  # 限制问题数量
        
        return " | ".join(diagnosis_parts)
    
    def _timeout_fallback(self, reason: str) -> Dict:
        """超时回退结果"""
        return {
            "overall_score": 0.0,
            "quality_level": "超时",
            "dimension_scores": {},
            "diagnosis": f"评估超时: {reason}",
            "entity_analysis": {},
            "detailed_analysis": {},
            "processing_time": self.timeout_seconds,
            "error": "timeout"
        }
    
    def _error_fallback(self, error_msg: str) -> Dict:
        """错误回退结果"""
        return {
            "overall_score": 0.0,
            "quality_level": "错误",
            "dimension_scores": {},
            "diagnosis": f"评估失败: {error_msg}",
            "entity_analysis": {},
            "detailed_analysis": {},
            "processing_time": 0,
            "error": error_msg
        }