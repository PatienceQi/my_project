"""
HotpotQA数据集预处理器

负责从Hugging Face加载HotpotQA数据集，进行数据清洗、格式转换和预处理。
支持从多种数据源加载，包括本地JSON文件和Hugging Face数据集。
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from datasets import load_dataset
    DATASETS_AVAILABLE = True
except ImportError:
    DATASETS_AVAILABLE = False
    logging.warning("datasets库未安装，将仅支持本地JSON文件加载")

class HotpotQAPreprocessor:
    """HotpotQA数据预处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'total_questions': 0,
            'processed_questions': 0,
            'valid_questions': 0,
            'invalid_questions': 0,
            'total_paragraphs': 0,
            'total_supporting_facts': 0
        }
    
    def load_dataset(self, dataset_path: str, data_format: str = "auto") -> List[Dict[str, Any]]:
        """
        加载HotpotQA数据集
        
        Args:
            dataset_path: 数据集路径或Hugging Face数据集名称
            data_format: 数据格式 ("train", "dev", "test", "auto")
            
        Returns:
            处理后的问题数据列表
        """
        self.logger.info(f"开始加载HotpotQA数据集: {dataset_path}")
        
        # 判断是本地文件还是Hugging Face数据集
        if Path(dataset_path).exists():
            data = self._load_from_local(dataset_path)
        elif DATASETS_AVAILABLE:
            data = self._load_from_huggingface(dataset_path, data_format)
        else:
            raise ValueError("无法加载数据集：datasets库未安装且未找到本地文件")
        
        self.stats['total_questions'] = len(data)
        self.logger.info(f"成功加载 {len(data)} 个问题")
        
        return data
    
    def _load_from_local(self, file_path: str) -> List[Dict[str, Any]]:
        """从本地JSON文件加载数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 如果是单个对象，转换为列表
            if isinstance(data, dict):
                data = [data]
            
            self.logger.info(f"从本地文件加载了 {len(data)} 个样本")
            return data
            
        except Exception as e:
            self.logger.error(f"加载本地文件失败: {e}")
            raise
    
    def _load_from_huggingface(self, dataset_name: str, split: str) -> List[Dict[str, Any]]:
        """从Hugging Face加载数据集"""
        try:
            # 自动检测split
            if split == "auto":
                split = "validation"  # HotpotQA通常使用validation作为dev集
            
            dataset = load_dataset(dataset_name, split=split)
            data = [item for item in dataset]
            
            self.logger.info(f"从Hugging Face加载了 {len(data)} 个样本")
            return data
            
        except Exception as e:
            self.logger.error(f"从Hugging Face加载数据集失败: {e}")
            raise
    
    def clean_text(self, text) -> str:
        """
        清洗文本内容 - 增强类型检查
        
        Args:
            text: 原始文本（支持字符串、列表或其他类型）
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ""
        
        # 类型检查和转换
        if isinstance(text, list):
            # 如果是列表，合并为字符串
            text = " ".join(str(item) for item in text if item)
        elif not isinstance(text, str):
            # 如果不是字符串，转换为字符串
            text = str(text)
        
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 标准化空格
        text = re.sub(r'\s+', ' ', text)
        
        # 移除前后空格
        text = text.strip()
        
        # 处理特殊字符
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        return text
    
    def split_contexts(self, contexts: List[List]) -> List[Dict[str, Any]]:
        """
        分割上下文为段落单元 - 修复版本
        支持嵌套列表结构: [["title", ["sentence1", "sentence2", ...]]]
        
        Args:
            contexts: HotpotQA的context字段 [[title, content], ...]
                     content可能是字符串或句子列表
            
        Returns:
            段落字典列表
        """
        paragraphs = []
        
        for i, context in enumerate(contexts):
            if len(context) >= 2:
                # 确保title为字符串
                title = self.clean_text(str(context[0]))
                
                # 处理嵌套列表结构
                content = context[1]
                if isinstance(content, list):
                    # 合并列表中的所有句子
                    text = " ".join(str(sentence).strip() for sentence in content if sentence)
                else:
                    text = str(content)
                    
                text = self.clean_text(text)
                
                # 按句子分割长文本
                sentences = self._split_into_sentences(text)
                
                for j, sentence in enumerate(sentences):
                    if sentence.strip():
                        paragraphs.append({
                            'paragraph_id': f"para_{i}_{j}",
                            'title': title,
                            'text': sentence,
                            'order': j,
                            'source_index': i
                        })
        
        return paragraphs
    
    def _split_into_sentences(self, text: str, max_length: int = 200) -> List[str]:
        """将长文本分割为句子"""
        if len(text) <= max_length:
            return [text]
        
        # 按句号分割
        sentences = re.split(r'[.!?]+', text)
        result = []
        current = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(current + sentence) <= max_length:
                current += sentence + ". "
            else:
                if current:
                    result.append(current.strip())
                current = sentence + ". "
        
        if current:
            result.append(current.strip())
        
        return result if result else [text]
    
    def extract_supporting_facts(self, supporting_facts: List[List]) -> List[Dict[str, Any]]:
        """
        提取支持事实
        
        Args:
            supporting_facts: [[title, sentence_id], ...]
            
        Returns:
            支持事实字典列表
        """
        facts = []
        
        for i, fact in enumerate(supporting_facts):
            if len(fact) >= 2:
                facts.append({
                    'fact_id': f"fact_{i}",
                    'title': self.clean_text(str(fact[0])),
                    'sentence_id': int(fact[1]) if str(fact[1]).isdigit() else 0,
                    'relevance_score': 1.0  # 默认高相关性
                })
        
        return facts
    
    def validate_question_data(self, data: Dict[str, Any]) -> bool:
        """
        验证问题数据的有效性
        
        Args:
            data: 问题数据字典
            
        Returns:
            是否有效
        """
        required_fields = ['question', 'answer', 'context']
        
        # 检查必需字段
        for field in required_fields:
            if field not in data or not data[field]:
                self.logger.warning(f"问题数据缺少必需字段: {field}")
                return False
        
        # 检查问题和答案长度
        if len(data['question'].strip()) < 5:
            self.logger.warning("问题过短")
            return False
            
        if len(data['answer'].strip()) < 1:
            self.logger.warning("答案为空")
            return False
        
        # 检查上下文格式
        if not isinstance(data['context'], list) or len(data['context']) == 0:
            self.logger.warning("上下文格式无效")
            return False
        
        return True
    
    def preprocess_question(self, question_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        预处理单个问题数据 - 增强错误处理版本
        
        Args:
            question_data: 原始问题数据
            
        Returns:
            预处理后的问题数据，失败时返回None
        """
        try:
            # 检查输入是否为空
            if not question_data or not isinstance(question_data, dict):
                self.logger.warning(f"无效的问题数据类型: {type(question_data)}")
                self.stats['invalid_questions'] += 1
                return None
            
            # 验证数据有效性
            if not self.validate_question_data(question_data):
                self.logger.warning(f"问题数据验证失败: {question_data.get('_id', 'unknown')}")
                self.stats['invalid_questions'] += 1
                return None
            
            # 安全的字段提取
            processed = {
                'question_id': question_data.get('_id', f"q_{self.stats['processed_questions']}"),
                'question': self.clean_text(str(question_data.get('question', ''))),
                'answer': self.clean_text(str(question_data.get('answer', ''))),
                'level': question_data.get('level', 'unknown'),
                'type': question_data.get('type', 'unknown')
            }
            
            # 安全的上下文处理
            context_data = question_data.get('context', [])
            if isinstance(context_data, list):
                processed['paragraphs'] = self.split_contexts(context_data)
            else:
                self.logger.warning(f"无效的context格式: {type(context_data)}")
                processed['paragraphs'] = []
            
            self.stats['total_paragraphs'] += len(processed['paragraphs'])
            
            # 安全的支持事实处理
            supporting_facts = question_data.get('supporting_facts', [])
            if isinstance(supporting_facts, list):
                processed['supporting_facts'] = self.extract_supporting_facts(supporting_facts)
            else:
                self.logger.warning(f"无效的supporting_facts格式: {type(supporting_facts)}")
                processed['supporting_facts'] = []
                
            self.stats['total_supporting_facts'] += len(processed['supporting_facts'])
            
            self.stats['processed_questions'] += 1
            self.stats['valid_questions'] += 1
            
            return processed
            
        except Exception as e:
            self.logger.error(f"预处理问题失败 {question_data.get('_id', 'unknown') if question_data else 'None'}: {e}")
            self.stats['invalid_questions'] += 1
            return None
    
    def preprocess_batch(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量预处理问题数据
        
        Args:
            questions: 原始问题数据列表
            
        Returns:
            预处理后的有效问题数据列表
        """
        processed_questions = []
        
        for question_data in questions:
            processed = self.preprocess_question(question_data)
            if processed:
                processed_questions.append(processed)
        
        self.logger.info(f"批量预处理完成: {len(processed_questions)}/{len(questions)} 个问题有效")
        return processed_questions
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return {
            **self.stats,
            'success_rate': self.stats['valid_questions'] / max(self.stats['total_questions'], 1),
            'avg_paragraphs_per_question': self.stats['total_paragraphs'] / max(self.stats['valid_questions'], 1),
            'avg_supporting_facts_per_question': self.stats['total_supporting_facts'] / max(self.stats['valid_questions'], 1)
        }
    
    def export_processed_data(self, processed_data: List[Dict[str, Any]], output_path: str):
        """
        导出预处理后的数据
        
        Args:
            processed_data: 预处理后的数据
            output_path: 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'metadata': {
                        'total_questions': len(processed_data),
                        'processing_stats': self.get_statistics()
                    },
                    'questions': processed_data
                }, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"预处理数据已导出到: {output_path}")
            
        except Exception as e:
            self.logger.error(f"导出预处理数据失败: {e}")
            raise
