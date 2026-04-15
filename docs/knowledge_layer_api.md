# Knowledge Layer API

## 概述

当前系统已支持最小知识编译层，会基于 `derived_documents` 生成一种知识对象：`insight_card`。

知识层的目标不是替代原始资料，而是在原始资料和问答层之间提供稳定、可持续更新的中间知识对象。

## 编译链路

1. `POST /ingest/*` 写入原始材料
2. `POST /jobs/run` 执行 `index_source_version`
3. 索引任务完成后自动入队 `compile_knowledge_item`
4. 同一次 `POST /jobs/run` 在剩余额度内继续执行知识编译
5. 生成 `knowledge_items`

## 当前知识对象

### `insight_card`

最小知识对象类型，适合承载：

- 某条原始材料的摘要
- 某次采集内容的结构化表达
- 后续主题页 / 项目页的中间原料

## 读取接口

### `GET /knowledge`

查询知识对象列表。

查询参数：

- `knowledge_type`
- `limit`
- `offset`

### `GET /knowledge/{knowledge_item_id}`

查询单个知识对象详情。

## 响应示例

```json
{
  "items": [
    {
      "id": "91688b29-b4ee-41b7-a44f-4fef8e772e14",
      "knowledge_type": "insight_card",
      "status": "active",
      "slug": "insight_card-pkos-memory-layer-91688b29",
      "title": "PKOS Memory Layer",
      "summary": "PKOS Memory Layer Semantic search and full text retrieval",
      "source_item_id": "7ec5d31e-4157-48e9-8478-c6d54d5174fb",
      "source_version_id": "732413f2-cb70-4688-9d08-f4494b1547a1",
      "derived_document_id": "59d4f8c9-5d4c-4238-b9b9-ef44d3a1ffeb",
      "metadata": {
        "source_type": "web_page",
        "generated_from": "derived_document"
      }
    }
  ],
  "limit": 50,
  "offset": 0
}
```

## 当前限制

- 目前只有 `insight_card`
- 尚未生成主题页、项目页、实体页、时间线页
- 尚未支持多文档聚合编译
- 尚未支持知识对象之间的显式链接关系
