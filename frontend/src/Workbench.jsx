import React, { useCallback, useEffect, useRef, useState } from "react";
import Editor, { useMonaco } from "@monaco-editor/react";
import * as api from "./api";
import Results, { FsTree } from "./Results";
import Coach from "./Coach";
import { useSplitter } from "./ui";

const THEME = {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "comment", foreground: "5c6b7a", fontStyle: "italic" },
    { token: "keyword", foreground: "ff9d5c" },
    { token: "string", foreground: "9ecbff" },
    { token: "number", foreground: "d2a8ff" },
  ],
  colors: {
    "editor.background": "#0b1017",
    "editor.lineHighlightBackground": "#12181f",
    "editorLineNumber.foreground": "#3a4552",
    "editorLineNumber.activeForeground": "#8b98a7",
    "editor.selectionBackground": "#264066",
    "editorCursor.foreground": "#42c586",
    "editorIndentGuide.background1": "#1b2430",
  },
};

export default function Workbench({
  drill, code, setCode, dirty, onSave, lastRun, setLastRun, onOpenProblem, refreshMenu, say,
}) {
  const [tab, setTab] = useState("results");
  const [running, setRunning] = useState(false);
  const [lint, setLint] = useState("");
  const monaco = useMonaco();
  const editorRef = useRef(null);
  const leftRef = useSplitter("left");
  const rightRef = useSplitter("right");

  // Keep callbacks fresh for the Monaco commands + the top-bar buttons.
  const codeRef = useRef(code);
  codeRef.current = code;

  const run = useCallback(async () => {
    if (running) return;
    setRunning(true);
    setTab("results");
    try {
      const data = await api.runCode(drill.slug, codeRef.current);
      setLastRun(data);
      if (data.state) setTab((t) => t); // fs tab available; stay on results
    } catch (err) {
      setLastRun({
        error:
          "Can't reach the server — the backend process may have stopped. Restart it (reps start), " +
          "then Run again. Your code is safe; it's saved in this browser.",
        stderr: String(err),
      });
    } finally {
      setRunning(false);
    }
  }, [drill, running, setLastRun]);

  // The top bar lives above this component; expose the two actions it drives.
  useEffect(() => {
    window.__repsRun = run;
    window.__repsCoach = () => setTab("coach");
    return () => {
      delete window.__repsRun;
      delete window.__repsCoach;
    };
  }, [run]);

  // Reset the task scroll + tab when switching problems.
  useEffect(() => {
    setTab("results");
  }, [drill.slug]);

  // Debounced pyflakes lint -> Monaco gutter markers.
  useEffect(() => {
    if (!monaco) return;
    const t = setTimeout(async () => {
      try {
        const { markers } = await api.lintCode(code);
        const model = editorRef.current?.getModel();
        if (!model) return;
        const marks = (markers || []).map((m) => ({
          severity: m.severity === "error" ? monaco.MarkerSeverity.Error : monaco.MarkerSeverity.Warning,
          startLineNumber: m.line, startColumn: m.col,
          endLineNumber: m.line, endColumn: m.col + 1,
          message: m.message,
        }));
        monaco.editor.setModelMarkers(model, "pyflakes", marks);
        const errs = marks.filter((m) => m.severity === monaco.MarkerSeverity.Error).length;
        const warns = marks.length - errs;
        setLint(errs ? `${errs} error${errs > 1 ? "s" : ""}` : warns ? `${warns} warning${warns > 1 ? "s" : ""}` : "no issues");
      } catch {}
    }, 650);
    return () => clearTimeout(t);
  }, [code, monaco]);

  const onMount = (editor, m) => {
    editorRef.current = editor;
    m.editor.defineTheme("ica-dark", THEME);
    m.editor.setTheme("ica-dark");
    editor.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.Enter, () => window.__repsRun?.());
    editor.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.KeyS, () => onSaveRef.current?.());
  };
  const onSaveRef = useRef(onSave);
  onSaveRef.current = onSave;

  const hasFs = !!lastRun?.state;

  return (
    <main className="workbench">
      <section className="pane pane-task">
        <div className="pane-head">
          <h2>{drill.title}</h2>
        </div>
        <div className="pane-body task" dangerouslySetInnerHTML={{ __html: drill.markdown_html }} />
      </section>

      <div className="gutter" ref={leftRef} />

      <section className="pane pane-editor">
        <div className="pane-head editor-head">
          <span className="lang-badge">Python 3</span>
          <span className={"save-state" + (dirty ? " dirty" : "")}>{dirty ? "unsaved" : "saved"}</span>
          <span className={"lint-state" + (/error/.test(lint) ? " has-err" : /warning/.test(lint) ? " has-warn" : "")}>
            {lint}
          </span>
        </div>
        <div className="editor-host">
          <Editor
            language="python"
            theme="ica-dark"
            value={code}
            onChange={(v) => setCode(v ?? "")}
            onMount={onMount}
            options={{
              fontSize: 13.5,
              fontFamily: '"JetBrains Mono","Fira Code",Menlo,Consolas,monospace',
              fontLigatures: true,
              tabSize: 4,
              insertSpaces: true,
              detectIndentation: false,
              autoIndent: "full",
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              renderWhitespace: "selection",
              bracketPairColorization: { enabled: true },
              smoothScrolling: true,
              cursorBlinking: "smooth",
              padding: { top: 12 },
              automaticLayout: true,
            }}
          />
        </div>
      </section>

      <div className="gutter" ref={rightRef} />

      <section className="pane pane-results">
        <div className="pane-head tabs">
          <button className={"tab" + (tab === "results" ? " active" : "")} onClick={() => setTab("results")}>
            Results
          </button>
          {hasFs && (
            <button className={"tab" + (tab === "fs" ? " active" : "")} onClick={() => setTab("fs")}>
              Filesystem
            </button>
          )}
          <button className={"tab" + (tab === "coach" ? " active" : "")} onClick={() => setTab("coach")}>
            ✦ Coach
          </button>
        </div>
        <div className="pane-body">
          {tab === "results" && <Results data={lastRun} running={running} />}
          {tab === "fs" && <FsTree state={lastRun?.state} />}
          {tab === "coach" && (
            <Coach
              drill={drill}
              code={code}
              lastRun={lastRun}
              onOpenProblem={onOpenProblem}
              refreshMenu={refreshMenu}
              say={say}
            />
          )}
        </div>
      </section>
    </main>
  );
}
