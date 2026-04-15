# 系统功能清单

## 概述

当前仓库已经从单纯的 `Collector MVP` 推进到 `Source Layer + Memory Layer MVP`。系统不再只是接收和存储 ingest 请求，而是已经具备最小的去重、派生索引、任务处理和检索能力。

## 当前实现状态摘要

- 已实现：健康检查、四类 ingest、幂等去重、本地资产落盘、PostgreSQL 元数据入库、读取类 API、后台任务表、全文索引、向量化存储、基础全文/语义检索、最小知识对象编译、内置前端控制台
- 部分实现：测试覆盖、真实数据库集成测试、知识编译层、对话调用层
- 未实现：时间推送层、认证权限、可观测性增强

## 功能清单

### 已实现

1. 健康检查接口
   - 状态：`implemented`
   - 说明：提供 `GET /healthz`
   - 依据：`app/main.py`

2. 四类采集接口
   - 状态：`implemented`
   - 说明：已支持 `POST /ingest/webpage`、`/ingest/bookmark`、`/ingest/search`、`/ingest/chat`
   - 依据：`app/main.py`

3. 本地原始资产落盘
   - 状态：`implemented`
   - 说明：支持 JSON、文本和二进制落盘，并按 sha256 分片
   - 依据：`app/storage.py`

4. PostgreSQL 核心持久化
   - 状态：`implemented`
   - 说明：采集时写入 `source_items`、`source_versions`、`binary_assets`、`events`
   - 依据：`app/repositories.py`

5. 启动期初始化
   - 状态：`implemented`
   - 说明：启动时创建目录、创建 ORM 表，并尝试启用 `vector` 扩展
   - 依据：`app/main.py`

6. 内容级幂等去重
   - 状态：`implemented`
   - 说明：基于 `canonical_uri + content_sha256` 检测重复内容；重复 ingest 只新增事件，不重复创建版本
   - 依据：`app/repositories.py`

7. 采集元字段补齐
   - 状态：`implemented`
   - 说明：`device_context` 已提升为显式 schema 和持久化字段
   - 依据：`app/schemas.py`、`app/models.py`

8. 读取类 API
   - 状态：`implemented`
   - 说明：已支持 `source`、`version`、`event` 的基础列表与详情查询
   - 依据：`app/main.py`、`app/repositories.py`

9. 后台任务最小闭环
   - 状态：`implemented`
   - 说明：已支持 `processing_jobs` 表、任务入队、任务列表和进程内任务执行
   - 依据：`app/models.py`、`app/repositories.py`、`app/main.py`

10. 全文索引
    - 状态：`implemented`
    - 说明：已支持从落盘资产抽取文本、生成 `derived_documents` 并进行 PostgreSQL 全文检索
    - 依据：`app/indexing.py`、`app/models.py`、`app/repositories.py`

11. 向量化存储与语义检索
    - 状态：`implemented`
    - 说明：已支持生成轻量 embedding、写入向量列，并提供基础语义检索接口
    - 依据：`app/vector.py`、`app/indexing.py`、`app/repositories.py`

12. 文档与接口说明
    - 状态：`implemented`
    - 说明：已补齐 Source Layer、Memory Layer、Knowledge Layer 和 Web UI 文档
    - 依据：`docs/source_layer_api.md`、`docs/memory_layer_api.md`、`docs/knowledge_layer_api.md`、`docs/web_ui.md`

13. 内置前端控制台
    - 状态：`implemented`
    - 说明：已提供基于 Vue 的内置页面，可浏览核心数据、执行导入、任务和搜索
    - 依据：`frontend/`、`app/main.py`

### 部分实现

1. 测试覆盖
   - 状态：`partial`
   - 说明：当前已覆盖本地存储、API 路由、索引工具和部分 repository 纯逻辑，但还没有真实 PostgreSQL 事务级集成测试
   - 依据：`tests/test_storage.py`、`tests/test_api.py`、`tests/test_indexing.py`、`tests/test_repositories.py`

2. API 与数据库集成测试
   - 状态：`partial`
   - 说明：已经有 API happy path 和部分逻辑单测，但缺少“真实数据库 + 真正 ingest + 真任务处理”的端到端测试
   - 依据：`tests/test_api.py`、`tests/test_repositories.py`

3. 知识编译层
   - 状态：`partial`
   - 说明：已支持基于 `derived_documents` 编译 `insight_card`，但尚未实现主题页、项目页、实体页、时间线页等更高阶知识对象
   - 依据：`app/models.py`、`app/repositories.py`、`app/main.py`

4. 对话调用层
   - 状态：`partial`
   - 说明：已支持基于 DeepSeek 的最小结构化问答接口，可返回直接回答、命中的知识对象和原始证据；未配置 API Key 时会降级到本地模板回答，但仍未支持多轮上下文
   - 依据：`app/llm.py`、`app/main.py`、`app/repositories.py`、`docs/conversation_layer_api.md`

### 未实现

1. 时间驱动推送与复盘
   - 状态：`not_implemented`
   - 说明：暂无日报、周报、变化追踪、复习提醒

2. 认证与权限
   - 状态：`not_implemented`
   - 说明：当前没有鉴权、用户隔离和访问控制

3. 可观测性增强
   - 状态：`not_implemented`
   - 说明：除健康检查外，暂无结构化日志、指标和链路跟踪

## 建议优先级

1. 先补真实 PostgreSQL 集成测试和任务处理端到端验证
2. 再推进知识编译层，开始沉淀稳定知识对象
3. 最后补对话层、时间层、认证和可观测性
