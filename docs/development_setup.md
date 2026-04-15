# 开发环境初始化

本文档说明如何使用 `uv` 初始化本项目的本地开发环境。

## 前提

- 已安装 `uv`
- 本机可访问本地 PostgreSQL

## Python 版本

项目统一使用 `Python 3.13`。

仓库根目录的 `.python-version` 已声明本地开发版本：

```text
3.13
```

## 安装依赖

在仓库根目录执行：

```bash
make setup
cp .env.example .env
```

说明：

- `make setup` 会执行 `uv python install 3.13` 和 `uv sync --dev`
- 默认会创建并使用项目本地虚拟环境
- 后续使用 `make run`、`make test`、`make lint` 时，不需要手工激活 `.venv`

如果要使用内置前端工作台，还需要安装前端依赖并构建：

```bash
make frontend-install
make frontend-build
```

说明：

- 前端位于 `frontend/`，现已升级为独立的 `Vue + Vite` 工程
- 后端 `GET /ui` 默认读取 `frontend/dist/` 下的构建产物
- 若未构建，`/ui` 会返回明确提示，要求先执行前端构建

如果你要启用真实对话层，请在 `.env` 中配置：

```env
PKOS_DEEPSEEK_API_KEY=your_deepseek_api_key
PKOS_DEEPSEEK_MODEL=deepseek-chat
```

## 启动服务

```bash
make run
```

如果你偏好脚本方式，也可以执行：

```bash
./run.sh
```

说明：

- 服务启动时会自动创建缺失表
- 对于已有旧库，会执行一组轻量兼容性 DDL，用于补齐新增但向后兼容的字段，例如 `source_versions.device_context`
- 这套机制只适合小规模兼容修复，不替代正式 migration 工具

## 常用校验命令

```bash
make test
make lint
make frontend-build
```

如果你要运行真实 PostgreSQL 集成测试，请额外配置：

```env
PKOS_TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pkos_test
```

然后执行：

```bash
uv run pytest -q tests/test_integration_postgres.py
```

说明：

- 该测试会创建表、执行 `ingest -> jobs/run -> search` 的完整链路，再清理测试库对象
- 若未设置 `PKOS_TEST_DATABASE_URL`，该文件中的集成测试会自动跳过
- 测试库需允许创建 `vector` 扩展

关于 `Makefile`、`run.sh` 和 VS Code 调试入口的说明，见 [development_workflow.md](/home/choho/gitee/self-hosted-knowledgehub/docs/development_workflow.md)。
