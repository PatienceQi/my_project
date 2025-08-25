#!/usr/bin/env python3
"""
检查项目中是否还有使用ollama.Client()的地方
确保所有组件都使用HTTP API而不是ollama客户端库
"""

import os
import re
import sys
from pathlib import Path

def check_file_for_ollama_client(file_path):
    """检查单个文件是否使用了ollama客户端"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # 跳过检查脚本本身和文档文件
        file_name = file_path.name.lower()
        if file_name in ['check_ollama_client_usage.py', '64482端口问题分析和解决方案.md', '远程ollama配置修复完成报告.md']:
            return []  # 跳过检查脚本和文档文件
        
        # 检查import ollama（但跳过注释和字符串中的）
        import_lines = []
        for line_num, line in enumerate(content.split('\n'), 1):
            line_stripped = line.strip()
            # 跳过注释和空行
            if line_stripped.startswith('#') or not line_stripped:
                continue
            # 跳过字符串内的内容
            if 'import ollama' in line and not ('"' in line or "'" in line):
                import_lines.append(f"第{line_num}行: {line_stripped}")
        
        if import_lines:
            issues.append(f"发现 'import ollama': {', '.join(import_lines)}")
        
        # 检查from ollama import
        from_import_lines = []
        for line_num, line in enumerate(content.split('\n'), 1):
            line_stripped = line.strip()
            if line_stripped.startswith('#') or not line_stripped:
                continue
            if 'from ollama import' in line and not ('"' in line or "'" in line):
                from_import_lines.append(f"第{line_num}行: {line_stripped}")
        
        if from_import_lines:
            issues.append(f"发现 'from ollama import': {', '.join(from_import_lines)}")
        
        # 检查ollama.Client()（但跳过注释和字符串中的）
        client_lines = []
        for line_num, line in enumerate(content.split('\n'), 1):
            line_stripped = line.strip()
            if line_stripped.startswith('#') or not line_stripped:
                continue
            # 跳过字符串中的内容和注释
            if 'ollama.Client(' in line and not ('"' in line or "'" in line or line_stripped.startswith('#')):
                client_lines.append(f"第{line_num}行: {line_stripped}")
        
        if client_lines:
            issues.append(f"发现 'ollama.Client()': {', '.join(client_lines)}")
        
        # 检查.chat()或.generate()调用（更精确的检查）
        suspicious_calls = []
        for line_num, line in enumerate(content.split('\n'), 1):
            line_stripped = line.strip()
            if line_stripped.startswith('#') or not line_stripped:
                continue
            
            # 只检查明显的客户端调用，跳过HTTP API调用
            if re.search(r'\bclient\s*\.\s*(?:chat|generate)\s*\(', line) and 'requests' not in line:
                suspicious_calls.append(f"第{line_num}行: {line_stripped}")
        
        if suspicious_calls:
            issues.append(f"发现可疑的ollama客户端调用: {', '.join(suspicious_calls)}")
        
        return issues
        
    except Exception as e:
        return [f"文件读取错误: {e}"]

def main():
    """主函数"""
    print("🔍 检查项目中是否还有ollama客户端使用...")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    
    # 检查所有Python文件
    python_files = []
    for pattern in ['**/*.py']:
        python_files.extend(project_root.glob(pattern))
    
    # 过滤掉不需要检查的文件
    excluded_patterns = [
        '.ipynb_checkpoints',
        '__pycache__',
        '.git',
        'venv',
        'env'
    ]
    
    python_files = [
        f for f in python_files 
        if not any(pattern in str(f) for pattern in excluded_patterns)
    ]
    
    print(f"检查 {len(python_files)} 个Python文件...")
    
    found_issues = False
    issue_summary = {}
    
    for file_path in python_files:
        issues = check_file_for_ollama_client(file_path)
        if issues:
            found_issues = True
            relative_path = file_path.relative_to(project_root)
            
            print(f"\n❌ {relative_path}:")
            for issue in issues:
                print(f"   - {issue}")
            
            issue_summary[str(relative_path)] = issues
    
    print("\n" + "=" * 60)
    
    if found_issues:
        print("⚠️ 发现ollama客户端使用问题！")
        print("\n修复建议:")
        print("1. 将 'import ollama' 替换为 'import requests'")
        print("2. 将 'ollama.Client(host=...)' 替换为直接的HTTP API调用")
        print("3. 将 'client.chat()' 替换为 'requests.post(url, json=payload)'")
        print("4. 将 'client.generate()' 替换为 'requests.post(url, json=payload)'")
        
        print(f"\n发现问题的文件数量: {len(issue_summary)}")
        return False
    else:
        print("✅ 未发现ollama客户端使用问题！")
        print("所有文件都正确使用HTTP API调用。")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)