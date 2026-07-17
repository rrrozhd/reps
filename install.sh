#!/usr/bin/env bash
# reps installer — makes `reps` a global command.
#   curl -fsSL https://raw.githubusercontent.com/rrrozhd/reps/main/install.sh | bash
#
# Installs the app into ~/.reps and links a `reps` command onto your PATH.
set -euo pipefail

REPO="${REPS_REPO:-https://github.com/rrrozhd/reps}"
REPS_HOME="${REPS_HOME:-$HOME/.reps}"
say() { printf '\033[1;33m▪ %s\033[0m\n' "$*"; }

command -v git >/dev/null 2>&1 || { echo "reps needs git. Install it and re-run."; exit 1; }

# 1. fetch / update the app
if [ -d "$REPS_HOME/.git" ]; then
  say "Updating reps in $REPS_HOME"
  git -C "$REPS_HOME" pull --ff-only || true
else
  say "Installing reps into $REPS_HOME"
  git clone --depth 1 "$REPO" "$REPS_HOME"
fi
chmod +x "$REPS_HOME/reps" "$REPS_HOME/run.sh" "$REPS_HOME/backend/reps_cli.py" 2>/dev/null || true

# 2. link `reps` onto a PATH bin dir (prefer one already on PATH)
BIN=""
for d in "$HOME/.local/bin" "/usr/local/bin"; do
  case ":$PATH:" in *":$d:"*) BIN="$d"; break ;; esac
done
[ -z "$BIN" ] && BIN="$HOME/.local/bin"
mkdir -p "$BIN"
ln -sf "$REPS_HOME/reps" "$BIN/reps"
say "Linked 'reps' → $BIN/reps"

# 3. helpful nudges
command -v uv >/dev/null 2>&1 || \
  say "Tip: install uv for the smoothest run —  curl -LsSf https://astral.sh/uv/install.sh | sh"

echo
case ":$PATH:" in
  *":$BIN:"*) say "All set. Run:  reps" ;;
  *)
    say "Almost — add $BIN to your PATH, then open a new terminal:"
    echo "    echo 'export PATH=\"$BIN:\$PATH\"' >> ~/.zshrc"
    echo
    say "…then run:  reps"
    ;;
esac
