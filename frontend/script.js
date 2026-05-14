const API_URL = "http://127.0.0.1:8000/api/chat/";
const HEALTH_URL = "http://127.0.0.1:8000/";

const svg = document.getElementById("stars");
const themeIcon = document.getElementById("themeIcon");
const messagesEl = document.getElementById("messages");
const qInput = document.getElementById("q");
const chatForm = document.getElementById("chatForm");
const sendBtn = document.getElementById("send");
const apiBadge = document.getElementById("apiBadge");

const ships = [
  document.getElementById("ship1"),
  document.getElementById("ship2")
];

let currentShip = 0;

/* ---------------- ЗОРІ ---------------- */
function drawStars() {
  let html = "";
  const fillColor = document.body.classList.contains("dark") ? "white" : "black";

  for (let i = 0; i < 300; i++) {
    const x = Math.random() * 100;
    const y = Math.random() * 100;
    const r = Math.random() * 1.5;

    html += `<circle cx="${x}%" cy="${y}%" r="${r}" fill="${fillColor}" opacity="0.8"></circle>`;
  }

  svg.innerHTML = html;
}

/* ---------------- ТЕМА ---------------- */
function applyThemeIcon() {
  themeIcon.textContent = document.body.classList.contains("dark") ? "🌙" : "☀️";
}

themeIcon.addEventListener("click", () => {
  document.body.classList.toggle("dark");
  document.body.classList.toggle("light");
  drawStars();
  applyThemeIcon();
});

/* ---------------- КОМЕТИ ---------------- */
function spawnComet() {
  const comet = document.createElement("div");
  comet.className = "comet";
  comet.style.left = (-20 - Math.random() * 30) + "%";
  comet.style.top = (-20 - Math.random() * 40) + "%";
  comet.style.animationDuration = (4 + Math.random() * 4) + "s";
  comet.style.animationDelay = (Math.random() * 2) + "s";

  document.body.appendChild(comet);
  setTimeout(() => comet.remove(), 8000);
}

/* ---------------- КОРАБЛІ ---------------- */
function cycleShips() {
  ships.forEach(s => {
    s.style.display = "none";
  });

  const ship = ships[currentShip];
  ship.style.display = "block";
  ship.style.top = (10 + Math.random() * 70) + "%";
  ship.style.animationDuration = (18 + Math.random() * 25) + "s";

  currentShip = (currentShip + 1) % ships.length;
}

/* ---------------- ДОПОМІЖНІ ---------------- */
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setLoadingState(isLoading) {
  sendBtn.disabled = isLoading;
  qInput.disabled = isLoading;
  sendBtn.textContent = isLoading ? "Надсилання..." : "Надіслати";
}

function getModeLabel(mode) {
  switch (mode) {
    case "rag":
      return "RAG";
    case "faq_only":
      return "FAQ only";
    case "clarify":
      return "Уточнення";
    case "greeting":
      return "Привітання";
    case "no_results":
      return "Без результатів";
    default:
      return mode || "невідомо";
  }
}

function buildSourcesHtml(sources) {
  if (!Array.isArray(sources) || sources.length === 0) return "";

  let html = `<div class="sources"><div class="sources-title">Знайдені джерела</div>`;

  sources.forEach((source, index) => {
    // Використовуємо теги <details> та <summary> для створення розгортки
    html += `
      <details class="source-card">
        <summary class="source-summary">
          <span class="source-label">${index + 1}. Питання:</span> ${escapeHtml(source.question || "Деталі")}
        </summary>
        <div class="source-content" style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(127, 127, 127, 0.2);">
          <div style="margin-bottom:6px;"><span class="source-label">Відповідь:</span> ${escapeHtml(source.answer || "")}</div>
          <div><span class="source-label">Score:</span> ${Number(source.score || 0).toFixed(3)}</div>
        </div>
      </details>
    `;
  });

  html += `</div>`;
  return html;
}

function addMessage(text, who = "bot", meta = null) {
  const row = document.createElement("div");
  row.className = `msg-row ${who === "user" ? "user-row" : "bot-row"}`;

  const box = document.createElement("div");
  box.className = `msg ${who}`;

  let parsedText = "";
  if (who === "bot") {
    parsedText = marked.parse(text || "");
  } else {
    parsedText = escapeHtml(text).replace(/\n/g, "<br>");
  }

  let html = `<div class="msg-text">${parsedText}</div>`;

  if (meta && who === "bot") {
    const chips = [];

    if (meta.mode) {
      chips.push(
        `<span class="meta-chip mode-${escapeHtml(meta.mode)}">Режим: ${escapeHtml(getModeLabel(meta.mode))}</span>`
      );
    }

    if (typeof meta.confidence === "number") {
      chips.push(
        `<span class="meta-chip">Впевненість: ${meta.confidence.toFixed(3)}</span>`
      );
    }

    if (chips.length > 0) {
      html += `<div class="msg-meta">${chips.join("")}</div>`;
    }

    html += buildSourcesHtml(meta.sources);
  }

  box.innerHTML = html;
  row.appendChild(box);
  messagesEl.appendChild(row);
  scrollToBottom();
}

function addLoader() {
  const row = document.createElement("div");
  row.className = "msg-row bot-row";
  row.id = "loader-row";

  const box = document.createElement("div");
  box.className = "msg bot";
  box.innerHTML = `
    <div class="typing" aria-label="Завантаження">
      <span></span><span></span><span></span>
    </div>
  `;

  row.appendChild(box);
  messagesEl.appendChild(row);
  scrollToBottom();
}

function removeLoader() {
  const loader = document.getElementById("loader-row");
  if (loader) loader.remove();
}

/* ---------------- API ---------------- */
async function checkApi() {
  try {
    const resp = await fetch(HEALTH_URL, { method: "GET" });
    if (!resp.ok) throw new Error("API unavailable");
    apiBadge.textContent = "API: online";
  } catch {
    apiBadge.textContent = "API: offline";
  }
}

async function sendQuestion(question) {
  const resp = await fetch(API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question,
      session_id: "web-user-session"
    })
  });

  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }

  return await resp.json();
}

/* ---------------- ПОДІЇ ---------------- */
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const question = qInput.value.trim();
  if (!question) return;

  addMessage(question, "user");
  qInput.value = "";
  setLoadingState(true);
  addLoader();

  try {
    const data = await sendQuestion(question);
    removeLoader();

    addMessage(data.reply || "Немає відповіді", "bot", {
      mode: data.mode,
      confidence: typeof data.confidence === "number" ? data.confidence : undefined,
      sources: data.sources || []
    });
  } catch (error) {
    removeLoader();
    addMessage(
      "Помилка з'єднання з сервером. Перевір, чи запущений FastAPI бекенд і чи правильна адреса API.",
      "bot",
      { mode: "no_results" }
    );
    console.error(error);
  } finally {
    setLoadingState(false);
    qInput.focus();
  }
});

qInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

/* ---------------- INIT ---------------- */
drawStars();
applyThemeIcon();
setInterval(spawnComet, 2500);
setInterval(cycleShips, 12000);
cycleShips();
checkApi();

addMessage(
  "Вітаю! Я чат-бот університету. Постав запитання щодо вступу, навчання, розкладу або документів.",
  "bot",
  { mode: "greeting", confidence: 1.0 }
);