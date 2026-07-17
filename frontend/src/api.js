// Thin wrappers over the reps backend. Every call returns parsed JSON and
// throws on transport failure so callers can surface "server is down" clearly.

async function req(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok && res.status >= 500) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

const json = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const listProblems = () => req("/api/drills");
export const getDrill = (slug) => req(`/api/drills/${slug}`);

export const loadSolution = (slug) =>
  fetch(`/api/solution/${slug}`)
    .then((r) => (r.ok ? r.json() : { code: null }))
    .catch(() => ({ code: null }));

export const saveSolution = (slug, code) =>
  fetch(`/api/solution/${slug}`, { ...json({ code }), method: "PUT" }).catch(() => {});

export const runCode = (slug, code) => req("/api/run", json({ slug, code }));
export const lintCode = (code) => req("/api/lint", json({ code }));

export const agentHealth = () => req("/api/agent/health");
export const agentGenerate = (body) => req("/api/agent/generate", json(body));
export const agentExplain = (body) => req("/api/agent/explain", json(body));
export const agentTest = (provider = "") => req("/api/agent/test", json({ provider }));

export const getConfig = () => req("/api/config");
export const putConfig = (body) =>
  fetch("/api/config", { ...json(body), method: "PUT" }).then((r) => r.json());

export const loginStatus = (provider = "claude") =>
  req(`/api/agent/login/status?provider=${provider}`);
export const loginStart = (provider = "claude") => req("/api/agent/login/start", json({ provider }));
export const loginPoll = (provider = "claude") => req(`/api/agent/login/poll?provider=${provider}`);
export const loginCode = (provider, code) => req("/api/agent/login/code", json({ provider, code }));
export const logout = (provider = "claude") => req("/api/agent/login/logout", json({ provider }));
