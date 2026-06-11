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

  // Lightweight two-step delete: ghost "Delete" -> inline "Yes, delete / Cancel".
  // Used for low-impact deletes (tasks, notes). Projects use a stricter type-to-confirm.
  function ConfirmDelete(props) {
    var c = useState(false), confirming = c[0], setConfirming = c[1];
    if (confirming) {
      return html`<span class="confirmdelete">
        <span class="muted">${props.prompt || "Delete?"}</span>
        <button class="btn small danger" type="button" disabled=${props.busy}
          onClick=${function () { props.onConfirm(); }}>Yes, delete</button>
        <button class="btn small ghost" type="button" disabled=${props.busy}
          onClick=${function () { setConfirming(false); }}>Cancel</button>
      </span>`;
    }
    return html`<button class="btn small ghost danger-text" type="button"
      onClick=${function () { setConfirming(true); }}>${props.label || "Delete"}</button>`;
  }

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
    var pj = useState(""), proj = pj[0], setProj = pj[1];
    var e = useState(""), err = e[0], setErr = e[1];
    var data = useApi("/api/projects", 0);
    var projects = (data && !data.error && data.projects) || [];
    function submit(ev) {
      ev.preventDefault();
      if (!title.trim()) { setErr("Please type what you want to get done."); return; }
      post("/api/tasks/create", { title: title.trim(), priority: prio, project: proj || undefined })
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
        <div class="field">
          <label for="task-project">Project</label>
          <select id="task-project" value=${proj} onChange=${function (ev) { setProj(ev.target.value); }}>
            <option value="">No project</option>
            ${projects.map(function (p) {
              return html`<option key=${p.id} value=${p.name}>${p.name}</option>`; })}
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
    var ed = useState(false), editing = ed[0], setEditing = ed[1];
    var ti = useState(t.title), title = ti[0], setTitle = ti[1];
    var bs = useState(false), busy = bs[0], setBusy = bs[1];
    function change(status) {
      post("/api/tasks/update", { id: t.id, status: status })
        .then(props.onDone).catch(function (x) { setErr(x.message); });
    }
    function saveTitle() {
      if (!title.trim()) { setErr("A task needs a title."); return; }
      post("/api/tasks/update", { id: t.id, title: title.trim() })
        .then(function () { setEditing(false); setErr(""); props.onDone(); })
        .catch(function (x) { setErr(x.message); });
    }
    function remove() {
      setBusy(true);
      post("/api/tasks/delete", { id: t.id })
        .then(props.onDone).catch(function (x) { setBusy(false); setErr(x.message); });
    }
    if (editing) {
      return html`<div class="item taskrow">
        <div class="field grow"><label class="sr-only" for=${"tt" + t.id}>Edit task title</label>
          <input id=${"tt" + t.id} value=${title}
                 onInput=${function (ev) { setTitle(ev.target.value); }} /></div>
        <div class="taskactions">
          <button class="btn small" type="button" onClick=${saveTitle}>Save</button>
          <button class="btn small ghost" type="button"
            onClick=${function () { setEditing(false); setTitle(t.title); setErr(""); }}>Cancel</button>
        </div>
        <${Msg} text=${err} />
      </div>`;
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
        <button class="btn small ghost" type="button"
          onClick=${function () { setEditing(true); }}>Edit</button>
        <${ConfirmDelete} busy=${busy} prompt="Delete this task?" onConfirm=${remove} />
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
    var pj = useState(""), proj = pj[0], setProj = pj[1];
    var e = useState(""), err = e[0], setErr = e[1];
    var data = useApi("/api/projects", 0);
    var projects = (data && !data.error && data.projects) || [];
    function submit(ev) {
      ev.preventDefault();
      if (!title.trim() || !body.trim()) { setErr("Please give your note a title and some text."); return; }
      post("/api/notes/create", { title: title.trim(), body: body.trim(), project: proj || undefined })
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
      <div class="field">
        <label for="note-project">Project</label>
        <select id="note-project" value=${proj} onChange=${function (ev) { setProj(ev.target.value); }}>
          <option value="">No project</option>
          ${projects.map(function (p) {
            return html`<option key=${p.id} value=${p.name}>${p.name}</option>`; })}
        </select>
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
    var bs = useState(false), busy = bs[0], setBusy = bs[1];
    function save() {
      post("/api/notes/update", { id: m.id, title: title.trim(), body: body.trim() })
        .then(function () { setEditing(false); setErr(""); props.onDone(); })
        .catch(function (x) { setErr(x.message); });
    }
    function remove() {
      setBusy(true);
      post("/api/notes/delete", { id: m.id })
        .then(props.onDone).catch(function (x) { setBusy(false); setErr(x.message); });
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
        <div class="row">
          <button class="btn small ghost" type="button" onClick=${function () { setEditing(true); }}>Edit</button>
          <${ConfirmDelete} busy=${busy} prompt="Delete this note?" onConfirm=${remove} />
        </div>
      </div>
      <div class="muted notebody">${m.body}</div>
      <${Msg} text=${err} />
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
    var dn = useState(""), delName = dn[0], setDelName = dn[1];
    var db = useState(false), delBusy = db[0], setDelBusy = db[1];
    var de = useState(""), delErr = de[0], setDelErr = de[1];
    if (!data) return html`<${Empty}>Loading…<//>`;
    if (data.error) return html`<${Empty}>Couldn't load this project.<//>`;
    var p = data.project, idx = data.index || {}, cats = data.by_category || {};
    var catKeys = Object.keys(cats).sort();
    function onRescanned(r) { setResult(r); setReScanning(false); props.reload(); }
    function removeProject() {
      setDelBusy(true); setDelErr("");
      post("/api/projects/delete", { id: props.id })
        .then(function () { props.reload(); props.onBack(); })
        .catch(function (x) { setDelBusy(false); setDelErr(x.message); });
    }
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
      <div class="panel danger-zone">
        <h2>Danger zone</h2>
        <p class="muted">Deleting removes <strong>${p.name}</strong> from DeveloperOS — its index, and any
          tasks and notes attached to this project. <strong>Your files on disk are not touched.</strong>
          This can't be undone.</p>
        <div class="field">
          <label for="del-confirm">Type the project name <code>${p.name}</code> to confirm</label>
          <input id="del-confirm" value=${delName} placeholder=${p.name} autoComplete="off"
                 onInput=${function (ev) { setDelName(ev.target.value); }} />
        </div>
        <button class="btn danger" type="button"
          disabled=${delBusy || delName.trim() !== p.name}
          onClick=${removeProject}>${delBusy ? "Deleting…" : "Delete this project"}</button>
        <${Msg} text=${delErr} />
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

  // --- LEARNING CENTER -----------------------------------------------------
  function qurl(base, params) {
    var parts = [];
    Object.keys(params).forEach(function (k) {
      if (params[k] != null && params[k] !== "") parts.push(k + "=" + encodeURIComponent(params[k]));
    });
    return base + (parts.length ? "?" + parts.join("&") : "");
  }

  // Renders a grounded answer (text + sources) with a friendly note when ungrounded.
  function AnswerBlock(props) {
    var d = props.d;
    return html`<div>
      ${!d.grounded ? html`<${Msg} kind="error"
        text="Not enough of your indexed code matched this. Try a file path, different words, or import/re-scan the project in the Projects tab." />` : null}
      <div class="answer"><p>${d.text}</p>
        ${d.sources && d.sources.length ? html`<div class="sources">
          <div class="muted">Based on your code:</div>
          ${d.sources.map(function (s, i) {
            return html`<div class="item" key=${i}><code>${s.location}</code>
              <span class="muted"> [${s.project}]</span></div>`; })}
        </div>` : null}</div>
    </div>`;
  }

  function LearningView() {
    var tg = useState(""), target = tg[0], setTarget = tg[1];
    var pr = useState(""), project = pr[0], setProject = pr[1];
    var lv = useState("intermediate"), level = lv[0], setLevel = lv[1];
    var rk = useState(null), kind = rk[0], setKind = rk[1];
    var rs = useState(null), result = rs[0], setResult = rs[1];
    var er = useState(""), err = er[0], setErr = er[1];
    var an = useState(""), answer = an[0], setAnswer = an[1];
    var gr = useState(null), grade = gr[0], setGrade = gr[1];
    var ge = useState(""), gErr = ge[0], setGErr = ge[1];

    var pj = useApi("/api/projects", 0);
    var projects = (pj && !pj.error && pj.projects) || [];

    function run(which) {
      if (!target.trim()) { setErr("Type a file path or a topic to learn about."); return; }
      setErr(""); setKind(which); setResult("loading");
      var ep = which === "learn" ? "/api/learn" : which === "quiz" ? "/api/quiz" : "/api/exercise";
      var params = { target: target.trim(), project: project || undefined };
      if (which === "learn") params.level = level;
      fetch(qurl(ep, params)).then(function (r) { return r.json(); })
        .then(setResult).catch(function () { setResult({ error: true }); });
    }
    function runGrade(ev) {
      ev.preventDefault();
      if (!target.trim()) { setGErr("Fill in what you're learning about (the box at the top) first."); return; }
      if (!answer.trim()) { setGErr("Write your answer first."); return; }
      setGErr(""); setGrade("loading");
      post("/api/grade", { target: target.trim(), answer: answer.trim(), project: project || undefined })
        .then(setGrade).catch(function (x) { setGrade({ error: true, message: x.message }); });
    }

    var resultTitle = kind === "learn" ? "Explanation" : kind === "quiz" ? "Quiz" : "Exercises";

    return html`<div>
      <div class="panel form">
        <h2>Learn from your code</h2>
        <p class="muted">Pick a file or a topic from a project you've indexed, then have DeveloperOS
          explain it, quiz you, or set practice exercises — all grounded in your real code, offline.</p>
        <div class="field">
          <label for="learn-target">File path or topic</label>
          <input id="learn-target" value=${target} placeholder="e.g. src/app.py — or a topic like “routing”"
                 onInput=${function (ev) { setTarget(ev.target.value); }} />
        </div>
        <div class="row">
          <div class="field">
            <label for="learn-project">Project (optional)</label>
            <select id="learn-project" value=${project}
                    onChange=${function (ev) { setProject(ev.target.value); }}>
              <option value="">Any project</option>
              ${projects.map(function (p) {
                return html`<option key=${p.id} value=${p.name}>${p.name}</option>`; })}
            </select>
          </div>
          <div class="field">
            <label for="learn-level">Explanation depth</label>
            <select id="learn-level" value=${level} onChange=${function (ev) { setLevel(ev.target.value); }}>
              <option value="eli5">Beginner (plain English)</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
        </div>
        <div class="row">
          <button class="btn" type="button" onClick=${function () { run("learn"); }}>Explain it</button>
          <button class="btn ghost" type="button" onClick=${function () { run("quiz"); }}>Quiz me</button>
          <button class="btn ghost" type="button" onClick=${function () { run("exercise"); }}>Give me exercises</button>
        </div>
        <${Msg} text=${err} />
      </div>

      ${result === "loading" && html`<div class="panel"><${Empty}>Working on it…<//></div>`}
      ${result && result !== "loading" && html`<div class="panel">
        <h2>${resultTitle}</h2>
        ${result.error ? html`<${Msg} text="Something went wrong. Try again." />`
          : html`<${AnswerBlock} d=${result} />`}
      </div>`}

      <form class="panel form" onSubmit=${runGrade}>
        <h2>Check my understanding</h2>
        <p class="muted">Explain the file or topic above in your own words and get grounded feedback.</p>
        <div class="field">
          <label for="learn-answer">Your answer</label>
          <textarea id="learn-answer" rows="4" value=${answer}
            placeholder="Write what you understand…"
            onInput=${function (ev) { setAnswer(ev.target.value); }}></textarea>
        </div>
        <button class="btn" type="submit">Grade my answer</button>
        <${Msg} text=${gErr} />
      </form>
      ${grade === "loading" && html`<div class="panel"><${Empty}>Grading…<//></div>`}
      ${grade && grade !== "loading" && html`<div class="panel">
        <h2>Feedback</h2>
        ${grade.error ? html`<${Msg} text=${grade.message || "Couldn't grade that."} />`
          : html`<${AnswerBlock} d=${grade} />`}
      </div>`}
    </div>`;
  }

  // --- CAREER --------------------------------------------------------------
  var JOB_STATUS_OPTS = [
    ["saved", "Saved"], ["applied", "Applied"], ["interview", "Interviewing"],
    ["offer", "Offer"], ["rejected", "Rejected"], ["closed", "Closed"]
  ];
  function statusKind(s) {
    return s === "offer" ? "done" : s === "interview" ? "in_progress"
      : (s === "rejected" || s === "closed") ? "blocked" : "";
  }
  function statusLabel(s) {
    var m = JOB_STATUS_OPTS.filter(function (o) { return o[0] === s; })[0];
    return m ? m[1] : s;
  }

  function AddJob(props) {
    var c = useState(""), company = c[0], setCompany = c[1];
    var r = useState(""), role = r[0], setRole = r[1];
    var u = useState(""), url = u[0], setUrl = u[1];
    var st = useState("saved"), status = st[0], setStatus = st[1];
    var n = useState(""), notes = n[0], setNotes = n[1];
    var e = useState(""), err = e[0], setErr = e[1];
    function submit(ev) {
      ev.preventDefault();
      if (!company.trim()) { setErr("Please enter the company name."); return; }
      post("/api/jobs/create", { company: company.trim(), role: role.trim() || undefined,
        url: url.trim() || undefined, status: status, notes: notes.trim() || undefined })
        .then(function () { setCompany(""); setRole(""); setUrl(""); setStatus("saved");
          setNotes(""); setErr(""); props.onDone(); })
        .catch(function (x) { setErr(x.message); });
    }
    return html`<form class="panel form" onSubmit=${submit}>
      <h2>Track a job application</h2>
      <div class="row">
        <div class="field grow">
          <label for="job-company">Company</label>
          <input id="job-company" value=${company} placeholder="e.g. Acme Corp"
                 onInput=${function (ev) { setCompany(ev.target.value); }} />
        </div>
        <div class="field grow">
          <label for="job-role">Role</label>
          <input id="job-role" value=${role} placeholder="e.g. Backend Engineer"
                 onInput=${function (ev) { setRole(ev.target.value); }} />
        </div>
        <div class="field">
          <label for="job-status">Status</label>
          <select id="job-status" value=${status} onChange=${function (ev) { setStatus(ev.target.value); }}>
            ${JOB_STATUS_OPTS.map(function (o) {
              return html`<option key=${o[0]} value=${o[0]}>${o[1]}</option>`; })}
          </select>
        </div>
      </div>
      <div class="field">
        <label for="job-url">Job link (optional)</label>
        <input id="job-url" value=${url} placeholder="https://…"
               onInput=${function (ev) { setUrl(ev.target.value); }} />
      </div>
      <div class="field">
        <label for="job-notes">Notes — paste the job description or what matters (used for interview prep & CV check)</label>
        <textarea id="job-notes" rows="3" value=${notes} placeholder="Responsibilities, required skills, your thoughts…"
                  onInput=${function (ev) { setNotes(ev.target.value); }}></textarea>
      </div>
      <button class="btn" type="submit">Save application</button>
      <${Msg} text=${err} />
    </form>`;
  }

  function JobRow(props) {
    var j = props.j;
    var ed = useState(false), editing = ed[0], setEditing = ed[1];
    var c = useState(j.company), company = c[0], setCompany = c[1];
    var r = useState(j.role || ""), role = r[0], setRole = r[1];
    var u = useState(j.url || ""), url = u[0], setUrl = u[1];
    var n = useState(j.notes || ""), notes = n[0], setNotes = n[1];
    var e = useState(""), err = e[0], setErr = e[1];
    var bs = useState(false), busy = bs[0], setBusy = bs[1];
    function changeStatus(s) {
      post("/api/jobs/update", { id: j.id, status: s }).then(props.onDone)
        .catch(function (x) { setErr(x.message); });
    }
    function save() {
      if (!company.trim()) { setErr("Company can't be empty."); return; }
      post("/api/jobs/update", { id: j.id, company: company.trim(), role: role.trim(),
        url: url.trim(), notes: notes.trim() })
        .then(function () { setEditing(false); setErr(""); props.onDone(); })
        .catch(function (x) { setErr(x.message); });
    }
    function remove() {
      setBusy(true);
      post("/api/jobs/delete", { id: j.id }).then(props.onDone)
        .catch(function (x) { setBusy(false); setErr(x.message); });
    }
    if (editing) {
      return html`<div class="item">
        <div class="row">
          <div class="field grow"><label class="sr-only" for=${"jc" + j.id}>Company</label>
            <input id=${"jc" + j.id} value=${company} onInput=${function (ev) { setCompany(ev.target.value); }} /></div>
          <div class="field grow"><label class="sr-only" for=${"jr" + j.id}>Role</label>
            <input id=${"jr" + j.id} value=${role} placeholder="Role"
                   onInput=${function (ev) { setRole(ev.target.value); }} /></div>
        </div>
        <div class="field"><label class="sr-only" for=${"ju" + j.id}>Link</label>
          <input id=${"ju" + j.id} value=${url} placeholder="Job link"
                 onInput=${function (ev) { setUrl(ev.target.value); }} /></div>
        <div class="field"><label class="sr-only" for=${"jn" + j.id}>Notes</label>
          <textarea id=${"jn" + j.id} rows="3" value=${notes}
                    onInput=${function (ev) { setNotes(ev.target.value); }}></textarea></div>
        <div class="row">
          <button class="btn small" type="button" onClick=${save}>Save</button>
          <button class="btn small ghost" type="button"
            onClick=${function () { setEditing(false); setCompany(j.company); setRole(j.role || "");
              setUrl(j.url || ""); setNotes(j.notes || ""); setErr(""); }}>Cancel</button>
        </div>
        <${Msg} text=${err} />
      </div>`;
    }
    return html`<div class="item">
      <div class="row spread">
        <div><${Badge} k=${statusKind(j.status)}>${statusLabel(j.status)}<//>
          <strong>${j.company}</strong>${j.role ? html`<span class="muted"> — ${j.role}</span>` : null}</div>
        <div class="row">
          <label class="sr-only" for=${"js" + j.id}>Change status for ${j.company}</label>
          <select id=${"js" + j.id} value=${j.status} onChange=${function (ev) { changeStatus(ev.target.value); }}>
            ${JOB_STATUS_OPTS.map(function (o) {
              return html`<option key=${o[0]} value=${o[0]}>${o[1]}</option>`; })}
          </select>
          <button class="btn small ghost" type="button" onClick=${function () { setEditing(true); }}>Edit</button>
          <${ConfirmDelete} busy=${busy} prompt="Remove this application?" onConfirm=${remove} />
        </div>
      </div>
      ${j.url ? html`<div class="item"><a href=${j.url} target="_blank" rel="noopener noreferrer">${j.url}</a></div>` : null}
      ${j.notes ? html`<div class="muted notebody">${j.notes}</div>` : null}
      <${Msg} text=${err} />
    </div>`;
  }

  function InterviewPrep(props) {
    var jobs = props.jobs || [];
    var sj = useState(""), jobId = sj[0], setJobId = sj[1];
    var rs = useState(null), res = rs[0], setRes = rs[1];
    function go() {
      var id = jobId || (jobs[0] && jobs[0].id);
      if (!id) return;
      setRes("loading");
      fetch("/api/jobs/interview?id=" + encodeURIComponent(id))
        .then(function (r) { return r.json(); }).then(setRes)
        .catch(function () { setRes({ error: true }); });
    }
    return html`<div class="panel form">
      <h2>Interview prep</h2>
      ${!jobs.length ? html`<${Empty}>Add a job application above (with notes) to generate interview questions.<//>`
        : html`<div>
          <div class="row">
            <div class="field grow">
              <label for="prep-job">Prepare for</label>
              <select id="prep-job" value=${jobId} onChange=${function (ev) { setJobId(ev.target.value); }}>
                ${jobs.map(function (j) {
                  return html`<option key=${j.id} value=${j.id}>${j.company}${j.role ? " — " + j.role : ""}</option>`; })}
              </select>
            </div>
            <button class="btn" type="button" onClick=${go}>Prepare questions</button>
          </div>
          ${res === "loading" && html`<${Empty}>Thinking…<//>`}
          ${res && res !== "loading" && (res.error
            ? html`<${Msg} text="Couldn't generate prep." />`
            : !res.grounded
              ? html`<${Msg} kind="error" text=${res.text || "Add notes to this job to generate prep."} />`
              : html`<div class="answer"><p>${res.text}</p>
                  ${res.sources && res.sources.length ? html`<div class="sources muted">
                    For: ${res.sources.map(function (s) { return s.company + (s.role ? " — " + s.role : ""); }).join(", ")}
                  </div>` : null}</div>`)}
        </div>`}
    </div>`;
  }

  function CvCheck(props) {
    var jobs = props.jobs || [];
    var cv = useState(""), cvText = cv[0], setCvText = cv[1];
    var tg = useState(""), against = tg[0], setAgainst = tg[1]; // "" = paste a description
    var td = useState(""), targetText = td[0], setTargetText = td[1];
    var rs = useState(null), res = rs[0], setRes = rs[1];
    var er = useState(""), err = er[0], setErr = er[1];
    function go(ev) {
      ev.preventDefault();
      if (!cvText.trim()) { setErr("Paste your CV text first."); return; }
      var body = { cv_text: cvText.trim() };
      if (against) { body.job_id = parseInt(against, 10); }
      else if (targetText.trim()) { body.target_text = targetText.trim(); }
      else { setErr("Pick a job to compare against, or paste a job description."); return; }
      setErr(""); setRes("loading");
      post("/api/cv", body).then(setRes).catch(function (x) { setRes(null); setErr(x.message); });
    }
    var pct = res && res !== "loading" && !res.error ? Math.round((res.coverage || 0) * 100) : 0;
    return html`<form class="panel form" onSubmit=${go}>
      <h2>CV match check</h2>
      <p class="muted">Paste your CV and compare it against a job's notes (or a pasted description) to see
        which keywords you cover — and which you're missing. Runs on your machine; your CV isn't stored.</p>
      <div class="field">
        <label for="cv-text">Your CV text</label>
        <textarea id="cv-text" rows="5" value=${cvText} placeholder="Paste your CV / resume text…"
                  onInput=${function (ev) { setCvText(ev.target.value); }}></textarea>
      </div>
      <div class="field">
        <label for="cv-against">Compare against</label>
        <select id="cv-against" value=${against} onChange=${function (ev) { setAgainst(ev.target.value); }}>
          <option value="">Paste a job description…</option>
          ${jobs.map(function (j) {
            return html`<option key=${j.id} value=${j.id}>${j.company}${j.role ? " — " + j.role : ""}</option>`; })}
        </select>
      </div>
      ${!against ? html`<div class="field">
        <label for="cv-target">Job description</label>
        <textarea id="cv-target" rows="3" value=${targetText} placeholder="Paste the job description / required skills…"
                  onInput=${function (ev) { setTargetText(ev.target.value); }}></textarea>
      </div>` : null}
      <button class="btn" type="submit">Check match</button>
      <${Msg} text=${err} />
      ${res === "loading" && html`<${Empty}>Checking…<//>`}
      ${res && res !== "loading" && !res.error && html`<div>
        <div class="item"><strong>${pct}% keyword match</strong>
          <span class="muted"> (${res.matched_count} of ${res.target_count} keywords${res.target_label ? " · " + res.target_label : ""})</span></div>
        ${res.matched.length ? html`<div class="item"><span class="muted">You cover:</span>
          <div class="catrow">${res.matched.map(function (k) {
            return html`<${Badge} k="done" key=${k}>${k}<//>`; })}</div></div>` : null}
        ${res.missing.length ? html`<div class="item"><span class="muted">Consider adding:</span>
          <div class="catrow">${res.missing.map(function (k) {
            return html`<${Badge} k="blocked" key=${k}>${k}<//>`; })}</div></div>`
          : html`<div class="item muted">Nice — you cover every keyword in the target.</div>`}
      </div>`}
    </form>`;
  }

  function CareerView() {
    var tk = useState(0), tick = tk[0], setTick = tk[1];
    function reload() { setTick(function (n) { return n + 1; }); }
    var data = useApi("/api/jobs", tick);
    var jobs = (data && !data.error && data.jobs) || [];
    return html`<div>
      <${AddJob} onDone=${reload} />
      <div class="panel"><h2>Your job applications</h2>
        ${!data ? html`<${Empty}>Loading…<//>`
          : jobs.length ? jobs.map(function (j) {
              return html`<${JobRow} j=${j} key=${j.id} onDone=${reload} />`; })
          : html`<${Empty}>No applications yet — add your first one above.<//>`}
      </div>
      <${InterviewPrep} jobs=${jobs} />
      <${CvCheck} jobs=${jobs} />
    </div>`;
  }

  // --- MEETING --------------------------------------------------------------
  function ActionItemsBridge(props) {
    // Turn extracted action items into tasks: review + select first, then one
    // guarded POST per selected item (reuses /api/tasks/create — no new write path).
    var items = props.items || [];
    var sel = useState(items.map(function () { return true; })), checked = sel[0], setChecked = sel[1];
    var bs = useState(false), busy = bs[0], setBusy = bs[1];
    var dn = useState(null), done = dn[0], setDone = dn[1];
    var er = useState(""), err = er[0], setErr = er[1];

    function toggle(i) {
      setChecked(function (prev) {
        var next = prev.slice(); next[i] = !next[i]; return next;
      });
    }
    function createTasks() {
      var todo = items.filter(function (_, i) { return checked[i]; });
      if (!todo.length) { setErr("Select at least one action item."); return; }
      setErr(""); setBusy(true); setDone(null);
      var ok = 0;
      // Sequential posts keep the API simple and surface the first real error.
      var chain = todo.reduce(function (p, title) {
        return p.then(function () {
          return post("/api/tasks/create", { title: title }).then(function () { ok += 1; });
        });
      }, Promise.resolve());
      chain.then(function () { setDone(ok); setBusy(false); })
        .catch(function (x) { setErr(x.message + (ok ? " (" + ok + " created before the error)" : "")); setBusy(false); });
    }

    if (!items.length) return null;
    return html`<div class="panel">
      <h2>Action items → tasks</h2>
      <p class="muted">Found in your notes. Untick anything you don't want, then create them as tasks.</p>
      ${items.map(function (it, i) {
        return html`<label class="item" key=${i} style="display:flex;gap:.5em;align-items:flex-start;cursor:pointer">
          <input type="checkbox" checked=${checked[i]} onChange=${function () { toggle(i); }} />
          <span>${it}</span></label>`;
      })}
      <div class="row">
        <button class="btn" type="button" onClick=${createTasks} disabled=${busy || done !== null}>
          ${busy ? "Creating…" : done !== null ? "Created ✓" : "Create selected as tasks"}</button>
      </div>
      ${done !== null && html`<div class="msg ok" role="status">${done} task(s) created — see the Tasks tab.</div>`}
      <${Msg} text=${err} />
    </div>`;
  }

  function MeetingView() {
    var tx = useState(""), text = tx[0], setText = tx[1];
    var lb = useState(""), label = lb[0], setLabel = lb[1];
    var rs = useState(null), res = rs[0], setRes = rs[1];
    var bs = useState(false), busy = bs[0], setBusy = bs[1];
    var er = useState(""), err = er[0], setErr = er[1];

    function summarize(ev) {
      ev.preventDefault();
      if (!text.trim()) { setErr("Paste your meeting notes or transcript first."); return; }
      setErr(""); setBusy(true); setRes(null);
      post("/api/meeting", { text: text, source_label: label })
        .then(function (d) { setRes(d); setBusy(false); })
        .catch(function (x) { setErr(x.message); setBusy(false); });
    }
    function clear() { setText(""); setLabel(""); setRes(null); setErr(""); }

    return html`<div>
      <form class="panel form" onSubmit=${summarize}>
        <h2>Summarize a meeting</h2>
        <p class="muted">Paste meeting notes or a transcript and get a summary, the decisions made,
          and the action items — which you can turn into tasks with one click.
          Nothing is uploaded or saved: the text stays on your machine and is not persisted.</p>
        <div class="field">
          <label for="mtg-label">Where is this from? (optional)</label>
          <input id="mtg-label" value=${label} placeholder="e.g. Sprint planning — June 11"
            onInput=${function (ev) { setLabel(ev.target.value); }} />
        </div>
        <div class="field">
          <label for="mtg-text">Meeting notes or transcript</label>
          <textarea id="mtg-text" rows="10" value=${text}
            placeholder=${"Paste here, e.g.\nWe agreed to ship Friday.\nAction items\n- Alice fixes the login bug\n- Bob updates the docs"}
            onInput=${function (ev) { setText(ev.target.value); }}></textarea>
        </div>
        <div class="row">
          <button class="btn" type="submit" disabled=${busy}>${busy ? "Summarizing…" : "Summarize"}</button>
          <button class="btn ghost" type="button" onClick=${clear} disabled=${busy}>Clear</button>
        </div>
        <${Msg} text=${err} />
      </form>

      ${busy && html`<${Empty}>Summarizing…<//>`}
      ${res && html`<div>
        <div class="panel">
          <div class="panelhead"><h2>Summary${res.source_label ? " — " + res.source_label : ""}</h2>
            <${Badge} k=${res.grounded ? "done" : "blocked"}>${res.provider}<//></div>
          <div class="answer"><p style="white-space:pre-wrap">${res.text}</p></div>
        </div>
        <${ActionItemsBridge} items=${res.action_items} key=${res.text} />
        ${res.action_items && !res.action_items.length ? html`<${Empty}>
          No action items detected. Tip: bullets under an “Action items” heading, or lines
          starting with “TODO:” / “Action:”, are picked up automatically.<//>` : null}
      </div>`}
      ${!res && !busy && html`<${Empty}>Paste your notes above and click Summarize.<//>`}
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
    { id: "learning", label: "Learn" },
    { id: "career", label: "Career" },
    { id: "meeting", label: "Meeting" },
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
        ${tab === "learning" && html`<${LearningView} />`}
        ${tab === "career" && html`<${CareerView} />`}
        ${tab === "meeting" && html`<${MeetingView} />`}
        ${tab === "settings" && html`<${SettingsView} />`}
      </main>
      <div class="footer">DeveloperOS · local-first · runs only on your machine</div>
    </div>`;
  }

  ReactDOM.createRoot(document.getElementById("root")).render(html`<${App} />`);
})();
