/* HomeBase — Phase 1 frontend */

let selectedSpeakerId = null;
let pendingVoiceEntryId = null;
let recognition = null;
let isListening = false;
let users = [];

// Calendar state
let calYear = new Date().getFullYear();
let calMonth = new Date().getMonth() + 1;  // 1-based
let calEvents = [];  // events for current month
let calSelectedDay = null;

// Notes state
let currentNoteCategory = "";

// ─── Bootstrap ────────────────────────────────────────────────────────────────

async function init() {
  await loadUsers();
  await loadShiftHistory();
  await loadFeed();
  setupMicButton();
  document.getElementById("mic-btn").disabled = true;
}

// ─── Tab navigation ───────────────────────────────────────────────────────────

function switchTab(tab) {
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${tab}`));

  if (tab === "calendar") loadCalendar();
  if (tab === "notes") loadNotes();
}

// ─── Users / Speaker toggle ───────────────────────────────────────────────────

async function loadUsers() {
  try {
    const res = await fetch("/api/users/");
    users = await res.json();
    renderSpeakerToggle();
    renderShiftToggle();
  } catch (e) {
    setStatus("Could not load users — is the server running?");
  }
}

function renderSpeakerToggle() {
  const container = document.getElementById("speaker-toggle");
  container.innerHTML = "";
  users.forEach((u) => {
    const btn = document.createElement("button");
    btn.className = "speaker-btn";
    btn.textContent = u.name;
    btn.dataset.id = u.id;
    btn.onclick = () => selectSpeaker(u.id, btn);
    container.appendChild(btn);
  });
}

function selectSpeaker(id, btn) {
  selectedSpeakerId = id;
  document.querySelectorAll(".speaker-btn").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById("mic-btn").disabled = false;
}

// ─── Mic button + Web Speech API ──────────────────────────────────────────────

function setupMicButton() {
  const btn = document.getElementById("mic-btn");
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    setStatus("Speech recognition not supported in this browser. Use Chrome or Edge.");
    btn.disabled = true;
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "ca-ES";

  let finalTranscript = "";
  let interimTranscript = "";

  recognition.onresult = (event) => {
    interimTranscript = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const t = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += t + " ";
      } else {
        interimTranscript += t;
      }
    }
    setStatus(finalTranscript + interimTranscript || "Listening…");
  };

  recognition.onerror = (event) => {
    if (event.error === "no-speech") {
      setStatus("No speech detected. Try again.");
    } else {
      setStatus(`Speech error: ${event.error}`);
    }
    stopListening();
  };

  recognition.onend = () => {
    if (isListening) {
      isListening = false;
      btn.classList.remove("recording");
      if (finalTranscript.trim()) {
        processTranscription(finalTranscript.trim());
      } else {
        setStatus("No speech captured. Try again.");
      }
    }
  };

  btn.addEventListener("click", () => {
    if (isListening) {
      stopListening();
    } else {
      finalTranscript = "";
      startListening();
    }
  });
}

function startListening() {
  if (isListening) return;
  isListening = true;
  document.getElementById("mic-btn").classList.add("recording");
  setStatus("Listening…");
  recognition.start();
}

function stopListening() {
  if (!isListening) return;
  recognition.stop();
}

async function processTranscription(text) {
  setStatus("Classifying…");
  try {
    const res = await fetch("/api/voice/classify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        speaker_id: selectedSpeakerId,
        language_hint: recognition.lang.split("-")[0],
      }),
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(errText);
    }
    const data = await res.json();
    pendingVoiceEntryId = data.voice_entry_id;
    renderConfirmCard(data);
    setStatus("");
  } catch (e) {
    setStatus(`Error: ${e.message}`);
  }
}

// ─── Confirmation card ────────────────────────────────────────────────────────

function renderConfirmCard(data) {
  const card = document.getElementById("confirm-card");
  const tag = document.getElementById("confirm-tag");
  const transcription = document.getElementById("confirm-transcription");
  const extracted = document.getElementById("confirm-extracted");

  const cat = data.category || "household";
  tag.textContent = `${cat} · ${data.type || ""}`;
  tag.className = `tag tag-${cat}`;

  transcription.textContent = `"${data.transcription}"`;

  extracted.innerHTML = "";
  const ed = data.extracted_data || {};
  Object.entries(ed).forEach(([k, v]) => {
    if (k === "voice_entry_id" || v === null || v === undefined) return;
    extracted.innerHTML += `<dt>${k.replace(/_/g, " ")}</dt><dd>${v}</dd>`;
  });

  card.classList.add("visible");
}

document.getElementById("btn-confirm").onclick = async () => {
  if (!pendingVoiceEntryId) return;
  try {
    const res = await fetch(`/api/voice/confirm?voice_entry_id=${pendingVoiceEntryId}`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    hideConfirmCard();
    setStatus("Saved ✓");
    await loadFeed();
    // Refresh the active tab if it might be affected
    const activeTab = document.querySelector(".tab-btn.active")?.dataset.tab;
    if (activeTab === "calendar") loadCalendar();
    if (activeTab === "notes") loadNotes();
  } catch (e) {
    setStatus(`Error saving: ${e.message}`);
  }
};

document.getElementById("btn-discard").onclick = async () => {
  if (pendingVoiceEntryId) {
    try {
      await fetch(`/api/voice/discard?voice_entry_id=${pendingVoiceEntryId}`, { method: "DELETE" });
    } catch (_) {}
  }
  hideConfirmCard();
  setStatus("Discarded.");
  pendingVoiceEntryId = null;
};

function hideConfirmCard() {
  document.getElementById("confirm-card").classList.remove("visible");
}

// ─── Language selector ────────────────────────────────────────────────────────

function setLanguage(lang) {
  if (recognition) recognition.lang = lang;
  document.querySelectorAll(".lang-btn").forEach((b) => b.classList.remove("active"));
  document.querySelector(`.lang-btn[data-lang="${lang}"]`)?.classList.add("active");
}

// ─── Night shift widget ───────────────────────────────────────────────────────

function renderShiftToggle() {
  const container = document.getElementById("shift-toggle");
  container.innerHTML = "";
  users.forEach((u) => {
    const btn = document.createElement("button");
    btn.className = "shift-btn";
    btn.textContent = u.name;
    btn.onclick = () => setOnDuty(u.id, btn);
    container.appendChild(btn);
  });
}

async function setOnDuty(userId, btn) {
  try {
    await fetch("/api/shifts/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ on_duty: userId }),
    });
    document.querySelectorAll(".shift-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    await loadShiftHistory();
  } catch (e) {
    setStatus(`Shift error: ${e.message}`);
  }
}

async function loadShiftHistory() {
  try {
    const res = await fetch("/api/shifts/history?limit=7");
    const shifts = await res.json();
    const container = document.getElementById("shift-history");
    if (!shifts.length) { container.textContent = "No shifts logged yet."; return; }

    const userMap = Object.fromEntries(users.map((u) => [u.id, u.name]));
    container.innerHTML = shifts
      .map((s) => `<div class="shift-row"><span>${s.shift_date}</span><span>${userMap[s.on_duty] || s.on_duty}</span></div>`)
      .join("");

    const today = new Date().toISOString().split("T")[0];
    const tonight = shifts.find((s) => s.shift_date === today);
    if (tonight) {
      document.querySelectorAll(".shift-btn").forEach((btn) => {
        if (users.find((u) => u.id === tonight.on_duty && btn.textContent === u.name)) {
          btn.classList.add("active");
        }
      });
    }
  } catch (_) {}
}

// ─── Daily feed (enhanced cards) ─────────────────────────────────────────────

async function loadFeed() {
  try {
    const res = await fetch("/api/voice/today");
    const entries = await res.json();
    const container = document.getElementById("feed-items");

    if (!entries.length) {
      container.innerHTML = "<p style='color:var(--muted);font-size:.85rem'>Nothing logged yet today.</p>";
      return;
    }

    container.innerHTML = entries.map(renderFeedCard).join("");
  } catch (_) {}
}

function renderFeedCard(e) {
  const t = new Date(e.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const bl = e.baby_log;

  // ── Formula feeding card ──────────────────────────
  if (bl && bl.feed_time) {
    const ml = bl.amount_ml ? `${bl.amount_ml} ml` : "—";
    return `
      <div class="feed-item">
        <div class="feed-item-header">
          <span class="tag tag-baby" style="margin:0">🍼 feeding</span>
          <span class="feed-time">${bl.feed_time}</span>
        </div>
        <div class="feed-card-row">
          <div class="feed-card-metric">
            <span class="metric-val">${ml}</span>
            <span class="metric-lbl">amount</span>
          </div>
          <span class="feed-card-meta">${bl.feed_type || "formula"}</span>
        </div>
      </div>`;
  }

  // ── Nappy / diaper card ───────────────────────────
  if (bl && bl.diaper_type) {
    const typeLabel = { wet: "💧 Wet", soiled: "💩 Soiled", mixed: "💧💩 Mixed" }[bl.diaper_type] || bl.diaper_type;
    const count = bl.diaper_count ? `×${bl.diaper_count}` : "";
    return `
      <div class="feed-item">
        <div class="feed-item-header">
          <span class="tag tag-baby" style="margin:0">🧷 nappy</span>
          <span class="feed-time">${t}</span>
        </div>
        <div class="feed-card-row">
          <div class="feed-card-metric">
            <span class="metric-val" style="font-size:.85rem">${typeLabel}</span>
            <span class="metric-lbl">type ${count}</span>
          </div>
        </div>
      </div>`;
  }

  // ── Sleep card ────────────────────────────────────
  if (bl && (bl.wake_time || bl.sleep_time)) {
    const range = [bl.wake_time && `awake ${bl.wake_time}`, bl.sleep_time && `asleep ${bl.sleep_time}`]
      .filter(Boolean).join("  →  ");
    return `
      <div class="feed-item">
        <div class="feed-item-header">
          <span class="tag tag-baby" style="margin:0">😴 sleep</span>
          <span class="feed-time">${t}</span>
        </div>
        <div class="feed-card-meta" style="margin-top:.25rem">${range}</div>
      </div>`;
  }

  // ── Calendar event card ───────────────────────────
  if (e.entry_type === "calendar_event") {
    const ed = e.extracted_data?.extracted_data || e.extracted_data || {};
    const title = ed.event_title || ed.title || e.transcription;
    const date = ed.event_date || "";
    const time = ed.event_time || "";
    return `
      <div class="feed-item">
        <div class="feed-item-header">
          <span class="tag tag-${e.category}" style="margin:0">📅 appointment</span>
          <span class="feed-time">${t}</span>
        </div>
        <div class="feed-text">${title}${date ? ` · ${date}` : ""}${time ? ` at ${time}` : ""}</div>
      </div>`;
  }

  // ── Note card ─────────────────────────────────────
  if (e.entry_type === "note") {
    const summary = e.summary || e.transcription;
    return `
      <div class="feed-item">
        <div class="feed-item-header">
          <span class="tag tag-${e.category}" style="margin:0">📝 note</span>
          <span class="feed-time">${t}</span>
        </div>
        <div class="feed-text">${summary}</div>
      </div>`;
  }

  // ── Default card (dog, household tasks, etc.) ─────
  return `
    <div class="feed-item">
      <div class="feed-item-header">
        <span class="tag tag-${e.category}" style="margin:0">${e.category}</span>
        <span style="font-size:.8rem;color:var(--muted)">${e.entry_type.replace(/_/g, " ")}</span>
        <span class="feed-time">${t}</span>
      </div>
      <div class="feed-text">${e.transcription}</div>
    </div>`;
}

// ─── Calendar ────────────────────────────────────────────────────────────────

async function loadCalendar() {
  try {
    const res = await fetch(`/api/calendar/events?year=${calYear}&month=${calMonth}`);
    calEvents = await res.json();
  } catch (_) {
    calEvents = [];
  }
  renderCalendarGrid();
  renderCalendarEvents(calSelectedDay);
}

function calNav(delta) {
  calMonth += delta;
  if (calMonth > 12) { calMonth = 1; calYear++; }
  if (calMonth < 1) { calMonth = 12; calYear--; }
  calSelectedDay = null;
  loadCalendar();
}

function renderCalendarGrid() {
  const MONTHS = ["January","February","March","April","May","June",
                  "July","August","September","October","November","December"];
  document.getElementById("cal-title").textContent = `${MONTHS[calMonth - 1]} ${calYear}`;

  // Group events by day string "YYYY-MM-DD"
  const eventsByDay = {};
  calEvents.forEach((ev) => {
    if (!eventsByDay[ev.event_date]) eventsByDay[ev.event_date] = [];
    eventsByDay[ev.event_date].push(ev);
  });

  const todayStr = new Date().toISOString().split("T")[0];
  const firstDay = new Date(calYear, calMonth - 1, 1);
  const daysInMonth = new Date(calYear, calMonth, 0).getDate();

  // Monday-first offset (0=Mo … 6=Su)
  let startOffset = firstDay.getDay() - 1;
  if (startOffset < 0) startOffset = 6;

  // Remove old day cells (keep the 7 dow headers)
  const grid = document.getElementById("cal-grid");
  grid.querySelectorAll(".cal-day, .cal-day-empty").forEach((el) => el.remove());

  // Empty cells before the 1st
  for (let i = 0; i < startOffset; i++) {
    const cell = document.createElement("div");
    cell.className = "cal-day empty";
    grid.appendChild(cell);
  }

  // Day cells
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${calYear}-${String(calMonth).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const evs = eventsByDay[dateStr] || [];
    const cell = document.createElement("div");
    cell.className = "cal-day" +
      (dateStr === todayStr ? " today" : "") +
      (dateStr === calSelectedDay ? " selected" : "");
    cell.innerHTML = `<span>${d}</span>`;

    if (evs.length) {
      const dots = document.createElement("div");
      dots.className = "cal-dots";
      evs.slice(0, 3).forEach((ev) => {
        const dot = document.createElement("div");
        dot.className = `cal-dot cal-dot-${ev.category}`;
        dots.appendChild(dot);
      });
      cell.appendChild(dots);
    }

    cell.onclick = () => selectCalDay(dateStr, cell);
    grid.appendChild(cell);
  }
}

function selectCalDay(dateStr, cell) {
  calSelectedDay = dateStr;
  document.querySelectorAll(".cal-day").forEach((c) => c.classList.remove("selected"));
  cell.classList.add("selected");
  renderCalendarEvents(dateStr);
}

function renderCalendarEvents(dateStr) {
  const container = document.getElementById("cal-events");
  if (!dateStr) {
    container.innerHTML = `<p class="muted-hint">Tap a day to see appointments</p>`;
    return;
  }
  const evs = calEvents.filter((e) => e.event_date === dateStr);
  if (!evs.length) {
    const [y, m, d] = dateStr.split("-");
    container.innerHTML = `<p class="muted-hint">No appointments on ${d}/${m}/${y}</p>`;
    return;
  }
  container.innerHTML = evs.map((e) => `
    <div class="cal-event-item">
      <div class="cal-event-emoji">${e.emoji}</div>
      <div class="cal-event-body">
        <div class="cal-event-title">${e.title}</div>
        <div class="cal-event-time">
          ${e.event_time ? e.event_time : "All day"}
          ${e.duration_min && e.duration_min !== 60 ? ` · ${e.duration_min} min` : ""}
        </div>
        ${e.notes ? `<div class="cal-event-notes">${e.notes}</div>` : ""}
      </div>
    </div>`).join("");
}

// ─── Notes ───────────────────────────────────────────────────────────────────

async function loadNotes() {
  const url = currentNoteCategory
    ? `/api/notes/?category=${currentNoteCategory}`
    : "/api/notes/";
  try {
    const res = await fetch(url);
    const notes = await res.json();
    renderNotes(notes);
  } catch (_) {
    document.getElementById("notes-list").innerHTML =
      `<p class="muted-hint">Could not load notes.</p>`;
  }
}

function filterNotes(category) {
  currentNoteCategory = category;
  document.querySelectorAll(".filter-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.cat === category)
  );
  loadNotes();
}

function renderNotes(notes) {
  const container = document.getElementById("notes-list");
  if (!notes.length) {
    container.innerHTML = `<p class="muted-hint">No notes yet. Say something like "Note: she seems to prefer …"</p>`;
    return;
  }
  container.innerHTML = notes.map((n) => {
    const d = new Date(n.created_at);
    const dateLabel = d.toLocaleDateString([], { day: "numeric", month: "short" });
    return `
      <div class="note-card">
        <div class="note-card-header">
          <span class="tag tag-${n.category}" style="margin:0">${n.emoji} ${n.category}</span>
          <span class="note-date">${dateLabel}</span>
        </div>
        ${n.summary
          ? `<div class="note-summary">${n.summary}</div>
             <div class="note-raw">${n.transcription}</div>`
          : `<div class="note-summary">${n.transcription}</div>`
        }
      </div>`;
  }).join("");
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function setStatus(msg) {
  document.getElementById("status").textContent = msg;
}

// ─── Start ────────────────────────────────────────────────────────────────────
init();
