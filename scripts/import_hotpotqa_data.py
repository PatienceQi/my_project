#!/usr/bin/env python3
"""
HotpotQA数据集导入脚本

功能：
1. 从Hugging Face、本地文件或远程URL加载HotpotQA数据集
2. 进行数据预处理和清洗
3. 使用Ollama进行实体关系提取
4. 构建Neo4j知识图谱
5. 提供批处理和进度监控

使用方法:
python scripts/import_hotpotqa_data.py <dataset_path> [选项]

示例:
python scripts/import_hotpotqa_data.py database/hotpotqa_dev_subset.json --batch-size 20 --max-questions 100
python scripts/import_hotpotqa_data.py hotpot_qa --format dev --max-questions 200 --rebuild-graph
python scripts/import_hotpotqa_data.py --download-test --max-questions 200 --rebuild-graph
python scripts/import_hotpotqa_data.py database/hotpot_dev_fullwiki_v1.json --max-questions 200  --batch-size 1 --start-index 1 --end-index 1
"""

import argparse
import json
import logging
import sys
import time
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.hotpotqa_processor.preprocessor import HotpotQAPreprocessor
from scripts.hotpotqa_processor.entity_extractor import HotpotQAEntityExtractor
from scripts.hotpotqa_processor.graph_builder import HotpotQAGraphBuilder

# HotpotQA数据集URL配置
HOTPOTQA_URLS = {
    'test_fullwiki': 'http://curtis.ml.cmu.edu/datasets/hotpot/hotpot_test_fullwiki_v1.json',
    'dev_fullwiki': 'http://curtis.ml.cmu.edu/datasets/hotpot/hotpot_dev_fullwiki_v1.json',
    'train': 'http://curtis.ml.cmu.edu/datasets/hotpot/hotpot_train_v1.1.json'
}

class DataRangeValidator:
    """数据范围参数验证器"""
    
    @staticmethod
    def validate_range_params(
        start_index: int = None,
        end_index: int = None, 
        skip_count: int = None,
        import_count: int = None,
        dataset_size: int = None
    ) -> Dict[str, Any]:
        """
        验证范围参数的有效性和一致性
        
        Args:
            start_index: 起始索引 (1-based)
            end_index: 结束索引 (1-based)
            skip_count: 跳过数量
            import_count: 导入数量
            dataset_size: 数据集总大小
            
        Returns:
            {
                'is_valid': bool,
                'error_message': str,
                'computed_start': int,
                'computed_end': int
            }
        """
        result = {
            'is_valid': False,
            'error_message': '',
            'computed_start': None,
            'computed_end': None
        }
        
        # 参数冲突检查
        if start_index is not None and skip_count is not None:
            result['error_message'] = "不能同时使用 --start-index 和 --skip-count 参数"
            return result
        
        # 基本参数验证
        if start_index is not None and start_index < 1:
            result['error_message'] = "起始索引必须大于等于1"
            return result
            
        if end_index is not None and end_index < 1:
            result['error_message'] = "结束索引必须大于等于1"
            return result
            
        if skip_count is not None and skip_count < 0:
            result['error_message'] = "跳过数量不能为负数"
            return result
            
        if import_count is not None and import_count < 1:
            result['error_message'] = "导入数量必须大于0"
            return result
        
        # 计算实际的起始和结束索引
        computed_start = None
        computed_end = None
        
        # 模式1: 精确范围 (start_index + end_index)
        if start_index is not None and end_index is not None:
            if end_index < start_index:
                result['error_message'] = "结束索引必须大于等于起始索引"
                return result
            computed_start = start_index
            computed_end = end_index
            
        # 模式2: 起始位置 + 导入数量 (start_index + import_count)
        elif start_index is not None and import_count is not None:
            computed_start = start_index
            computed_end = start_index + import_count - 1
            
        # 模式3: 跳过模式 (skip_count + import_count)
        elif skip_count is not None and import_count is not None:
            computed_start = skip_count + 1
            computed_end = skip_count + import_count
            
        # 模式4: 仅起始位置 (start_index, 导入到末尾)
        elif start_index is not None:
            computed_start = start_index
            computed_end = dataset_size if dataset_size else None
            
        # 模式5: 仅跳过数量 (skip_count, 导入剩余)
        elif skip_count is not None:
            computed_start = skip_count + 1
            computed_end = dataset_size if dataset_size else None
            
        # 数据集大小验证
        if dataset_size is not None:
            if computed_start and computed_start > dataset_size:
                result['error_message'] = f"起始索引({computed_start})超出数据集大小({dataset_size})"
                return result
                
            if computed_end and computed_end > dataset_size:
                result['error_message'] = f"结束索引({computed_end})超出数据集大小({dataset_size})"
                return result
        
        # 如果没有设置任何范围参数，表示导入全部
        if computed_start is None and computed_end is None:
            computed_start = 1
            computed_end = dataset_size if dataset_size else None
        
        result['is_valid'] = True
        result['computed_start'] = computed_start
        result['computed_end'] = computed_end
        
        return result
    
    @staticmethod
    def provide_user_friendly_error_messages(validation_result: Dict) -> str:
        """提供用户友好的错误提示"""
        return validation_result.get('error_message', '未知错误')

