<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/reps-mark-dark.svg">
    <img src="assets/reps-mark.svg" alt="reps" width="170">
  </picture>
</p>

<h1 align="center">reps</h1>

<p align="center">
  <strong>Coding-interview practice with a real editor, a verifying runner, and an
  agent coach that generates and explains problems — all from the browser.</strong>
</p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="#the-coach-generate--explain-from-the-ui">The Coach</a> ·
  <a href="#the-problem-library">Problems</a> ·
  <a href="LICENSE">MIT</a>
</p>

---

reps is a local, CodeSignal-style harness for **progressive** coding problems
(one problem, several levels, each bolting a new requirement onto the same
growing system — the format CodeSignal ICAs use). You solve in a real
Monaco editor; a sandboxed runner tests each level. When you want a new problem,
you ask the built-in **Coach**, which drives *your* coding agent (or an API
model) to write a fresh drill — spec, starter, reference, and tests — and only
ships it once it passes its own verification.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/rrrozhd/reps/main/install.sh | bash
reps
```

That installs a global **`reps`** command (app lives in `~/.reps`, linked onto
your PATH — no directories to manage). First run walks you through the coach
engine — sign in to a CLI agent (`claude auth login`, native), point at a local
model (vLLM / Ollama), or paste an API key — then opens http://127.0.0.1:8777.

- **`reps`** — start (runs first-time setup automatically)
- **`reps setup`** — pick / switch engines, sign in
- **`reps status`** — show the active engine

Reconfigure later from the terminal (`reps setup`) or the in-app **⚙ Settings**.

**From source instead:**

```bash
git clone https://github.com/rrrozhd/reps && cd reps && ./reps
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

## The problem library

**17 problems ship with it**, all verified (`verify_drill.py` runs each reference
against its own tests).

**9 progressive drills** — one growing system, 4 levels, the last level punishes a
naive data model:

| Drill | The twist that forces good state design |
|-------|-----------------------------------------|
| **Banking System** | historical `get_balance` + `merge` → balance is a checkpoint log |
| **In-Memory File System** | `get_file_size(path, at_version)` → per-file write log |
| **Key-Value Store w/ TTL** | `get(key, at_ts)` + lazy expiry → per-key record log |
| **LRU Cache with TTL** | eviction + TTL + an as-of read |
| **Sliding-Window Rate Limiter** | timestamp log + bisect, not a deque you pop |
| **In-Memory DB with Transactions** | nested `begin` / `commit` / `rollback` |
| **Lazy Job Scheduler** | jobs fire lazily on the next op, not on a timer |
| **Versioned Object Store** | versions + `restore` + as-of read |
| **Inventory w/ Expiring Reservations** | holds expire lazily; historical availability |

**8 algorithms** — single function, tested in example / edge / scale groups:
`two-sum` (hashmap, easy) · `valid-parentheses` (stack, easy) · `merge-intervals`
(medium) · `search-rotated` (binary search, medium) · `longest-substring`
(sliding window, medium) · `num-islands` (graphs, medium) · `coin-change` (DP,
medium) · `trapping-rain-water` (two-pointers, hard).

Ask the Coach for more, on any topic or difficulty.

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
