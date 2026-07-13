// Renders the registry client-side from registry.json (built by scripts/build.py).
// No framework, no external requests — self-contained static site.
(() => {
  "use strict";

  const grid = document.getElementById("grid");
  const empty = document.getElementById("empty");
  const q = document.getElementById("q");
  const countEl = document.getElementById("count");

  // Theme toggle: persist and stamp data-theme so CSS overrides win both ways.
  const themeBtn = document.getElementById("theme");
  const stored = localStorage.getItem("cw-theme");
  if (stored) document.documentElement.setAttribute("data-theme", stored);
  themeBtn.addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", cur);
    localStorage.setItem("cw-theme", cur);
  });

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // Show every install method the tool ships — the mix of script / brew / scoop / go makes
  // the cross-platform story obvious without a word of explanation. Lead with the curl|sh
  // script: it's the fleet's primary path and needs no package manager.
  const METHOD_ORDER = ["script", "brew", "scoop", "go"];
  const installRows = (inst) =>
    METHOD_ORDER.filter((m) => inst && inst[m])
      .map((m) =>
        `<div class="irow"><span class="ilabel">${m}</span>` +
        `<code>${esc(inst[m])}</code>` +
        `<button class="copy" type="button" data-cmd="${esc(inst[m])}" aria-label="Copy ${m} command">copy</button></div>`)
      .join("");

  let tools = [];

  // repoLabel strips the scheme so the card shows a clean "owner/repo" source link.
  const repoLabel = (url) => String(url).replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "");

  function card(t) {
    const li = document.createElement("li");
    li.className = "card";
    const chips = (t.tags || []).map((x) => `<span class="chip">${esc(x)}</span>`).join("");
    const agent = t.agent_ready ? `<span class="chip agent" title="Ships an MCP server + agent guard">agent-ready</span>` : "";
    li.innerHTML = `
      <div class="wraps">wraps ${esc(t.wraps)}</div>
      <h3><a href="${esc(t.repo)}" target="_blank" rel="noopener">${esc(t.binary)}</a></h3>
      <p class="desc">${esc(t.description)}</p>
      <div class="installs">${installRows(t.install)}</div>
      <div class="tags">${agent}${chips}</div>
      <a class="repo" href="${esc(t.repo)}" target="_blank" rel="noopener">${esc(repoLabel(t.repo))} ↗</a>`;
    li.querySelectorAll(".copy").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(btn.getAttribute("data-cmd") || "");
          btn.textContent = "copied";
          setTimeout(() => (btn.textContent = "copy"), 1200);
        } catch { btn.textContent = "⌘C"; }
      });
    });
    return li;
  }

  function render(list) {
    grid.replaceChildren(...list.map(card));
    empty.hidden = list.length > 0;
    countEl.textContent = `${list.length} tool${list.length === 1 ? "" : "s"}`;
  }

  function filter() {
    const term = q.value.trim().toLowerCase();
    if (!term) return render(tools);
    const hit = (t) =>
      [t.name, t.binary, t.wraps, t.description, ...(t.tags || [])]
        .join(" ").toLowerCase().includes(term);
    render(tools.filter(hit));
  }

  q.addEventListener("input", filter);

  fetch("registry.json")
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((data) => { tools = data.tools || []; render(tools); })
    .catch(() => {
      countEl.textContent = "";
      empty.hidden = false;
      empty.textContent = "Could not load the registry.";
    });
})();
