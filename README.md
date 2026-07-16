# reps

**Coding-interview practice with a real editor, a verifying runner, and an agent
coach that generates and explains problems — all from the browser.**

reps is a local, CodeSignal-style harness for **progressive** coding problems
(one problem, several levels, each bolting a new requirement onto the same
growing system — the format Ramp / CodeSignal ICAs use). You solve in a real
Monaco editor; a sandboxed runner tests each level. When you want a new problem,
you ask the built-in **Coach**, which drives *your* coding agent (or an API
model) to write a fresh drill — spec, starter, reference, and tests — and only
ships it once it passes its own verification.

---

## Quick start

```bash
git clone https://github.com/rrrozhd/reps && cd reps
./run.sh                     # uses uv if present; else pip + uvicorn
# open http://127.0.0.1:8777
```

Or one line:

```bash
curl -fsSL https://raw.githubusercontent.com/rrrozhd/reps/main/install.sh | bash
```

> The editor loads Monaco from a CDN (jsDelivr), so the browser needs internet.
> Everything else — task specs, the runner, linting, your saved solutions — is
> fully local.

---

## What you get

- **Real editor** — Monaco (the VS Code engine): Python highlighting, bracket
  colors, multi-cursor, `⌘/Ctrl+Enter` to run, `⌘/Ctrl+S` to save.
- **Live linting** — `pyflakes` paints warnings/errors in the gutter as you type.
- **Progressive runner** — each drill has multiple levels; Run shows per-level
  pass/fail with `expected · got` diffs. Runs in an isolated subprocess with a
  timeout, and captures your `print()` output into a panel.
- **Durable progress** — your solution for each drill is saved **server-side**
  (plus the browser), so a closed server or cleared browser never loses work.
- **Rendered filesystem** — the File System drill draws the tree your code builds.
- **90-minute ICA clock**, one-click reference solutions.

## The Coach (generate & explain, from the UI)

Open the **✦ Coach** tab:

- **Generate a problem** — type a topic (e.g. *sliding-window rate limiter*,
  *LRU cache*, *interval merge*), pick easy/medium/hard, hit **Generate**. The
  Coach authors a full drill and **verifies it** before it appears; a broken
  problem never ships.
- **Ask the coach** — *Explain this level*, *Give me a hint*, *Why is my code
  failing?*, or free-text. It sees the current problem, your code, and your last
  results.

### Bring your own engine

reps is **provider-agnostic**. The Coach's **Engine** dropdown lists whatever it
detects, in this precedence (override with `REPS_PROVIDER`):

| Kind | Engines | Auth |
|------|---------|------|
| **Local CLI agent** (preferred) | `claude` (Claude Code), `gemini`, `codex`, `cursor-agent`, `opencode` | your existing CLI login — **no API key** |
| **API** | `anthropic` (native) · **OpenAI-compatible**: OpenAI, OpenRouter, Groq, Together, local Ollama/LM Studio | env key |
| **mock** | offline sample generator | none — for trying the loop |

API keys / models (any one enables the API path):

```bash
export ANTHROPIC_API_KEY=...                 # native Anthropic
export OPENAI_API_KEY=...   # + optional OPENAI_BASE_URL for OpenAI-compatible
export OPENROUTER_API_KEY=...                # one key, hundreds of models
export GROQ_API_KEY=...
export REPS_MODEL=...                        # override the model id
```

Whatever engine writes a drill, **reps re-runs the verify gate itself** — so
correctness never depends on the model, only on passing the tests.

> Health check: `GET /api/agent/health` (or the Engine dropdown) shows what's
> detected and active. If a local CLI errors on auth, run it once in a terminal
> to log in.

## The built-in drills

| Drill | Skin | The twist that forces good state design |
|-------|------|------------------------------------------|
| **Banking System** | accounts, transfers, cashback | historical `get_balance` + `merge` → balance is a checkpoint log |
| **In-Memory File System** | dirs, files, copy/move | `get_file_size(path, at_version)` → per-file write log |
| **Key-Value Store w/ TTL** | set/get, prefix scan, expiry | `get(key, at_ts)` + lazy expiry → per-key record log |

## Use it as a Claude Code plugin

The repo ships a drill-authoring **skill** and a plugin manifest.

- **In-repo:** open the folder with Claude Code — `.claude/skills/authoring-drills`
  auto-activates, so `/authoring-drills sliding-window hard` works in the terminal.
- **Install elsewhere:**
  ```
  /plugin marketplace add rrrozhd/reps
  /plugin install reps@reps
  ```

## Add or author a drill

A drill is one module in `backend/drills/<slug>.py` exposing `SLUG, TITLE,
DIFFICULTY, ENTRYPOINT, MARKDOWN, STARTER, REFERENCE, LEVELS` (see
[`.claude/skills/authoring-drills/SKILL.md`](.claude/skills/authoring-drills/SKILL.md)
for the full contract). Prove it before shipping:

```bash
python3 backend/verify_drill.py <slug>   # runs your REFERENCE against your LEVELS
```

Drills are discovered from the directory — no registration needed.

## Layout

```
backend/     app.py (API) · agent.py (engine bridge) · worker.py (sandboxed runner)
             verify_drill.py · drills/*.py
frontend/    index.html · app.js · styles.css   (Monaco UI)
.claude/     skills/authoring-drills/SKILL.md    (the drill contract)
```

## Shortcuts

`⌘/Ctrl+Enter` run · `⌘/Ctrl+S` save · plus all the usual Monaco keys.

## License

MIT — see [LICENSE](LICENSE).
