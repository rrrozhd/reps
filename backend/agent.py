"""Agent bridge — lets the web frontend drive *any* coding agent or LLM to author
drills and explain concepts, without the user touching a terminal.

Provider-agnostic. Two families, auto-detected:

  Local CLI agents (preferred — use the user's existing login, no API key):
      claude · gemini · codex · cursor-agent · opencode
  API backends (by env key):
      anthropic (native)  ·  openai-compatible (OpenAI / OpenRouter / Groq /
      Together / local Ollama|LM Studio via OPENAI_BASE_URL)
  mock — deterministic, no LLM; writes a valid template drill so the whole
      generate→verify→appear loop is testable offline.

Precedence: REPS_PROVIDER override → first CLI on PATH → first API key present →
mock. Per-request `provider` can override too. Whatever engine writes a drill,
the harness re-runs verify_drill.py itself, so correctness never depends on the
agent parsing its own output.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
DRILLS_DIR = os.path.join(HERE, "drills")
SKILL_PATH = os.path.join(REPO, ".claude", "skills", "authoring-drills", "SKILL.md")
VERIFY = os.path.join(HERE, "verify_drill.py")
CLI_TIMEOUT = int(os.environ.get("REPS_CLI_TIMEOUT", "300"))

# Env vars injected when running INSIDE a Claude Code session that would make a
# nested agent CLI hit the wrong endpoint / fail auth. Stripped for children so
# they use the user's normal login. No-ops in a plain user shell.
_STRIP_ENV = [
    "ANTHROPIC_BASE_URL", "CLAUDECODE", "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_OAUTH_SCOPES",
    "USE_LOCAL_OAUTH", "USE_STAGING_OAUTH", "CLAUDE_AGENT_SDK_VERSION",
    "CLAUDE_CODE_SDK_HAS_OAUTH_REFRESH", "CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH",
    "AI_AGENT",
]


# ============================================================= CLI agent registry
def _claude_argv(prompt, read_only):
    tools = ["Read", "Grep", "Glob", "Bash"] + ([] if read_only else ["Write", "Edit"])
    return ["claude", "-p", prompt,
            "--permission-mode", "default" if read_only else "acceptEdits",
            "--allowedTools", *tools, "--add-dir", REPO,
            "--output-format", "json"]


def _gemini_argv(prompt, read_only):
    return ["gemini", "-p", prompt] + ([] if read_only else ["--yolo"])


def _codex_argv(prompt, read_only):
    return ["codex", "exec"] + ([] if read_only else ["--full-auto"]) + [prompt]


def _cursor_argv(prompt, read_only):
    return ["cursor-agent", "-p", prompt, "--output-format", "text"] + \
           ([] if read_only else ["--force"])


def _opencode_argv(prompt, read_only):
    return ["opencode", "run", prompt]


# order = detection preference
CLI_AGENTS = {
    "claude": {"name": "Claude Code", "bin": "claude", "build": _claude_argv, "output": "json"},
    "gemini": {"name": "Gemini CLI", "bin": "gemini", "build": _gemini_argv, "output": "text"},
    "codex": {"name": "OpenAI Codex CLI", "bin": "codex", "build": _codex_argv, "output": "text"},
    "cursor-agent": {"name": "Cursor CLI", "bin": "cursor-agent", "build": _cursor_argv, "output": "text"},
    "opencode": {"name": "opencode", "bin": "opencode", "build": _opencode_argv, "output": "text"},
}


# ============================================================= provider detection
def detect_clis():
    return [aid for aid, spec in CLI_AGENTS.items() if shutil.which(spec["bin"])]


def _openai_conf():
    """(base_url, api_key, default_model, display) for the first configured
    OpenAI-compatible backend, or None."""
    m = os.environ.get("REPS_MODEL")
    if os.environ.get("OPENROUTER_API_KEY"):
        return ("https://openrouter.ai/api/v1", os.environ["OPENROUTER_API_KEY"],
                m or "anthropic/claude-3.5-sonnet", "OpenRouter")
    if os.environ.get("GROQ_API_KEY"):
        return ("https://api.groq.com/openai/v1", os.environ["GROQ_API_KEY"],
                m or "llama-3.3-70b-versatile", "Groq")
    if os.environ.get("OPENAI_API_KEY"):
        return (os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                os.environ["OPENAI_API_KEY"], m or "gpt-4o",
                "OpenAI-compatible" if os.environ.get("OPENAI_BASE_URL") else "OpenAI")
    return None


def detect_apis():
    apis = []
    if os.environ.get("ANTHROPIC_API_KEY"):
        apis.append("anthropic")
    if _openai_conf():
        apis.append("openai-compatible")
    return apis


def _display(pid):
    if pid in CLI_AGENTS:
        return CLI_AGENTS[pid]["name"]
    if pid == "anthropic":
        return "Anthropic API"
    if pid == "openai-compatible":
        conf = _openai_conf()
        return conf[3] if conf else "OpenAI-compatible"
    return "Offline sample generator"


def available():
    out = [{"id": a, "kind": "cli", "name": CLI_AGENTS[a]["name"]} for a in detect_clis()]
    out += [{"id": a, "kind": "api", "name": _display(a)} for a in detect_apis()]
    out.append({"id": "mock", "kind": "mock", "name": "Offline sample generator"})
    return out


def active_provider(override=None):
    pid = override or os.environ.get("REPS_PROVIDER")
    ids = {p["id"] for p in available()}
    if pid and pid in ids:
        return pid
    clis, apis = detect_clis(), detect_apis()
    if clis:
        return clis[0]
    if apis:
        return apis[0]
    return "mock"


def health():
    active = active_provider()
    notes = {
        "cli": "Runs your local agent CLI with your existing login (no API key). "
               "If generation errors on auth, run that CLI once in a terminal to log in.",
        "api": "Uses an API key from your environment.",
        "mock": "No agent CLI and no API key detected — using the offline sample "
                "generator. Install a coding-agent CLI or set an API key for real problems.",
    }
    kind = ("cli" if active in CLI_AGENTS else
            "api" if active in ("anthropic", "openai-compatible") else "mock")
    return {"active": active, "active_name": _display(active),
            "available": available(), "note": notes[kind]}


def _child_env():
    env = dict(os.environ)
    for k in _STRIP_ENV:
        env.pop(k, None)
    return env


# ================================================================== slug + verify
def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "drill"


def unique_slug(base):
    import drills
    existing = set(drills.list_slugs())
    if base not in existing:
        return base
    i = 2
    while f"{base}-{i}" in existing:
        i += 1
    return f"{base}-{i}"


def verify_slug(slug):
    proc = subprocess.run([sys.executable, VERIFY, slug],
                          capture_output=True, text=True, cwd=HERE, timeout=120)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


# ===================================================================== public API
def generate_drill(topic, level="medium", extra="", provider=None):
    pid = active_provider(provider)
    slug = unique_slug(slugify(topic))
    if pid == "mock":
        return _generate_mock(slug, topic, level)
    if pid in CLI_AGENTS:
        return _generate_cli(pid, slug, topic, level, extra)
    return _generate_api(pid, slug, topic, level, extra)


def explain(question, context="", provider=None):
    pid = active_provider(provider)
    prompt = (context + "\n\n" if context else "") + question
    system = ("You are a rigorous, concise coding-interview coach. Explain clearly "
              "with short examples. Don't dump a full solution unless asked.")
    if pid == "mock":
        return {"ok": True, "provider": pid,
                "text": "(offline) Install an agent CLI or set an API key for real "
                        "explanations. You asked:\n\n" + question}
    if pid in CLI_AGENTS:
        r = _run_cli(pid, "You are a coding-interview coach. " + prompt, read_only=True)
        return {"ok": r["ok"], "provider": pid, "text": r.get("text", ""), "error": r.get("error")}
    r = _api_text(pid, system, prompt)
    return {"ok": r["ok"], "provider": pid, "text": r.get("text", ""), "error": r.get("error")}


# ================================================================= CLI generation
def _generate_cli(pid, slug, topic, level, extra):
    prompt = (
        f"You are in the `reps` interview-practice repo. Read the drill-authoring "
        f"contract at {SKILL_PATH} and follow it EXACTLY.\n\n"
        f"Create ONE new drill: topic = \"{topic}\", difficulty = \"{level}\".\n"
        f"{('Extra requirements: ' + extra) if extra else ''}\n"
        f"Write it to backend/drills/{slug}.py with SLUG = \"{slug}\". Then run\n"
        f"    python3 backend/verify_drill.py {slug}\n"
        f"and iterate until it prints that ALL checks passed. Do not stop until "
        f"verification is green. Reply with just: {slug}")
    r = _run_cli(pid, prompt, read_only=False)
    exists = os.path.exists(os.path.join(DRILLS_DIR, f"{slug}.py"))
    ok, vout = verify_slug(slug) if exists else (False, "the agent did not create the drill file")
    return {"ok": ok, "slug": slug, "provider": pid, "provider_name": _display(pid),
            "agent_output": r.get("text", ""), "verify": vout,
            "error": None if ok else (r.get("error") or "the generated drill did not pass verification")}


def _run_cli(pid, prompt, read_only):
    spec = CLI_AGENTS[pid]
    argv = spec["build"](prompt, read_only)
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, cwd=REPO,
                              env=_child_env(), timeout=CLI_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"ok": False, "text": "", "error": f"{spec['name']} timed out after {CLI_TIMEOUT}s."}
    except FileNotFoundError:
        return {"ok": False, "text": "", "error": f"{spec['bin']} not found on PATH."}
    if spec.get("output") == "json":
        try:
            data = json.loads(proc.stdout)
            return {"ok": not data.get("is_error"), "text": data.get("result", ""),
                    "error": data.get("result") if data.get("is_error") else None}
        except (json.JSONDecodeError, ValueError):
            pass
    text = (proc.stdout or "").strip()
    return {"ok": proc.returncode == 0, "text": text,
            "error": None if proc.returncode == 0 else (proc.stderr or proc.stdout or "")[-2000:]}


# ================================================================= API generation
def _generate_api(pid, slug, topic, level, extra):
    contract = _read(SKILL_PATH)
    system = ("You author Python drill modules for an interview-practice harness. "
              "Follow this contract exactly and output ONLY raw Python module source "
              "for one drill — no markdown fences, no prose:\n\n" + contract)
    base_user = (f"Create a drill module. topic=\"{topic}\", difficulty=\"{level}\", "
                 f"SLUG must be \"{slug}\". {('Extra: ' + extra) if extra else ''}")
    last = ""
    for attempt in range(2):
        user = base_user if attempt == 0 else (
            base_user + f"\n\nYour previous module failed verification:\n{last}\n"
            "Return a corrected COMPLETE module.")
        r = _api_text(pid, system, user)
        if not r["ok"]:
            return {"ok": False, "slug": slug, "provider": pid,
                    "provider_name": _display(pid), "error": r.get("error"), "verify": ""}
        with open(os.path.join(DRILLS_DIR, f"{slug}.py"), "w") as fh:
            fh.write(_strip_fences(r["text"]))
        ok, vout = verify_slug(slug)
        if ok:
            return {"ok": True, "slug": slug, "provider": pid,
                    "provider_name": _display(pid), "verify": vout}
        last = vout
    return {"ok": False, "slug": slug, "provider": pid, "provider_name": _display(pid),
            "error": "generated drill failed verification twice", "verify": last}


def _api_text(pid, system, user):
    if pid == "anthropic":
        return _anthropic_text(system, user)
    if pid == "openai-compatible":
        conf = _openai_conf()
        if not conf:
            return {"ok": False, "error": "no OpenAI-compatible API key set", "text": ""}
        return _openai_text(system, user, conf)
    return {"ok": False, "error": f"unknown API provider '{pid}'", "text": ""}


def _anthropic_text(system, user):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {"ok": False, "error": "ANTHROPIC_API_KEY not set", "text": ""}
    model = os.environ.get("REPS_MODEL", "claude-sonnet-5")
    body = json.dumps({"model": model, "max_tokens": 8000, "system": system,
                       "messages": [{"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        return {"ok": True, "text": "".join(b.get("text", "") for b in data.get("content", [])),
                "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Anthropic API error: {exc}", "text": ""}


def _openai_text(system, user, conf):
    base, key, model, _name = conf
    body = json.dumps({"model": model, "max_tokens": 8000,
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={"authorization": f"Bearer {key}", "content-type": "application/json",
                 "http-referer": "https://github.com/reps", "x-title": "reps"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        return {"ok": True, "text": data["choices"][0]["message"]["content"], "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"API error ({base}): {exc}", "text": ""}


# ======================================================================= mock/util
def _generate_mock(slug, topic, level):
    code = _MOCK_TEMPLATE.format(slug=slug, topic=_pyq(topic), level=_pyq(level),
                                 title=_pyq(f"{topic} (sample)"))
    with open(os.path.join(DRILLS_DIR, f"{slug}.py"), "w") as fh:
        fh.write(code)
    ok, vout = verify_slug(slug)
    return {"ok": ok, "slug": slug, "provider": "mock", "provider_name": "Offline sample",
            "verify": vout, "error": None if ok else "mock drill failed verification (bug)",
            "agent_output": "Generated an offline sample drill (tally/ranking). Install an "
                            "agent CLI or set an API key for real, topic-specific problems."}


def _read(path):
    try:
        with open(path) as fh:
            return fh.read()
    except OSError:
        return "(contract file missing)"


def _pyq(s):
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def _strip_fences(text):
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n", "", t)
        t = re.sub(r"\n```$", "", t)
    return t


_MOCK_TEMPLATE = '''\
"""Auto-generated sample drill (mock provider). Topic: {topic}."""

SLUG = "{slug}"
TITLE = "{title}"
DIFFICULTY = "sample · {level} · 2 levels"
ENTRYPOINT = "Tally"

MARKDOWN = """
# {title}

