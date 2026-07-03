const state = {
  filter: "all",
  city: "all",
  sort: "newest",
  notesTimers: {},
};

function el(id) { return document.getElementById(id); }

async function api(url, opts) {
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "request failed");
    err.data = data;
    err.status = res.status;
    throw err;
  }
  return data;
}

function statusRowClass(agency) {
  if (agency.status === "DO_NOT_CONTACT") return "status-do-not-contact";
  if (agency.status === "NEW") return "status-new";
  if (agency.status === "SENT") return "status-sent";
  if (agency.status === "REPLIED") return "status-replied";
  return "";
}

const STATUSES = ["NEW", "SENT", "REPLIED", "MEETING", "CLIENT", "NOT_INTERESTED", "DO_NOT_CONTACT"];

function buildRow(agency) {
  const tr = document.createElement("tr");
  tr.className = statusRowClass(agency);
  tr.dataset.id = agency.id;

  const websiteCell = agency.website_url
    ? `<a href="${agency.website_url}" target="_blank" rel="noopener">Website</a>`
    : `<span class="no-site">No site</span>`;

  const phoneLabel = agency.phone_source === "direct_mobile" ? "(mobile)"
    : agency.phone_source === "tracking_073" ? "(073)"
    : agency.phone_source === "manual" ? "(manual)" : "";

  const waDisabled = agency.status === "DO_NOT_CONTACT" || !agency.phone_used;
  const followUpBadge = agency.is_follow_up_due ? `<span class="follow-up-badge">Follow-up due</span>` : "";

  const statusOptions = STATUSES.map(
    s => `<option value="${s}" ${s === agency.status ? "selected" : ""}>${s.replace(/_/g, " ")}</option>`
  ).join("");

  const profileLink = agency.profile_url
    ? `<a href="${agency.profile_url}" target="_blank" rel="noopener" class="profile-link" title="Open this agency's Madlan page in your browser to look up its phone number">Open profile &#8599;</a>`
    : "";

  tr.innerHTML = `
    <td>${agency.name || ""}</td>
    <td>${agency.city_label || agency.city}</td>
    <td>${agency.deals_count ?? ""}</td>
    <td>${agency.exclusives_count ?? ""}</td>
    <td>
      <input class="phone-input" data-action="phone-edit" value="${(agency.phone_used || "").replace(/"/g, "&quot;")}" placeholder="paste phone here">
      <small>${phoneLabel}</small><br>
      ${profileLink}
    </td>
    <td>
      ${followUpBadge}
      <button class="wa-btn" data-action="wa-click" ${waDisabled ? "disabled" : ""}>WhatsApp</button>
      ${agency.status === "SENT" ? `<button class="wa-undo" data-action="wa-toggle">undo</button>` : ""}
    </td>
    <td>${websiteCell}</td>
    <td>${(agency.scraped_at || "").slice(0, 10)}</td>
    <td><select class="status-select" data-action="status-change">${statusOptions}</select></td>
    <td><input class="notes-input" data-action="notes-edit" value="${(agency.notes || "").replace(/"/g, "&quot;")}"></td>
  `;
  return tr;
}

async function loadAgencies() {
  const params = new URLSearchParams({ filter: state.filter, city: state.city, sort: state.sort });
  const data = await api(`/api/agencies?${params}`);

  el("counter-total").textContent = data.counters.total;
  el("counter-new").textContent = data.counters.new;
  el("counter-sent").textContent = data.counters.sent;
  el("counter-replied").textContent = data.counters.replied;

  const tbody = el("agency-tbody");
  tbody.innerHTML = "";
  data.agencies.forEach(a => tbody.appendChild(buildRow(a)));
}

