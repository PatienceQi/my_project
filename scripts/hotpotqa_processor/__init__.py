"""
HotpotQA数据集处理器模块
支持HotpotQA数据集的预处理、实体关系提取和知识图谱构建
"""

from .preprocessor import HotpotQAPreprocessor
from .entity_extractor import HotpotQAEntityExtractor
from .graph_builder import HotpotQAGraphBuilder
from .utils import (
    HotpotQADataFormat,
    EntityType,
    RelationType,
    validate_hotpotqa_data,
    calculate_confidence_score,
    normalize_entity_name
)

__version__ = "1.0.0"
__author__ = "GraphRAG Team"

__all__ = [
    'HotpotQAPreprocessor',
    'HotpotQAEntityExtractor', 
    'HotpotQAGraphBuilder',
    'HotpotQADataFormat',
    'EntityType',
    'RelationType',
    'validate_hotpotqa_data',
    'calculate_confidence_score',
    'normalize_entity_name'
]