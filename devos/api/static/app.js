/* DeveloperOS dashboard — React via htm (no build step).
   Reads the local API and performs guarded actions (tasks, notes) with a CSRF token. */
(function () {
  "use strict";
  var html = htm.bind(React.createElement);
  var useState = React.useState, useEffect = React.useEffect;

  // --- API helpers ---------------------------------------------------------
  var _token = null;
  function token() {
    if (_token) return Promise.resolve(_token);
    return fetch("/api/session").then(function (r) { return r.json(); })
      .then(function (d) { _token = d.token; return _token; });
  }
  function post(path, body) {
    return token().then(function (tok) {
      return fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-DevOS-Token": tok },
        body: JSON.stringify(body)
      }).then(function (r) {
        return r.json().then(function (d) {
          if (!r.ok) throw new Error((d && d.error) || ("Something went wrong (" + r.status + ")"));
          return d;
        });
      });
    });
  }

  function useApi(path, dep) {
    var s = useState(null), data = s[0], setData = s[1];
    useEffect(function () {
      var alive = true;
      setData(null);
      fetch(path).then(function (r) { return r.json(); })
        .then(function (d) { if (alive) setData(d); })
        .catch(function () { if (alive) setData({ error: true }); });
      return function () { alive = false; };
    }, [path, dep]);
    return data;
  }

  // --- small presentational pieces ----------------------------------------
  function Stat(props) {
    return html`<div class=${"card stat " + props.k}>
      <div class="n">${props.n}</div><div class="l">${props.label}</div></div>`;
  }

  function Badge(props) {
    return html`<span class=${"badge " + (props.k || "")}>${props.children}</span>`;
  }

  function Msg(props) {
    if (!props.text) return null;
    return html`<div class=${"msg " + (props.kind || "error")} role="status">${props.text}</div>`;
  }

  function Empty(props) { return html`<div class="muted empty">${props.children}</div>`; }

  // --- HOME ----------------------------------------------------------------
  function Activity(props) {
    var items = props.items || [];
    if (!items.length) return html`<${Empty}>No activity yet.<//>`;
    return items.map(function (a, i) {
      return html`<div class="item" key=${i}>
        <${Badge}>${a.type}<//> ${a.title}
        <span class="muted"> — ${(a.when || "").replace("T", " ")}</span></div>`;
    });
  }

  function HomeView(props) {
    var ov = useApi("/api/overview", props.tick);
    if (!ov) return html`<${Empty}>Loading…<//>`;
    if (ov.error) return html`<${Empty}>Couldn't load your overview. Is the dashboard still running?<//>`;
    var c = ov.task_counts || {}, w = ov.where_i_left_off || {};
    return html`<div>
      <div class="grid cards">
        <${Stat} k="todo" n=${c.todo || 0} label="To do" />
        <${Stat} k="in_progress" n=${c.in_progress || 0} label="In progress" />
        <${Stat} k="blocked" n=${c.blocked || 0} label="Blocked" />
        <${Stat} k="done" n=${c.done || 0} label="Done" />
      </div>
      <div class="grid panels">
        <div class="panel"><h2>Where you left off</h2>
          ${(!w.task && !w.memory) ? html`<${Empty}>Nothing yet — add a task or a note to get started.<//>`
            : html`<div>
              ${w.task && html`<div class="item">Last task:
                <${Badge} k=${w.task.status}>${w.task.status}<//>
                <strong>#${w.task.id}</strong> ${w.task.title}</div>`}
              ${w.memory && html`<div class="item">Recent note:
                <${Badge}>${w.memory.kind}<//> ${w.memory.title}</div>`}
            </div>`}</div>
        <div class="panel"><h2>Needs attention</h2>
          ${ov.blocked.length ? ov.blocked.map(function (t, i) {
              return html`<div class="item" key=${i}><${Badge} k="blocked">blocked<//>
                <strong>#${t.id}</strong> ${t.title}</div>`; })
            : html`<${Empty}>Nothing blocked — nice.<//>`}</div>
        <div class="panel"><h2>Recent activity</h2><${Activity} items=${ov.recent_activity} /></div>
        <div class="panel"><h2>Your projects</h2>
          ${ov.projects.length ? ov.projects.map(function (p, i) {
              return html`<div class="item" key=${i}>
                <strong>${p.name}</strong> <span class="muted">${p.file_count} files</span></div>`; })
            : html`<${Empty}>No projects scanned yet.<//>`}</div>
      </div>
    </div>`;
  }

  // --- TASKS ---------------------------------------------------------------
  function AddTask(props) {
    var t = useState(""), title = t[0], setTitle = t[1];
    var p = useState("medium"), prio = p[0], setPrio = p[1];
    var e = useState(""), err = e[0], setErr = e[1];
    function submit(ev) {
      ev.preventDefault();
      if (!title.trim()) { setErr("Please type what you want to get done."); return; }
      post("/api/tasks/create", { title: title.trim(), priority: prio })
        .then(function () { setTitle(""); setPrio("medium"); setErr(""); props.onDone(); })
        .catch(function (x) { setErr(x.message); });
    }
    return html`<form class="panel form" onSubmit=${submit}>
      <h2>Add a task</h2>
      <div class="field">
        <label for="task-title">What do you want to get done?</label>
        <input id="task-title" value=${title} placeholder="e.g. Write the welcome email"
               onInput=${function (ev) { setTitle(ev.target.value); }} />
      </div>
      <div class="row">
        <div class="field">
          <label for="task-prio">Priority</label>
          <select id="task-prio" value=${prio} onChange=${function (ev) { setPrio(ev.target.value); }}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
        <button class="btn" type="submit">Add task</button>
      </div>
      <${Msg} text=${err} />
    </form>`;
  }

  function TaskRow(props) {
    var t = props.t;
    var e = useState(""), err = e[0], setErr = e[1];
    function change(status) {
      post("/api/tasks/update", { id: t.id, status: status })
        .then(props.onDone).catch(function (x) { setErr(x.message); });
    }
    return html`<div class="item taskrow">
      <div class="taskmeta">
        <${Badge} k=${t.status}>${t.status.replace("_", " ")}<//>
        <${Badge} k=${t.priority}>${t.priority}<//>
        <strong>#${t.id}</strong> ${t.title}
      </div>
      <div class="taskactions">
        ${t.status !== "done" && html`<button class="btn small" type="button"
            onClick=${function () { change("done"); }}>Mark done ✓</button>`}
        <label class="sr-only" for=${"st" + t.id}>Change status of task ${t.id}</label>
        <select id=${"st" + t.id} value=${t.status}
                onChange=${function (ev) { change(ev.target.value); }}>
          <option value="todo">To do</option>
          <option value="in_progress">In progress</option>
          <option value="blocked">Blocked</option>
          <option value="done">Done</option>
        </select>
      </div>
      <${Msg} text=${err} />
    </div>`;
  }

  function TasksView(props) {
    var f = useState(""), filter = f[0], setFilter = f[1];
    var path = filter ? "/api/tasks?status=" + filter : "/api/tasks";
    var data = useApi(path, props.tick);
    var tasks = (data && !data.error && data.tasks) || [];
    return html`<div>
      <${AddTask} onDone=${props.reload} />
      <div class="panel">
        <div class="panelhead">
          <h2>Your tasks</h2>
          <div class="field inline">
            <label for="task-filter">Show</label>
            <select id="task-filter" value=${filter} onChange=${function (ev) { setFilter(ev.target.value); }}>
              <option value="">All</option>
              <option value="todo">To do</option>
              <option value="in_progress">In progress</option>
              <option value="blocked">Blocked</option>
              <option value="done">Done</option>
            </select>
          </div>
        </div>
        ${!data ? html`<${Empty}>Loading…<//>`
          : tasks.length ? tasks.map(function (t) {
              return html`<${TaskRow} t=${t} key=${t.id} onDone=${props.reload} />`; })
          : html`<${Empty}>No tasks here yet. Add one above.<//>`}
      </div>
    </div>`;
  }

  // --- NOTES ---------------------------------------------------------------
  function AddNote(props) {
    var t = useState(""), title = t[0], setTitle = t[1];
    var b = useState(""), body = b[0], setBody = b[1];
    var e = useState(""), err = e[0], setErr = e[1];
    function submit(ev) {
      ev.preventDefault();
      if (!title.trim() || !body.trim()) { setErr("Please give your note a title and some text."); return; }
      post("/api/notes/create", { title: title.trim(), body: body.trim() })
        .then(function () { setTitle(""); setBody(""); setErr(""); props.onDone(); })
        .catch(function (x) { setErr(x.message); });
    }
    return html`<form class="panel form" onSubmit=${submit}>
      <h2>Add a note</h2>
      <div class="field">
        <label for="note-title">Title</label>
        <input id="note-title" value=${title} placeholder="e.g. Decision: use loopback only"
               onInput=${function (ev) { setTitle(ev.target.value); }} />
      </div>
      <div class="field">
        <label for="note-body">Note</label>
        <textarea id="note-body" rows="3" value=${body} placeholder="Write what you want to remember…"
                  onInput=${function (ev) { setBody(ev.target.value); }}></textarea>
      </div>
      <button class="btn" type="submit">Save note</button>
      <${Msg} text=${err} />
    </form>`;
  }

  function NoteRow(props) {
    var m = props.m;
    var ed = useState(false), editing = ed[0], setEditing = ed[1];
    var t = useState(m.title), title = t[0], setTitle = t[1];
    var b = useState(m.body), body = b[0], setBody = b[1];
    var e = useState(""), err = e[0], setErr = e[1];
    function save() {
      post("/api/notes/update", { id: m.id, title: title.trim(), body: body.trim() })
        .then(function () { setEditing(false); setErr(""); props.onDone(); })
        .catch(function (x) { setErr(x.message); });
    }
    if (editing) {
      return html`<div class="item">
        <div class="field"><label class="sr-only" for=${"nt" + m.id}>Note title</label>
          <input id=${"nt" + m.id} value=${title} onInput=${function (ev) { setTitle(ev.target.value); }} /></div>
        <div class="field"><label class="sr-only" for=${"nb" + m.id}>Note text</label>
          <textarea id=${"nb" + m.id} rows="3" value=${body}
            onInput=${function (ev) { setBody(ev.target.value); }}></textarea></div>
        <div class="row">
          <button class="btn small" type="button" onClick=${save}>Save</button>
          <button class="btn small ghost" type="button"
            onClick=${function () { setEditing(false); setTitle(m.title); setBody(m.body); }}>Cancel</button>
        </div>
        <${Msg} text=${err} />
      </div>`;
    }
    return html`<div class="item">
      <div class="row spread">
        <div><${Badge}>${m.kind}<//> <strong>${m.title}</strong></div>
        <button class="btn small ghost" type="button" onClick=${function () { setEditing(true); }}>Edit</button>
      </div>
      <div class="muted notebody">${m.body}</div>
    </div>`;
  }

  function NotesView(props) {
    var data = useApi("/api/memory", props.tick);
    var notes = (data && !data.error && data.memory) || [];
    return html`<div>
      <${AddNote} onDone=${props.reload} />
      <div class="panel"><h2>Your notes</h2>
        ${!data ? html`<${Empty}>Loading…<//>`
          : notes.length ? notes.map(function (m) {
              return html`<${NoteRow} m=${m} key=${m.id} onDone=${props.reload} />`; })
          : html`<${Empty}>No notes yet. Add your first one above.<//>`}
      </div>
    </div>`;
  }

  // --- SEARCH / AI ASSISTANT ----------------------------------------------
  function SearchView() {
    var sq = useState(""), sQ = sq[0], setSQ = sq[1];
    var sr = useState(null), sRes = sr[0], setSRes = sr[1];
    var aq = useState(""), aQ = aq[0], setAQ = aq[1];
    var ar = useState(null), aRes = ar[0], setARes = ar[1];
    var busy = useState(false), isBusy = busy[0], setBusy = busy[1];

    function runSearch(ev) {
      ev.preventDefault();
      if (!sQ.trim()) return;
      setSRes("loading");
      fetch("/api/search?q=" + encodeURIComponent(sQ)).then(function (r) { return r.json(); })
        .then(setSRes).catch(function () { setSRes({ error: true }); });
    }
    function runAsk(ev) {
      ev.preventDefault();
      if (!aQ.trim()) return;
      setBusy(true); setARes("loading");
      fetch("/api/ask?q=" + encodeURIComponent(aQ)).then(function (r) { return r.json(); })
        .then(function (d) { setARes(d); setBusy(false); })
        .catch(function () { setARes({ error: true }); setBusy(false); });
    }

    return html`<div>
      <form class="panel form" onSubmit=${runSearch}>
        <h2>Search your code</h2>
        <div class="row">
          <div class="field grow">
            <label for="search-q">Find files and snippets by keyword</label>
            <input id="search-q" value=${sQ} placeholder="e.g. provider, auth, login"
                   onInput=${function (ev) { setSQ(ev.target.value); }} />
          </div>
          <button class="btn" type="submit">Search</button>
        </div>
        ${sRes === "loading" && html`<${Empty}>Searching…<//>`}
        ${sRes && sRes !== "loading" && (sRes.error
          ? html`<${Msg} text="Search failed." />`
          : html`<div>${sRes.results.length ? sRes.results.map(function (r, i) {
              return html`<div class="item" key=${i}><code>${r.location}</code>
                <span class="muted"> [${r.project}]</span>
                <div class="snippet">${r.snippet}</div></div>`; })
            : html`<${Empty}>No matches. Try different words.<//>`}</div>`)}
      </form>

      <form class="panel form" onSubmit=${runAsk}>
        <h2>Ask about your project</h2>
        <div class="row">
          <div class="field grow">
            <label for="ask-q">Ask a question in plain English</label>
            <input id="ask-q" value=${aQ} placeholder="e.g. How does the dashboard load data?"
                   onInput=${function (ev) { setAQ(ev.target.value); }} />
          </div>
          <button class="btn" type="submit" disabled=${isBusy}>Ask</button>
        </div>
        ${aRes === "loading" && html`<${Empty}>Thinking…<//>`}
        ${aRes && aRes !== "loading" && (aRes.error
          ? html`<${Msg} text="Couldn't answer that." />`
          : html`<div class="answer">
              <p>${aRes.text}</p>
              ${aRes.sources && aRes.sources.length ? html`<div class="sources">
                <div class="muted">Based on:</div>
                ${aRes.sources.map(function (s, i) {
                  return html`<div class="item" key=${i}><code>${s.location}</code>
                    <span class="muted"> [${s.project}]</span></div>`; })}
              </div>` : null}
            </div>`)}
      </form>
    </div>`;
  }

  // --- DEBUG ---------------------------------------------------------------
  function DebugView() {
    var tx = useState(""), text = tx[0], setText = tx[1];
    var rs = useState(null), res = rs[0], setRes = rs[1];
    var bs = useState(false), busy = bs[0], setBusy = bs[1];
    var er = useState(""), err = er[0], setErr = er[1];

    function analyze(ev) {
      ev.preventDefault();
      if (!text.trim()) { setErr("Paste an error, stack trace, or log first."); return; }
      setErr(""); setBusy(true); setRes(null);
      post("/api/debug", { trace: text })
        .then(function (d) { setRes(d); setBusy(false); })
        .catch(function (x) { setErr(x.message); setBusy(false); });
    }
    function clear() { setText(""); setRes(null); setErr(""); }

    var conf = res && res.confidence;
    return html`<div>
      <form class="panel form" onSubmit=${analyze}>
        <h2>Debug an error</h2>
        <p class="muted">Paste an error message, a stack trace, or a chunk of logs and we'll point you
          to the likely cause and a fix — using your own code. Everything stays on your machine.</p>
        <div class="field">
          <label for="dbg-trace">Your error, stack trace, or log</label>
          <textarea id="dbg-trace" rows="8" value=${text} class="mono"
            placeholder=${"Paste here, e.g.\nTraceback (most recent call last):\n  File \"app.py\", line 12, in main\nValueError: ..."}
            onInput=${function (ev) { setText(ev.target.value); }}></textarea>
        </div>
        <div class="row">
          <button class="btn" type="submit" disabled=${busy}>${busy ? "Analyzing…" : "Analyze"}</button>
          <button class="btn ghost" type="button" onClick=${clear} disabled=${busy}>Clear</button>
        </div>
        <${Msg} text=${err} />
      </form>

      ${busy && html`<${Empty}>Analyzing…<//>`}
      ${res && html`<div>
        <div class="panel">
          <div class="panelhead"><h2>Summary</h2>
            <${Badge} k=${conf === "high" ? "done" : conf === "medium" ? "in_progress" : "blocked"}>
              ${conf} confidence<//></div>
          <div class="item">${res.error_type
            ? html`<strong>${res.error_type}</strong>: ${res.error_message || ""}`
            : html`<span class="muted">No clear error line found — we used the text and your code.</span>`}</div>
        </div>

        <div class="panel">
          <h2>What we think is going on</h2>
          ${!res.grounded && html`<${Msg} kind="error"
            text="Not enough of your indexed code matched this error. Import or re-scan the relevant project in the Projects tab, then try again." />`}
          <div class="answer"><p>${res.analysis}</p></div>
        </div>

        ${res.located && res.located.length ? html`<div class="panel">
          <h2>Where it points</h2>
          ${res.located.map(function (l, i) {
            return html`<div class="item" key=${i}><code>${l.rel_path}${l.line ? ":" + l.line : ""}</code>
              ${l.func ? html`<span class="muted"> in ${l.func}</span>` : null}
              ${l.has_code ? null : html`<span class="muted"> (not indexed)</span>`}</div>`; })}
        </div>` : null}

        ${res.sources && res.sources.length ? html`<div class="panel">
          <h2>Sources</h2>
          ${res.sources.map(function (s, i) {
            return html`<div class="item" key=${i}><span class="badge">code</span>
              <code>${s.location}</code> <span class="muted">[${s.project}]</span></div>`; })}
        </div>` : null}
      </div>`}
      ${!res && !busy && html`<${Empty}>Paste an error above and click Analyze.<//>`}
    </div>`;
  }

  // --- PROJECTS ------------------------------------------------------------
  function fmtWhen(s) {
    if (!s) return "never";
    return String(s).replace("T", " ").slice(0, 16);
  }

  function ScanResult(props) {
    var r = props.r;
    return html`<div class="msg ok" role="status">
      <strong>Imported “${r.project_name}”.</strong>
      ${r.total} file(s) recorded${r.indexed_chunks ? ", " + r.indexed_chunks + " sections indexed" : ""}.
      <span class="muted"> (+${r.added} new, ~${r.updated} updated, ${r.skipped} skipped)</span>
    </div>`;
  }

  // Reusable confirm-before-scan widget. Calls onDone(result) after a successful scan.
  function ScanFlow(props) {
    var pth = useState(props.path || ""), path = pth[0], setPath = pth[1];
    var nm = useState(""), name = nm[0], setName = nm[1];
    var cf = useState(false), confirming = cf[0], setConfirming = cf[1];
    var bs = useState(false), busy = bs[0], setBusy = bs[1];
    var er = useState(""), err = er[0], setErr = er[1];
    var fixedPath = !!props.path; // re-scan: path is locked to the project root

    function cont(ev) {
      ev.preventDefault();
      if (!path.trim()) { setErr("Please enter the folder you want to import."); return; }
      setErr(""); setConfirming(true);
    }
    function scanNow() {
      setBusy(true); setErr("");
      post("/api/projects/scan", { path: path.trim(), name: name.trim() || undefined })
        .then(function (r) { setBusy(false); setConfirming(false); props.onDone(r); })
        .catch(function (x) { setBusy(false); setConfirming(false); setErr(x.message); });
    }

    if (confirming) {
      return html`<div class="confirm">
        <p>You're about to import:</p>
        <p><code>${path.trim()}</code></p>
        <p class="muted">This reads the text files in that folder into your local index so you can
          search and ask about them. Nothing leaves your computer.</p>
        <div class="row">
          <button class="btn" type="button" onClick=${scanNow} disabled=${busy}>
            ${busy ? "Scanning…" : "Scan now"}</button>
          <button class="btn ghost" type="button" onClick=${function () { setConfirming(false); }}
                  disabled=${busy}>Cancel</button>
        </div>
        <${Msg} text=${err} />
      </div>`;
    }
    return html`<form class="form" onSubmit=${cont}>
      <div class="field">
        <label for="scan-path">Folder to import</label>
        <input id="scan-path" value=${path} readOnly=${fixedPath}
               placeholder="e.g. C:\\Projects\\my-app"
               onInput=${function (ev) { setPath(ev.target.value); }} />
      </div>
      ${!fixedPath && html`<div class="field">
        <label for="scan-name">Name (optional)</label>
        <input id="scan-name" value=${name} placeholder="defaults to the folder name"
               onInput=${function (ev) { setName(ev.target.value); }} />
      </div>`}
      <button class="btn" type="submit">${props.cta || "Continue"}</button>
      <${Msg} text=${err} />
    </form>`;
  }

  function ProjectDetail(props) {
    var data = useApi("/api/projects/detail?id=" + props.id, props.tick);
    var rescan = useState(false), reScanning = rescan[0], setReScanning = rescan[1];
    var done = useState(null), result = done[0], setResult = done[1];
    if (!data) return html`<${Empty}>Loading…<//>`;
    if (data.error) return html`<${Empty}>Couldn't load this project.<//>`;
    var p = data.project, idx = data.index || {}, cats = data.by_category || {};
    var catKeys = Object.keys(cats).sort();
    function onRescanned(r) { setResult(r); setReScanning(false); props.reload(); }
    return html`<div>
      <button class="btn ghost small" type="button" onClick=${props.onBack}>← Back to projects</button>
      <div class="panel detail">
        <div class="panelhead"><h2>${p.name}</h2>
          ${idx.chunks ? html`<button class="btn" type="button"
            onClick=${props.onStudy}>Study this project</button>` : null}</div>
        <div class="item"><span class="muted">Folder:</span> <code>${p.root_path}</code></div>
        <div class="grid cards">
          <${Stat} k="todo" n=${p.file_count} label="Files" />
          <${Stat} k="in_progress" n=${idx.chunks || 0} label="Indexed sections" />
        </div>
        <div class="item"><span class="muted">Last scanned:</span> ${fmtWhen(p.last_scanned_at)}</div>
        <div class="item"><span class="muted">Status:</span>
          ${idx.chunks ? "Indexed — ready to search and ask." : "Not indexed yet."}</div>
        ${catKeys.length ? html`<div class="item"><span class="muted">What's inside:</span>
          <div class="catrow">${catKeys.map(function (k) {
            return html`<${Badge} key=${k}>${k}: ${cats[k]}<//>`; })}</div></div>` : null}
      </div>
      <div class="panel">
        <div class="panelhead"><h2>Refresh this project</h2>
          ${!reScanning && html`<button class="btn small" type="button"
            onClick=${function () { setReScanning(true); setResult(null); }}>Re-scan</button>`}</div>
        ${result && html`<${ScanResult} r=${result} />`}
        ${reScanning && html`<${ScanFlow} path=${p.root_path} cta="Re-scan" onDone=${onRescanned} />`}
        ${!reScanning && !result && html`<${Empty}>Re-scan to pick up files you've added or changed.<//>`}
      </div>
    </div>`;
  }

  function ProjectAsk(props) {
    var qs = useState(""), q = qs[0], setQ = qs[1];
    var rs = useState(null), res = rs[0], setRes = rs[1];
    function go(e) {
      e.preventDefault();
      if (!q.trim()) return;
      setRes("loading");
      fetch("/api/ask?q=" + encodeURIComponent(q) + "&project=" + encodeURIComponent(props.project))
        .then(function (r) { return r.json(); }).then(setRes)
        .catch(function () { setRes({ error: true }); });
    }
    return html`<div class="panel form">
      <h2>Ask about this project</h2>
      <form class="row" onSubmit=${go}>
        <div class="field grow">
          <label for="study-ask">Ask anything in plain English</label>
          <input id="study-ask" value=${q} placeholder="e.g. Where does it start? How does X work?"
                 onInput=${function (e) { setQ(e.target.value); }} />
        </div>
        <button class="btn" type="submit">Ask</button>
      </form>
      ${res === "loading" && html`<${Empty}>Thinking…<//>`}
      ${res && res !== "loading" && (res.error
        ? html`<${Msg} text="Couldn't answer that." />`
        : html`<div class="answer"><p>${res.text}</p>
            ${res.sources && res.sources.length ? html`<div class="sources">
              <div class="muted">Based on:</div>
              ${res.sources.map(function (s, i) {
                return html`<div class="item" key=${i}><code>${s.location}</code></div>`; })}
            </div>` : null}</div>`)}
    </div>`;
  }

  function ProjectStudy(props) {
    var data = useApi("/api/projects/study?id=" + props.id, 0);
    if (!data) return html`<${Empty}>Loading…<//>`;
    if (data.error) return html`<${Empty}>Couldn't load this project.<//>`;
    var p = data.project, keys = data.key_files || [], ov = data.overview || {},
        qz = data.questions || {}, prep = data.interview_prep || [];
    var starters = keys.slice(0, 3);
    return html`<div>
      <button class="btn ghost small" type="button" onClick=${props.onBack}>← Back to project</button>
      <header class="top"><h1>Project Deep Dive</h1>
        <span class="sub">study “${p.name}” · ${p.file_count} files</span></header>

      <div class="panel">
        <h2>Start here</h2>
        ${starters.length ? html`<div>
          <div class="muted">Open these first — they're the busiest parts of the project.</div>
          ${starters.map(function (f, i) {
            return html`<div class="item" key=${i}><code>${f.rel_path}</code>
              <span class="muted"> · ${f.category}${f.lang ? " · " + f.lang : ""}</span></div>`; })}
        </div>` : html`<${Empty}>Import or re-scan this project first, then come back to study it.<//>`}
      </div>

      ${keys.length ? html`<div class="panel"><h2>Key files</h2>
        ${keys.map(function (f, i) {
          return html`<div class="item" key=${i}><code>${f.rel_path}</code>
            <${Badge}>${f.category}<//>${f.lang ? html`<span class="muted"> ${f.lang}</span>` : null}</div>`; })}
      </div>` : null}

      <div class="panel">
        <h2>How this works</h2>
        ${!ov.grounded && html`<${Msg} kind="error"
          text="Not enough indexed content yet. Import or re-scan this project in the Projects tab, then study it." />`}
        <div class="answer"><p>${ov.text}</p>
          ${ov.sources && ov.sources.length ? html`<div class="sources">
            <div class="muted">Based on:</div>
            ${ov.sources.map(function (s, i) {
              return html`<div class="item" key=${i}><code>${s.location}</code></div>`; })}
          </div>` : null}</div>
      </div>

      <div class="panel">
        <h2>Questions to explore</h2>
        ${qz.grounded
          ? html`<div class="answer"><p>${qz.text}</p></div>`
          : html`<${Empty}>${qz.text || "Index this project to generate study questions."}<//>`}
      </div>

      ${prep.length ? html`<div class="panel">
        <h2>Interview prep</h2>
        <div class="muted">Practice saying each of these out loud.</div>
        ${prep.map(function (line, i) {
          return html`<div class="item" key=${i}>${line}</div>`; })}
      </div>` : null}

      <${ProjectAsk} project=${p.name} />
    </div>`;
  }

  function ProjectsView(props) {
    var md = useState("list"), mode = md[0], setMode = md[1];
    var sel = useState(null), selectedId = sel[0], setSelectedId = sel[1];
    var res = useState(null), result = res[0], setResult = res[1];
    var data = useApi("/api/projects", props.tick);
    var projects = (data && !data.error && data.projects) || [];

    function open(id) { setSelectedId(id); setMode("detail"); }
    function onImported(r) { setResult(r); setMode("list"); props.reload(); }

    if (mode === "study" && selectedId != null) {
      return html`<${ProjectStudy} id=${selectedId}
        onBack=${function () { setMode("detail"); }} />`;
    }
    if (mode === "detail" && selectedId != null) {
      return html`<${ProjectDetail} id=${selectedId} tick=${props.tick} reload=${props.reload}
        onBack=${function () { setMode("list"); }}
        onStudy=${function () { setMode("study"); }} />`;
    }
    if (mode === "import") {
      return html`<div>
        <button class="btn ghost small" type="button"
          onClick=${function () { setMode("list"); }}>← Back to projects</button>
        <div class="panel form">
          <h2>Import a project</h2>
          <p class="muted">Point DeveloperOS at a project folder on your computer. It reads the text
            files inside so you can search them and ask questions. It runs entirely on your machine.</p>
          <${ScanFlow} cta="Continue" onDone=${onImported} />
        </div>
      </div>`;
    }
    // list
    return html`<div>
      <div class="panelhead">
        <h2>Your projects</h2>
        <button class="btn" type="button" onClick=${function () { setMode("import"); }}>Import a project</button>
      </div>
      ${result && html`<${ScanResult} r=${result} />`}
      ${!data ? html`<${Empty}>Loading…<//>`
        : projects.length ? html`<div class="grid panels">
            ${projects.map(function (p) {
              return html`<div class="panel projcard" key=${p.id}>
                <h2>${p.name}</h2>
                <div class="item"><strong>${p.file_count}</strong> files
                  <span class="muted"> · last scanned ${fmtWhen(p.last_scanned_at)}</span></div>
                <div class="item muted"><code>${p.root_path}</code></div>
                <button class="btn small ghost" type="button"
                  onClick=${function () { open(p.id); }}>View</button>
              </div>`; })}
          </div>`
        : html`<div class="panel"><${Empty}>No projects yet — import a folder to get started.<//>
            <button class="btn" type="button" onClick=${function () { setMode("import"); }}>Import a project</button>
          </div>`}
    </div>`;
  }

  // --- SETTINGS & AI MANAGEMENT --------------------------------------------
  function StatusRow(props) {
    return html`<div class="item statusrow">
      <span class="muted">${props.label}</span>
      <span class="statusval">${props.children}</span></div>`;
  }

  function SystemStatus(props) {
    var s = props.sys;
    if (!s || s.error) return html`<${Empty}>Couldn't load system status.<//>`;
    var prov = {};
    (s.providers || []).forEach(function (p) { prov[p.id] = p; });
    var effLabel = (prov[s.provider_effective] && prov[s.provider_effective].label) || s.provider_effective;
    var selLabel = (prov[s.provider_selected] && prov[s.provider_selected].label) || s.provider_selected;
    var differs = s.provider_selected !== s.provider_effective;
    return html`<div class="panel">
      <h2>System status</h2>
      <${StatusRow} label="Local-first">${s.local_first ? "Yes — your data stays on this machine" : "No"}<//>
      <${StatusRow} label="Works offline">${s.offline ? html`<${Badge} k="done">Offline<//> No internet needed` : "No"}<//>
      <${StatusRow} label="AI">${s.ai_enabled
        ? html`<${Badge} k="done">Enabled<//>` : html`<${Badge} k="blocked">Disabled<//>`}<//>
      <${StatusRow} label="Active provider">${effLabel}
        ${differs ? html`<span class="muted"> — you selected ${selLabel}, but it isn't available yet, so DeveloperOS is using the offline mock.</span>` : null}<//>
      <${StatusRow} label="Version">${s.version}<//>
      <${StatusRow} label="Roadmap phase">${s.roadmap_phase}<//>
      <${StatusRow} label="Projects indexed">${s.indexed_project_count}<//>
      <${StatusRow} label="Dashboard">${s.dashboard_maturity}<//>
    </div>`;
  }

  function ProviderChoice(props) {
    var p = props.p;
    return html`<label class=${"provrow" + (props.checked ? " checked" : "")}>
      <input type="radio" name="ai-provider" checked=${props.checked}
             onChange=${function () { props.onPick(p.id); }} />
      <div class="provbody">
        <div class="provhead">
          <strong>${p.label}</strong>
          <${Badge} k=${p.kind === "local" ? "done" : "in_progress"}>${p.kind === "local" ? "Local" : "Cloud"}<//>
          <${Badge} k=${p.free ? "done" : "high"}>${p.free ? "Free" : "May cost money"}<//>
          ${p.available ? null : html`<${Badge}>Coming soon<//>`}
        </div>
        <div class="muted">${p.blurb}</div>
        ${p.requires_key ? html`<div class="muted keyline">API key: ${p.key_present
          ? html`<span class="ok-text">detected in your environment</span>`
          : html`<span>not set — define <code>${p.key_env}</code> in your environment</span>`}</div>` : null}
      </div>
    </label>`;
  }

  function ProviderDetails(props) {
    var p = props.p;
    if (!p) return null;
    return html`<div class="panel">
      <h2>Provider configuration</h2>
      <p class="muted">DeveloperOS <strong>never stores API keys</strong>. Cloud providers read their
        key from an environment variable; local providers need no key. These fields are prepared for a
        future release and are disabled for now.</p>
      ${p.requires_key ? html`<div class="field">
        <label>API key</label>
        <input type="password" disabled placeholder=${"Set " + p.key_env + " in your environment"} />
        <div class="muted">${p.key_present ? "A key is currently detected in your environment." : "No key detected."}</div>
      </div>` : null}
      <div class="field">
        <label>Endpoint</label>
        <input disabled placeholder=${p.endpoint_hint || "Default endpoint (managed automatically)"} />
      </div>
      <div class="field">
        <label>Model</label>
        <select disabled><option>Coming soon</option></select>
      </div>
    </div>`;
  }

  function SettingsView() {
    var tk = useState(0), tick = tk[0], setTick = tk[1];
    var sys = useApi("/api/system", tick);
    var cfg = useApi("/api/settings", tick);
    var dp = useState(null), draftProv = dp[0], setDraftProv = dp[1];
    var de = useState(null), draftEn = de[0], setDraftEn = de[1];
    var bs = useState(false), busy = bs[0], setBusy = bs[1];
    var mg = useState(null), msg = mg[0], setMsg = mg[1];

    useEffect(function () {
      if (cfg && !cfg.error) { setDraftProv(cfg.ai_provider); setDraftEn(cfg.ai_enabled); }
    }, [cfg]);

    if (!sys || !cfg) return html`<${Empty}>Loading…<//>`;
    if (cfg.error) return html`<${Empty}>Couldn't load your settings.<//>`;

    var providers = cfg.providers || [];
    var selected = providers.filter(function (p) { return p.id === draftProv; })[0];
    var dirty = draftProv !== cfg.ai_provider || draftEn !== cfg.ai_enabled;
    var cloudSelected = selected && selected.kind === "cloud";

    function save() {
      setBusy(true); setMsg(null);
      post("/api/settings", { ai_provider: draftProv, ai_enabled: draftEn })
        .then(function () {
          setBusy(false);
          setMsg({ kind: "ok", text: "Saved. Your AI settings are updated." });
          setTick(function (n) { return n + 1; });
        })
        .catch(function (x) { setBusy(false); setMsg({ kind: "error", text: x.message }); });
    }

    return html`<div>
      <${SystemStatus} sys=${sys} />

      <div class="panel form">
        <h2>AI settings</h2>
        <div class="field inline">
          <label for="ai-enabled">Use AI features</label>
          <select id="ai-enabled" value=${draftEn ? "on" : "off"}
                  onChange=${function (ev) { setDraftEn(ev.target.value === "on"); }}>
            <option value="on">On</option>
            <option value="off">Off — turn all AI features off</option>
          </select>
        </div>

        <div class="field">
          <label>AI provider</label>
          <div class="provlist" role="radiogroup" aria-label="AI provider">
            ${providers.map(function (p) {
              return html`<${ProviderChoice} key=${p.id} p=${p} checked=${draftProv === p.id}
                onPick=${setDraftProv} />`; })}
          </div>
        </div>

        ${!draftEn ? html`<${Msg} kind="ok"
          text="AI is turned off. DeveloperOS still works for browsing, tasks and notes — it just won't run any AI features." />` : null}
        ${draftEn && cloudSelected && (!selected.available) ? html`<${Msg} kind="ok"
          text="Heads up: this is a cloud provider that isn't wired in yet, so DeveloperOS keeps running the offline mock — nothing leaves your machine until real providers ship." />` : null}
        ${draftEn && cloudSelected ? html`<${Msg} kind="error"
          text="Privacy & cost: cloud providers send your prompts over the internet and may cost money. Local options (Offline, Ollama) keep everything on your machine for free." />` : null}

        <div class="row">
          <button class="btn" type="button" onClick=${save} disabled=${busy || !dirty}>
            ${busy ? "Saving…" : "Save settings"}</button>
          ${dirty ? html`<button class="btn ghost" type="button" disabled=${busy}
            onClick=${function () { setDraftProv(cfg.ai_provider); setDraftEn(cfg.ai_enabled); setMsg(null); }}>Cancel</button>` : null}
        </div>
        ${msg ? html`<${Msg} kind=${msg.kind} text=${msg.text} />` : null}
      </div>

      <${ProviderDetails} p=${selected} />
    </div>`;
  }

  // --- shell + tabs --------------------------------------------------------
  var TABS = [
    { id: "home", label: "Home" },
    { id: "tasks", label: "Tasks" },
    { id: "notes", label: "Notes" },
    { id: "assist", label: "Search & Ask" },
    { id: "debug", label: "Debug" },
    { id: "projects", label: "Projects" },
    { id: "settings", label: "Settings" }
  ];

  function App() {
    var tb = useState("home"), tab = tb[0], setTab = tb[1];
    var tk = useState(0), tick = tk[0], setTick = tk[1];
    function reload() { setTick(function (n) { return n + 1; }); }
    var ov = useApi("/api/overview", 0); // header counts only (loads once)
    var pcount = ov && !ov.error && ov.projects ? ov.projects.length : 0;

    return html`<div class="wrap">
      <header class="top">
        <h1>DeveloperOS</h1>
        <span class="sub">your local workspace · ${pcount} project(s)</span>
      </header>
      <nav class="tabs" role="tablist" aria-label="Dashboard sections">
        ${TABS.map(function (t) {
          return html`<button key=${t.id} role="tab" type="button"
            aria-selected=${tab === t.id ? "true" : "false"}
            class=${"tab" + (tab === t.id ? " active" : "")}
            onClick=${function () { setTab(t.id); }}>${t.label}</button>`;
        })}
      </nav>
      <main>
        ${tab === "home" && html`<${HomeView} tick=${tick} />`}
        ${tab === "tasks" && html`<${TasksView} tick=${tick} reload=${reload} />`}
        ${tab === "notes" && html`<${NotesView} tick=${tick} reload=${reload} />`}
        ${tab === "assist" && html`<${SearchView} />`}
        ${tab === "debug" && html`<${DebugView} />`}
        ${tab === "projects" && html`<${ProjectsView} tick=${tick} reload=${reload} />`}
        ${tab === "settings" && html`<${SettingsView} />`}
      </main>
      <div class="footer">DeveloperOS · local-first · runs only on your machine</div>
    </div>`;
  }

  ReactDOM.createRoot(document.getElementById("root")).render(html`<${App} />`);
})();
