/**
 * frontend/app.js - Modern, accessible, streaming chat widget client with Gnani TTS.
 */

// Generate or retrieve persistent session ID
let sessionId = localStorage.getItem("college_chat_session_id");
if (!sessionId) {
  sessionId = "session_" + Math.random().toString(36).substring(2, 10);
  localStorage.setItem("college_chat_session_id", sessionId);
}

// DOM Elements
const chatViewport = document.getElementById("chatViewport");
const messagesList = document.getElementById("messagesList");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const stopBtn = document.getElementById("stopBtn");
const newChatBtn = document.getElementById("newChatBtn");
const typingIndicator = document.getElementById("typingIndicator");
const autoSpeakToggle = document.getElementById("autoSpeakToggle");
const errorBanner = document.getElementById("errorBanner");
const errorMessage = document.getElementById("errorMessage");
const retryBtn = document.getElementById("retryBtn");
const charCounter = document.getElementById("charCounter");
const ttsAudio = document.getElementById("ttsAudio");

let currentAbortController = null;
let lastUserQuery = "";
let currentlyPlayingBtn = null;

// Audio state management
function stopAudio() {
  if (!ttsAudio.paused) {
    ttsAudio.pause();
    ttsAudio.currentTime = 0;
  }
  if (currentlyPlayingBtn) {
    currentlyPlayingBtn.classList.remove("playing");
    currentlyPlayingBtn.innerHTML = "🔊 Listen";
    currentlyPlayingBtn = null;
  }
}

ttsAudio.addEventListener("ended", stopAudio);
ttsAudio.addEventListener("pause", stopAudio);

// Character counter & textarea auto-resize
chatInput.addEventListener("input", () => {
  const len = chatInput.value.length;
  charCounter.textContent = `${len}/500`;
  chatInput.style.height = "auto";
  chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
});

// Keyboard handling: Enter to send, Shift+Enter for newline
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

sendBtn.addEventListener("click", handleSend);
stopBtn.addEventListener("click", () => {
  if (currentAbortController) {
    currentAbortController.abort();
    currentAbortController = null;
    finishStreamingState();
  }
});

newChatBtn.addEventListener("click", async () => {
  stopAudio();
  if (currentAbortController) {
    currentAbortController.abort();
    currentAbortController = null;
  }
  try {
    await fetch("/api/chat/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId })
    });
  } catch (e) {
    // ignore network errors on clear
  }
  messagesList.innerHTML = "";
  hideError();
  finishStreamingState();
});

retryBtn.addEventListener("click", () => {
  hideError();
  if (lastUserQuery) {
    sendMessage(lastUserQuery);
  }
});

// Setup click delegation for initial suggestion chips
document.addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (chip && chip.dataset.query) {
    sendMessage(chip.dataset.query);
  }
});

function showError(msg) {
  errorMessage.textContent = msg;
  errorBanner.style.display = "flex";
}

function hideError() {
  errorBanner.style.display = "none";
}

function scrollToBottom() {
  chatViewport.scrollTop = chatViewport.scrollHeight;
}

function handleSend() {
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";
  chatInput.style.height = "auto";
  charCounter.textContent = "0/500";
  sendMessage(text);
}

// Simple Markdown Formatter
function renderMarkdown(md) {
  if (!md) return "";
  let html = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  // Italics
  html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
  // Markdown links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // Convert paragraphs & linebreaks
  const paragraphs = html.split(/\n\n+/);
  return paragraphs.map(p => {
    const lines = p.split(/\n/);
    if (lines.every(l => l.trim().startsWith("- ") || l.trim().startsWith("* "))) {
      const items = lines.map(l => `<li>${l.replace(/^[-*]\s+/, "")}</li>`).join("");
      return `<ul>${items}</ul>`;
    }
    if (lines.every(l => /^\d+\.\s+/.test(l.trim()))) {
      const items = lines.map(l => `<li>${l.replace(/^\d+\.\s+/, "")}</li>`).join("");
      return `<ol>${items}</ol>`;
    }
    return `<p>${p.replace(/\n/g, "<br>")}</p>`;
  }).join("");
}

function appendUserMessage(text) {
  const row = document.createElement("div");
  row.className = "message-row user";
  row.innerHTML = `
    <div class="avatar">👤</div>
    <div class="message-bubble"><p>${text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}</p></div>
  `;
  messagesList.appendChild(row);
  scrollToBottom();
}

function createAssistantMessage() {
  const row = document.createElement("div");
  row.className = "message-row assistant";
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  
  row.innerHTML = `<div class="avatar">🎓</div>`;
  row.appendChild(bubble);
  messagesList.appendChild(row);
  scrollToBottom();

  return { row, bubble };
}

function setStreamingState() {
  sendBtn.classList.add("hidden");
  stopBtn.classList.remove("hidden");
  chatInput.disabled = true;
  typingIndicator.classList.remove("hidden");
  scrollToBottom();
}

function finishStreamingState() {
  sendBtn.classList.remove("hidden");
  stopBtn.classList.add("hidden");
  chatInput.disabled = false;
  typingIndicator.classList.add("hidden");
  chatInput.focus();
}

