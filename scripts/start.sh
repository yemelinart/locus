#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ] || [ ! -f frontend/dist/index.html ]; then
  printf 'Сначала выполните scripts/setup.sh\n'
  exit 1
fi
exec .venv/bin/python -m uvicorn locus.api:create_app --factory --host 127.0.0.1 --port "${LOCUS_PORT:-8420}"