el("agency-tbody").addEventListener("click", async (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  const tr = e.target.closest("tr");
  const id = tr.dataset.id;
  const action = btn.dataset.action;

  if (action === "wa-click") {
    // Open the tab synchronously, inside the click handler itself, and point it
    // at the real URL once the API call resolves — most browsers block
    // window.open() if it happens after an `await`, since by then it's no
    // longer considered a direct response to the user's click.
    const newTab = window.open("", "_blank");
    try {
      const result = await api(`/api/agencies/${id}/whatsapp_click`, { method: "POST" });
      if (newTab) {
        newTab.location.href = result.wa_url;
      } else {
        alert("Your browser blocked the popup. Please allow popups for this site and try again.");
      }
      loadAgencies();
    } catch (err) {
      if (newTab) newTab.close();
      alert(err.message || "Could not send WhatsApp message");
    }
  } else if (action === "wa-toggle") {
    await api(`/api/agencies/${id}/whatsapp_toggle_sent`, { method: "POST" });
    loadAgencies();
  }
});

el("agency-tbody").addEventListener("change", async (e) => {
  const tr = e.target.closest("tr");
  const id = tr.dataset.id;
  if (e.target.dataset.action === "status-change") {
    try {
      await api(`/api/agencies/${id}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: e.target.value }),
      });
      loadAgencies();
    } catch (err) {
      if (err.status === 409) {
        if (confirm("This agency is DO NOT CONTACT. Change anyway?")) {
          await api(`/api/agencies/${id}/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: e.target.value, confirm: true }),
          });
          loadAgencies();
        } else {
          loadAgencies();
        }
      } else {
        alert(err.message || "Could not update status");
        loadAgencies();
      }
    }
  }
});