async function sendMessage(query) {
  stopAudio();
  hideError();
  lastUserQuery = query;

  appendUserMessage(query);
  setStreamingState();

  currentAbortController = new AbortController();
  const signal = currentAbortController.signal;

  let assistantItem = null;
  let fullAccumulatedText = "";
  let metadata = null;

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: query, session_id: sessionId }),
      signal
    });

    if (!response.ok) {
      throw new Error(`Server returned status ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // keep remainder

      for (const block of lines) {
        const line = block.trim();
        if (line.startsWith("data: ")) {
          const jsonStr = line.substring(6);
          try {
            const data = JSON.parse(jsonStr);

            if (data.type === "error") {
              showError(data.message);
              break;
            }

            if (data.type === "chunk") {
              typingIndicator.classList.add("hidden");

              if (!assistantItem) {
                assistantItem = createAssistantMessage();
              }
              fullAccumulatedText += data.content;
              assistantItem.bubble.innerHTML = renderMarkdown(fullAccumulatedText);
              scrollToBottom();
            }

            if (data.type === "done") {
              metadata = data;
            }
          } catch (e) {
            console.error("Error parsing event frame:", e);
          }
        }
      }
    }

    // Attach interactive buttons & audio controls once stream is done
    if (assistantItem && metadata) {
      attachAssistantControls(assistantItem.row, fullAccumulatedText, metadata);

      // Auto-speak if enabled
      if (autoSpeakToggle.checked && metadata.lang) {
        const speakBtn = assistantItem.row.querySelector(".audio-btn");
        if (speakBtn) {
          triggerTTS(speakBtn, fullAccumulatedText, metadata.lang);
        }
      }
    }

  } catch (err) {
    if (err.name === "AbortError") {
      console.log("Stream aborted by user.");
    } else {
      console.error("Stream failed:", err);
      showError("Cannot connect to server. Please ensure 'python api.py' is running in PowerShell on port 8000.");
    }
  } finally {
    currentAbortController = null;
    finishStreamingState();
  }
}

function attachAssistantControls(row, fullText, meta) {
  const chipsWrapper = document.createElement("div");
  chipsWrapper.className = "chips-container";

  // Course options (disambiguation)
  if (meta.course_buttons && meta.course_buttons.length > 0) {
    meta.course_buttons.forEach(c => {
      const btn = document.createElement("button");
      btn.className = "chip";
      btn.textContent = c.name;
      btn.dataset.query = c.name;
      chipsWrapper.appendChild(btn);
    });
  }

  // Action buttons (Eligibility, Fees, How to apply)
  if (meta.action_buttons && meta.action_buttons.length > 0) {
    meta.action_buttons.forEach(a => {
      const btn = document.createElement("button");
      btn.className = "chip";
      btn.textContent = a;
      btn.dataset.query = a;
      chipsWrapper.appendChild(btn);
    });
  }

  // Follow-up suggested chips
  if (meta.suggested_chips && meta.suggested_chips.length > 0) {
    meta.suggested_chips.forEach(s => {
      const btn = document.createElement("button");
      btn.className = "chip";
      btn.textContent = s;
      btn.dataset.query = s;
      chipsWrapper.appendChild(btn);
    });
  }

  if (chipsWrapper.children.length > 0) {
    row.querySelector(".message-bubble").appendChild(chipsWrapper);
  }

  // Audio Speaker + Feedback controls
  const controls = document.createElement("div");
  controls.className = "assistant-controls";

  const audioBtn = document.createElement("button");
  audioBtn.className = "audio-btn";
  audioBtn.innerHTML = "🔊 Listen";
  audioBtn.title = "Read answer aloud";
  audioBtn.addEventListener("click", () => {
    triggerTTS(audioBtn, fullText, meta.lang || "en");
  });
  controls.appendChild(audioBtn);

  // Thumbs up / down feedback
  const feedbackGroup = document.createElement("div");
  feedbackGroup.className = "feedback-group";

  const upBtn = document.createElement("button");
  upBtn.className = "feedback-btn";
  upBtn.innerHTML = "👍";
  upBtn.title = "Helpful answer";
  upBtn.addEventListener("click", () => sendFeedback("up", upBtn, feedbackGroup, lastUserQuery));

  const downBtn = document.createElement("button");
  downBtn.className = "feedback-btn";
  downBtn.innerHTML = "👎";
  downBtn.title = "Not helpful";
  downBtn.addEventListener("click", () => sendFeedback("down", downBtn, feedbackGroup, lastUserQuery));

  feedbackGroup.appendChild(upBtn);
  feedbackGroup.appendChild(downBtn);
  controls.appendChild(feedbackGroup);

  row.appendChild(controls);
  scrollToBottom();
}

async function triggerTTS(btn, text, lang) {
  if (currentlyPlayingBtn === btn && !ttsAudio.paused) {
    stopAudio();
    return;
  }

  stopAudio();
  currentlyPlayingBtn = btn;
  btn.classList.add("playing");
  btn.innerHTML = "⏳ Loading...";

  try {
    const res = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang })
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.error || "Failed to generate audio.");
    }

    const blob = await res.blob();
    const audioUrl = URL.createObjectURL(blob);
    ttsAudio.src = audioUrl;
    btn.innerHTML = "⏹️ Stop";
    await ttsAudio.play();
  } catch (err) {
    console.error("TTS error:", err);
    showError(err.message || "Voice service could not play this message.");
    btn.classList.remove("playing");
    btn.innerHTML = "🔊 Listen";
    currentlyPlayingBtn = null;
  }
}

async function sendFeedback(vote, clickedBtn, group, query) {
  clickedBtn.style.fontWeight = "bold";
  clickedBtn.style.color = "var(--primary)";
  Array.from(group.children).forEach(b => b.disabled = true);

  try {
    await fetch("/api/chat/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, vote, query })
    });
  } catch (e) {
    console.error("Feedback failed to record:", e);
  }
}