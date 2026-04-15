# Upload API

## 概述

系统支持通过 `multipart/form-data` 直接上传本地文件，并将其作为 `document` 类型 source 写入系统。

接口：

- `POST /ingest/upload`

## 表单字段

- `file`：必填，上传文件
- `title`：可选，自定义标题
- `occurred_at`：可选，ISO 时间字符串
- `capture_method`：可选，默认 `manual_upload`
- `device_context`：可选

## 行为

- 文件会被写入 `binary_assets`
- `source_type` 固定为 `document`
- 会创建对应的 `source_items`、`source_versions`、`events`
- 后续仍可通过 `/jobs/run` 进入索引和知识编译链路

## 适用类型

当前适合：

- `txt`
- `md`
- `html`
- `json`
- `pdf`

其中文本类文件会直接保留文本内容；二进制文件会按二进制资产落盘。
