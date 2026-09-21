#!/bin/sh
set -eu
cd "$(dirname "$0")"
if curl --max-time 2 -fsS "http://127.0.0.1:${LOCUS_PORT:-8420}/api/health" >/dev/null 2>&1; then
  open "http://127.0.0.1:${LOCUS_PORT:-8420}"
  exit 0
fi
if [ ! -x .venv/bin/python ] || [ ! -f frontend/dist/index.html ]; then
  ./scripts/setup.sh
fi
./scripts/start.sh &
LOCUS_SERVER_PID=$!
trap 'kill "$LOCUS_SERVER_PID" 2>/dev/null || true' EXIT HUP INT TERM
for LOCUS_ATTEMPT in 1 2 3 4 5 6 7 8 9 10; do
  if curl --max-time 1 -fsS "http://127.0.0.1:${LOCUS_PORT:-8420}/api/health" >/dev/null 2>&1; then
    open "http://127.0.0.1:${LOCUS_PORT:-8420}"
    break
  fi
  sleep 1
done
wait "$LOCUS_SERVER_PID"
