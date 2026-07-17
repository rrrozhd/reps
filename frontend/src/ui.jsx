import React, { useEffect, useRef, useState } from "react";
import { useMonaco } from "@monaco-editor/react";

/** 90-minute ICA clock: amber at 5:00, red at 1:00. */
export function Timer() {
  const TOTAL = 90 * 60;
  const [left, setLeft] = useState(TOTAL);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setLeft((s) => (s <= 0 ? 0 : s - 1)), 1000);
    return () => clearInterval(t);
  }, [running]);
  useEffect(() => {
    if (left === 0) setRunning(false);
  }, [left]);

  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");
  const cls = "timer" + (left <= 60 ? " danger" : left <= 300 ? " warn" : "");

  return (
    <div className={cls} title="90-minute ICA clock">
      <span className="timer-face">{`${mm}:${ss}`}</span>
      <button className="tbtn" onClick={() => setRunning((r) => !r)} title="Start / pause">
        {running ? "❚❚" : "▶"}
      </button>
      <button
        className="tbtn"
        onClick={() => {
          setRunning(false);
          setLeft(TOTAL);
        }}
        title="Reset to 90:00"
      >
        ↺
      </button>
    </div>
  );
}

export function Toast({ msg }) {
  if (!msg) return null;
  return <div className="toast">{msg}</div>;
}

/** Reference solution, syntax-highlighted with Monaco's colorizer. */
export function RefModal({ code, onClose, say }) {
  const monaco = useMonaco();
  const [html, setHtml] = useState("colorizing…");

  useEffect(() => {
    if (!monaco) return;
    monaco.editor.colorize(code, "python", { tabSize: 4 }).then(setHtml);
  }, [monaco, code]);

  useEffect(() => {
    const esc = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-head">
          <h3>Reference solution</h3>
          <div className="modal-actions">
            <button
              className="btn ghost"
              onClick={() => navigator.clipboard.writeText(code).then(() => say("Reference copied"))}
            >
              Copy
            </button>
            <button className="btn ghost" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
        <div className="modal-warn">
          Attempt all the levels <em>cold</em> first — then diff against this to find exactly where
          you'd have had to rewrite.
        </div>
        <div className="modal-code">
          <pre dangerouslySetInnerHTML={{ __html: html }} />
        </div>
      </div>
    </div>
  );
}

/** Draggable pane splitter; writes a CSS var on <html>. */
export function useSplitter(side) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const down = (e) => {
      e.preventDefault();
      el.classList.add("dragging");
      el.setPointerCapture(e.pointerId);
      const wb = el.parentElement.getBoundingClientRect();
      const move = (ev) => {
        const min = side === "left" ? 240 : 300;
        const hi = Math.max(min, wb.width - 620);
        const raw = side === "left" ? ev.clientX - wb.left : wb.right - ev.clientX;
        const w = Math.min(Math.max(raw, min), hi);
        document.documentElement.style.setProperty(`--${side}`, `${w}px`);
      };
      const up = (ev) => {
        el.classList.remove("dragging");
        el.releasePointerCapture(ev.pointerId);
        el.removeEventListener("pointermove", move);
        el.removeEventListener("pointerup", up);
      };
      el.addEventListener("pointermove", move);
      el.addEventListener("pointerup", up);
    };
    el.addEventListener("pointerdown", down);
    return () => el.removeEventListener("pointerdown", down);
  }, [side]);
  return ref;
}
