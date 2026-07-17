import React, { useMemo, useState } from "react";

const shortLevel = (name) => name.replace(/^Level\s*\d+\s*[—-]\s*/, "");
const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);
// Short topics are acronyms ("dp", "bfs") — show them uppercased; longer,
// hyphenated ones ("sliding-window") become spaced words (CSS title-cases them).
const prettyTopic = (t) => {
  if (!t) return "";
  return t.length <= 3 ? t.toUpperCase() : t.replace(/-/g, " ");
};

const FILTERS = [
  ["all", "All"],
  ["drill", "Progressive drills"],
  ["algo", "Algorithms"],
];

// Layered-stack glyph — a progressive drill is built level on level.
const IconDrill = (props) => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
       strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <path d="M12 3 3 7.5 12 12l9-4.5L12 3Z" />
    <path d="M3 12l9 4.5 9-4.5" />
    <path d="M3 16.5 12 21l9-4.5" />
  </svg>
);

// Braces glyph — a self-contained algorithm.
const IconAlgo = (props) => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
       strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <path d="M8 4H7a3 3 0 0 0-3 3v2a2 2 0 0 1-2 2 2 2 0 0 1 2 2v2a3 3 0 0 0 3 3h1" />
    <path d="M16 4h1a3 3 0 0 1 3 3v2a2 2 0 0 0 2 2 2 2 0 0 0-2 2v2a3 3 0 0 1-3 3h-1" />
  </svg>
);

function ProblemCard({ d, onOpen }) {
  const isAlgo = (d.kind || "drill") === "algo";
  const levels = d.levels || [];
  const diff = (d.difficulty || "").toLowerCase();
  return (
    <button
      className={"problem-card " + (isAlgo ? "is-algo" : "is-drill")}
      onClick={() => onOpen(d.slug)}
    >
      <div className="pc-head">
        <span className="pc-kind">
          <span className="pc-icon" aria-hidden="true">{isAlgo ? <IconAlgo /> : <IconDrill />}</span>
          <span className="pc-kind-label">{isAlgo ? "Algorithm" : "Progressive drill"}</span>
        </span>
        {isAlgo ? (
          <span className={"pc-badge diff-" + diff}>{cap(d.difficulty)}</span>
        ) : (
          <span className="pc-badge levels">
            {levels.length} level{levels.length === 1 ? "" : "s"}
          </span>
        )}
      </div>

      <h3 className="pc-title">{d.title}</h3>
      <p className="pc-blurb">{d.blurb || ""}</p>

      {!isAlgo && levels.length > 0 && (
        <div className="pc-levels">
          {levels.map((n, i) => (
            <span className="pc-lvl" key={i}>{shortLevel(n)}</span>
          ))}
        </div>
      )}

      <div className="pc-foot">
        <span className="pc-foot-meta">{isAlgo ? prettyTopic(d.topic) : ""}</span>
        <span className="pc-cta">
          Start <span className="pc-arrow" aria-hidden="true">→</span>
        </span>
      </div>
    </button>
  );
}

export default function Menu({ problems, onOpen, onGenerate }) {
  const [filter, setFilter] = useState("all");

  const counts = useMemo(() => {
    const c = { all: problems.length, drill: 0, algo: 0 };
    for (const d of problems) c[(d.kind || "drill") === "algo" ? "algo" : "drill"]++;
    return c;
  }, [problems]);

  const shown = problems.filter((d) => filter === "all" || (d.kind || "drill") === filter);

  return (
    <section className="menu">
      <div className="menu-inner">
        <div className="menu-head">
          <div className="menu-head-text">
            <p className="menu-eyebrow">Interview practice</p>
            <h1>Choose a problem</h1>
            <p className="menu-sub">
              Progressive coding drills. Read every level first, design your state object,
              then green each level in order.
            </p>
          </div>
          <button
            className="btn primary menu-gen"
            onClick={onGenerate}
            title="Generate a new problem with the agent"
          >
            <span className="menu-gen-spark" aria-hidden="true">✦</span> Generate a new problem
          </button>
        </div>

        <div className="menu-toolbar" role="tablist" aria-label="Filter problems">
          {FILTERS.map(([id, label]) => (
            <button
              key={id}
              role="tab"
              aria-selected={filter === id}
              className={"filter-btn" + (filter === id ? " active" : "")}
              onClick={() => setFilter(id)}
            >
              {label}
              <span className="filter-count">{counts[id] ?? 0}</span>
            </button>
          ))}
        </div>

        {shown.length === 0 ? (
          <p className="menu-empty">No problems in this category yet.</p>
        ) : (
          <div className="menu-grid">
            {shown.map((d) => (
              <ProblemCard key={d.slug} d={d} onOpen={onOpen} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
