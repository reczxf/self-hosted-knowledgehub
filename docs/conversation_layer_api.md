# Conversation Layer API

## 概述

系统现在提供一个支持最小多轮上下文的对话调用层接口：

- `POST /conversation/answer`

默认会优先调用 `DeepSeek Chat Completions`，并将系统内的知识对象和原始证据作为上下文输入。

若未传 `session_id`，接口会自动创建一个新的会话；若传入已有 `session_id`，系统会读取最近几轮历史消息并一并送入模型。

它不会直接返回“文档列表”，而是返回三层结构：

- `answer`：直接回答
- `knowledge_items`：命中的知识对象
- `evidence_items`：命中的原始证据

同时还会返回：

- `provider`
- `model`
- `used_fallback`
- `session_id`
- `conversation_turns`

## 请求体

```json
{
  "question": "目前 PKOS 已经实现到什么程度？",
  "session_id": null,
  "search_mode": "hybrid",
  "limit": 5
}
```

字段说明：

- `question`：用户问题
- `session_id`：可选，会话标识；为空时自动创建新会话
- `search_mode`：`text`、`semantic`、`hybrid`
- `limit`：返回候选数量

## 响应示例

```json
{
  "session_id": "49d6f947-d5b5-4f01-b268-8b0632a8a726",
  "question": "目前 PKOS 已经实现到什么程度？",
  "answer": "围绕该问题，当前最相关的知识对象包括：PKOS Insight ...",
  "provider": "deepseek",
  "model": "deepseek-chat",
  "used_fallback": false,
  "conversation_turns": [
    {
      "id": "d9f2d1be-f6f0-4f2d-940a-1d2d7f17a521",
      "session_id": "49d6f947-d5b5-4f01-b268-8b0632a8a726",
      "turn_no": 1,
      "role": "user",
      "content": "目前 PKOS 已经实现到什么程度？"
    },
    {
      "id": "6d4a2910-30d6-4e6f-8a7f-f4315971f1bb",
      "session_id": "49d6f947-d5b5-4f01-b268-8b0632a8a726",
      "turn_no": 2,
      "role": "assistant",
      "content": "围绕该问题，当前最相关的知识对象包括：PKOS Insight ..."
    }
  ],
  "knowledge_items": [
    {
      "id": "c5ef3d76-264f-4280-851b-ff9f9705de0a",
      "knowledge_type": "insight_card",
      "title": "PKOS Insight",
      "summary": "PKOS 已有最小知识层"
    }
  ],
  "evidence_items": [
    {
      "source_version_id": "ec1fd2df-aad0-4a38-bc81-9824861cc4d7",
      "title": "PKOS Memory Layer",
      "preview": "PKOS memory layer supports ...",
      "score": 0.82,
      "match_type": "text"
    }
  ]
}
```

## 当前限制

- 若未配置 `PKOS_DEEPSEEK_API_KEY`，系统会自动降级到本地模板回答
- 当前只保留最近若干轮消息作为上下文窗口，不做更复杂的摘要压缩
- 还不支持回答结果回写为新知识对象

## 配置

需要设置：

- `PKOS_DEEPSEEK_API_KEY`

可选：

- `PKOS_DEEPSEEK_BASE_URL`
- `PKOS_DEEPSEEK_MODEL`
- `PKOS_DEEPSEEK_TIMEOUT_SECONDS`
- `PKOS_DEEPSEEK_MAX_TOKENS`
