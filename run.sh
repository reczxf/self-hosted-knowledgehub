#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_ACTIVATE="${ROOT_DIR}/.venv/bin/activate"

if [[ ! -f "${VENV_ACTIVATE}" ]]; then
  echo "未找到虚拟环境: ${VENV_ACTIVATE}" >&2
  echo "请先在仓库根目录执行: uv sync --dev" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${VENV_ACTIVATE}"

exec make -C "${ROOT_DIR}" run