class DataSliceProcessor:
    """数据切片处理器"""
    
    @staticmethod
    def slice_dataset(
        data: List[Dict], 
        start_index: int,
        end_index: int
    ) -> tuple[List[Dict], Dict[str, Any]]:
        """
        根据指定范围切片数据集
        
        Args:
            data: 原始数据集
            start_index: 起始索引 (1-based)
            end_index: 结束索引 (1-based)
            
        Returns:
            (sliced_data, slice_info)
        """
        original_size = len(data)
        
        # 转换为0-based索引
        start_idx = start_index - 1 if start_index else 0
        end_idx = end_index if end_index else original_size
        
        # 边界检查
        start_idx = max(0, start_idx)
        end_idx = min(original_size, end_idx)
        
        # 切片数据
        sliced_data = data[start_idx:end_idx]
        
        # 生成切片信息
        slice_info = {
            'original_dataset_size': original_size,
            'requested_start_index': start_index,
            'requested_end_index': end_index,
            'actual_start_index': start_idx + 1,  # 转回1-based显示
            'actual_end_index': min(end_idx, original_size),
            'filtered_dataset_size': len(sliced_data),
            'range_description': f"第{start_index}-{min(end_index, original_size)}条" if start_index and end_index else f"从第{start_index}条开始" if start_index else "全部数据"
        }
        
        return sliced_data, slice_info