el("agency-tbody").addEventListener("input", (e) => {
  if (e.target.dataset.action !== "notes-edit") return;
  const tr = e.target.closest("tr");
  const id = tr.dataset.id;
  clearTimeout(state.notesTimers[id]);
  state.notesTimers[id] = setTimeout(async () => {
    await api(`/api/agencies/${id}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notes: e.target.value }),
    });
  }, 600);
});

el("filter-tabs").addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  document.querySelectorAll("#filter-tabs button").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  state.filter = btn.dataset.filter;
  loadAgencies();
});

el("city-filter").addEventListener("change", (e) => { state.city = e.target.value; loadAgencies(); });
el("sort-select").addEventListener("change", (e) => { state.sort = e.target.value; loadAgencies(); });

el("export-xlsx-btn").addEventListener("click", () => { window.location.href = "/api/export/xlsx"; });
el("export-csv-btn").addEventListener("click", () => { window.location.href = "/api/export/csv"; });

// --- Scraper control ---

let pollTimer = null;

function renderProgress(s) {
  const progressPanel = el("scrape-progress");
  const summaryPanel = el("scrape-summary");
  const btn = el("scrape-btn");

  if (s.running) {
    btn.disabled = true;
    progressPanel.classList.remove("hidden");
    summaryPanel.classList.add("hidden");
    el("progress-text").textContent = `${s.scraped}/${s.target}... (no-site: ${s.no_website_count}, credits: ${s.credits_used})`;
    const pct = s.target ? Math.min(100, (s.scraped / s.target) * 100) : 0;
    el("progress-bar-fill").style.width = pct + "%";
  } else {
    btn.disabled = false;
    progressPanel.classList.add("hidden");
    if (s.done && (s.summary || s.error)) {
      summaryPanel.classList.remove("hidden");
      if (s.error) {
        summaryPanel.innerHTML = `<b>Error:</b> ${s.error}`;
      } else {
        const sm = s.summary;
        summaryPanel.innerHTML = `
          <b>Run complete</b><br>
          Scraped: ${sm.new_saved}<br>
          No website: ${sm.no_website_count}<br>
          Firecrawl credits used: ${sm.credits_used}<br>
          Failed URLs: ${sm.failed_count}<br>
          ${sm.city_exhausted ? "<b>This city has no more new agencies.</b>" : ""}
        `;
      }
      loadAgencies();
    }
  }
}

async function pollProgress() {
  const s = await api("/api/scrape/progress");
  renderProgress(s);
  if (s.running) {
    pollTimer = setTimeout(pollProgress, 1000);
  }
}

el("scrape-btn").addEventListener("click", async () => {
  const city = el("city-select").value;
  try {
    await api("/api/scrape/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ city }),
    });
    clearTimeout(pollTimer);
    pollProgress();
  } catch (err) {
    if (err.status === 409) {
      alert("A scrape is already running.");
    } else {
      alert(err.message || "Could not start scrape");
    }
  }
});

// --- Scrape Mobile control ---

let mobilePollTimer = null;

function renderMobileProgress(s) {
  const progressPanel = el("mobile-progress");
  const summaryPanel = el("mobile-summary");
  const btn = el("mobile-scrape-btn");

  if (s.running) {
    btn.disabled = true;
    progressPanel.classList.remove("hidden");
    summaryPanel.classList.add("hidden");
    el("mobile-progress-text").textContent = `${s.checked}/${s.target}... (found: ${s.found})`;
    const pct = s.target ? Math.min(100, (s.checked / s.target) * 100) : 0;
    el("mobile-progress-bar-fill").style.width = pct + "%";
  } else {
    btn.disabled = false;
    progressPanel.classList.add("hidden");
    if (s.done && (s.summary || s.error)) {
      summaryPanel.classList.remove("hidden");
      if (s.error) {
        summaryPanel.innerHTML = `<b>Error:</b> ${s.error}`;
      } else {
        const sm = s.summary;
        summaryPanel.innerHTML = `
          <b>Done</b><br>
          Checked: ${sm.checked}<br>
          Mobile numbers found: ${sm.found}
        `;
      }
      loadAgencies();
    }
  }
}

async function pollMobileProgress() {
  const s = await api("/api/mobile/progress");
  renderMobileProgress(s);
  if (s.running) {
    mobilePollTimer = setTimeout(pollMobileProgress, 1000);
  }
}

el("mobile-scrape-btn").addEventListener("click", async () => {
  try {
    await api("/api/mobile/start", { method: "POST" });
    clearTimeout(mobilePollTimer);
    pollMobileProgress();
  } catch (err) {
    if (err.status === 409) {
      alert("A mobile re-check is already running.");
    } else {
      alert(err.message || "Could not start mobile re-check");
    }
  }
});

// --- Failed URLs panel ---

el("failed-urls-toggle").addEventListener("click", async () => {
  const list = el("failed-urls-list");
  list.classList.toggle("hidden");
  if (!list.classList.contains("hidden")) {
    const rows = await api("/api/scrape/failed_urls");
    list.innerHTML = rows.length
      ? rows.map(r => `<div>[${r.url_type}] ${r.city || ""} — ${r.reason || ""}<br><small>${r.url}</small></div>`).join("")
      : "<div>No failed URLs.</div>";
  }
});

// --- Template stats panel ---

el("template-stats-toggle").addEventListener("click", async () => {
  const list = el("template-stats-list");
  list.classList.toggle("hidden");
  if (!list.classList.contains("hidden")) {
    const rows = await api("/api/templates/stats");
    list.innerHTML = rows.length
      ? rows.map(r => `<div>${r.template_version}: ${r.sent} sent, ${r.replied_or_better} replied+ (${r.reply_rate}%)</div>`).join("")
      : "<div>No messages sent yet.</div>";
  }
});

// --- Auto-reply panel ---

async function loadAutoreplyStatus() {
  const s = await api("/api/settings/autoreply");
  el("autoreply-status").textContent = `Connection: ${s.autoreply_connection_status}`;
  el("autoreply-toggle").checked = !!s.autoreply_enabled;
}

el("autoreply-toggle").addEventListener("change", async (e) => {
  await api("/api/settings/autoreply/toggle", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled: e.target.checked }),
  });
});

// --- Init ---

(async function init() {
  await loadAgencies();
  await loadAutoreplyStatus();
  const s = await api("/api/scrape/progress");
  renderProgress(s);
  if (s.running) pollProgress();
  const ms = await api("/api/mobile/progress");
  renderMobileProgress(ms);
  if (ms.running) pollMobileProgress();
  setInterval(loadAutoreplyStatus, 10000);
})();
