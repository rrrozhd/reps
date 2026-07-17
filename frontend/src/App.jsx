import React, { useCallback, useEffect, useRef, useState } from "react";
import * as api from "./api";
import Menu from "./Menu";
import Workbench from "./Workbench";
import Settings from "./Settings";
import { RefModal, Timer, Toast } from "./ui";

const codeKey = (slug) => "ica:code:" + slug;

export default function App() {
  const [view, setView] = useState("menu"); // menu | workbench | settings
  const [problems, setProblems] = useState([]);
  const [drill, setDrill] = useState(null);
  const [code, setCode] = useState("");
  const [lastRun, setLastRun] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [refOpen, setRefOpen] = useState(false);
  const [toast, setToast] = useState(null);

  const say = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 1600);
  }, []);

  const refreshMenu = useCallback(
    () => api.listProblems().then(setProblems).catch(() => {}),
    []
  );
  useEffect(() => {
    refreshMenu();
  }, [refreshMenu]);

  // ---- open a problem: prefer durable server-saved code, then local, then starter
  const openProblem = useCallback(async (slug) => {
    const [d, sol] = await Promise.all([api.getDrill(slug), api.loadSolution(slug)]);
    let saved = null;
    try {
      saved = localStorage.getItem(codeKey(slug));
    } catch {}
    setDrill(d);
    setCode(sol && sol.code != null ? sol.code : saved ?? d.starter);
    setLastRun(null);
    setDirty(false);
    try {
      localStorage.setItem("ica:last", slug);
    } catch {}
    setView("workbench");
  }, []);

  // ---- autosave (debounced): browser cache + durable server copy
  const saveTimer = useRef(null);
  useEffect(() => {
    if (!drill || !dirty) return;
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      try {
        localStorage.setItem(codeKey(drill.slug), code);
      } catch {}
      api.saveSolution(drill.slug, code);
      setDirty(false);
    }, 700);
    return () => clearTimeout(saveTimer.current);
  }, [code, drill, dirty]);

  const saveNow = useCallback(() => {
    if (!drill) return;
    try {
      localStorage.setItem(codeKey(drill.slug), code);
    } catch {}
    api.saveSolution(drill.slug, code);
    setDirty(false);
    say("Saved");
  }, [drill, code, say]);

  const resetCode = useCallback(() => {
    if (!drill) return;
    if (confirm("Restore the starter code for this drill? Your current edits will be lost.")) {
      setCode(drill.starter);
      setDirty(true);
    }
  }, [drill]);

  const goHome = useCallback(() => {
    setView("menu");
    refreshMenu();
  }, [refreshMenu]);

  const inWorkbench = view === "workbench";

  return (
    <>
      <header className="topbar">
        <div className="brand" id="brand" title="Back to problems" onClick={goHome}>
          <img className="logo" src="/assets/reps-mark-dark.svg" alt="" width="156" height="66" />
          <span className="brand-name">reps</span>
        </div>

        {inWorkbench && (
          <>
            <button className="btn ghost" onClick={goHome} title="Back to all problems">
              ← Problems
            </button>
            <span className="current-title">{drill?.title}</span>
            <span className="pill muted" id="drill-diff">
              {drill?.difficulty}
            </span>
          </>
        )}

        <div className="topbar-right">
          {inWorkbench && (
            <div className="wb-controls">
              <Timer />
              <button className="btn ghost" onClick={() => window.__repsCoach?.()}>
                ✦ Coach
              </button>
              <button className="btn ghost" onClick={resetCode} title="Restore starter code">
                Reset code
              </button>
              <button className="btn ghost" onClick={() => setRefOpen(true)}>
                Reference
              </button>
              <button
                className="btn primary"
                onClick={() => window.__repsRun?.()}
                title="Run tests (⌘/Ctrl + Enter)"
              >
                <span className="run-label">Run</span> <kbd>⌘↵</kbd>
              </button>
            </div>
          )}
          <button className="btn ghost" onClick={() => setView("settings")} title="Coach & engine settings">
            ⚙ Settings
          </button>
        </div>
      </header>

      {view === "menu" && (
        <Menu problems={problems} onOpen={openProblem} onGenerate={() => {
          const last = problems[0];
          if (last) openProblem(last.slug).then(() => setTimeout(() => window.__repsCoach?.(), 150));
        }} />
      )}

      {inWorkbench && drill && (
        <Workbench
          drill={drill}
          code={code}
          setCode={(c) => {
            setCode(c);
            setDirty(true);
          }}
          dirty={dirty}
          onSave={saveNow}
          lastRun={lastRun}
          setLastRun={setLastRun}
          onOpenProblem={openProblem}
          refreshMenu={refreshMenu}
          say={say}
        />
      )}

      {view === "settings" && <Settings onBack={goHome} say={say} />}

      {refOpen && drill && <RefModal code={drill.reference} onClose={() => setRefOpen(false)} say={say} />}
      <Toast msg={toast} />
    </>
  );
}
