#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if command -v uv >/dev/null 2>&1; then
  if [ ! -d .venv ]; then uv venv --python 3.12 .venv; fi
  uv pip install --python .venv/bin/python -r requirements.lock
  uv pip install --python .venv/bin/python --no-deps -e .
else
  if [ ! -d .venv ]; then python3 -m venv .venv; fi
  .venv/bin/python -m pip install -r requirements.lock
  .venv/bin/python -m pip install --no-deps -e .
fi
cd frontend
npm ci
npm run build
printf '\nLocus готов. Запустите scripts/start.sh из папки проекта.\n'
