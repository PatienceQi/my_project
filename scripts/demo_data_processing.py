#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据处理演示脚本

用于验证修复后的数据处理逻辑，不依赖Neo4j数据库
"""

import os
import json
import hashlib
from typing import Dict, List

class DataProcessor:
    """数据处理器演示"""
    
    def __init__(self):
        self.stats = {
            'processed_files': 0,
            'detected_policies': 0,
            'detected_sections': 0,
            'detected_articles': 0
        }
    
    def detect_data_format(self, data: Dict) -> str:
        """检测数据格式类型"""
        if 'main_body' in data:
            return 'ocr_format'
        elif 'chapters' in data:
            return 'standard_format'
        else:
            return 'unknown_format'
    
    def generate_id(self, text: str, prefix: str = "ID") -> str:
        """生成唯一ID"""
        return f"{prefix}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
    
    def process_ocr_format(self, policy_data: Dict) -> Dict:
        """处理OCR格式数据"""
        print("  处理OCR格式数据")
        title = policy_data.get('title', '未知政策')
        policy_id = self.generate_id(title, "POL")
        
        result = {
            'policy_id': policy_id,
            'title': title,
            'format': 'ocr_format',
            'sections': []
        }
        
        main_body = policy_data.get('main_body', [])
        print(f"  发现 {len(main_body)} 个章节")
        
        for section_data in main_body:
            section_title = section_data.get('section_title', '未知章节')
            section_content = section_data.get('content', '')
            section_id = self.generate_id(f"{policy_id}_{section_title}", "SEC")
            
            section_result = {
                'section_id': section_id,
                'title': section_title,
                'content_length': len(section_content),
                'articles': []
            }
            
            result['sections'].append(section_result)
            self.stats['detected_sections'] += 1
            print(f"    章节: {section_title} (内容长度: {len(section_content)})")
        
        return result
    
    def process_standard_format(self, policy_data: Dict) -> Dict:
        """处理标准格式数据"""
        print("  处理标准格式数据")
        title = policy_data.get('title', '未知政策')
        policy_id = self.generate_id(title, "POL")
        
        result = {
            'policy_id': policy_id,
            'title': title,
            'format': 'standard_format',
            'chapters': []
        }
        
        chapters = policy_data.get('chapters', [])
        print(f"  发现 {len(chapters)} 个章节")
        
        for chapter in chapters:
            chapter_title = chapter.get('title', '未知章节')
            chapter_number = chapter.get('number', '')
            full_title = f"{chapter_number} {chapter_title}" if chapter_number else chapter_title
            
            chapter_result = {
                'chapter_title': full_title,
                'articles': []
            }
            
            articles = chapter.get('articles', [])
            print(f"    章节: {full_title} (包含 {len(articles)} 条)")
            
            for article in articles:
                article_number = article.get('number', '')
                article_content = article.get('content', '')
                
                article_result = {
                    'number': article_number,
                    'content_length': len(article_content)
                }
                
                chapter_result['articles'].append(article_result)
                self.stats['detected_articles'] += 1
                print(f"      条款: {article_number} (内容长度: {len(article_content)})")
            
            result['chapters'].append(chapter_result)
            self.stats['detected_sections'] += 1
        
        return result
    
    def process_file(self, file_path: str) -> Dict:
        """处理单个文件"""
        print(f"\n处理文件: {os.path.basename(file_path)}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                policy_data = json.load(f)
        except Exception as e:
            print(f"  ✗ 读取文件失败: {e}")
            return None
        
        # 检测数据格式
        data_format = self.detect_data_format(policy_data)
        print(f"  检测到数据格式: {data_format}")
        
        if data_format == 'unknown_format':
            print("  ✗ 未知的数据格式")
            return None
        
        self.stats['detected_policies'] += 1
        
        if data_format == 'ocr_format':
            return self.process_ocr_format(policy_data)
        elif data_format == 'standard_format':
            return self.process_standard_format(policy_data)
        
        return None
    
    def print_statistics(self):
        """打印统计信息"""
        print("\n" + "="*50)
        print("数据处理统计")
        print("="*50)
        print(f"处理文件数: {self.stats['processed_files']}")
        print(f"检测到政策: {self.stats['detected_policies']}")
        print(f"检测到章节: {self.stats['detected_sections']}")
        print(f"检测到条款: {self.stats['detected_articles']}")
        print("="*50)

def main():
    """主函数"""
    print("="*50)
    print("数据处理演示")
    print("="*50)
    
    processor = DataProcessor()
    
    # 处理两种格式的文件
    files_to_process = [
        './database/华侨经济文化合作试验区.json',  # 标准格式
        './database/[OCR]_华侨经济文化合作试验区.json'  # OCR格式
    ]
    
    results = []
    
    for file_path in files_to_process:
        if os.path.exists(file_path):
            result = processor.process_file(file_path)
            if result:
                results.append(result)
                processor.stats['processed_files'] += 1
        else:
            print(f"文件不存在: {file_path}")
    
    processor.print_statistics()
    
    # 输出处理结果摘要
    print("\n处理结果摘要:")
    for result in results:
        print(f"- 政策: {result['title']}")
        print(f"  格式: {result['format']}")
        if result['format'] == 'standard_format':
            print(f"  章节数: {len(result['chapters'])}")
            total_articles = sum(len(ch['articles']) for ch in result['chapters'])
            print(f"  总条款数: {total_articles}")
        else:
            print(f"  章节数: {len(result['sections'])}")
    
    print("\n✓ 数据处理逻辑验证完成")

if __name__ == "__main__":
    main()