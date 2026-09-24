# ADAS-KB-AGENT

智能驾驶知识库Agent。核心设计:LLM、向量库(Milvus)都通过抽象接口访问,
没有API Key/Milvus时,系统用mock后端跑通全部业务逻辑,
资源到位后只改 `.env` 里的开关,业务代码不用动。

**当前状态:核心链路已经端到端跑通过**——本地Postgres + 公司提供的Milvus +
真实Anthropic API,能完整跑完"投喂文档→分类→切块→向量化→入库"全流程,
也能跑通Agent多轮工具调用。仍在细化的部分见文末"已知待办"。

## 一、环境搭建

\`\`\`bash
cp .env.example .env
python3.12 -m venv venv    # 建议锁定3.11/3.12,3.14太新很多包还没适配
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
\`\`\`

**几个装依赖时大概率会碰到的坑**(都是环境问题,不是代码问题):
- `unstructured`解析PDF报错缺依赖 → `pip install "unstructured[pdf]"`
- 报`libmagic`找不到(Mac)→ `brew install libmagic`
- `pymilvus`导入报`pkg_resources`缺失 → `pip install "setuptools<81"`(新版setuptools移除了这个模块,pymilvus还依赖它)
- Apple Silicon Mac上出现"Bad CPU type in executable" → 大概率是装了Intel版Homebrew的工具,确认`which brew`输出的是`/opt/homebrew/bin/brew`而不是`/usr/local/bin/brew`

## 二、跑单元测试(不需要任何外部资源)

\`\`\`bash
PYTHONPATH=. pytest tests/ -v
\`\`\`
应该10个测试全部通过——这部分完全不依赖Postgres/Milvus/LLM,是纯逻辑验证。

## 三、起Postgres(结构化数据:模块一~四+法规索引表+状态机)

用Postgres.app(Mac图形化,推荐)或Homebrew装都行,装完要**手动建一个数据库**
(默认不会自动帮你建项目需要的库名):

\`\`\`sql
CREATE DATABASE kb_structured;
\`\`\`

`.env`里对应配好:
\`\`\`
PG_HOST=localhost
PG_PORT=5432
PG_DB=kb_structured
PG_USER=你的用户名
PG_PASSWORD=
\`\`\`

建表:
\`\`\`bash
psql -h localhost -p 5432 -U 你的用户名 -d kb_structured -f scripts/init_db.sql
\`\`\`

**注意**:`.env`里`PG_DB`必须跟你手动`psql`进去检查时用的库名完全一致——
这两个对不上是实测踩过的坑,代码往一个库写数据,人在另一个库里查,
永远对不上,查的时候记得先`python3 -c "from config.settings import PG_CONFIG; print(PG_CONFIG)"`
确认代码实际连的是哪个库。

## 四、接Milvus(向量库:模块五)

拿到host/port后(Attu图形界面能确认collection建没建出来):

\`\`\`
MILVUS_HOST=xxx
MILVUS_PORT=19530
VECTOR_BACKEND=real
\`\`\`

建collection:
\`\`\`bash
PYTHONPATH=. python scripts/init_milvus_collection.py
\`\`\`

## 五、接LLM(分类判断/结构化抽取/Agent推理)

\`\`\`
ANTHROPIC_API_KEY=xxx
LLM_BACKEND=real
\`\`\`

也支持接Gemini做横向对比(`agent/llm_client.py`里的`GeminiClient`,
用的是新版`google-genai`包,旧的`google-generativeai`已停止维护):
\`\`\`bash
pip install google-genai
\`\`\`
\`\`\`
LLM_PROVIDER=gemini   # 或 anthropic,切换供应商只改这一行
GEMINI_API_KEY=xxx
\`\`\`

## 六、投喂文档

\`\`\`bash
PYTHONPATH=. python main.py ingest test_data/你的文件.docx
PYTHONPATH=. python main.py ingest-feishu "https://xxx.feishu.cn/docx/xxx" "文档名"
\`\`\`

第一次跑会比较慢,要下载BGE-M3(embedding)和bge-reranker(rerank)两个开源模型,
网络不好可以配国内镜像:
\`\`\`bash
export HF_ENDPOINT=https://hf-mirror.com
\`\`\`

## 七、问Agent

\`\`\`bash
PYTHONPATH=. python main.py ask "MPI怎么计算"
\`\`\`

## 八、常见的"卡住"排查顺序

投喂或查询报错时,按这个顺序缩小范围,不要一遇到报错就整个重装:
1. 确认Postgres/Milvus服务本身在不在跑(`psql`能不能连上,Attu能不能打开)
2. 确认`.env`里的库名/host跟你实际检查的是同一个(`print(PG_CONFIG)`)
3. 看报错的文件路径,定位是哪一层(parsers/classifiers/kb.modules/agent)出的问题
4. 如果是同一份文件重复投喂被误判`DUPLICATE`,但你确实想重跑,先去`documents`表把
   卡住的旧记录删掉(注意`review_queue`和`chunks`表有外键引用,要按顺序先删这两个)

## 九、分类逻辑说明(容易被问起,先写清楚)

`resolve_document_category`是四级优先级链,**能用便宜的方法判断就不往下一级走**:
1. 显式元数据(目前实际调用方基本没传,预留接口)
2. 命名规则——文件名里带"流程/验收/CRB""GB/国标/标准""测试用例/TP/校验"直接判定
3. 内容级规则——文件名没命中时,扫描正文里流程/法规/测试用例/需求spec各自的特征词
   (比如"测试步骤""预期结果"→测试用例,"本标准规定""实施日期"→法规),按命中数打分取最高
4. LLM——前面都判断不了,交给真实模型(mock模式下固定给0.3的低置信度,必然会被拦进`NEEDS_REVIEW`,这是有意设计的兜底,不是bug)

置信度低于`CONFIDENCE_THRESHOLD`(`pipeline/dispatcher.py`里,默认0.6)会被
推进`review_queue`人工审核,不会硬着头皮继续往下走。

## 十、目录结构

\`\`\`
config/
  settings.py          全局配置(mock/real开关、embedding/rerank参数、分类关键词)
  prompts.py           LLM Prompt模板
pipeline/
  parsers/             物理解析层:Excel/Word/DBC/CK系统表/飞书文档
  classifiers/         意图识别层:命名规则→内容规则→LLM四级优先级链
  extractors/          结构化抽取:切块/规则抽取/信号抽取
  dedup.py             双层指纹查重
  reranker.py          检索结果精排
  observability.py     耗时/失败日志记录
  dispatcher.py        总调度器,串联A→B→C→D四个分区
kb/
  storage/             存储客户端:Postgres真实 / Milvus真实+mock / 对象存储 / 本地队列
  modules/              六个知识库模块的读写接口 + 状态机 + 审核队列 + 分类配置
agent/
  llm_client.py         LLM抽象接口:mock / Anthropic真实 / Gemini真实
  core.py                Agent多轮工具调用循环
  tools/                  Agent可调用的工具(检索/查KPI/查信号/查路由/生成SQL)
tests/                  单元测试,不依赖任何外部资源
scripts/                建表SQL / Milvus collection初始化 / 质量评测脚本
\`\`\`

## 十一、已知待办(不影响核心链路,但要知道存在)

- Excel/Matrix表格文件的路由还是简化占位,没有做"表头识别决定该进KPI库还是信号字典库"这一步
- MQ是本地SQLite模拟的,没有真实队列的异步/死信重试调度逻辑
- `GeminiClient.chat_with_tools`是简化实现,没有真正对齐Gemini的function calling格式,多轮工具调用这块建议优先用Anthropic验证
- `category_config`表结构建好了,但`dispatcher.py`目前还没有真正读它做路由决策,还是内嵌逻辑