A placeholder drill generated offline (no LLM available). It still exercises the
full harness. Install a coding-agent CLI or set an API key, then ask the coach
for a real **{topic}** problem.

## Level 1 — Count

- **`add(key) -> int`** — record one occurrence of `key`; return its new count.
- **`count(key) -> int`** — current count for `key` (0 if unseen).

## Level 2 — Rank

- **`top(n) -> list[str]`** — the `n` keys with the highest counts, formatted
  `"key(count)"`, ties broken by `key` ascending.
"""

STARTER = """\\
class Tally:
    def __init__(self):
        pass

    def add(self, key):
        pass

    def count(self, key):
        pass

    def top(self, n):
        pass
"""

REFERENCE = """\\
class Tally:
    def __init__(self):
        self.counts = {{}}

    def add(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def count(self, key):
        return self.counts.get(key, 0)

    def top(self, n):
        ranked = sorted(self.counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [f"{{k}}({{c}})" for k, c in ranked[:n]]
"""


def l1_count(C):
    t = C()
    return [
        ("add a -> 1", 1, t.add("a")),
        ("add a -> 2", 2, t.add("a")),
        ("add b -> 1", 1, t.add("b")),
        ("count a -> 2", 2, t.count("a")),
        ("count unseen -> 0", 0, t.count("z")),
    ]


def l2_rank(C):
    t = C()
    for k in ["a", "a", "a", "b", "b", "c"]:
        t.add(k)
    return [
        ("top 2 -> [a(3), b(2)]", ["a(3)", "b(2)"], t.top(2)),
        ("top 5 (all, tie by key)", ["a(3)", "b(2)", "c(1)"], t.top(5)),
    ]


LEVELS = [
    {{"name": "Level 1 — Count", "tests": [l1_count]}},
    {{"name": "Level 2 — Rank", "tests": [l2_rank]}},
]
'''
