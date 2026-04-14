# Ingestion MVP 设计

## 目标

第一步只解决一件事：把浏览器或其他来源的原始数据稳定抓进本地，并保留足够多的元信息，支持后续做索引、知识编译、对话和推送。

## 设计原则

- PostgreSQL 存结构化元数据、关系和检索字段
- 本地目录存原始文件，例如 HTML、Markdown、截图、附件、原始 JSON
- 原始内容尽量不可变，后续处理通过新增版本或派生对象完成
- 每条记录都必须可追溯到来源、采集时间、采集方式和原始载荷
- 先做统一采集协议，不为某一种来源单独设计数据库

## 建议目录

目录根路径必须可配置，例如 `PKOS_DATA_DIR=/data/pkos`。

建议结构：

```text
data/
  blobs/            # 原始载荷，按 sha256 分片
  captures/         # 页面快照、截图、导出文件
  imports/          # 手工导入文件
  derived/          # 后续提取文本、清洗结果、embedding
```

## 最小对象模型

1. `source_items`
   表示原始材料本体，例如网页、聊天记录、搜索结果页、PDF、笔记。
2. `source_versions`
   表示某次实际采集到的内容快照。同一个 URL 可有多次抓取。
3. `binary_assets`
   表示落盘文件，例如 `raw.json`、`page.html`、`screenshot.png`、`document.pdf`。
4. `events`
   表示用户行为，例如搜索、收藏、打开页面、导入文件、发起 AI 对话。

## 必须保留的元信息

- `source_type`：`web_page`、`bookmark`、`search_result`、`chat_thread`、`document`
- `capture_method`：`browser_extension`、`manual_import`、`api_push`、`cli`
- `captured_at`、`occurred_at`、`original_created_at`、`original_updated_at`
- `url`、`canonical_url`、`referrer_url`
- `title`、`author`、`language`、`mime_type`
- `content_sha256`、`size_bytes`
- `browser_profile`、`user_agent`、`device_context`
- `metadata` JSONB：保留来源特有字段，避免过早定死 schema
- `extractor_version`、`schema_version`

## 推荐入库流程

1. 采集端产生统一 JSON envelope。
2. 服务端计算内容哈希并写入本地文件目录。
3. 在一个事务里写入 `source_items`、`source_versions`、`binary_assets`、`events`。
4. 若 `canonical_url + content_sha256` 已存在，只新增事件或版本，不覆盖原记录。

## 第一阶段接口建议

- `POST /ingest/webpage`
- `POST /ingest/bookmark`
- `POST /ingest/search`
- `POST /ingest/chat`

请求体统一包含：

```json
{
  "source_type": "web_page",
  "capture_method": "browser_extension",
  "occurred_at": "2026-04-14T09:00:00Z",
  "metadata": {},
  "assets": []
}
```

## 实现建议

MVP 不要直接做复杂 ETL。先实现一个本地 collector：

- 接收浏览器插件或 CLI 推送
- 落盘原始文件
- 写 PostgreSQL
- 返回稳定 `source_id` 和 `version_id`

当这层稳定后，再追加全文索引、向量索引和知识编译。
