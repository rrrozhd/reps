import React, { useCallback, useEffect, useRef, useState } from "react";
import * as api from "./api";

export default function Settings({ onBack, say }) {
  const [health, setHealth] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [account, setAccount] = useState(null);
  const [login, setLogin] = useState(null); // {url, output} while a sign-in runs
  const [loginCodeVal, setLoginCodeVal] = useState("");
  const [test, setTest] = useState(null);
  const pollRef = useRef(null);

  const load = useCallback(async () => {
    const [h, c] = await Promise.all([api.agentHealth(), api.getConfig()]);
    setHealth(h);
    setCfg(c);
    api.loginStatus("claude").then(setAccount).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    return () => clearTimeout(pollRef.current);
  }, [load]);

  const pickEngine = async (id) => {
    await api.putConfig({ provider: id });
    load();
  };

  const saveEndpoint = async () => {
    const body = {
      base_url: cfg.endpoint.base_url.trim(),
      model: cfg.endpoint.model.trim(),
      name: "Local model",
    };
    if (cfg.endpoint._key) body.api_key = cfg.endpoint._key;
    await api.putConfig(body);
    say("Endpoint saved");
    load();
  };

  const runTest = async () => {
    setTest({ pending: true });
    try {
      setTest(await api.agentTest(""));
    } catch (e) {
      setTest({ ok: false, message: String(e) });
    }
  };

  const poll = useCallback(() => {
    clearTimeout(pollRef.current);
    api
      .loginPoll("claude")
      .then((p) => {
        setLogin({ url: p.url, output: p.output });
        if (p.status?.loggedIn) {
          setLogin(null);
          setAccount(p.status);
          say("Signed in");
          load();
          return;
        }
        pollRef.current = setTimeout(poll, 2000);
      })
      .catch(() => {
        pollRef.current = setTimeout(poll, 3000);
      });
  }, [load, say]);

  const startLogin = async () => {
    setLogin({ output: "starting sign-in…" });
    const res = await api.loginStart("claude");
    if (!res.ok) return setLogin({ output: res.error || "could not start sign-in" });
    setLogin({ url: res.url, output: res.output });
    poll();
  };

  const ep = cfg?.endpoint || {};
  const needsCode = /code|paste/i.test(login?.output || "");

  return (
    <section className="settings">
      <div className="settings-inner">
        <button className="btn ghost" onClick={onBack}>← Back</button>
        <h1>Coach settings</h1>
        <p className="settings-lead">
          Pick the engine that generates and explains problems. Local CLI agents use your existing
          login; the local-model / API option uses an endpoint you point at.
        </p>

        <div className="set-block">
          <h2>Engine</h2>
          <div className="engine-list">
            {(health?.available || []).map((p) => (
              <label className={"engine-opt" + (p.id === health.active ? " sel" : "")} key={p.id}>
                <input
                  type="radio"
                  name="engine"
                  value={p.id}
                  checked={p.id === health.active}
                  onChange={() => pickEngine(p.id)}
                />
                <span>{p.name}</span>
                <span className="eo-kind">{p.kind}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="set-block">
          <h2>Claude Code account</h2>
          <div className="account-status">
            {!account ? (
              "checking…"
            ) : account.supported === false ? (
              "Claude Code CLI not detected on this machine."
            ) : account.loggedIn ? (
              <>
                <span className="acc-in">✓ Logged in</span>
                {account.email ? ` as ${account.email}` : ""}
                {account.subscription ? ` · ${account.subscription}` : ""}
              </>
            ) : account.loggedIn === false ? (
              <>
                <span className="acc-out">Not logged in</span> — click <strong>Log in</strong>.
              </>
            ) : (
              "Status unavailable" + (account.error ? ` (${account.error})` : "")
            )}
          </div>
          <div className="account-actions">
            <button className="btn primary" onClick={startLogin}>Log in</button>
            <button className="btn ghost" onClick={() => api.logout("claude").then(() => { say("Logged out"); load(); })}>
              Log out
            </button>
            <button className="btn ghost" onClick={() => api.loginStatus("claude").then(setAccount)}>
              Recheck
            </button>
          </div>
          {login && (
            <div className="login-flow">
              <p className="set-hint">
                A browser sign-in started. Open the link below, authorize, then come back — this page
                auto-detects when you're in.
              </p>
              {login.url && (
                <a className="login-url" href={login.url} target="_blank" rel="noopener">
                  Open sign-in page ↗
                </a>
              )}
              {needsCode && (
                <div className="login-code-row">
                  <input
                    value={loginCodeVal}
                    onChange={(e) => setLoginCodeVal(e.target.value)}
                    placeholder="paste the code from that page (only if it asks)"
                  />
                  <button
                    className="btn"
                    onClick={() => api.loginCode("claude", loginCodeVal).then(() => { setLoginCodeVal(""); poll(); })}
                  >
                    Submit
                  </button>
                </div>
              )}
              {login.output && <pre className="login-output">{login.output}</pre>}
            </div>
          )}
        </div>

        <div className="set-block">
          <h2>Local model · vLLM / OpenAI-compatible</h2>
          <p className="set-hint">
            Point at any OpenAI-compatible server — vLLM, Ollama, LM Studio, OpenRouter, or a hosted
            API. Then choose <em>“Local model”</em> above.
          </p>
          <label className="set-field">
            Base URL
            <input
              value={ep.base_url || ""}
              onChange={(e) => setCfg({ ...cfg, endpoint: { ...ep, base_url: e.target.value } })}
              placeholder="http://localhost:8000/v1"
              spellCheck="false"
            />
          </label>
          <label className="set-field">
            Model
            <input
              value={ep.model || ""}
              onChange={(e) => setCfg({ ...cfg, endpoint: { ...ep, model: e.target.value } })}
              placeholder="e.g. meta-llama/Llama-3.1-8B-Instruct"
              spellCheck="false"
            />
          </label>
          <label className="set-field">
            API key <span className="set-opt">optional — leave blank for vLLM/Ollama</span>
            <input
              type="password"
              value={ep._key || ""}
              onChange={(e) => setCfg({ ...cfg, endpoint: { ...ep, _key: e.target.value } })}
              placeholder={ep.has_key ? "•••••• saved — leave blank to keep it" : "stored locally in .reps-config.json"}
            />
          </label>
          <button className="btn" onClick={saveEndpoint}>Save endpoint</button>
        </div>

        <div className="set-block">
          <button className="btn primary" onClick={runTest}>Test connection</button>
          <div className={"test-result " + (test?.pending ? "" : test ? (test.ok ? "ok" : "err") : "")}>
            {test?.pending ? (
              <>
                <span className="spin" /> testing the active engine…
              </>
            ) : test ? (
              <>
                {test.ok ? "✓ connected — " : "✕ failed — "}
                {test.name || test.provider || ""}
                <pre>{test.message}</pre>
              </>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
