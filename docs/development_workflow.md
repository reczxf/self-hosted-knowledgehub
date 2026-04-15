# 本地开发入口说明

本文档说明本项目推荐的本地开发入口，以及 `Makefile`、`run.sh` 和 VS Code 调试配置之间的分工。

## 推荐方案

当前仓库最适合采用：

- `Makefile` 作为统一开发入口
- `run.sh` 作为命令行兼容包装
- `.vscode/launch.json` 作为 IDE 调试入口

原因：

- `Makefile` 更适合管理多个常用动作，而不只是启动服务
- 新成员进入项目后，看到 `make run`、`make test`、`make lint` 的含义更直观
- VS Code 调试需要独立配置，不能由 `run.sh` 替代
- 保留 `run.sh` 可以兼容习惯直接执行脚本的场景

## 三者区别

### `Makefile`

适合统一管理开发命令，例如：

- `make setup`
- `make run`
- `make test`
- `make lint`
- `make frontend-install`
- `make frontend-build`

它的优势是：

- 入口统一
- 易扩展
- 适合团队协作
- 适合 CI 或文档引用

### `run.sh`

`run.sh` 更适合做一个简单包装层。

当前脚本会：

1. 检查本地 `.venv` 是否存在
2. 激活虚拟环境
3. 调用 `make run`

它的优势是：

- 适合习惯直接执行脚本的开发者
- 可以显式处理环境激活

它的局限是：

- 不适合继续承载越来越多的开发动作
- 如果测试、格式化、迁移等命令都堆在脚本里，会很快失去可维护性

## 推荐使用方式

初始化环境：

```bash
make setup
cp .env.example .env
```

启动服务：

```bash
make run
```

或：

```bash
./run.sh
```

运行测试：

```bash
make test
```

运行检查：

```bash
make lint
```

安装前端依赖：

```bash
make frontend-install
```

构建前端：

```bash
make frontend-build
```

说明：

- `Makefile` 已直接使用项目虚拟环境中的 `.venv/bin/python`
- 因此执行 `make run`、`make test`、`make lint` 前，不需要手工执行 `source .venv/bin/activate`
- `run.sh` 仍然保留显式激活，主要是为了兼容“脚本启动”的使用习惯
- 前端工作台现已升级为独立 `Vue + Vite` 工程，因此访问 `/ui` 前应先完成前端构建

## VS Code 调试

仓库已提供 `.vscode/launch.json`。

在 VS Code 中可直接选择：

```text
PKOS API
```

该配置会使用项目本地解释器：

```text
.venv/bin/python
```

并以调试模式启动：

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

使用前请先确保：

- 已执行 `make setup`
- 已复制 `.env.example` 为 `.env`
- 本地 PostgreSQL 可访问，且存在 `pkos` 数据库
