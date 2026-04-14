.PHONY: setup run test lint format help ensure-venv

PYTHON_VERSION := 3.13
VENV_PYTHON := .venv/bin/python
VENV_BIN := .venv/bin

help:
	@echo "Available targets:"
	@echo "  make setup  - install Python $(PYTHON_VERSION) and sync dependencies"
	@echo "  make run    - start the FastAPI app with reload"
	@echo "  make test   - run pytest"
	@echo "  make lint   - run ruff check"
	@echo "  make ensure-venv - verify the local virtual environment exists"

setup:
	uv python install $(PYTHON_VERSION)
	uv sync --dev

ensure-venv:
	@if [ ! -x "$(VENV_PYTHON)" ]; then \
		echo "未找到项目虚拟环境: $(VENV_PYTHON)" >&2; \
		echo "请先执行: make setup" >&2; \
		exit 1; \
	fi

run: ensure-venv
	$(VENV_PYTHON) -m uvicorn app.main:app --reload

test: ensure-venv
	$(VENV_PYTHON) -m pytest

lint: ensure-venv
	$(VENV_PYTHON) -m ruff check .
