"""Runs a user's submission against a drill's levels in an isolated process.

Reads ``{"slug": ..., "code": ...}`` as JSON on stdin, prints a JSON result on
stdout. The parent process (``app.py``) enforces a wall-clock timeout so a
runaway loop in the submission can't hang the server.
"""

import importlib
import io
import json
import os
import sys
import traceback
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harness import matches, show  # noqa: E402


def run_test(tf, cls):
    name = getattr(tf, "__name__", "test")
    doc = (tf.__doc__ or "").strip()
    try:
        checks = tf(cls)
    except Exception as exc:  # noqa: BLE001
        return {
            "name": name,
            "doc": doc,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "checks": [],
        }
    out = []
    ok = True
    for item in checks:
        # Guard per-check: a submission whose return value has a raising
        # __eq__/__repr__ fails that one check instead of crashing the worker.
        try:
            label, expected, actual = item
            passed = matches(expected, actual)
            check = {"label": label, "expected": show(expected),
                     "actual": show(actual), "passed": passed}
        except Exception as exc:  # noqa: BLE001
            passed = False
            check = {"label": "check could not be evaluated", "expected": "<n/a>",
                     "actual": f"{type(exc).__name__}: {exc}", "passed": False}
        ok = ok and passed
        out.append(check)
    return {"name": name, "doc": doc, "ok": ok, "checks": out}


def build_result(payload):
    slug = payload["slug"]
    code = payload["code"]

    try:
        drill = importlib.import_module(f"drills.{slug}")
    except Exception as exc:  # noqa: BLE001
        return {"error": f"unknown drill '{slug}': {exc}"}

    namespace = {}
    try:
        exec(compile(code, "<solution>", "exec"), namespace)
    except Exception as exc:  # noqa: BLE001
        return {"loadError": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc()}

    # Entry point is a class (progressive drills) or a function (algorithms).
    entry = namespace.get(drill.ENTRYPOINT)
    if not callable(entry):
        return {"loadError": f"Your code must define `{drill.ENTRYPOINT}` "
                             f"(a {'function' if getattr(drill, 'KIND', 'drill') == 'algo' else 'class'})."}

    levels = []
    try:
        for level in drill.LEVELS:
            tests = [run_test(tf, entry) for tf in level["tests"]]
            levels.append({
                "name": level["name"],
                "ok": all(t["ok"] for t in tests),
                "tests": tests,
            })
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Runner crashed while executing tests: "
                         f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc()}

    result = {"levels": levels}
    if hasattr(drill, "render_state"):
        try:
            result["state"] = drill.render_state(entry)
        except Exception as exc:  # noqa: BLE001
            result["state"] = {"error": str(exc)}
    return result


def main():
    payload = json.load(sys.stdin)
    # Run everything (exec + tests + render_state) with the submission's stdout
    # redirected into a buffer, so a stray print() in the solution can't corrupt
    # the JSON result channel. Captured output is surfaced back to the UI.
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            result = build_result(payload)
    except Exception as exc:  # noqa: BLE001
        result = {"error": f"{type(exc).__name__}: {exc}",
                  "traceback": traceback.format_exc()}

    captured = buf.getvalue()
    if captured.strip():
        result["output"] = captured[-8000:]

    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
