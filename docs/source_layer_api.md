# Source Layer API

## 概述

当前阶段的 API 目标是先形成 Source Layer 的最小闭环：

- 能写入多种原始来源
- 能查询核心采集对象
- 为后续索引、知识编译和对话层提供稳定输入

## 已支持的写入接口

### `POST /ingest/webpage`

用于写入网页快照。

### `POST /ingest/bookmark`

用于写入书签或收藏链接。

最小请求体示例：

```json
{
  "capture_method": "browser_extension",
  "url": "https://example.com/bookmark",
  "occurred_at": "2026-04-15T10:00:00Z"
}
```

### `POST /ingest/search`

用于写入搜索行为或搜索结果页快照。

最小请求体示例：

```json
{
  "capture_method": "browser_extension",
  "url": "https://example.com/search?q=pkos",
  "query": "pkos",
  "occurred_at": "2026-04-15T10:00:00Z"
}
```

### `POST /ingest/chat`

用于写入对话线程。

最小请求体示例：

```json
{
  "capture_method": "api_push",
  "provider": "openai",
  "thread_id": "thread-123",
  "occurred_at": "2026-04-15T10:00:00Z",
  "messages": [
    {
      "role": "user",
      "content": "hello"
    }
  ]
}
```

说明：

- 当 `chat` 请求包含 `messages` 时，服务端会自动生成 `messages.json` 资产并随版本一起落盘
- 所有 ingest 接口都会返回 `source_item_id`、`source_version_id`、`event_id` 和 `asset_count`

## 已支持的读取接口

### `GET /sources`

列出 `source_items`。

支持参数：

- `source_type`
- `limit`
- `offset`

### `GET /sources/{source_item_id}`

返回单个 source item 详情，以及关联版本数和事件数。

### `GET /sources/{source_item_id}/versions`

列出某个 source item 下的版本。

支持参数：

- `limit`
- `offset`

### `GET /versions/{source_version_id}`

返回单个 source version 详情，并包含关联资产列表。

### `GET /events`

列出事件。

支持参数：

- `event_type`
- `limit`
- `offset`

### `GET /events/{event_id}`

返回单个事件详情。

## 当前边界

当前 API 仍然属于 Source Layer MVP，尚未实现：

- 全文检索
- 向量召回
- 知识页生成
- 对话问答
- 时间驱动推送
