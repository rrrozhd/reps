#!/usr/bin/env bash
# Launch the ICA Trainer (backend serves the frontend too).
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8777}"
URL="http://127.0.0.1:$PORT"

# Pop the app open in the browser once the server is accepting connections.
# Runs in the background (the server is exec'd below, so nothing after it would
# run otherwise) and only once per launch — uvicorn's --reload restarts the app
# in-process, so this never re-fires on a code change. Disable with
# REPS_NO_BROWSER=1 (headless boxes, SSH, or a second local instance).
open_browser() {
  [ -n "${REPS_NO_BROWSER:-}" ] && return 0
  local opener=""
  if   command -v open      >/dev/null 2>&1; then opener="open"       # macOS
  elif command -v xdg-open  >/dev/null 2>&1; then opener="xdg-open"   # Linux
  elif command -v wslview   >/dev/null 2>&1; then opener="wslview"    # WSL
  fi
  [ -z "$opener" ] && return 0
  # Wait (≤10s) for the port to listen, then open exactly once.
  for ((i = 0; i < 50; i++)); do
    if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then break; fi
    sleep 0.2
  done
  "$opener" "$URL" >/dev/null 2>&1 || true
}
open_browser &

if command -v uv >/dev/null 2>&1; then
  exec uv run --with fastapi --with "uvicorn[standard]" --with markdown --with pyflakes \
    uvicorn app:app --app-dir backend --host 127.0.0.1 --port "$PORT" --reload
else
  echo "uv not found — falling back to system python. Install deps first:"
  echo "  pip install fastapi 'uvicorn[standard]' markdown pyflakes"
  exec python3 -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port "$PORT" --reload
fi
