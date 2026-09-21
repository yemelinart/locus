#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
# Check prerequisites before making a partial installation.
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  printf 'Install Node.js 22.12+ (with npm), reopen Terminal, and try again. See START-HERE.md / START-HERE.ru.md.\n' >&2
  exit 1
fi
node -e 'const [major,minor]=process.versions.node.split(".").map(Number); if (major<22 || (major===22 && minor<12)) { console.error("Locus needs Node.js 22.12+ or a supported newer version."); process.exit(1); }'
if ! command -v uv >/dev/null 2>&1; then
  if ! command -v python3 >/dev/null 2>&1; then
    printf 'Install Python 3.12 and try again. See START-HERE.md / START-HERE.ru.md.\n' >&2
    exit 1
  fi
  python3 -c 'import sys; assert (3,11) <= sys.version_info[:2] < (3,15), "Locus needs Python 3.11–3.14 (3.12 recommended)."'
fi
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
