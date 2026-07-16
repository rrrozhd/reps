"""FastAPI backend for the Ramp ICA practice harness.

Endpoints:
    GET  /api/drills            list drills
    GET  /api/drills/{slug}     task markdown (rendered), starter, reference
    POST /api/run               run a submission against a drill's levels
    POST /api/lint              pyflakes diagnostics for the editor gutter
Static frontend is served from ../frontend at /.
"""

import json
import os
import re
import subprocess
import sys

import markdown as md
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.normpath(os.path.join(HERE, "..", "frontend"))
WORKER = os.path.join(HERE, "worker.py")
SOLUTIONS_DIR = os.path.normpath(os.path.join(HERE, "..", ".solutions"))
RUN_TIMEOUT = 15  # seconds — kills runaway loops in a submission

sys.path.insert(0, HERE)
import drills  # noqa: E402
import agent  # noqa: E402

app = FastAPI(title="reps — interview practice harness")

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _safe_slug(slug: str) -> bool:
    return bool(_SLUG_RE.match(slug))


def _render_md(text: str) -> str:
    return md.markdown(text, extensions=["fenced_code", "tables", "sane_lists"])


@app.get("/api/drills")
def list_drills():
    out = []
    for slug in drills.list_slugs():
        d = drills.load(slug)
        out.append({
            "slug": d.SLUG,
            "title": d.TITLE,
            "difficulty": getattr(d, "DIFFICULTY", ""),
            "levels": [lv["name"] for lv in d.LEVELS],
        })
    return out


@app.get("/api/drills/{slug}")
def get_drill(slug: str):
    try:
        d = drills.load(slug)
    except KeyError:
        return JSONResponse({"error": "unknown drill"}, status_code=404)
    return {
        "slug": d.SLUG,
        "title": d.TITLE,
        "difficulty": getattr(d, "DIFFICULTY", ""),
        "entrypoint": d.ENTRYPOINT,
        "markdown_html": _render_md(d.MARKDOWN),
        "starter": d.STARTER,
        "reference": d.REFERENCE,
        "levels": [lv["name"] for lv in d.LEVELS],
        "has_state_view": hasattr(d, "render_state"),
    }


class RunBody(BaseModel):
    slug: str
    code: str


@app.post("/api/run")
def run(body: RunBody):
    try:
        d = drills.load(body.slug)  # noqa: F841  (validates slug early)
    except KeyError:
        return JSONResponse({"error": "unknown drill"}, status_code=404)

    try:
        proc = subprocess.run(
            [sys.executable, WORKER],
            input=json.dumps({"slug": body.slug, "code": body.code}),
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT,
            cwd=HERE,
        )
    except subprocess.TimeoutExpired:
        return {
            "timeout": True,
            "message": f"Time limit exceeded ({RUN_TIMEOUT}s) — likely an "
                       f"infinite loop in your solution.",
        }

    if not proc.stdout.strip():
        return {
            "error": "The runner crashed before producing output.",
            "stderr": proc.stderr[-4000:],
        }
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "error": "Could not parse runner output.",
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
        }


class LintBody(BaseModel):
    code: str


@app.post("/api/lint")
def lint(body: LintBody):
    return {"markers": _lint(body.code)}


def _lint(code: str):
    """Return a list of {line, col, message, severity} using pyflakes, with a
    compile() fallback so syntax errors always surface with a location."""
    items = []
    try:
        from pyflakes.api import check as pyflakes_check

        class _Reporter:
            def unexpectedError(self, filename, msg):
                items.append({"line": 1, "col": 1, "message": str(msg),
                              "severity": "error"})

            def syntaxError(self, filename, msg, lineno, offset, text):
                items.append({"line": lineno or 1, "col": (offset or 1),
                              "message": msg, "severity": "error"})

            def flake(self, warning):
                try:
                    message = warning.message % warning.message_args
                except Exception:  # noqa: BLE001
                    message = str(warning.message)
                items.append({
                    "line": getattr(warning, "lineno", 1),
                    "col": getattr(warning, "col", 0) + 1,
                    "message": message,
                    "severity": "warning",
                })

        pyflakes_check(code, "<solution>", _Reporter())
        return items
    except Exception:  # noqa: BLE001  — pyflakes missing: fall back to compile
        try:
            compile(code, "<solution>", "exec")
        except SyntaxError as exc:
            return [{"line": exc.lineno or 1, "col": exc.offset or 1,
                     "message": exc.msg, "severity": "error"}]
        return []


# -------------------------------------------------- durable progress (per drill)
@app.get("/api/solution/{slug}")
def load_solution(slug: str):
    if not _safe_slug(slug):
        return JSONResponse({"error": "bad slug"}, status_code=400)
    path = os.path.join(SOLUTIONS_DIR, f"{slug}.py")
    if os.path.exists(path):
        with open(path) as fh:
            return {"code": fh.read()}
    return {"code": None}


class SolutionBody(BaseModel):
    code: str


@app.put("/api/solution/{slug}")
def save_solution(slug: str, body: SolutionBody):
    if not _safe_slug(slug):
        return JSONResponse({"error": "bad slug"}, status_code=400)
    os.makedirs(SOLUTIONS_DIR, exist_ok=True)
    with open(os.path.join(SOLUTIONS_DIR, f"{slug}.py"), "w") as fh:
        fh.write(body.code)
    return {"ok": True}


# ------------------------------------------------------------------- agent bridge
@app.get("/api/agent/health")
def agent_health():
    return agent.health()


class GenerateBody(BaseModel):
    topic: str
    level: str = "medium"
    extra: str = ""
    provider: str = ""


@app.post("/api/agent/generate")
def agent_generate(body: GenerateBody):
    if not body.topic.strip():
        return JSONResponse({"error": "topic is required"}, status_code=400)
    return agent.generate_drill(body.topic.strip(), body.level.strip() or "medium",
                                body.extra.strip(), body.provider.strip() or None)


class ExplainBody(BaseModel):
    question: str
    context: str = ""
    provider: str = ""


@app.post("/api/agent/explain")
def agent_explain(body: ExplainBody):
    if not body.question.strip():
        return JSONResponse({"error": "question is required"}, status_code=400)
    return agent.explain(body.question.strip(), body.context, body.provider.strip() or None)


# Static frontend last, so /api/* wins.
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="static")
