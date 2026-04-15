# Memory Layer API

## 概述

当前仓库已经提供最小 Memory Layer 能力，用于将 Source Layer 中的采集版本转换为可检索的派生文档。

能力包括：

- 任务入队与处理
- 文本抽取
- 全文索引
- 向量化存储
- 全文检索
- 语义检索

## 处理链路

1. `POST /ingest/*` 写入 `source_items`、`source_versions`、`binary_assets`、`events`
2. 新版本创建后自动写入一条 `processing_jobs`
3. 调用 `POST /jobs/run` 处理 pending 任务
4. 任务处理时读取已落盘资产，抽取文本并生成 `derived_documents`
5. 后续通过 `/search/text` 或 `/search/semantic` 查询

## 后台任务接口

### `GET /jobs`

查询任务列表。

查询参数：

- `status`
- `job_type`
- `limit`
- `offset`

### `POST /jobs/run`

在 API 进程内执行 pending 任务。

查询参数：

- `limit`：本次最多处理多少条任务

响应示例：

```json
{
  "requested_limit": 10,
  "processed": 1,
  "completed": 1,
  "failed": 0,
  "jobs": [
    {
      "id": "1d0c0d7b-44e9-4dc2-9f16-4388ec1a14dd",
      "job_type": "index_source_version",
      "status": "completed",
      "source_version_id": "4d57ef93-34e3-4ce0-9039-f0bb06711f0c",
      "attempts": 1,
      "payload": {
        "source_item_id": "5614b474-19fb-4afd-8eb8-33f4f95570d8"
      },
      "result": {
        "derived_document_id": "8f7a0d68-e8a5-4f68-8f7e-8fa2368cc692",
        "token_count": 124
      }
    }
  ]
}
```

## 检索接口

### `GET /search/text`

执行 PostgreSQL 全文检索。

查询参数：

- `q`：查询词
- `limit`

### `GET /search/semantic`

执行基于已存储 embedding 的基础语义检索。

查询参数：

- `q`：查询词
- `limit`

响应结构：

```json
{
  "query": "pkos",
  "limit": 10,
  "items": [
    {
      "match_type": "text",
      "score": 0.87,
      "document": {
        "id": "5ad4b52c-9e7f-4e8c-91ef-c16ba27b2cad",
        "source_item_id": "5614b474-19fb-4afd-8eb8-33f4f95570d8",
        "source_version_id": "4d57ef93-34e3-4ce0-9039-f0bb06711f0c",
        "title": "PKOS memory notes",
        "plain_text_preview": "PKOS memory layer ...",
        "token_count": 124,
        "metadata": {
          "source_type": "web_page",
          "asset_roles": ["page_html"]
        }
      }
    }
  ]
}
```

## 当前限制

- 任务执行仍是进程内触发，不是独立 worker
- embedding 为本地轻量实现，后续可替换成真实模型
- 暂未提供分块索引、混合召回、重排或过滤器查询
