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

  // Prefer a real package manager over a source build in the shown one-liner.
  const primaryInstall = (install) =>
    install.brew || install.scoop || install.script || install.go || "";

  let tools = [];

  function card(t) {
    const li = document.createElement("li");
    li.className = "card";
    const install = primaryInstall(t.install || {});
    const chips = (t.tags || []).map((x) => `<span class="chip">${esc(x)}</span>`).join("");
    const agent = t.agent_ready ? `<span class="chip agent" title="Ships an MCP server + agent guard">agent-ready</span>` : "";
    li.innerHTML = `
      <div class="wraps">wraps ${esc(t.wraps)}</div>
      <h3><a href="${esc(t.repo)}" rel="noopener">${esc(t.binary)}</a></h3>
      <p class="desc">${esc(t.description)}</p>
      ${install ? `<div class="install"><code>${esc(install)}</code><button class="copy" type="button">copy</button></div>` : ""}
      <div class="tags">${agent}${chips}</div>`;
    const copyBtn = li.querySelector(".copy");
    if (copyBtn) {
      copyBtn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(install);
          copyBtn.textContent = "copied";
          setTimeout(() => (copyBtn.textContent = "copy"), 1200);
        } catch { copyBtn.textContent = "⌘C"; }
      });
    }
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