class HotpotQADownloader:
    """HotpotQA数据集下载器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HotpotQA-Downloader/1.0'
        })
    
    def download_dataset(self, url: str, output_path: str, max_samples: int = None) -> str:
        """
        下载HotpotQA数据集
        
        Args:
            url: 数据集URL
            output_path: 输出文件路径
            max_samples: 最大样本数限制
            
        Returns:
            下载的文件路径
        """
        self.logger.info(f"开始下载HotpotQA数据集: {url}")
        
        try:
            # 创建输出目录
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 下载数据
            response = self.session.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            self.logger.info(f"数据集大小: {total_size / (1024*1024):.1f} MB")
            
            # 流式下载并解析JSON
            self.logger.info("下载并解析数据...")
            content = response.content.decode('utf-8')
            data = json.loads(content)
            
            self.logger.info(f"原始数据集包含 {len(data)} 个样本")
            
            # 限制样本数量
            if max_samples and len(data) > max_samples:
                data = data[:max_samples]
                self.logger.info(f"限制为前 {max_samples} 个样本")
            
            # 保存处理后的数据
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"数据集已保存到: {output_path}")
            self.logger.info(f"实际保存样本数: {len(data)}")
            
            return str(output_path)
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"下载失败: {e}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            raise
        except Exception as e:
            self.logger.error(f"下载数据集时出现错误: {e}")
            raise
    
    def get_cached_dataset_path(self, dataset_type: str, max_samples: int = None) -> str:
        """获取缓存数据集路径"""
        cache_dir = Path('database/cache')
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        if max_samples:
            filename = f"hotpotqa_{dataset_type}_{max_samples}samples.json"
        else:
            filename = f"hotpotqa_{dataset_type}_full.json"
        
        return str(cache_dir / filename)
    
    def download_if_needed(self, dataset_type: str, max_samples: int = None, force_download: bool = False) -> str:
        """
        按需下载数据集
        
        Args:
            dataset_type: 数据集类型 ('test_fullwiki', 'dev_fullwiki', 'train')
            max_samples: 最大样本数
            force_download: 是否强制重新下载
            
        Returns:
            数据集文件路径
        """
        if dataset_type not in HOTPOTQA_URLS:
            raise ValueError(f"不支持的数据集类型: {dataset_type}. 支持的类型: {list(HOTPOTQA_URLS.keys())}")
        
        cache_path = self.get_cached_dataset_path(dataset_type, max_samples)
        
        # 检查缓存
        if Path(cache_path).exists() and not force_download:
            self.logger.info(f"使用缓存的数据集: {cache_path}")
            return cache_path
        
        # 下载数据集
        url = HOTPOTQA_URLS[dataset_type]
        return self.download_dataset(url, cache_path, max_samples)

class HotpotQAImporter:
    """HotpotQA数据导入器"""
    
    def __init__(self, batch_size: int = 50, max_questions: int = None, range_info: Dict[str, Any] = None):
        self.batch_size = batch_size
        self.max_questions = max_questions
        self.range_info = range_info or {}
        
        # 配置日志
        self.logger = self._setup_logging()
        
        # 初始化下载器
        self.downloader = HotpotQADownloader()
        
        # 初始化组件
        self.preprocessor = HotpotQAPreprocessor()
        self.entity_extractor = HotpotQAEntityExtractor()
        self.graph_builder = HotpotQAGraphBuilder()
        
        # 导入统计
        self.import_stats = {
            'start_time': None,
            'end_time': None,
            'total_questions_loaded': 0,
            'total_questions_processed': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'total_batches': 0,
            'avg_batch_time': 0.0
        }
        
        self.logger.info(f"HotpotQA导入器初始化完成 - 批次大小: {batch_size}")
        if self.range_info:
            self.logger.info(f"范围导入模式: {self.range_info.get('range_description', '未指定')}")
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('hotpotqa_import.log', encoding='utf-8')
            ]
        )
        return logging.getLogger(__name__)
    
    def import_filtered_dataset(
        self, 
        filtered_data: List[Dict[str, Any]], 
        slice_info: Dict[str, Any],
        rebuild_graph: bool = False
    ) -> Dict[str, Any]:
        """
        导入过滤后的数据集
        
        Args:
            filtered_data: 过滤后的数据集
            slice_info: 切片信息
            rebuild_graph: 是否重建图谱
            
        Returns:
            导入统计信息
        """
        self.import_stats['start_time'] = time.time()
        self.range_info = slice_info
        
        try:
            self.logger.info(f"开始导入HotpotQA数据集 - {slice_info['range_description']}")
            self.logger.info(f"原始数据集: {slice_info['original_dataset_size']} 个样本")
            self.logger.info(f"过滤后数据集: {slice_info['filtered_dataset_size']} 个样本")
            
            # 1. 清除现有数据（如果需要）
            if rebuild_graph:
                self.logger.info("清除现有HotpotQA数据...")
                self.graph_builder.clear_hotpotqa_data(confirm=True)
            
            # 2. 设置统计信息
            self.import_stats['total_questions_loaded'] = len(filtered_data)
            
            # 3. 批处理导入
            self._process_in_batches(filtered_data)
            
            # 4. 优化图结构
            self.logger.info("优化图结构...")
            optimization_results = self.graph_builder.optimize_graph_structure()
            
            # 5. 生成最终统计
            final_stats = self._generate_final_statistics(optimization_results)
            
            self.import_stats['end_time'] = time.time()
            total_time = self.import_stats['end_time'] - self.import_stats['start_time']
            
            self.logger.info(f"HotpotQA数据集导入完成，总用时: {total_time:.2f}s")
            self.logger.info(f"成功导入: {self.import_stats['successful_imports']}/{self.import_stats['total_questions_processed']} 个问题")
            
            return final_stats
            
        except Exception as e:
            self.logger.error(f"导入数据集失败: {e}")
            raise
        finally:
            # 清理资源
            self.graph_builder.close()
    
    def import_dataset(
        self, 
        dataset_path: str, 
        data_format: str = "auto",
        rebuild_graph: bool = False
    ) -> Dict[str, Any]:
        """
        导入HotpotQA数据集 (保持向后兼容)
        
        Args:
            dataset_path: 数据集路径
            data_format: 数据格式
            rebuild_graph: 是否重建图谱
            
        Returns:
            导入统计信息
        """
        self.import_stats['start_time'] = time.time()
        
        try:
            self.logger.info(f"开始导入HotpotQA数据集: {dataset_path}")
            
            # 1. 清除现有数据（如果需要）
            if rebuild_graph:
                self.logger.info("清除现有HotpotQA数据...")
                self.graph_builder.clear_hotpotqa_data(confirm=True)
            
            # 2. 加载数据集
            self.logger.info("加载数据集...")
            raw_questions = self.preprocessor.load_dataset(dataset_path, data_format)
            
            # 限制处理数量
            if self.max_questions and len(raw_questions) > self.max_questions:
                raw_questions = raw_questions[:self.max_questions]
                self.logger.info(f"限制处理数量为: {self.max_questions}")
            
            self.import_stats['total_questions_loaded'] = len(raw_questions)
            
            # 3. 批处理导入
            self._process_in_batches(raw_questions)
            
            # 4. 优化图结构
            self.logger.info("优化图结构...")
            optimization_results = self.graph_builder.optimize_graph_structure()
            
            # 5. 生成最终统计
            final_stats = self._generate_final_statistics(optimization_results)
            
            self.import_stats['end_time'] = time.time()
            total_time = self.import_stats['end_time'] - self.import_stats['start_time']
            
            self.logger.info(f"HotpotQA数据集导入完成，总用时: {total_time:.2f}s")
            self.logger.info(f"成功导入: {self.import_stats['successful_imports']}/{self.import_stats['total_questions_processed']} 个问题")
            
            return final_stats
            
        except Exception as e:
            self.logger.error(f"导入数据集失败: {e}")
            raise
        finally:
            # 清理资源
            self.graph_builder.close()
    
    def _process_in_batches(self, raw_questions: List[Dict[str, Any]]):
        """批量处理问题 - 增强异常处理"""
        total_questions = len(raw_questions)
        self.import_stats['total_batches'] = (total_questions + self.batch_size - 1) // self.batch_size
        
        for batch_idx in range(0, total_questions, self.batch_size):
            batch_start_time = time.time()
            batch_questions = raw_questions[batch_idx:batch_idx + self.batch_size]
            current_batch = batch_idx // self.batch_size + 1
            
            self.logger.info(f"处理批次 {current_batch}/{self.import_stats['total_batches']} "
                           f"({len(batch_questions)} 个问题)")
            
            try:
                # 预处理批次
                processed_questions = self.preprocessor.preprocess_batch(batch_questions)
                
                # 处理每个问题
                batch_success_count = 0
                for question_data in processed_questions:
                    if question_data:  # 检查预处理是否成功
                        success = self._process_single_question(question_data)
                        if success:
                            batch_success_count += 1
                
                # 更新批次统计
                batch_time = time.time() - batch_start_time
                self._update_batch_stats(batch_time)
                
                self.logger.info(f"批次 {current_batch} 完成，用时: {batch_time:.2f}s, "
                              f"成功: {batch_success_count}/{len(processed_questions)}")
                
                # 显示进度
                self._show_progress(current_batch, self.import_stats['total_batches'])
                
            except Exception as e:
                self.logger.error(f"批次 {current_batch} 处理失败: {e}")
                # 继续处理下一个批次，而不是停止整个导入
                continue
    
    def _process_single_question(self, question_data: Dict[str, Any]) -> bool:
        """处理单个问题 - 增强错误处理"""
        if not question_data:  # 检查是否为None
            self.import_stats['failed_imports'] += 1
            return False
            
        question_id = question_data.get('question_id', 'unknown')
        
        try:
            self.import_stats['total_questions_processed'] += 1
            
            # 1. 实体关系提取
            extraction_result = self.entity_extractor.extract_all_from_question(question_data)
            
            # 2. 验证提取结果
            if not extraction_result or not self.entity_extractor.validate_extraction_result(extraction_result):
                self.logger.warning(f"问题 {question_id} 实体提取结果无效")
                self.import_stats['failed_imports'] += 1
                return False
            
            # 3. 构建图谱
            graph_question_id = self.graph_builder.build_question_graph(question_data, extraction_result)
            
            if graph_question_id:
                self.import_stats['successful_imports'] += 1
                self.logger.debug(f"问题 {question_id} 导入成功")
                return True
            else:
                self.import_stats['failed_imports'] += 1
                self.logger.warning(f"问题 {question_id} 图谱构建失败")
                return False
                
        except Exception as e:
            self.import_stats['failed_imports'] += 1
            self.logger.error(f"处理问题 {question_id} 失败: {e}")
            return False
    
    def _update_batch_stats(self, batch_time: float):
        """更新批次统计"""
        current_batches = self.import_stats['total_batches']
        if current_batches > 0:
            total_time = self.import_stats['avg_batch_time'] * (current_batches - 1)
            self.import_stats['avg_batch_time'] = (total_time + batch_time) / current_batches
    
    def _show_progress(self, current_batch: int, total_batches: int):
        """显示进度信息"""
        progress = (current_batch / total_batches) * 100
        success_rate = (self.import_stats['successful_imports'] / 
                       max(self.import_stats['total_questions_processed'], 1)) * 100
        
        # 估算剩余时间 - 增强空值检查
        if current_batch > 1:
            start_time = self.import_stats.get('start_time')
            if start_time is not None:
                elapsed_time = time.time() - start_time
                avg_time_per_batch = elapsed_time / current_batch
                remaining_batches = total_batches - current_batch
                estimated_remaining = avg_time_per_batch * remaining_batches
                
                self.logger.info(
                    f"进度: {progress:.1f}% | "
                    f"成功率: {success_rate:.1f}% | "
                    f"预计剩余时间: {estimated_remaining/60:.1f}分钟"
                )
            else:
                self.logger.info(f"进度: {progress:.1f}% | 成功率: {success_rate:.1f}%")
        else:
            self.logger.info(f"进度: {progress:.1f}% | 成功率: {success_rate:.1f}%")
    
    def _generate_final_statistics(self, optimization_results: Dict) -> Dict[str, Any]:
        """生成最终统计信息 - 增强空值处理"""
        # 获取各组件统计，并提供默认值
        try:
            preprocessor_stats = self.preprocessor.get_statistics()
        except Exception as e:
            self.logger.warning(f"获取预处理器统计失败: {e}")
            preprocessor_stats = {}
            
        try:
            extractor_stats = self.entity_extractor.get_statistics()
        except Exception as e:
            self.logger.warning(f"获取提取器统计失败: {e}")
            extractor_stats = {}
            
        try:
            graph_stats = self.graph_builder.get_graph_statistics()
        except Exception as e:
            self.logger.warning(f"获取图构建器统计失败: {e}")
            graph_stats = {}
        
        # 安全计算总时间 - 处理start_time或end_time为None的情况
        start_time = self.import_stats.get('start_time')
        end_time = self.import_stats.get('end_time')
        
        if start_time is None:
            self.logger.warning("start_time未设置，使用当前时间作为默认值")
            start_time = time.time()
        
        if end_time is None:
            end_time = time.time()
        
        total_time = end_time - start_time
        
        # 确保total_time为正数
        if total_time < 0:
            self.logger.warning("计算的总时间为负数，重置为0")
            total_time = 0
        
        # 安全地计算成功率
        total_processed = max(self.import_stats.get('total_questions_processed', 0), 1)
        successful = self.import_stats.get('successful_imports', 0)
        
        final_stats = {
            'import_summary': {
                'total_time_seconds': total_time,
                'total_time_formatted': f"{total_time/60:.1f} 分钟",
                'questions_loaded': self.import_stats.get('total_questions_loaded', 0),
                'questions_processed': self.import_stats.get('total_questions_processed', 0),
                'successful_imports': successful,
                'failed_imports': self.import_stats.get('failed_imports', 0),
                'success_rate': (successful / total_processed) * 100,
                'avg_processing_time': total_time / total_processed if total_processed > 0 else 0,
                'questions_per_minute': (total_processed / (total_time/60)) if total_time > 0 else 0
            },
            'range_import_info': self.range_info,  # 新增范围导入信息
            'preprocessing_stats': preprocessor_stats,
            'extraction_stats': extractor_stats,
            'graph_stats': graph_stats,
            'optimization_results': optimization_results or {}
        }
        
        return final_stats
    
    def export_statistics(self, output_path: str, stats: Dict[str, Any]):
        """导出统计信息"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
            
            self.logger.info(f"统计信息已导出到: {output_path}")
            
        except Exception as e:
            self.logger.error(f"导出统计信息失败: {e}")

