#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复版本的政策数据导入脚本

主要修复内容：
1. 支持两种JSON数据格式（OCR版本和标准版本）
2. 修复Ollama API调用方式
3. 简化数据处理逻辑，提高稳定性
4. 完善错误处理和日志记录
"""

import os
import json
import argparse
import hashlib
from typing import Dict, List, Optional, Union
from neo4j import GraphDatabase
import dotenv
import requests
import traceback

# 加载环境变量
dotenv.load_dotenv()

class PolicyDataImporter:
    """政策数据导入器"""
    
    def __init__(self):
        """初始化导入器"""
        self.setup_neo4j()
        self.setup_ollama()
        self.stats = {
            'processed_files': 0,
            'created_policies': 0,
            'created_sections': 0,
            'created_articles': 0,
            'errors': 0
        }
    
    def setup_neo4j(self):
        """设置Neo4j连接"""
        self.neo4j_uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        try:
            self.driver = GraphDatabase.driver(
                self.neo4j_uri, 
                auth=(self.neo4j_user, self.neo4j_password)
            )
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("✓ Neo4j连接成功")
        except Exception as e:
            print(f"✗ Neo4j连接失败: {e}")
            self.driver = None
    
    def setup_ollama(self):
        """设置Ollama连接"""
        self.llm_host = os.getenv("LLM_BINDING_HOST", "http://120.232.79.82:11434")
        self.llm_model = os.getenv("LLM_MODEL", "llama3.2:latest")
        
        try:
            # 简单的连接测试
            response = requests.get(f"{self.llm_host}/api/tags", timeout=5)
            if response.status_code == 200:
                print("✓ Ollama连接成功")
                self.ollama_available = True
            else:
                print(f"✗ Ollama连接失败: HTTP {response.status_code}")
                self.ollama_available = False
        except Exception as e:
            print(f"✗ Ollama连接失败: {e}")
            self.ollama_available = False
    
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
    
    def create_policy_node(self, tx, policy_data: Dict) -> str:
        """创建政策节点"""
        title = policy_data.get('title', '未知政策')
        policy_id = self.generate_id(title, "POL")
        
        query = """
        MERGE (p:Policy {policy_id: $policy_id})
        SET p.title = $title,
            p.doc_number = $doc_number,
            p.publish_agency = $publish_agency,
            p.publish_date = $publish_date
        RETURN p.policy_id as policy_id
        """
        
        params = {
            'policy_id': policy_id,
            'title': title,
            'doc_number': policy_data.get('doc_number', ''),
            'publish_agency': policy_data.get('publish_agency', ''),
            'publish_date': policy_data.get('publish_date', '')
        }
        
        try:
            result = tx.run(query, **params)
            record = result.single()
            if record:
                self.stats['created_policies'] += 1
                print(f"  ✓ 创建政策节点: {title}")
                return policy_id
        except Exception as e:
            print(f"  ✗ 创建政策节点失败: {e}")
            self.stats['errors'] += 1
        
        return policy_id
    
    def process_ocr_format(self, tx, policy_data: Dict, policy_id: str):
        """处理OCR格式数据"""
        main_body = policy_data.get('main_body', [])
        
        for section_data in main_body:
            section_title = section_data.get('section_title', '未知章节')
            section_content = section_data.get('content', '')
            section_id = self.generate_id(f"{policy_id}_{section_title}", "SEC")
            
            # 创建章节节点
            self.create_section_node(tx, section_id, section_title, section_content, policy_id)
    
    def process_standard_format(self, tx, policy_data: Dict, policy_id: str):
        """处理标准格式数据"""
        chapters = policy_data.get('chapters', [])
        
        for chapter in chapters:
            chapter_title = chapter.get('title', '未知章节')
            chapter_number = chapter.get('number', '')
            full_title = f"{chapter_number} {chapter_title}" if chapter_number else chapter_title
            
            section_id = self.generate_id(f"{policy_id}_{full_title}", "SEC")
            
            # 创建章节节点
            self.create_section_node(tx, section_id, full_title, "", policy_id)
            
            # 处理条款
            articles = chapter.get('articles', [])
            for article in articles:
                article_number = article.get('number', '')
                article_content = article.get('content', '')
                article_title = f"{article_number}"
                
                article_id = self.generate_id(f"{section_id}_{article_title}", "ART")
                self.create_article_node(tx, article_id, article_title, article_content, section_id, policy_id)
    
    def create_section_node(self, tx, section_id: str, title: str, content: str, policy_id: str):
        """创建章节节点"""
        query = """
        MERGE (s:Section {section_id: $section_id})
        SET s.title = $title,
            s.content = $content
        WITH s
        MATCH (p:Policy {policy_id: $policy_id})
        MERGE (s)-[:BELONGS_TO]->(p)
        RETURN s.section_id as section_id
        """
        
        params = {
            'section_id': section_id,
            'title': title,
            'content': content,
            'policy_id': policy_id
        }
        
        try:
            result = tx.run(query, **params)
            if result.single():
                self.stats['created_sections'] += 1
                print(f"    ✓ 创建章节: {title}")
        except Exception as e:
            print(f"    ✗ 创建章节失败: {e}")
            self.stats['errors'] += 1
    
    def create_article_node(self, tx, article_id: str, title: str, content: str, section_id: str, policy_id: str):
        """创建条款节点"""
        query = """
        MERGE (a:Article {article_id: $article_id})
        SET a.title = $title,
            a.content = $content
        WITH a
        MATCH (s:Section {section_id: $section_id})
        MERGE (a)-[:BELONGS_TO]->(s)
        WITH a
        MATCH (p:Policy {policy_id: $policy_id})
        MERGE (a)-[:PART_OF]->(p)
        RETURN a.article_id as article_id
        """
        
        params = {
            'article_id': article_id,
            'title': title,
            'content': content,
            'section_id': section_id,
            'policy_id': policy_id
        }
        
        try:
            result = tx.run(query, **params)
            if result.single():
                self.stats['created_articles'] += 1
                print(f"      ✓ 创建条款: {title}")
        except Exception as e:
            print(f"      ✗ 创建条款失败: {e}")
            self.stats['errors'] += 1
    
    def import_policy_file(self, file_path: str) -> bool:
        """导入单个政策文件"""
        print(f"\n处理文件: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                policy_data = json.load(f)
        except Exception as e:
            print(f"✗ 读取文件失败: {e}")
            self.stats['errors'] += 1
            return False
        
        # 检测数据格式
        data_format = self.detect_data_format(policy_data)
        print(f"检测到数据格式: {data_format}")
        
        if data_format == 'unknown_format':
            print("✗ 未知的数据格式")
            self.stats['errors'] += 1
            return False
        
        if not self.driver:
            print("✗ Neo4j连接不可用")
            self.stats['errors'] += 1
            return False
        
        try:
            with self.driver.session() as session:
                policy_id = session.execute_write(self.create_policy_node, policy_data)
                
                if data_format == 'ocr_format':
                    session.execute_write(self.process_ocr_format, policy_data, policy_id)
                elif data_format == 'standard_format':
                    session.execute_write(self.process_standard_format, policy_data, policy_id)
                
                self.stats['processed_files'] += 1
                print(f"✓ 文件处理完成")
                return True
                
        except Exception as e:
            print(f"✗ 数据库操作失败: {e}")
            traceback.print_exc()
            self.stats['errors'] += 1
            return False
    
    def import_directory(self, directory_path: str):
        """导入目录中的所有JSON文件"""
        json_files = [f for f in os.listdir(directory_path) if f.endswith('.json')]
        
        if not json_files:
            print(f"在目录 {directory_path} 中未找到JSON文件")
            return
        
        print(f"发现 {len(json_files)} 个JSON文件")
        
        for json_file in json_files:
            file_path = os.path.join(directory_path, json_file)
            self.import_policy_file(file_path)
    
    def print_statistics(self):
        """打印导入统计信息"""
        print("\n" + "="*50)
        print("数据导入统计")
        print("="*50)
        print(f"处理文件数: {self.stats['processed_files']}")
        print(f"创建政策节点: {self.stats['created_policies']}")
        print(f"创建章节节点: {self.stats['created_sections']}")
        print(f"创建条款节点: {self.stats['created_articles']}")
        print(f"错误次数: {self.stats['errors']}")
        print("="*50)
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            print("Neo4j连接已关闭")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='导入政策数据到Neo4j数据库')
    parser.add_argument('--file', type=str, help='指定要处理的JSON文件路径')
    parser.add_argument('--directory', type=str, default='./database', help='指定要处理的目录路径')
    args = parser.parse_args()
    
    print("="*50)
    print("政策数据导入系统 - 修复版本")
    print("="*50)
    
    importer = PolicyDataImporter()
    
    try:
        if args.file:
            # 处理单个文件
            if os.path.exists(args.file):
                importer.import_policy_file(args.file)
            else:
                print(f"文件不存在: {args.file}")
        else:
            # 处理目录中的所有文件
            if os.path.exists(args.directory):
                importer.import_directory(args.directory)
            else:
                print(f"目录不存在: {args.directory}")
    
    finally:
        importer.print_statistics()
        importer.close()
    
    print("\n处理完成")

if __name__ == "__main__":
    main()