import React, { useEffect, useState } from "react";

const pretty = (name) => name.replace(/^l\d+_/, "").replace(/_/g, " ");

function Check({ c }) {
  return (
    <div className={"check " + (c.passed ? "pass" : "fail")}>
      <span className="cm">{c.passed ? "✓" : "✕"}</span>
      <span>
        <span className="check-label">{c.label}</span>
        {!c.passed && (
          <div className="check-diff">
            <span className="exp">expected {c.expected}</span> ·{" "}
            <span className="act">got {c.actual}</span>
          </div>
        )}
      </span>
    </div>
  );
}

function Test({ t }) {
  return (
    <div className={"test " + (t.ok ? "pass" : "fail")}>
      <div className="test-head">
        <span className="test-mark">{t.ok ? "✓" : "✕"}</span>
        <span className="test-name">{pretty(t.name)}</span>
      </div>
      {t.error && <div className="test-error">{t.error + (t.traceback ? "\n\n" + t.traceback : "")}</div>}
      {/* On failure show every check for context; passing tests stay collapsed. */}
      {!t.ok && t.checks.length > 0 && (
        <div className="checks">
          {t.checks.map((c, i) => (
            <Check c={c} key={i} />
          ))}
        </div>
      )}
    </div>
  );
}

function Level({ lv, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen);
  useEffect(() => setOpen(defaultOpen), [defaultOpen]);
  const passed = lv.tests.filter((t) => t.ok).length;
  return (
    <div className={"level " + (lv.ok ? "pass" : "fail") + (open ? " open" : "")}>
      <div className="level-head" onClick={() => setOpen((o) => !o)}>
        <span className="chevron">▶</span>
        <span className="level-dot" />
        <span className="level-name">{lv.name}</span>
        <span className="level-count">
          {passed}/{lv.tests.length}
        </span>
      </div>
      <div className="level-body">
        {lv.tests.map((t, i) => (
          <Test t={t} key={i} />
        ))}
      </div>
    </div>
  );
}

function Banner({ children }) {
  return <div className="run-banner err">{children}</div>;
}

function Output({ text }) {
  return (
    <div className="run-banner output">
      <div className="output-head">stdout — your print() output</div>
      <pre>{text}</pre>
    </div>
  );
}

export default function Results({ data, running }) {
  if (running && !data) {
    return (
      <div className="panel">
        <div className="empty">
          <span className="spin" /> running…
        </div>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="panel">
        <div className="empty">
          <p>
            Read all levels first. Design your state object. Then <strong>Run</strong> (<kbd>⌘↵</kbd>)
            to test each level.
          </p>
        </div>
      </div>
    );
  }

  if (data.error || data.stderr) {
    return (
      <div className="panel">
        <Banner>
          <strong>Runner error.</strong> {data.error || ""}
          {data.stderr && <pre>{data.stderr}</pre>}
          {data.stdout && <pre>{data.stdout}</pre>}
        </Banner>
      </div>
    );
  }
  if (data.timeout) {
    return (
      <div className="panel">
        <Banner>
          <strong>Time limit exceeded.</strong> {data.message}
        </Banner>
      </div>
    );
  }
  if (data.loadError) {
    return (
      <div className="panel">
        <Banner>
          <strong>Your code didn't load.</strong>
          <pre>{data.loadError + (data.traceback ? "\n\n" + data.traceback : "")}</pre>
        </Banner>
        {data.output && <Output text={data.output} />}
      </div>
    );
  }
  if (!Array.isArray(data.levels)) {
    return (
      <div className="panel">
        <Banner>
          <strong>Unexpected response.</strong>
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </Banner>
      </div>
    );
  }

  const levels = data.levels;
  const passedLevels = levels.filter((l) => l.ok).length;
  let total = 0,
    passed = 0;
  levels.forEach((l) =>
    l.tests.forEach((t) =>
      t.checks.forEach((c) => {
        total++;
        if (c.passed) passed++;
      })
    )
  );
  const firstFail = levels.findIndex((l) => !l.ok);

  return (
    <div className="panel">
      <div className="score-summary">
        <span className={"score-chip " + (passedLevels === levels.length ? "good" : passedLevels ? "" : "bad")}>
          {passedLevels} / {levels.length} levels
        </span>
        <span className={"score-chip " + (passed === total ? "good" : "bad")}>
          {passed} / {total} checks
        </span>
      </div>
      {levels.map((lv, i) => (
        <Level key={lv.name} lv={lv} defaultOpen={i === firstFail || (firstFail === -1 && i === levels.length - 1)} />
      ))}
      {data.output && <Output text={data.output} />}
    </div>
  );
}

/** The File System drill renders the tree its demo script builds. */
function Node({ name, node }) {
  if (node.__file__) {
    return (
      <li>
        <div className="fs-row">
          <span className="fs-file">◦ {name}</span>
          <span className="fs-size">{node.size == null ? "?" : node.size + " b"}</span>
        </div>
      </li>
    );
  }
  return (
    <li>
      <div className="fs-row">
        <span className="fs-dir">▸ {name}/</span>
      </div>
      <Children children={node.children} />
    </li>
  );
}

function Children({ children }) {
  const names = Object.keys(children || {}).sort();
  return (
    <ul>
      {names.map((n) => (
        <Node key={n} name={n} node={children[n]} />
      ))}
    </ul>
  );
}

export function FsTree({ state }) {
  if (!state) {
    return (
      <div className="panel">
        <div className="empty">
          <p>Run your code to render the filesystem it builds.</p>
        </div>
      </div>
    );
  }
  if (state.error) {
    return (
      <div className="panel">
        <Banner>
          <strong>Filesystem demo failed.</strong> {state.error}
        </Banner>
      </div>
    );
  }
  return (
    <div className="panel">
      <div className="fs-tree">
        <ul>
          <li>
            <div className="fs-row">
              <span className="fs-dir">▸ /</span>
            </div>
          </li>
        </ul>
        <Children children={state.tree || {}} />
      </div>
      {state.demo?.length > 0 && (
        <div className="fs-demo">
          <h4>Demo script (run on your code)</h4>
          <pre>{state.demo.join("\n")}</pre>
        </div>
      )}
    </div>
  );
}