def _execute_range_import(importer: HotpotQAImporter, dataset_path: str, args) -> Dict[str, Any]:
    """
    执行范围导入功能
    
    Args:
        importer: HotpotQA导入器实例
        dataset_path: 数据集路径
        args: 命令行参数
        
    Returns:
        导入统计信息
    """
    # 1. 加载完整数据集用于范围计算
    print("正在加载数据集以计算范围...")
    raw_data = importer.preprocessor.load_dataset(dataset_path, args.format)
    dataset_size = len(raw_data)
    
    print(f"数据集原始大小: {dataset_size} 个样本")
    
    # 2. 验证范围参数
    range_validator = DataRangeValidator()
    validation_result = range_validator.validate_range_params(
        start_index=args.start_index,
        end_index=args.end_index,
        skip_count=args.skip_count,
        import_count=args.import_count,
        dataset_size=dataset_size
    )
    
    if not validation_result['is_valid']:
        error_msg = range_validator.provide_user_friendly_error_messages(validation_result)
        raise ValueError(f"参数错误: {error_msg}")
    
    # 3. 应用范围过滤
    slice_processor = DataSliceProcessor()
    filtered_data, slice_info = slice_processor.slice_dataset(
        raw_data, 
        validation_result['computed_start'],
        validation_result['computed_end']
    )
    
    print(f"指定导入范围: {slice_info['range_description']} (共{slice_info['filtered_dataset_size']}个样本)")
    
    # 4. 执行范围导入
    print(f"\n开始导入数据集: {dataset_path}")
    print(f"范围过滤: {slice_info['range_description']} → 实际处理{slice_info['filtered_dataset_size']}个问题")
    
    stats = importer.import_filtered_dataset(
        filtered_data=filtered_data,
        slice_info=slice_info,
        rebuild_graph=args.rebuild_graph
    )
    
    return stats

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='HotpotQA数据集导入工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基本导入
  python scripts/import_hotpotqa_data.py database/hotpotqa_dev_subset.json
  python scripts/import_hotpotqa_data.py hotpot_qa --format dev --max-questions 200
  python scripts/import_hotpotqa_data.py --download-test --max-questions 200 --rebuild-graph
  python scripts/import_hotpotqa_data.py --download-dev --max-questions 100
  
  # 范围导入示例
  python scripts/import_hotpotqa_data.py --download-dev --start-index 21 --end-index 30
  python scripts/import_hotpotqa_data.py database/hotpotqa.json --start-index 51 --import-count 20
  python scripts/import_hotpotqa_data.py --download-test --skip-count 100 --import-count 50
  python scripts/import_hotpotqa_data.py database/hotpotqa.json --start-index 100 --end-index 100
  python scripts/import_hotpotqa_data.py --download-train --start-index 200
        """
    )
    
    # 数据源选择（互斥组）
    source_group = parser.add_mutually_exclusive_group(required=True)
    
    source_group.add_argument(
        'dataset_path',
        nargs='?',
        help='数据集路径（本地文件路径或Hugging Face数据集名称）'
    )
    
    source_group.add_argument(
        '--download-test',
        action='store_true',
        help='下载HotpotQA测试集(fullwiki)并导入'
    )
    
    source_group.add_argument(
        '--download-dev',
        action='store_true',
        help='下载HotpotQA验证集(fullwiki)并导入'
    )
    
    source_group.add_argument(
        '--download-train',
        action='store_true',
        help='下载HotpotQA训练集并导入'
    )
    
    parser.add_argument(
        '--format',
        choices=['train', 'dev', 'test', 'auto'],
        default='auto',
        help='数据格式（默认: auto）'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='批处理大小（默认: 50）'
    )
    
    parser.add_argument(
        '--max-questions',
        type=int,
        help='最大处理问题数（用于测试）'
    )
    
    parser.add_argument(
        '--rebuild-graph',
        action='store_true',
        help='重建图谱（清除现有数据）'
    )
    
    parser.add_argument(
        '--force-download',
        action='store_true',
        help='强制重新下载（即使缓存存在）'
    )
    
    parser.add_argument(
        '--export-stats',
        help='导出统计信息的文件路径'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日志级别（默认: INFO）'
    )
    
    # 数据范围控制参数组
    range_group = parser.add_argument_group('数据范围控制')
    
    # 精确范围控制
    range_group.add_argument(
        '--start-index',
        type=int,
        help='起始数据索引（从1开始，包含该位置）'
    )
    
    range_group.add_argument(
        '--end-index', 
        type=int,
        help='结束数据索引（包含该位置）'
    )
    
    # 便捷模式
    range_group.add_argument(
        '--skip-count',
        type=int,
        help='跳过前N条数据'
    )
    
    range_group.add_argument(
        '--import-count',
        type=int, 
        help='导入数据条数'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # 检查范围参数是否设置
    has_range_params = any([
        args.start_index is not None,
        args.end_index is not None,
        args.skip_count is not None,
        args.import_count is not None
    ])
    
    try:
        # 创建导入器
        importer = HotpotQAImporter(
            batch_size=args.batch_size,
            max_questions=args.max_questions if not has_range_params else None  # 范围模式下忽略max_questions
        )
        
        # 确定数据集路径
        dataset_path = None
        
        if args.download_test:
            print("正在下载HotpotQA测试集...")
            # 范围模式下不限制下载数量，由范围参数控制
            max_samples = None if has_range_params else (args.max_questions or 200)
            dataset_path = importer.downloader.download_if_needed(
                'test_fullwiki', 
                max_samples=max_samples,
                force_download=args.force_download
            )
            print(f"✓ 测试集已准备就绪: {dataset_path}")
            
        elif args.download_dev:
            print("正在下载HotpotQA验证集...")
            max_samples = None if has_range_params else (args.max_questions or 200)
            dataset_path = importer.downloader.download_if_needed(
                'dev_fullwiki',
                max_samples=max_samples,
                force_download=args.force_download
            )
            print(f"✓ 验证集已准备就绪: {dataset_path}")
            
        elif args.download_train:
            print("正在下载HotpotQA训练集...")
            max_samples = None if has_range_params else args.max_questions
            dataset_path = importer.downloader.download_if_needed(
                'train',
                max_samples=max_samples,
                force_download=args.force_download
            )
            print(f"✓ 训练集已准备就绪: {dataset_path}")
            
        else:
            dataset_path = args.dataset_path
            
        if not dataset_path:
            parser.error("必须指定数据集路径或下载选项")
        
        # 执行导入 - 区分范围模式和常规模式
        if has_range_params:
            # 范围导入模式
            stats = _execute_range_import(importer, dataset_path, args)
        else:
            # 常规导入模式（向后兼容）
            print(f"\n开始导入数据集: {dataset_path}")
            if args.max_questions:
                print(f"限制处理数量: {args.max_questions} 个问题")
            
            stats = importer.import_dataset(
                dataset_path=dataset_path,
                data_format=args.format,
                rebuild_graph=args.rebuild_graph
            )
        
        # 打印简要统计
        summary = stats['import_summary']
        range_info = stats.get('range_import_info', {})
        
        print(f"\n{'='*50}")
        print("导入完成！")
        print(f"{'='*50}")
        
        # 显示范围信息（如果有）
        if range_info:
            print(f"原始数据集: {range_info.get('original_dataset_size', 0)} 个样本")
            print(f"导入范围: {range_info.get('range_description', '未指定')}")
            print(f"实际处理: {range_info.get('filtered_dataset_size', 0)} 个问题")
        
        print(f"总用时: {summary['total_time_formatted']}")
        print(f"处理问题: {summary['questions_processed']} 个")
        print(f"成功导入: {summary['successful_imports']} 个")
        print(f"失败: {summary['failed_imports']} 个")
        print(f"成功率: {summary['success_rate']:.1f}%")
        if summary.get('questions_per_minute', 0) > 0:
            print(f"处理速度: {summary['questions_per_minute']:.1f} 问题/分钟")
        
        # 图谱统计
        graph_stats = stats['graph_stats']
        print(f"\n图谱统计:")
        print(f"问题节点: {graph_stats.get('hotpot_questions', 0)}")
        print(f"实体节点: {graph_stats.get('hotpot_entities', 0)}")
        print(f"段落节点: {graph_stats.get('hotpot_paragraphs', 0)}")
        print(f"支持事实: {graph_stats.get('hotpot_supporting_facts', 0)}")
        print(f"关系总数: {graph_stats.get('has_entity_relations', 0) + graph_stats.get('mentions_relations', 0) + graph_stats.get('related_to_relations', 0)}")
        
        # 导出统计信息
        if args.export_stats:
            importer.export_statistics(args.export_stats, stats)
        
        print(f"{'='*50}")
        print("✓ HotpotQA数据集导入成功！")
        print("您现在可以使用GraphRAG功能进行问答测试。")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n用户中断导入过程")
        return 1
    except Exception as e:
        print(f"\n导入失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())