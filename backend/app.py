"""FastAPI backend for the reps interview-practice harness.

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


def _blurb(d):
    """A short one-paragraph description for the menu: an explicit BLURB if the
    drill defines one, else the first real paragraph of its MARKDOWN."""
    b = getattr(d, "BLURB", None)
    if b:
        return b.strip()
    para = []
    for line in d.MARKDOWN.strip().splitlines():
        s = line.strip()
        if s.startswith("#") or s.startswith("---") or s.startswith(">"):
            if para:
                break
            continue
        if not s:
            if para:
                break
            continue
        para.append(s)
    text = " ".join(para).replace("**", "").replace("`", "")
    return (text[:200] + "…") if len(text) > 200 else text


@app.get("/api/drills")
def list_drills():
    out = []
    for slug in drills.list_slugs():
        d = drills.load(slug)
        out.append({
            "slug": d.SLUG,
            "title": d.TITLE,
            "kind": getattr(d, "KIND", "drill"),
            "topic": getattr(d, "TOPIC", ""),
            "difficulty": getattr(d, "DIFFICULTY", ""),
            "blurb": _blurb(d),
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


class TestBody(BaseModel):
    provider: str = ""


@app.post("/api/agent/test")
def agent_test(body: TestBody):
    return agent.test_provider(body.provider.strip() or None)


class LoginBody(BaseModel):
    provider: str = "claude"
    code: str = ""


@app.get("/api/agent/login/status")
def login_status(provider: str = "claude"):
    return agent.cli_login_status(provider)


@app.post("/api/agent/login/start")
def login_start(body: LoginBody):
    return agent.cli_login_start(body.provider or "claude")


@app.get("/api/agent/login/poll")
def login_poll(provider: str = "claude"):
    return agent.cli_login_poll(provider)


@app.post("/api/agent/login/code")
def login_code(body: LoginBody):
    return agent.cli_login_code(body.provider or "claude", body.code)


@app.post("/api/agent/login/logout")
def login_logout(body: LoginBody):
    return agent.cli_logout(body.provider or "claude")


@app.get("/api/config")
def get_config():
    cfg = agent.load_config()
    ep = cfg.get("endpoint") or {}
    # never echo the stored key back to the browser
    return {
        "provider": cfg.get("provider", ""),
        "endpoint": {
            "base_url": ep.get("base_url", ""),
            "model": ep.get("model", ""),
            "name": ep.get("name", ""),
            "has_key": bool(ep.get("api_key")),
        },
    }


class ConfigBody(BaseModel):
    provider: str | None = None
    base_url: str | None = None
    model: str | None = None
    name: str | None = None
    api_key: str | None = None


@app.put("/api/config")
def put_config(body: ConfigBody):
    cfg = agent.load_config()
    if body.provider is not None:
        cfg["provider"] = body.provider
    if any(v is not None for v in (body.base_url, body.model, body.name, body.api_key)):
        ep = cfg.get("endpoint") or {}
        if body.base_url is not None:
            ep["base_url"] = body.base_url.strip()
        if body.model is not None:
            ep["model"] = body.model.strip()
        if body.name is not None:
            ep["name"] = body.name.strip()
        if body.api_key:  # only overwrite when a non-empty key is provided
            ep["api_key"] = body.api_key
        cfg["endpoint"] = ep
    agent.save_config(cfg)
    return {"ok": True}


# Static frontend last, so /api/* wins.
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="static")
