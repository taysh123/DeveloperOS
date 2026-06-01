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

  // --- shell + tabs --------------------------------------------------------
  var TABS = [
    { id: "home", label: "Home" },
    { id: "tasks", label: "Tasks" },
    { id: "notes", label: "Notes" },
    { id: "assist", label: "Search & Ask" }
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
      </main>
      <div class="footer">DeveloperOS · local-first · runs only on your machine</div>
    </div>`;
  }

  ReactDOM.createRoot(document.getElementById("root")).render(html`<${App} />`);
})();
