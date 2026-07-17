#!/usr/bin/env python3
"""reps setup — a first-run terminal wizard to configure the coach engine.

A real terminal has a TTY, so this is the reliable place to sign a CLI agent in
(`claude auth login`) or point at a local/hosted model. It writes
`.reps-config.json`, which the web app then uses. Stdlib only.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import agent  # noqa: E402  (stdlib-only imports)

Y = "\033[1;33m"; G = "\033[1;32m"; DIM = "\033[2m"; R = "\033[0m"

PRESETS = {
    "openai":     ("https://api.openai.com/v1", "gpt-4o", True),
    "openrouter": ("https://openrouter.ai/api/v1", "anthropic/claude-3.5-sonnet", True),
    "groq":       ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", True),
    "vllm":       ("http://localhost:8000/v1", "", False),
    "custom":     ("", "", False),
}


def ask(prompt, default=""):
    s = input(f"{prompt}{(' [' + default + ']') if default else ''}: ").strip()
    return s or default


def choose(title, options):
    print(f"\n{Y}{title}{R}")
    for i, (label, _v) in enumerate(options, 1):
        print(f"  {i}) {label}")
    while True:
        c = input("> ").strip()
        if c.isdigit() and 1 <= int(c) <= len(options):
            return options[int(c) - 1][1]
        print("  pick a number")


def setup():
    print(f"{Y}reps setup{R}  {DIM}— configure the coach engine{R}\n")

    opts = []
    for c in agent.detect_clis():
        opts.append((f"{agent.CLI_AGENTS[c]['name']}  {DIM}(local CLI, its own login){R}", ("cli", c)))
    opts.append(("Hosted API or local model  (OpenAI / OpenRouter / Groq / vLLM / Ollama)", ("api", None)))
    opts.append((f"Offline sample generator  {DIM}(no model){R}", ("mock", None)))
    kind, pid = choose("Which engine should the coach use?", opts)

    cfg = agent.load_config()
    if kind == "cli":
        cfg["provider"] = pid
        agent.save_config(cfg)
        if pid == "claude":
            _ensure_claude_login()
        print(f"\n{G}✓ Engine set to {agent.CLI_AGENTS[pid]['name']}.{R}")
    elif kind == "mock":
        cfg["provider"] = "mock"
        agent.save_config(cfg)
        print(f"\n{G}✓ Using the offline sample generator.{R}")
    else:
        which = choose("Which one?", [
            ("OpenAI", "openai"),
            ("OpenRouter  (one key, many models incl. Claude)", "openrouter"),
            ("Groq", "groq"),
            ("vLLM / local OpenAI-compatible server", "vllm"),
            ("Ollama / LM Studio / other custom URL", "custom"),
        ])
        base, model_default, key_required = PRESETS[which]
        base = ask("Base URL", base)
        model = ask("Model", model_default)
        if key_required:
            key = ask("API key (stored locally in .reps-config.json)")
        else:
            key = ask("API key (optional — leave blank for vLLM/Ollama)")
        cfg["provider"] = "custom"
        cfg["endpoint"] = {"base_url": base, "model": model, "name": which,
                           "api_key": key or "none"}
        agent.save_config(cfg)
        print(f"\n{G}✓ Configured {which} at {base}.{R}")

    print(f"\n{DIM}Testing the engine…{R}")
    res = agent.test_provider()
    print((f"{G}✓ " if res.get("ok") else "✕ ") + (res.get("message") or "") + R)

    print(f"\n{DIM}Saved to {agent.CONFIG_PATH}{R}")
    print(f"\nStart practicing:  {Y}./reps{R}   {DIM}→ http://127.0.0.1:8777{R}")
    print(f"Reconfigure any time:  {Y}./reps setup{R}   (or the in-app ⚙ Settings)")


def _ensure_claude_login():
    st = agent.cli_login_status("claude")
    if st.get("loggedIn"):
        print(f"{G}Already signed in as {st.get('email', '?')}.{R}")
        return
    if input("Not signed in. Sign in to Claude now? [Y/n] ").strip().lower() in ("", "y", "yes"):
        print(f"{DIM}Opening Claude sign-in (a browser window)…{R}")
        subprocess.run(["claude", "auth", "login", "--claudeai"])  # native interactive TTY


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "setup"
    if cmd == "setup":
        try:
            setup()
        except (KeyboardInterrupt, EOFError):
            print("\ncancelled.")
            sys.exit(1)
    elif cmd == "status":
        print(json.dumps(agent.health(), indent=2))
    else:
        print("usage: reps_cli.py [setup|status]")
        sys.exit(1)
