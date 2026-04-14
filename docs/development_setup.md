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

## 启动服务

```bash
make run
```

如果你偏好脚本方式，也可以执行：

```bash
./run.sh
```

## 常用校验命令

```bash
make test
make lint
```

关于 `Makefile`、`run.sh` 和 VS Code 调试入口的说明，见 [development_workflow.md](/home/choho/gitee/self-hosted-knowledgehub/docs/development_workflow.md)。
