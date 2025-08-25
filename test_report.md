# GraphRAG系统测试报告
生成时间: 2025-08-25 17:46:29

## 测试摘要
- 总测试数: 8
- 通过测试: 1
- 失败测试: 7
- 通过率: 12.5%

## 详细测试结果
### 1. 环境设置 - ✗ 失败
- ✓ .env文件存在
- ✓ 数据目录存在
- ✓ neo4j已安装
- ✓ flask已安装
- ✓ requests已安装
- ✗ python-dotenv未安装
- ✓ chromadb已安装
- ✓ sentence_transformers已安装
- ✓ jieba已安装

### 2. 基础模块导入 - ✗ 失败
- ✗ VectorRetriever导入失败: No module named 'backend'
- ✗ GraphQueryEngine导入失败: No module named 'backend'
- ✗ EntityExtractor导入失败: No module named 'backend'
- ✗ HallucinationDetector导入失败: No module named 'backend'
- ✗ GraphRAGEngine导入失败: No module named 'backend'
**错误信息:**
- VectorRetriever: No module named 'backend'
- GraphQueryEngine: No module named 'backend'
- EntityExtractor: No module named 'backend'
- HallucinationDetector: No module named 'backend'
- GraphRAGEngine: No module named 'backend'

### 3. 向量检索 - ✗ 失败
- ✗ 测试失败: 无法导入任何向量检索器
**错误信息:**
- 无法导入任何向量检索器

### 4. 图谱查询 - ✗ 失败
- ✗ 测试失败: No module named 'backend'
**错误信息:**
- No module named 'backend'

### 5. 实体提取 - ✗ 失败
- ✗ 测试失败: No module named 'backend'
**错误信息:**
- No module named 'backend'

### 6. GraphRAG引擎 - ✗ 失败
- ✗ 测试失败: No module named 'backend'
**错误信息:**
- No module named 'backend'

### 7. API服务器 - ✗ 失败
- ✗ 测试失败: No module named 'backend'
**错误信息:**
- No module named 'backend'

### 8. 数据导入 - ✓ 通过
- ✓ 找到2个数据文件
- ✓ 数据文件加载成功: [OCR]_华侨经济文化合作试验区.json
- 数据类型: dict

## 建议
⚠️ 存在失败的测试，请检查以下问题：
- 环境设置: 
- 基础模块导入: VectorRetriever: No module named 'backend'; GraphQueryEngine: No module named 'backend'; EntityExtractor: No module named 'backend'; HallucinationDetector: No module named 'backend'; GraphRAGEngine: No module named 'backend'
- 向量检索: 无法导入任何向量检索器
- 图谱查询: No module named 'backend'
- 实体提取: No module named 'backend'
- GraphRAG引擎: No module named 'backend'
- API服务器: No module named 'backend'