/* ICA Trainer frontend — Monaco editor + drill runner. */
(function () {
  "use strict";

  var MONACO_BASE = "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs";
  var editor = null;
  var monacoReady = false;
  var current = null;          // current drill payload
  var lintTimer = null;
  var saveTimer = null;
  var running = false;
  var lastRun = null;          // last /api/run result (for coach context)
  var activeProvider = null;   // agent engine id
  var allProblems = [];        // menu cache
  var menuFilter = "all";      // all | drill | algo
  var loginPollTimer = null;   // CLI-login poll

  // ---- Monaco worker proxy (keeps the console clean; Python needs no LSP) ----
  window.MonacoEnvironment = {
    getWorkerUrl: function () {
      var code =
        "self.MonacoEnvironment={baseUrl:'" + MONACO_BASE + "/'};" +
        "importScripts('" + MONACO_BASE + "/base/worker/workerMain.js');";
      return "data:text/javascript;charset=utf-8," + encodeURIComponent(code);
    }
  };

  var $ = function (id) { return document.getElementById(id); };

  function toast(msg) {
    var el = $("toast");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.hidden = true; }, 1600);
  }

  // ------------------------------------------------------------ storage
  function codeKey(slug) { return "ica:code:" + slug; }
  function loadCode(slug, fallback) {
    try { return localStorage.getItem(codeKey(slug)) || fallback; }
    catch (e) { return fallback; }
  }
  function saveCode(slug, code) {
    try { localStorage.setItem(codeKey(slug), code); } catch (e) {}
    // durable: also persist server-side so a closed server / cleared browser
    // can't lose work.
    fetch("/api/solution/" + slug, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code })
    }).catch(function () {});
  }

  // ------------------------------------------------------------ boot
  require.config({ paths: { vs: MONACO_BASE } });
  require(["vs/editor/editor.main"], function () {
    monacoReady = true;
    defineTheme();
    createEditor();
    wireChrome();
    showMenu();
  });

  function defineTheme() {
    monaco.editor.defineTheme("ica-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "comment", foreground: "5c6b7a", fontStyle: "italic" },
        { token: "keyword", foreground: "ff9d5c" },
        { token: "string", foreground: "9ecbff" },
        { token: "number", foreground: "d2a8ff" }
      ],
      colors: {
        "editor.background": "#0b1017",
        "editor.lineHighlightBackground": "#12181f",
        "editorLineNumber.foreground": "#3a4552",
        "editorLineNumber.activeForeground": "#8b98a7",
        "editor.selectionBackground": "#264066",
        "editorCursor.foreground": "#ffe14d",
        "editorIndentGuide.background1": "#1b2430"
      }
    });
  }

  function createEditor() {
    editor = monaco.editor.create($("editor"), {
      value: "",
      language: "python",
      theme: "ica-dark",
      automaticLayout: true,
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
      padding: { top: 12 }
    });

    // Run
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, runCode);
    // Save
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, function () {
      if (current) { saveCode(current.slug, editor.getValue()); }
      markSaved();
      toast("Saved");
    });

    editor.onDidChangeModelContent(function () {
      markDirty();
      scheduleSave();
      scheduleLint();
    });
  }

  function markDirty() { var s = $("save-state"); s.textContent = "unsaved"; s.classList.add("dirty"); }
  function markSaved() { var s = $("save-state"); s.textContent = "saved"; s.classList.remove("dirty"); }

  function scheduleSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      if (current) { saveCode(current.slug, editor.getValue()); markSaved(); }
    }, 700);
  }

  // ------------------------------------------------------------ lint
  function scheduleLint() {
    clearTimeout(lintTimer);
    lintTimer = setTimeout(lint, 650);
  }

  function lint() {
    var code = editor.getValue();
    fetch("/api/lint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code })
    }).then(function (r) { return r.json(); }).then(function (data) {
      var markers = (data.markers || []).map(function (m) {
        return {
          severity: m.severity === "error"
            ? monaco.MarkerSeverity.Error
            : monaco.MarkerSeverity.Warning,
          startLineNumber: m.line, startColumn: m.col,
          endLineNumber: m.line, endColumn: m.col + 1,
          message: m.message
        };
      });
      monaco.editor.setModelMarkers(editor.getModel(), "pyflakes", markers);
      var errs = markers.filter(function (m) { return m.severity === monaco.MarkerSeverity.Error; }).length;
      var warns = markers.length - errs;
      var el = $("lint-state");
      el.classList.remove("has-warn", "has-err");
      if (errs) { el.textContent = errs + " error" + (errs > 1 ? "s" : ""); el.classList.add("has-err"); }
      else if (warns) { el.textContent = warns + " warning" + (warns > 1 ? "s" : ""); el.classList.add("has-warn"); }
      else { el.textContent = "no issues"; }
    }).catch(function () {});
  }

  // ------------------------------------------------------------ drills
  // ---- views: menu (browse) · workbench (solve) · settings ----
  function showMenu() {
    clearTimeout(loginPollTimer);
    $("menu").hidden = false;
    $("workbench").hidden = true;
    $("settings").hidden = true;
    $("btn-home").hidden = true;
    $("current-title").hidden = true;
    $("drill-diff").hidden = true;
    $("wb-controls").hidden = true;
    loadMenu();                      // refresh so newly generated problems appear
  }

  function showWorkbench() {
    clearTimeout(loginPollTimer);
    $("menu").hidden = true;
    $("workbench").hidden = false;
    $("settings").hidden = true;
    $("btn-home").hidden = false;
    $("current-title").hidden = false;
    $("drill-diff").hidden = false;
    $("wb-controls").hidden = false;
    if (editor) setTimeout(function () { editor.layout(); }, 0);  // Monaco was hidden
  }

  function showSettings() {
    $("menu").hidden = true;
    $("workbench").hidden = true;
    $("settings").hidden = false;
    $("btn-home").hidden = true;
    $("current-title").hidden = true;
    $("drill-diff").hidden = true;
    $("wb-controls").hidden = true;
    loadSettings();
  }

  function openProblem(slug) {
    showWorkbench();
    openDrill(slug);
  }

  function shortLevel(name) { return name.replace(/^Level\s*\d+\s*[—-]\s*/, ""); }

  // Fetch problems, then render the menu (respecting the active filter).
  function loadMenu() {
    return fetch("/api/drills").then(function (r) { return r.json(); }).then(function (list) {
      allProblems = list;
      renderCards();
    });
  }

  function renderCards() {
    var grid = $("menu-grid");
    grid.innerHTML = "";
    allProblems
      .filter(function (d) { return menuFilter === "all" || (d.kind || "drill") === menuFilter; })
      .forEach(function (d) { grid.appendChild(problemCard(d)); });
  }

  function problemCard(d) {
    var kind = d.kind || "drill";
    var levels = (d.levels || []).map(function (n) {
      return '<span class="pc-lvl">' + esc(shortLevel(n)) + "</span>";
    }).join("");
    var n = (d.levels || []).length;
    var badge, sub;
    if (kind === "algo") {
      var diff = (d.difficulty || "").toLowerCase();
      badge = '<span class="pc-badge diff-' + esc(diff) + '">' + esc(d.difficulty || "") + "</span>";
      sub = "Algorithm · " + esc(d.topic || "");
    } else {
      badge = '<span class="pc-diff">' + n + " level" + (n === 1 ? "" : "s") + "</span>";
      sub = "Progressive drill";
    }
    var card = document.createElement("button");
    card.className = "problem-card";
    card.innerHTML =
      '<div class="pc-top"><span class="pc-title">' + esc(d.title) + "</span>" + badge + "</div>" +
      '<div class="pc-sub">' + sub + "</div>" +
      '<p class="pc-blurb">' + esc(d.blurb || "") + "</p>" +
      '<div class="pc-levels">' + levels + "</div>" +
      '<span class="pc-cta">Start →</span>';
    card.addEventListener("click", function () { openProblem(d.slug); });
    return card;
  }

  function openCoachFromMenu() {
    fetch("/api/drills").then(function (r) { return r.json(); }).then(function (list) {
      var last = null;
      try { last = localStorage.getItem("ica:last"); } catch (e) {}
      var pick = (last && list.some(function (d) { return d.slug === last; })) ? last
                 : (list[0] && list[0].slug);
      if (!pick) return;
      openProblem(pick);
      setTimeout(function () { selectTab("coach"); $("gen-topic").focus(); }, 150);
    });
  }

  function openDrill(slug) {
    Promise.all([
      fetch("/api/drills/" + slug).then(function (r) { return r.json(); }),
      fetch("/api/solution/" + slug)
        .then(function (r) { return r.ok ? r.json() : { code: null }; })
        .catch(function () { return { code: null }; })
    ]).then(function (both) {
      var d = both[0], sol = both[1];
      current = d;
      try { localStorage.setItem("ica:last", slug); } catch (e) {}
      $("task-title").textContent = d.title;
      $("current-title").textContent = d.title;
      $("drill-diff").textContent = d.difficulty;
      $("task-body").innerHTML = d.markdown_html;
      colorizeTaskCode();

      // Prefer durable server-saved code, then local cache, then starter.
      var code = (sol && sol.code != null) ? sol.code : loadCode(slug, d.starter);
      editor.setValue(code);
      monaco.editor.setModelMarkers(editor.getModel(), "pyflakes", []);
      $("lint-state").textContent = "";
      markSaved();

      // reset results + fs tab
      $("results-empty").hidden = false;
      $("results-content").innerHTML = "";
      var fsTab = $("tab-fs");
      fsTab.hidden = !d.has_state_view;
      $("fs-content").innerHTML = "";
      $("fs-empty").hidden = false;
      selectTab("results");
      lint();
    });
  }

  function colorizeTaskCode() {
    var blocks = document.querySelectorAll("#task-body pre code");
    blocks.forEach(function (block) {
      monaco.editor.colorize(block.textContent, "python", { tabSize: 4 })
        .then(function (html) { block.innerHTML = html; });
    });
  }

  // ------------------------------------------------------------ run
  function runCode() {
    if (running || !current) return;
    running = true;
    var btn = $("btn-run");
    btn.classList.add("running");
    btn.querySelector(".run-label").textContent = "Running…";

    fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug: current.slug, code: editor.getValue() })
    }).then(function (r) { return r.json(); }).then(function (data) {
      renderResults(data);
      if (data.state) renderFs(data.state);
    }).catch(function (err) {
      renderResults({
        error: "Can't reach the server — the backend process may have stopped. " +
               "Restart it with ./run.sh (or ask Claude to), then Run again. " +
               "Your code is safe; it's saved in this browser.",
        stderr: String(err)
      });
    }).finally(function () {
      running = false;
      btn.classList.remove("running");
      btn.querySelector(".run-label").textContent = "Run";
    });
  }

  function renderResults(data) {
    lastRun = data;
    $("results-empty").hidden = true;
    var host = $("results-content");
    host.innerHTML = "";
    selectTab("results");

    if (data.error || data.stderr) {
      host.appendChild(banner("err",
        "<strong>Runner error.</strong> " + esc(data.error || "") +
        (data.stderr ? "<pre>" + esc(data.stderr) + "</pre>" : "") +
        (data.stdout ? "<pre>" + esc(data.stdout) + "</pre>" : "")));
      return;
    }
    if (data.timeout) {
      host.appendChild(banner("err", "<strong>Time limit exceeded.</strong> " + esc(data.message)));
      return;
    }
    if (data.loadError) {
      host.appendChild(banner("err",
        "<strong>Your code didn't load.</strong><pre>" + esc(data.loadError) +
        (data.traceback ? "\n\n" + esc(data.traceback) : "") + "</pre>"));
      if (data.output) host.appendChild(outputBlock(data.output));
      return;
    }

    if (!Array.isArray(data.levels)) {
      host.appendChild(banner("err", "<strong>Unexpected response.</strong><pre>" +
        esc(JSON.stringify(data, null, 2)) + "</pre>"));
      return;
    }

    var levels = data.levels;
    var passedLevels = levels.filter(function (l) { return l.ok; }).length;
    var totalChecks = 0, passedChecks = 0;
    levels.forEach(function (l) {
      l.tests.forEach(function (t) {
        t.checks.forEach(function (c) { totalChecks++; if (c.passed) passedChecks++; });
      });
    });

    var summary = document.createElement("div");
    summary.className = "score-summary";
    var lvlChip = document.createElement("span");
    lvlChip.className = "score-chip " + (passedLevels === levels.length ? "good" : (passedLevels ? "" : "bad"));
    lvlChip.textContent = passedLevels + " / " + levels.length + " levels";
    var chkChip = document.createElement("span");
    chkChip.className = "score-chip " + (passedChecks === totalChecks ? "good" : "bad");
    chkChip.textContent = passedChecks + " / " + totalChecks + " checks";
    summary.appendChild(lvlChip);
    summary.appendChild(chkChip);
    host.appendChild(summary);

    // Find the first failing level so we can auto-open it.
    var firstFail = levels.findIndex(function (l) { return !l.ok; });

    levels.forEach(function (lv, i) {
      host.appendChild(renderLevel(lv, i === firstFail || (firstFail === -1 && i === levels.length - 1)));
    });

    if (data.output) host.appendChild(outputBlock(data.output));
  }

  function outputBlock(text) {
    var el = document.createElement("div");
    el.className = "run-banner output";
    el.innerHTML = '<div class="output-head">stdout — your print() output</div><pre>' +
      esc(text) + "</pre>";
    return el;
  }

  function renderLevel(lv, open) {
    var el = document.createElement("div");
    el.className = "level " + (lv.ok ? "pass" : "fail") + (open ? " open" : "");
    var nTests = lv.tests.length;
    var passT = lv.tests.filter(function (t) { return t.ok; }).length;

    var head = document.createElement("div");
    head.className = "level-head";
    head.innerHTML =
      '<span class="chevron">▶</span>' +
      '<span class="level-dot"></span>' +
      '<span class="level-name">' + esc(lv.name) + "</span>" +
      '<span class="level-count">' + passT + "/" + nTests + "</span>";
    head.addEventListener("click", function () { el.classList.toggle("open"); });
    el.appendChild(head);

    var body = document.createElement("div");
    body.className = "level-body";
    lv.tests.forEach(function (t) { body.appendChild(renderTest(t)); });
    el.appendChild(body);
    return el;
  }

  function renderTest(t) {
    var el = document.createElement("div");
    el.className = "test " + (t.ok ? "pass" : "fail");
    var head = document.createElement("div");
    head.className = "test-head";
    head.innerHTML =
      '<span class="test-mark">' + (t.ok ? "✓" : "✕") + "</span>" +
      '<span class="test-name">' + esc(prettyName(t.name)) + "</span>";
    el.appendChild(head);

    if (t.error) {
      var er = document.createElement("div");
      er.className = "test-error";
      er.textContent = t.error + (t.traceback ? "\n\n" + t.traceback : "");
      el.appendChild(er);
    }

    var fails = t.checks.filter(function (c) { return !c.passed; });
    var show = t.ok ? [] : t.checks;   // on failure show every check for context
    if (show.length) {
      var wrap = document.createElement("div");
      wrap.className = "checks";
      show.forEach(function (c) { wrap.appendChild(renderCheck(c)); });
      el.appendChild(wrap);
    }
    return el;
  }

  function renderCheck(c) {
    var el = document.createElement("div");
    el.className = "check " + (c.passed ? "pass" : "fail");
    var diff = c.passed ? "" :
      '<div class="check-diff"><span class="exp">expected ' + esc(c.expected) +
      '</span> · <span class="act">got ' + esc(c.actual) + "</span></div>";
    el.innerHTML =
      '<span class="cm">' + (c.passed ? "✓" : "✕") + "</span>" +
      '<span><span class="check-label">' + esc(c.label) + "</span>" + diff + "</span>";
    return el;
  }

  function prettyName(name) {
    return name.replace(/^l\d+_/, "").replace(/_/g, " ");
  }

  function banner(kind, html) {
    var el = document.createElement("div");
    el.className = "run-banner " + kind;
    el.innerHTML = html;
    return el;
  }

  // ------------------------------------------------------------ filesystem view
  function renderFs(state) {
    var host = $("fs-content");
    host.innerHTML = "";
    $("fs-empty").hidden = true;

    if (state.error) {
      host.appendChild(banner("err", "<strong>Filesystem demo failed.</strong> " + esc(state.error)));
      return;
    }
    var treeWrap = document.createElement("div");
    treeWrap.className = "fs-tree";
    treeWrap.appendChild(fsNode("/", { __dir__: true, children: state.tree || {} }, true));
    host.appendChild(treeWrap);

    if (state.demo && state.demo.length) {
      var demo = document.createElement("div");
      demo.className = "fs-demo";
      demo.innerHTML = "<h4>Demo script (run on your code)</h4><pre>" +
        esc(state.demo.join("\n")) + "</pre>";
      host.appendChild(demo);
    }
  }

  function fsNode(name, node, isRoot) {
    var ul = document.createElement("ul");
    if (isRoot) {
      var rootLi = document.createElement("li");
      rootLi.innerHTML = '<div class="fs-row"><span class="fs-dir">▸ /</span></div>';
      ul.appendChild(rootLi);
      ul.appendChild(childList(node.children));
      return ul;
    }
    return ul;
  }

  function childList(children) {
    var ul = document.createElement("ul");
    var names = Object.keys(children || {}).sort();
    names.forEach(function (n) {
      var node = children[n];
      var li = document.createElement("li");
      if (node.__file__) {
        li.innerHTML = '<div class="fs-row"><span class="fs-file">◦ ' + esc(n) +
          '</span><span class="fs-size">' + (node.size == null ? "?" : node.size + " b") + "</span></div>";
      } else {
        li.innerHTML = '<div class="fs-row"><span class="fs-dir">▸ ' + esc(n) + "/</span></div>";
        li.appendChild(childList(node.children));
      }
      ul.appendChild(li);
    });
    return ul;
  }

  // ------------------------------------------------------------ coach
  function loadProviders() {
    fetch("/api/agent/health").then(function (r) { return r.json(); }).then(function (h) {
      activeProvider = h.active;
      var sel = $("provider-select");
      sel.innerHTML = "";
      (h.available || []).forEach(function (p) {
        var opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = p.name + " (" + p.kind + ")";
        if (p.id === h.active) opt.selected = true;
        sel.appendChild(opt);
      });
      $("provider-note").textContent = h.note || "";
    }).catch(function () {
      $("provider-note").textContent = "Could not reach the agent bridge.";
    });
  }

  function chosenProvider() {
    var sel = $("provider-select");
    return sel && sel.value ? sel.value : activeProvider;
  }

  function taskText() {
    var tmp = document.createElement("div");
    tmp.innerHTML = current ? current.markdown_html : "";
    return (tmp.textContent || "").trim();
  }

  function runSummary() {
    if (!lastRun || !lastRun.levels) return "(not run yet)";
    var out = [];
    lastRun.levels.forEach(function (l) {
      var fails = [];
      l.tests.forEach(function (t) {
        t.checks.forEach(function (c) { if (!c.passed) fails.push(c.label + " [exp " + c.expected + " got " + c.actual + "]"); });
        if (t.error) fails.push(t.name + ": " + t.error);
      });
      out.push((l.ok ? "PASS " : "FAIL ") + l.name + (fails.length ? " — " + fails.slice(0, 6).join("; ") : ""));
    });
    return out.join("\n");
  }

  function coachContext() {
    return "Problem: " + (current ? current.title : "?") +
      "\n\nSpec:\n" + taskText() +
      "\n\nMy current code:\n```python\n" + (editor ? editor.getValue() : "") + "\n```" +
      "\n\nLatest test results:\n" + runSummary();
  }

  function coachMsg(kind, headHtml, bodyHtml) {
    var log = $("coach-log");
    var el = document.createElement("div");
    el.className = "coach-msg " + kind;
    el.innerHTML = '<div class="cm-head">' + headHtml + "</div>" +
      '<div class="cm-body">' + bodyHtml + "</div>";
    log.insertBefore(el, log.firstChild);
    return el;
  }

  function generate() {
    var topic = $("gen-topic").value.trim();
    if (!topic) { $("gen-topic").focus(); return; }
    var level = $("gen-level").value;
    var provider = chosenProvider();
    var btn = $("btn-generate");
    btn.disabled = true;
    var msg = coachMsg("pending",
      '<span class="spin"></span> generating <strong>' + esc(topic) + "</strong> (" + esc(level) + ") via " + esc(provider), "Working… this can take a bit for a real agent.");
    fetch("/api/agent/generate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: topic, level: level, provider: provider })
    }).then(function (r) { return r.json(); }).then(function (res) {
      msg.remove();
      if (res.ok) {
        var ok = coachMsg("ok",
          '<span class="cm-badge">✓ generated</span> ' + esc(res.provider_name || res.provider || ""),
          "New drill <strong>" + esc(res.slug) + "</strong> is verified and ready." +
          '<div class="cm-open" data-open="' + esc(res.slug) + '">Open ' + esc(res.slug) + " →</div>" +
          (res.verify ? "<pre>" + esc(res.verify) + "</pre>" : ""));
        ok.querySelector(".cm-open").addEventListener("click", function () {
          openProblem(res.slug);     // jump into the new drill
        });
        $("gen-topic").value = "";
        loadMenu();                  // refresh the problem menu with the new card
      } else {
        coachMsg("err", '<span class="cm-badge">✕ failed</span> ' + esc(res.provider_name || res.provider || ""),
          esc(res.error || "generation failed") +
          (res.verify ? "<pre>" + esc(res.verify) + "</pre>" : "") +
          (res.agent_output ? "<pre>" + esc(res.agent_output.slice(0, 1500)) + "</pre>" : ""));
      }
    }).catch(function (err) {
      msg.remove();
      coachMsg("err", '<span class="cm-badge">✕ error</span>', esc(String(err)));
    }).finally(function () { btn.disabled = false; });
  }

  function ask(kind) {
    var presets = {
      "explain-level": "Explain what this problem is testing and the state-design approach that makes the later levels easy. Don't write the full solution.",
      "hint": "I'm stuck. Give me ONE progressive hint for what to do next, without revealing the full solution.",
      "review": "Here is my code and the failing tests. Explain why it's failing and how to fix it — guide me, don't just rewrite it."
    };
    var q = kind && presets[kind] ? presets[kind] : $("ask-text").value.trim();
    if (!q) { $("ask-text").focus(); return; }
    var provider = chosenProvider();
    var msg = coachMsg("pending", '<span class="spin"></span> asking ' + esc(provider), esc(q));
    fetch("/api/agent/explain", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, context: coachContext(), provider: provider })
    }).then(function (r) { return r.json(); }).then(function (res) {
      msg.remove();
      if (res.ok) {
        coachMsg("ok", '<span class="cm-badge">✦ coach</span> ' + esc(provider), esc(res.text || "(no answer)"));
      } else {
        coachMsg("err", '<span class="cm-badge">✕ error</span>', esc(res.error || "no answer"));
      }
    }).catch(function (err) {
      msg.remove();
      coachMsg("err", '<span class="cm-badge">✕ error</span>', esc(String(err)));
    });
    if (!kind) $("ask-text").value = "";
  }

  // ------------------------------------------------------------ settings
  function loadSettings() {
    Promise.all([
      fetch("/api/config").then(function (r) { return r.json(); }),
      fetch("/api/agent/health").then(function (r) { return r.json(); })
    ]).then(function (both) {
      var cfg = both[0], h = both[1];
      var ep = cfg.endpoint || {};
      $("cfg-base").value = ep.base_url || "";
      $("cfg-model").value = ep.model || "";
      $("cfg-key").value = "";
      $("cfg-key").placeholder = ep.has_key
        ? "•••••• saved — leave blank to keep it"
        : "stored locally in .reps-config.json";

      var list = $("engine-list");
      list.innerHTML = "";
      (h.available || []).forEach(function (p) {
        var opt = document.createElement("label");
        opt.className = "engine-opt" + (p.id === h.active ? " sel" : "");
        opt.innerHTML =
          '<input type="radio" name="engine" value="' + esc(p.id) + '"' +
          (p.id === h.active ? " checked" : "") + ">" +
          "<span>" + esc(p.name) + "</span>" +
          '<span class="eo-kind">' + esc(p.kind) + "</span>";
        opt.querySelector("input").addEventListener("change", function () {
          putConfig({ provider: p.id }).then(function () { loadSettings(); loadProviders(); });
        });
        list.appendChild(opt);
      });
      loadAccount();
    });
  }

  // ---- in-app CLI login ----
  function loadAccount() {
    fetch("/api/agent/login/status?provider=claude")
      .then(function (r) { return r.json(); }).then(renderAccount).catch(function () {});
  }

  function renderAccount(s) {
    var el = $("account-status");
    if (!s || s.supported === false) {
      el.textContent = "Claude Code CLI not detected on this machine.";
      $("btn-login").disabled = true;
      return;
    }
    if (s.loggedIn) {
      el.innerHTML = '<span class="acc-in">✓ Logged in</span>' +
        (s.email ? " as " + esc(s.email) : "") +
        (s.subscription ? " · " + esc(s.subscription) : "");
    } else if (s.loggedIn === false) {
      el.innerHTML = '<span class="acc-out">Not logged in</span> — click <strong>Log in</strong>.';
    } else {
      el.textContent = "Status unavailable" + (s.error ? " (" + s.error + ")" : "");
    }
  }

  function applyLoginState(res) {
    if (res.url) { var a = $("login-url"); a.href = res.url; a.style.display = "inline-block"; }
    else { $("login-url").style.display = "none"; }
    $("login-code-row").hidden = !/code|paste/i.test(res.output || "");
    if (res.output) $("login-output").textContent = res.output;
  }

  function startLogin() {
    $("login-flow").hidden = false;
    $("login-url").style.display = "none";
    $("login-output").textContent = "starting sign-in…";
    fetch("/api/agent/login/start", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: "claude" })
    }).then(function (r) { return r.json(); }).then(function (res) {
      if (!res.ok) { $("login-output").textContent = res.error || "could not start sign-in"; return; }
      applyLoginState(res);
      pollLogin();
    });
  }

  function pollLogin() {
    clearTimeout(loginPollTimer);
    fetch("/api/agent/login/poll?provider=claude").then(function (r) { return r.json(); })
      .then(function (p) {
        applyLoginState(p);
        if (p.status && p.status.loggedIn) {
          $("login-flow").hidden = true;
          renderAccount(p.status);
          toast("Signed in");
          loadProviders();
          return;
        }
        loginPollTimer = setTimeout(pollLogin, 2000);
      }).catch(function () { loginPollTimer = setTimeout(pollLogin, 3000); });
  }

  function submitLoginCode() {
    var code = $("login-code").value.trim();
    if (!code) return;
    fetch("/api/agent/login/code", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: "claude", code: code })
    }).then(function () { $("login-code").value = ""; pollLogin(); });
  }

  function logout() {
    fetch("/api/agent/login/logout", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: "claude" })
    }).then(function () { toast("Logged out"); loadAccount(); loadProviders(); });
  }

  function putConfig(body) {
    return fetch("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
  }

  function saveEndpoint() {
    var body = {
      base_url: $("cfg-base").value.trim(),
      model: $("cfg-model").value.trim(),
      name: "Local model"
    };
    var key = $("cfg-key").value;
    if (key) body.api_key = key;
    putConfig(body).then(function () {
      toast("Endpoint saved");
      loadSettings();
      loadProviders();
    });
  }

  function testConnection() {
    var el = $("test-result");
    el.className = "test-result";
    el.innerHTML = '<span class="spin"></span> testing the active engine…';
    fetch("/api/agent/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})   // empty -> tests whatever engine is active/saved
    }).then(function (r) { return r.json(); }).then(function (res) {
      el.className = "test-result " + (res.ok ? "ok" : "err");
      el.innerHTML = (res.ok ? "✓ connected — " : "✕ failed — ") +
        esc(res.name || res.provider || "") + "<pre>" + esc(res.message || "") + "</pre>";
    }).catch(function (e) {
      el.className = "test-result err";
      el.innerHTML = "✕ " + esc(String(e));
    });
  }

  // ------------------------------------------------------------ tabs
  function selectTab(which) {
    ["results", "fs", "coach"].forEach(function (t) {
      $("tab-" + t).classList.toggle("active", t === which);
      $("panel-" + t).hidden = t !== which;
    });
  }

  // ------------------------------------------------------------ chrome (buttons, timer, splitters, modal)
  function wireChrome() {
    $("btn-run").addEventListener("click", runCode);
    $("btn-home").addEventListener("click", showMenu);
    $("brand").addEventListener("click", showMenu);
    $("btn-menu-coach").addEventListener("click", openCoachFromMenu);
    $("btn-settings").addEventListener("click", showSettings);
    $("btn-settings-back").addEventListener("click", showMenu);
    $("cfg-save").addEventListener("click", saveEndpoint);
    $("btn-test").addEventListener("click", testConnection);
    $("btn-login").addEventListener("click", startLogin);
    $("btn-logout").addEventListener("click", logout);
    $("btn-recheck").addEventListener("click", loadAccount);
    $("btn-login-code").addEventListener("click", submitLoginCode);
    Array.prototype.forEach.call(document.querySelectorAll(".filter-btn"), function (b) {
      b.addEventListener("click", function () {
        menuFilter = b.dataset.filter;
        Array.prototype.forEach.call(document.querySelectorAll(".filter-btn"),
          function (x) { x.classList.toggle("active", x === b); });
        renderCards();
      });
    });
    $("tab-results").addEventListener("click", function () { selectTab("results"); });
    $("tab-fs").addEventListener("click", function () { selectTab("fs"); });
    $("tab-coach").addEventListener("click", function () { selectTab("coach"); });
    $("btn-coach").addEventListener("click", function () { selectTab("coach"); $("gen-topic").focus(); });
    $("btn-generate").addEventListener("click", generate);
    $("btn-ask").addEventListener("click", function () { ask(null); });
    $("gen-topic").addEventListener("keydown", function (e) { if (e.key === "Enter") generate(); });
    Array.prototype.forEach.call(document.querySelectorAll(".chip-btn"), function (b) {
      b.addEventListener("click", function () { ask(b.dataset.ask); });
    });
    loadProviders();

    $("btn-reset").addEventListener("click", function () {
      if (!current) return;
      if (confirm("Restore the starter code for this drill? Your current edits will be lost.")) {
        editor.setValue(current.starter);
        saveCode(current.slug, current.starter);
        markSaved();
      }
    });

    // reference modal
    $("btn-ref").addEventListener("click", openRef);
    $("btn-close-ref").addEventListener("click", closeRef);
    $("modal").addEventListener("click", function (e) { if (e.target === $("modal")) closeRef(); });
    $("btn-copy-ref").addEventListener("click", function () {
      if (current) navigator.clipboard.writeText(current.reference).then(function () { toast("Reference copied"); });
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeRef(); });

    setupTimer();
    setupSplitters();
  }

  function openRef() {
    if (!current) return;
    var host = $("ref-code");
    host.innerHTML = "<pre>colorizing…</pre>";
    monaco.editor.colorize(current.reference, "python", { tabSize: 4 }).then(function (html) {
      host.innerHTML = "<pre>" + html + "</pre>";
    });
    $("modal").hidden = false;
  }
  function closeRef() { $("modal").hidden = true; }

  // ---- 90-minute timer ----
  function setupTimer() {
    var total = 90 * 60;
    var remaining = total;
    var ticking = false;
    var iv = null;
    var face = $("timer-face");
    var wrap = $("timer");
    var toggle = $("timer-toggle");

    function fmt(s) {
      var m = Math.floor(s / 60), ss = s % 60;
      return (m < 10 ? "0" : "") + m + ":" + (ss < 10 ? "0" : "") + ss;
    }
    function paint() {
      face.textContent = fmt(remaining);
      wrap.classList.toggle("warn", remaining <= 300 && remaining > 60);
      wrap.classList.toggle("danger", remaining <= 60);
    }
    function tick() {
      if (remaining <= 0) { stop(); return; }
      remaining--;
      paint();
    }
    function start() { ticking = true; toggle.textContent = "❚❚"; iv = setInterval(tick, 1000); }
    function stop() { ticking = false; toggle.textContent = "▶"; clearInterval(iv); }

    toggle.addEventListener("click", function () { ticking ? stop() : start(); });
    $("timer-reset").addEventListener("click", function () { stop(); remaining = total; paint(); });
    paint();
  }

  // ---- draggable splitters ----
  function setupSplitters() {
    var root = document.documentElement;
    ["gutter-left", "gutter-right"].forEach(function (id) {
      var g = $(id);
      var side = g.dataset.side;
      g.addEventListener("pointerdown", function (e) {
        e.preventDefault();
        g.classList.add("dragging");
        g.setPointerCapture(e.pointerId);
        var wb = $("workbench").getBoundingClientRect();

        function move(ev) {
          if (side === "left") {
            var hiL = Math.max(240, wb.width - 620);
            var w = Math.min(Math.max(ev.clientX - wb.left, 240), hiL);
            root.style.setProperty("--left", w + "px");
          } else {
            var hiR = Math.max(300, wb.width - 620);
            var w2 = Math.min(Math.max(wb.right - ev.clientX, 300), hiR);
            root.style.setProperty("--right", w2 + "px");
          }
        }
        function up(ev) {
          g.classList.remove("dragging");
          g.releasePointerCapture(ev.pointerId);
          g.removeEventListener("pointermove", move);
          g.removeEventListener("pointerup", up);
        }
        g.addEventListener("pointermove", move);
        g.addEventListener("pointerup", up);
      });
    });
  }

  // ------------------------------------------------------------ util
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
})();
