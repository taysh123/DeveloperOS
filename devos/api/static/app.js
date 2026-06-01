/* DeveloperOS dashboard — React via htm (no build step). Reads the read-only local API. */
(function () {
  "use strict";
  var html = htm.bind(React.createElement);
  var useState = React.useState, useEffect = React.useEffect;

  function useApi(path) {
    var s = useState(null), data = s[0], setData = s[1];
    useEffect(function () {
      var alive = true;
      fetch(path).then(function (r) { return r.json(); })
        .then(function (d) { if (alive) setData(d); })
        .catch(function () { if (alive) setData({ error: true }); });
      return function () { alive = false; };
    }, [path]);
    return data;
  }

  function Stat(props) {
    return html`<div class=${"card stat " + props.k}>
      <div class="n">${props.n}</div><div class="l">${props.label}</div></div>`;
  }

  function TaskLine(props) {
    var t = props.t;
    return html`<div class="item">
      <span class=${"badge " + t.status}>${t.status}</span>
      <span class=${"badge " + t.priority}>${t.priority}</span>
      <strong>#${t.id}</strong> ${t.title}</div>`;
  }

  function LeftOff(props) {
    var w = props.w || {};
    if (!w.task && !w.memory) return html`<div class="muted">Nothing yet.</div>`;
    return html`<div>
      ${w.task && html`<div class="item">Last touched task:
        <span class=${"badge " + w.task.status}>${w.task.status}</span>
        <strong>#${w.task.id}</strong> ${w.task.title}</div>`}
      ${w.memory && html`<div class="item">Recent memory:
        <span class="badge">${w.memory.kind}</span> ${w.memory.title}</div>`}
    </div>`;
  }

  function Activity(props) {
    var items = props.items || [];
    if (!items.length) return html`<div class="muted">No activity yet.</div>`;
    return items.map(function (a, i) {
      return html`<div class="item" key=${i}>
        <span class="badge">${a.type}</span> ${a.title}
        <span class="muted"> — ${(a.when || "").replace("T", " ")}</span></div>`;
    });
  }

  function Recall() {
    var qs = useState(""), q = qs[0], setQ = qs[1];
    var rs = useState(null), res = rs[0], setRes = rs[1];
    function go(e) {
      e.preventDefault();
      fetch("/api/recall?q=" + encodeURIComponent(q)).then(function (r) { return r.json(); })
        .then(setRes).catch(function () { setRes({ error: true }); });
    }
    return html`<div class="panel">
      <h2>Recall — search memory, tasks & code</h2>
      <form class="search" onSubmit=${go}>
        <input placeholder="e.g. provider, auth, fts5..." value=${q}
               onInput=${function (e) { setQ(e.target.value); }} />
        <button type="submit">Recall</button>
      </form>
      ${res && !res.error && html`<div>
        ${res.memory.map(function (m, i) { return html`<div class="item" key=${"m" + i}>
          <span class="badge">memory/${m.kind}</span> ${m.title}</div>`; })}
        ${res.tasks.map(function (t, i) { return html`<${TaskLine} t=${t} key=${"t" + i} />`; })}
        ${res.code.map(function (c, i) { return html`<div class="item" key=${"c" + i}>
          <span class="badge">code</span> <code>${c.location}</code> [${c.project}]</div>`; })}
        ${(!res.memory.length && !res.tasks.length && !res.code.length)
          && html`<div class="muted">No matches.</div>`}
      </div>`}
    </div>`;
  }

  function App() {
    var ov = useApi("/api/overview");
    if (!ov) return html`<div class="wrap muted">Loading…</div>`;
    if (ov.error) return html`<div class="wrap">API error. Is <code>devos serve</code> running?</div>`;
    var c = ov.task_counts || {};
    return html`<div class="wrap">
      <header class="top"><h1>DeveloperOS</h1>
        <span class="sub">local dashboard · ${ov.projects.length} project(s)</span></header>
      <div class="grid cards">
        <${Stat} k="todo" n=${c.todo || 0} label="To do" />
        <${Stat} k="in_progress" n=${c.in_progress || 0} label="In progress" />
        <${Stat} k="blocked" n=${c.blocked || 0} label="Blocked" />
        <${Stat} k="done" n=${c.done || 0} label="Done" />
      </div>
      <div class="grid panels">
        <div class="panel"><h2>Where I left off</h2><${LeftOff} w=${ov.where_i_left_off} /></div>
        <div class="panel"><h2>Blocked items</h2>
          ${ov.blocked.length ? ov.blocked.map(function (t, i) {
              return html`<${TaskLine} t=${t} key=${i} />`; })
            : html`<div class="muted">Nothing blocked. </div>`}</div>
        <div class="panel"><h2>Recent activity</h2><${Activity} items=${ov.recent_activity} /></div>
        <div class="panel"><h2>Projects</h2>
          ${ov.projects.map(function (p, i) { return html`<div class="item" key=${i}>
            <strong>${p.name}</strong> <span class="muted">${p.file_count} files</span></div>`; })}</div>
      </div>
      <${Recall} />
      <div class="footer">DeveloperOS · local-first · read-only dashboard · mock AI provider</div>
    </div>`;
  }

  ReactDOM.createRoot(document.getElementById("root")).render(html`<${App} />`);
})();
