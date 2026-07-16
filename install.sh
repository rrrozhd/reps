#!/usr/bin/env bash
# reps — one-command install.
#   curl -fsSL https://raw.githubusercontent.com/rrrozhd/reps/main/install.sh | bash
#
# Clones (or updates) the repo and starts the local server. Uses `uv` if present.
set -euo pipefail

REPO="${REPS_REPO:-https://github.com/rrrozhd/reps}"
DIR="${REPS_DIR:-$HOME/reps}"
PORT="${PORT:-8777}"

say() { printf '\033[1;33m▪ %s\033[0m\n' "$*"; }

if [ -d "$DIR/.git" ]; then
  say "Updating $DIR"; git -C "$DIR" pull --ff-only || true
elif [ -f "./run.sh" ] && [ -d "./backend/drills" ]; then
  DIR="$(pwd)"; say "Running from the current checkout ($DIR)"
else
  command -v git >/dev/null || { echo "git is required"; exit 1; }
  say "Cloning $REPO -> $DIR"; git clone --depth 1 "$REPO" "$DIR"
fi

cd "$DIR"

if ! command -v uv >/dev/null 2>&1; then
  say "uv not found. Install it (recommended):"
  echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "  …or install deps manually and run:"
  echo "    pip install fastapi 'uvicorn[standard]' markdown pyflakes"
  echo "    python3 -m uvicorn app:app --app-dir backend --port $PORT"
  exit 1
fi

say "Starting reps at http://127.0.0.1:$PORT  (Ctrl-C to stop)"
PORT="$PORT" exec ./run.sh
