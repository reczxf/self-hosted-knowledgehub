# PKOS Collector MVP

This repository now includes a runnable ingestion collector for the first project step: receiving source data, persisting metadata in PostgreSQL, and storing raw assets on local disk.

## Run locally

1. Install `uv` and prepare Python `3.13`:

```bash
make setup
cp .env.example .env
```

2. Create a PostgreSQL database named `pkos`.

3. Start the API:

```bash
make run
```

4. Install and build the frontend:

```bash
make frontend-install
make frontend-build
```

5. Open `http://127.0.0.1:8000/docs`.
6. Open `http://127.0.0.1:8000/ui` for the built-in dashboard.

To enable DeepSeek-backed conversation answers, configure:

```env
PKOS_DEEPSEEK_API_KEY=your_deepseek_api_key
PKOS_DEEPSEEK_MODEL=deepseek-chat
```

## Common commands

```bash
make test
make lint
make frontend-build
```

You can also use `./run.sh` as a thin wrapper around `make run`.
For local IDE debugging, use the VS Code launch configuration documented in [development_workflow.md](/home/choho/gitee/self-hosted-knowledgehub/docs/development_workflow.md).

The repository pins local development to Python `3.13` via `.python-version`, and project metadata requires Python `>=3.13`.

## Example request

```bash
curl -X POST http://127.0.0.1:8000/ingest/webpage \
  -H "Content-Type: application/json" \
  -d '{
    "capture_method": "browser_extension",
    "url": "https://example.com/article",
    "canonical_url": "https://example.com/article",
    "title": "Example Article",
    "occurred_at": "2026-04-14T09:00:00Z",
    "assets": [
      {
        "asset_role": "page_html",
        "file_name": "page.html",
        "mime_type": "text/html",
        "text_content": "<html><body>Hello PKOS</body></html>"
      }
    ],
    "metadata": {
      "tags": ["demo", "browser"]
    }
  }'
```

Stored files will appear under `PKOS_DATA_DIR/captures/...`, and metadata will be written to PostgreSQL tables created on startup.
