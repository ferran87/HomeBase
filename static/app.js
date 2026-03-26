/* HomeBase — Phase 1 frontend */

let selectedSpeakerId = null;
let pendingVoiceEntryId = null;
let mediaRecorder = null;
let audioChunks = [];
let users = [];

// ─── Bootstrap ────────────────────────────────────────────────────────────────

async function init() {
  await loadUsers();
  await loadShiftHistory();
  await loadFeed();
  setupMicButton();
}

// ─── Users / Speaker toggle ───────────────────────────────────────────────────

async function loadUsers() {
  try {
    const res = await fetch("/api/users");
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
}

// ─── Mic button + MediaRecorder ───────────────────────────────────────────────

function setupMicButton() {
  const btn = document.getElementById("mic-btn");

  btn.addEventListener("mousedown", startRecording);
  btn.addEventListener("touchstart", (e) => { e.preventDefault(); startRecording(); });
  btn.addEventListener("mouseup", stopRecording);
  btn.addEventListener("touchend", (e) => { e.preventDefault(); stopRecording(); });
  btn.addEventListener("mouseleave", stopRecording);
}

async function startRecording() {
  if (!selectedSpeakerId) {
    setStatus("Tap your name first.");
    return;
  }
  if (mediaRecorder && mediaRecorder.state === "recording") return;

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  audioChunks = [];
  mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
  mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
  mediaRecorder.onstop = processAudio;
  mediaRecorder.start();

  document.getElementById("mic-btn").classList.add("recording");
  setStatus("Recording…");
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach((t) => t.stop());
    document.getElementById("mic-btn").classList.remove("recording");
    setStatus("Processing…");
  }
}

async function processAudio() {
  const blob = new Blob(audioChunks, { type: "audio/webm" });
  const form = new FormData();
  form.append("audio", blob, "recording.webm");
  form.append("speaker_id", selectedSpeakerId);

  try {
    const res = await fetch("/api/voice/", { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
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
  } catch (e) {
    setStatus(`Error saving: ${e.message}`);
  }
};

document.getElementById("btn-discard").onclick = () => {
  hideConfirmCard();
  setStatus("Discarded.");
  pendingVoiceEntryId = null;
};

function hideConfirmCard() {
  document.getElementById("confirm-card").classList.remove("visible");
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

    // Highlight tonight's active shift
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

// ─── Daily feed ───────────────────────────────────────────────────────────────

async function loadFeed() {
  try {
    const res = await fetch("/api/voice/today");
    const entries = await res.json();
    const container = document.getElementById("feed-items");

    if (!entries.length) {
      container.innerHTML = "<p style='color:var(--muted);font-size:.85rem'>Nothing logged yet today.</p>";
      return;
    }

    const userMap = Object.fromEntries(users.map((u) => [u.id, u.name]));
    container.innerHTML = entries
      .map((e) => {
        const t = new Date(e.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        return `
          <div class="feed-item">
            <div class="feed-item-header">
              <span class="tag tag-${e.category}" style="margin:0">${e.category}</span>
              <span style="font-size:.8rem;color:var(--muted)">${e.entry_type.replace(/_/g," ")}</span>
              <span class="feed-time">${t}</span>
            </div>
            <div class="feed-text">${e.transcription}</div>
          </div>`;
      })
      .join("");
  } catch (_) {}
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function setStatus(msg) {
  document.getElementById("status").textContent = msg;
}

// ─── Start ────────────────────────────────────────────────────────────────────
init();
