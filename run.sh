#!/usr/bin/env bash
# Launch the ICA Trainer (backend serves the frontend too).
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8777}"

if command -v uv >/dev/null 2>&1; then
  exec uv run --with fastapi --with "uvicorn[standard]" --with markdown --with pyflakes \
    uvicorn app:app --app-dir backend --host 127.0.0.1 --port "$PORT" --reload
else
  echo "uv not found — falling back to system python. Install deps first:"
  echo "  pip install fastapi 'uvicorn[standard]' markdown pyflakes"
  exec python3 -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port "$PORT" --reload
fi
