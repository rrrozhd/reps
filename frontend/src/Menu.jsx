import React, { useState } from "react";

const shortLevel = (name) => name.replace(/^Level\s*\d+\s*[—-]\s*/, "");

const FILTERS = [
  ["all", "All"],
  ["drill", "Progressive drills"],
  ["algo", "Algorithms"],
];

function ProblemCard({ d, onOpen }) {
  const kind = d.kind || "drill";
  const levels = d.levels || [];
  const isAlgo = kind === "algo";
  return (
    <button className="problem-card" onClick={() => onOpen(d.slug)}>
      <div className="pc-top">
        <span className="pc-title">{d.title}</span>
        {isAlgo ? (
          <span className={`pc-badge diff-${(d.difficulty || "").toLowerCase()}`}>{d.difficulty}</span>
        ) : (
          <span className="pc-diff">
            {levels.length} level{levels.length === 1 ? "" : "s"}
          </span>
        )}
      </div>
      <div className="pc-sub">{isAlgo ? `Algorithm · ${d.topic || ""}` : "Progressive drill"}</div>
      <p className="pc-blurb">{d.blurb || ""}</p>
      <div className="pc-levels">
        {levels.map((n) => (
          <span className="pc-lvl" key={n}>
            {shortLevel(n)}
          </span>
        ))}
      </div>
      <span className="pc-cta">Start →</span>
    </button>
  );
}

export default function Menu({ problems, onOpen, onGenerate }) {
  const [filter, setFilter] = useState("all");
  const shown = problems.filter((d) => filter === "all" || (d.kind || "drill") === filter);

  return (
    <section className="menu">
      <div className="menu-head">
        <h1>Choose a problem</h1>
        <p className="menu-sub">
          Progressive coding drills. Read every level first, design your state object, then green
          each level in order.
        </p>
        <button className="btn primary" onClick={onGenerate} title="Generate a new problem with the agent">
          ✦ Generate a new problem
        </button>
        <div className="menu-filters">
          {FILTERS.map(([id, label]) => (
            <button
              key={id}
              className={"filter-btn" + (filter === id ? " active" : "")}
              onClick={() => setFilter(id)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="menu-grid">
        {shown.map((d) => (
          <ProblemCard key={d.slug} d={d} onOpen={onOpen} />
        ))}
      </div>
    </section>
  );
}
