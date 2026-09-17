# ADAS-KB-AGENT

智能驾驶知识库Agent。核心设计:LLM和Milvus都通过抽象接口访问,
没有API Key/Milvus时,系统用mock后端跑通全部业务逻辑,
资源到位后只改 `.env` 两个开关,不用改代码。

## 现在没有API Key和Milvus,可以先做这些(按优先级排序)

### 1. 环境搭建(5分钟)
```bash
cp .env.example .env
pip install -r requirements.txt
# 保持 .env 里 VECTOR_BACKEND=mock, LLM_BACKEND=mock
```

### 2. 跑通单元测试,验证解析和分类逻辑(不需要任何外部资源)
```bash
pytest tests/ -v
```

### 3. 起一个本地Postgres(Docker一行命令,不需要申请任何账号)
```bash
docker run -d --name kb-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
psql -h localhost -U postgres -f scripts/init_db.sql
```
起了这个之后,模块一(信号字典库)、模块四(车型路由表)、法规索引表
就可以完整地写入、查询、测试了——这些不依赖LLM也不依赖Milvus。

### 4. 用真实DBC文件测试模块一
```bash
python main.py ingest path/to/your.dbc
```
这条链路是全项目确定性最高的,cantools解析零LLM依赖,可以先重点验证。

### 5. 用真实Word/PDF文档测试RAG链路(mock向量库)
```bash
python main.py ingest path/to/spec.docx
```
向量会写入内存假存储(重启程序即丢失,这是预期行为),
用来验证"解析→切块→打标→存储"这条链路对不对。

## 资源到位后要改的地方(只有这些)

| 资源 | 改哪里 |
|---|---|
| Milvus endpoint | `.env`: `MILVUS_HOST`、`VECTOR_BACKEND=real` |
| Anthropic API Key | `.env`: `ANTHROPIC_API_KEY`、`LLM_BACKEND=real` |
| ClickHouse连接 | `.env`: `CK_HOST`等字段 |

改完这三处,`kb/modules/`、`pipeline/dispatcher.py`、`agent/core.py` 等
全部业务代码不需要任何改动,自动切换到真实实现。

## 目录结构

```
config/          全局配置 + LLM Prompt模板
pipeline/
  parsers/       物理解析层(Excel/Word/DBC/CK系统表)
  classifiers/   意图识别层(规则粗筛 + LLM细分)
  extractors/    结构化抽取(规则/信号/文本切片)
  dispatcher.py  总调度器
kb/
  storage/       存储客户端(Postgres真实 / Milvus真实+mock双实现)
  modules/       六大知识库模块的读写接口
agent/
  tools/         Agent可调用的工具
  core.py        Agent对话循环
tests/           单元测试,现在就能跑
scripts/         建表SQL / Milvus collection初始化
```
