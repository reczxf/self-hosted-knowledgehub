# Repository Guidelines

## Project Structure & Module Organization

This repository includes both product documentation and a runnable Python service. The main source of truth for product direction is [personal_knowledge_os_technical_guidance.md](/home/choho/gitee/self-hosted-knowledgehub/personal_knowledge_os_technical_guidance.md). Root-level files include `LICENSE`, `.gitignore`, this contributor guide, and project configuration such as [`pyproject.toml`](/home/choho/gitee/self-hosted-knowledgehub/pyproject.toml).

Until application code is added, keep new materials organized by purpose:

- Product or architecture docs: repository root or a future `docs/` directory
- Source code: a future `src/` directory
- Tests: a future `tests/` directory that mirrors the code layout
- Static assets: a future `assets/` directory

## Build, Test, and Development Commands

Current useful commands are:

- `git status` - review local changes before committing
- `git diff --stat` - confirm the scope of documentation edits
- `uv sync --dev` - install runtime and development dependencies
- `uv run uvicorn app.main:app --reload` - start the local API
- `uv run pytest` - run the test suite
- `uv run ruff check .` - run lint checks
- `markdownlint AGENTS.md personal_knowledge_os_technical_guidance.md README.md docs/*.md` - optional Markdown lint check if installed locally

## Coding Style & Naming Conventions

Use concise, structured Markdown with clear heading levels and short paragraphs. Prefer descriptive file names in `snake_case`, matching the existing `personal_knowledge_os_technical_guidance.md` pattern. Keep prose direct and implementation-oriented. Wrap commands, paths, and identifiers in backticks.

For future code contributions, keep formatting tool-driven and document the formatter or linter in the repository before requiring it in reviews.

## Testing Guidelines

For documentation-only changes, verify links, headings, and terminology consistency manually. For future code, place tests under `tests/` and name them to mirror the target module, for example `tests/test_ingestion.py` or `tests/search.spec.ts`.

Any new feature should ship with a reproducible validation step, even if that is initially a documented manual check.

## Commit & Pull Request Guidelines

The current Git history starts with a simple `Initial commit`, so use short, imperative commit subjects such as `Add contributor guide` or `Refine architecture terminology`. Keep one logical change per commit.

Pull requests should include:

- A brief summary of what changed
- The reason for the change
- Any follow-up work or open questions
- Screenshots only when UI assets are introduced later

## Security & Configuration Tips

Do not commit secrets, local environment files, or generated artifacts. The existing `.gitignore` already excludes common Python caches, virtual environments, coverage outputs, and local `.env` files.

## AI Notes

- 使用中文来进行常规交互。
- 强制约定：在执行任何实现类操作（代码修改、重构、测试补充、文档落地）之前，必须先在 `.config/tasks` 目录生成 `tasks_YYYYMMDDHHMMSS.md` 任务文件，再让 AI 基于该任务文件生成执行计划并开始实现。
- 硬性约束：若不存在对应的 `tasks_YYYYMMDDHHMMSS.md` 任务文件，AI 不得执行任何实现类操作，仅允许先创建任务文件并输出计划。
- 将约定的规则回写在AGENTS.md文件中的AI Notes部分。
- 新增的一些接口和功能需要有对应文档在docs目录下生成一个对应的md文件，并且将这个md文件链接到AGENTS.md文件中的最近更改。

## 最近更改

- 新增开发环境文档：[development_setup.md](/home/choho/gitee/self-hosted-knowledgehub/docs/development_setup.md)
- 新增本地开发入口说明：[development_workflow.md](/home/choho/gitee/self-hosted-knowledgehub/docs/development_workflow.md)
- 新增系统功能清单：[system_feature_inventory.md](/home/choho/gitee/self-hosted-knowledgehub/docs/system_feature_inventory.md)
- 新增 Source Layer API 文档：[source_layer_api.md](/home/choho/gitee/self-hosted-knowledgehub/docs/source_layer_api.md)
- 新增 Memory Layer API 文档：[memory_layer_api.md](/home/choho/gitee/self-hosted-knowledgehub/docs/memory_layer_api.md)
- 更新开发环境文档，补充启动期 schema 兼容性说明：[development_setup.md](/home/choho/gitee/self-hosted-knowledgehub/docs/development_setup.md)
- 新增 Knowledge Layer API 文档：[knowledge_layer_api.md](/home/choho/gitee/self-hosted-knowledgehub/docs/knowledge_layer_api.md)
- 新增内置前端控制台说明：[web_ui.md](/home/choho/gitee/self-hosted-knowledgehub/docs/web_ui.md)
- 新增文件上传接口说明：[upload_api.md](/home/choho/gitee/self-hosted-knowledgehub/docs/upload_api.md)
- 新增对话层接口说明：[conversation_layer_api.md](/home/choho/gitee/self-hosted-knowledgehub/docs/conversation_layer_api.md)
- 更新对话层接口说明，补充多轮会话与 `session_id` 约定：[conversation_layer_api.md](/home/choho/gitee/self-hosted-knowledgehub/docs/conversation_layer_api.md)
- 更新内置前端说明，升级为完整 Vue/Vite 前端工程：[web_ui.md](/home/choho/gitee/self-hosted-knowledgehub/docs/web_ui.md)
