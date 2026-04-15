# Web UI

## 概述

系统现在提供一个内置前端管理台，入口是：

- `GET /ui`

前端代码独立放在仓库根目录的 [`frontend/`](/home/choho/gitee/self-hosted-knowledgehub/frontend) 下，现已升级为完整的 `Vue + Vite` 工程。后端只负责：

- 暴露 API
- 提供前端静态入口

## 目录结构

```text
frontend/
  package.json
  vite.config.js
  index.html
  src/
    main.js
    App.vue
    router/
    stores/
    services/
    components/
    views/
    styles/
```

## 当前能力

页面支持直接查看：

- Chat 主工作台
- `Sources`
- `Knowledge`
- `Events`
- `Jobs`
- 搜索结果

页面支持直接操作：

- `webpage` 导入
- `bookmark` 导入
- `search` 导入
- `chat` 导入
- 本地文件上传导入
- 执行 `POST /jobs/run`
- 触发全文检索和语义检索

在 `Conversation` 页面中，如果已配置 `PKOS_DEEPSEEK_API_KEY`，页面会显示：

- `provider=deepseek`
- `model=deepseek-chat` 或你配置的模型名

如果未配置，则会显示本地降级结果：

- `provider=local`
- `used_fallback=true`

## 设计说明

- 前端使用 `Vue 3 + Vite + Vue Router + Pinia`
- 主入口界面采用更接近常规 AI Chat 的布局：左侧导航、中央对话区、右侧上下文面板
- 通过 `npm run build` 产出 `frontend/dist/`
- FastAPI 的 `GET /ui` 直接服务构建产物

## 本地构建

```bash
make frontend-install
make frontend-build
```

构建完成后访问：

- `http://127.0.0.1:8000/ui`

## 后续可演进方向

- 增加更细粒度筛选、分页和联动详情
- 增加 conversation session 列表和历史会话恢复
- 增加文件上传式导入和表单式导入
- 增加知识对象图谱视图与时间线视图
