import React, { useEffect, useState } from "react";
import * as api from "./api";

const PRESETS = {
  "explain-level":
    "Explain what this problem is testing and the state-design approach that makes the later levels easy. Don't write the full solution.",
  hint: "I'm stuck. Give me ONE progressive hint for what to do next, without revealing the full solution.",
  review:
    "Here is my code and the failing tests. Explain why it's failing and how to fix it — guide me, don't just rewrite it.",
};

const runSummary = (lastRun) => {
  if (!lastRun?.levels) return "(not run yet)";
  return lastRun.levels
    .map((l) => {
      const fails = [];
      l.tests.forEach((t) => {
        t.checks.forEach((c) => {
          if (!c.passed) fails.push(`${c.label} [exp ${c.expected} got ${c.actual}]`);
        });
        if (t.error) fails.push(`${t.name}: ${t.error}`);
      });
      return (l.ok ? "PASS " : "FAIL ") + l.name + (fails.length ? " — " + fails.slice(0, 6).join("; ") : "");
    })
    .join("\n");
};

export default function Coach({ drill, code, lastRun, onOpenProblem, refreshMenu, say }) {
  const [health, setHealth] = useState(null);
  const [provider, setProvider] = useState("");
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState("medium");
  const [ask, setAsk] = useState("");
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState([]); // newest first

  useEffect(() => {
    api
      .agentHealth()
      .then((h) => {
        setHealth(h);
        setProvider(h.active);
      })
      .catch(() => setHealth({ note: "Could not reach the agent bridge.", available: [] }));
  }, []);

  const push = (m) => setLog((l) => [m, ...l]);

  const context = () => {
    const spec = new DOMParser().parseFromString(drill.markdown_html, "text/html").body.textContent || "";
    return (
      `Problem: ${drill.title}\n\nSpec:\n${spec.trim()}\n\nMy current code:\n\`\`\`python\n${code}\n\`\`\`` +
      `\n\nLatest test results:\n${runSummary(lastRun)}`
    );
  };

  const generate = async () => {
    const t = topic.trim();
    if (!t || busy) return;
    setBusy(true);
    try {
      const res = await api.agentGenerate({ topic: t, level, provider });
      if (res.ok) {
        push({
          kind: "ok",
          head: `✓ generated · ${res.provider_name || res.provider || ""}`,
          body: `New drill ${res.slug} is verified and ready.`,
          open: res.slug,
          pre: res.verify,
        });
        setTopic("");
        refreshMenu();
      } else {
        push({
          kind: "err",
          head: `✕ failed · ${res.provider_name || res.provider || ""}`,
          body: res.error || "generation failed",
          pre: [res.verify, res.agent_output?.slice(0, 1500)].filter(Boolean).join("\n\n"),
        });
      }
    } catch (e) {
      push({ kind: "err", head: "✕ error", body: String(e) });
    } finally {
      setBusy(false);
    }
  };

  const doAsk = async (kind) => {
    const q = kind ? PRESETS[kind] : ask.trim();
    if (!q) return;
    push({ kind: "pending", head: `asking ${provider}`, body: q });
    if (!kind) setAsk("");
    try {
      const res = await api.agentExplain({ question: q, context: context(), provider });
      setLog((l) => l.filter((m) => m.kind !== "pending"));
      push(
        res.ok
          ? { kind: "ok", head: `✦ coach · ${provider}`, body: res.text || "(no answer)" }
          : { kind: "err", head: "✕ error", body: res.error || "no answer" }
      );
    } catch (e) {
      setLog((l) => l.filter((m) => m.kind !== "pending"));
      push({ kind: "err", head: "✕ error", body: String(e) });
    }
  };

  return (
    <div className="panel">
      <div className="coach-provider">
        <label htmlFor="provider-select">Engine</label>
        <select id="provider-select" value={provider} onChange={(e) => setProvider(e.target.value)}>
          {(health?.available || []).map((p) => (
            <option value={p.id} key={p.id}>
              {p.name} ({p.kind})
            </option>
          ))}
        </select>
        <span className="coach-note">{health?.note || ""}</span>
      </div>

      <div className="coach-gen">
        <div className="coach-gen-title">Generate a problem</div>
        <input
          className="coach-input"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && generate()}
          placeholder="topic — e.g. sliding-window rate limiter, LRU cache, interval merge"
        />
        <div className="coach-gen-row">
          <select value={level} onChange={(e) => setLevel(e.target.value)} title="Difficulty">
            <option value="easy">easy · ~2 levels</option>
            <option value="medium">medium · ~3 levels</option>
            <option value="hard">hard · ~4 levels</option>
          </select>
          <button className="btn primary" onClick={generate} disabled={busy}>
            {busy ? "Generating…" : "Generate"}
          </button>
        </div>
      </div>

      <div className="coach-ask">
        <div className="coach-gen-title">Ask the coach</div>
        <div className="coach-quick">
          <button className="chip-btn" onClick={() => doAsk("explain-level")}>Explain this level</button>
          <button className="chip-btn" onClick={() => doAsk("hint")}>Give me a hint</button>
          <button className="chip-btn" onClick={() => doAsk("review")}>Why is my code failing?</button>
        </div>
        <textarea
          className="coach-input"
          rows={2}
          value={ask}
          onChange={(e) => setAsk(e.target.value)}
          placeholder="ask anything about the current problem…"
        />
        <button className="btn ghost" onClick={() => doAsk(null)}>Ask</button>
      </div>

      <div className="coach-log">
        {log.map((m, i) => (
          <div className={"coach-msg " + m.kind} key={i}>
            <div className="cm-head">
              {m.kind === "pending" && <span className="spin" />}
              <span className="cm-badge">{m.head}</span>
            </div>
            <div className="cm-body">{m.body}</div>
            {m.open && (
              <div className="cm-open" onClick={() => onOpenProblem(m.open)}>
                Open {m.open} →
              </div>
            )}
            {m.pre && <pre>{m.pre}</pre>}
          </div>
        ))}
      </div>
    </div>
  );
}
