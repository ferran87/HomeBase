/* HomeBase — Phase 1 frontend */

let selectedSpeakerId = null;
let pendingVoiceEntryId = null;
let recognition = null;
let isListening = false;
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

  // Auto-detect: browser will pick up the spoken language from these
  // Catalan, Spanish, English
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
      // Stopped by user — process the result
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
      startListening(finalTranscript = "");
    }
  });
}

function startListening() {
  if (!selectedSpeakerId) {
    setStatus("Tap your name first.");
    return;
  }
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
        text: text,
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
