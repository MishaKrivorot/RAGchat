const API_URL = "https://frecs-chat.up.railway.app/api/chat/";
const HEALTH_URL = "https://frecs-chat.up.railway.app/";

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
  const isDark = document.body.classList.contains("dark");
  themeIcon.textContent = isDark ? "🌙" : "☀️";

  // Змінюємо картинки залежно від теми
  const ship1 = document.getElementById("ship1");
  const ship2 = document.getElementById("ship2");

  if (ship1) {
    ship1.src = isDark ? "nlo_invert.png" : "nlo.png";
  }
  if (ship2) {
    ship2.src = isDark ? "rocket_invert.png" : "rocket.png";
  }
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
  comet.style.left = (-20 + Math.random() * 120) + "%";
  comet.style.top = (-20 - Math.random() * 40) + "%";
  comet.style.animationDuration = (4 + Math.random() * 4) + "s";
  comet.style.animationDelay = (Math.random() * 2) + "s";

  document.body.appendChild(comet);
  setTimeout(() => comet.remove(), 8000);
}

/* ---------------- КОРАБЛІ ---------------- */
function initShips() {
  ships.forEach((ship, index) => {
    if (!ship) return;
    ship.style.display = "block";
    ship.style.top = (10 + Math.random() * 70) + "%";
    ship.style.animationDuration = (18 + Math.random() * 25) + "s";
    ship.style.animationDelay = (index * 12) + "s";

    // Оновлюємо позицію та швидкість кожного разу, коли корабель завершує проліт
    ship.addEventListener("animationiteration", () => {
      ship.style.top = (10 + Math.random() * 70) + "%";
      ship.style.animationDuration = (18 + Math.random() * 25) + "s";
    });
  });
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
    // Безпечне отримання значень
    const qText = escapeHtml(source.question || "Загальна інформація");
    const aText = escapeHtml(source.answer || "Відповіді немає");
    const scoreVal = Number(source.score || 0).toFixed(3);
    const likesVal = source.likes || 0;
    const sId = source.id || "";
    const sType = source.source_type || "";

    html += `
      <details class="source-card">
        <summary style="display: flex; justify-content: space-between; align-items: center; list-style: none;">
            <div style="flex-grow: 1; padding-right: 10px;">
              <span class="source-label">${index + 1}. Питання:</span> ${qText}
            </div>
            <div style="display:flex; gap: 5px;">
              <button class="like-btn" onclick="event.preventDefault(); sendFeedback('${sId}', '${sType}', 'like', this)" title="Корисне">👍 <span style="font-size:11px">${likesVal}</span></button>
              <button class="like-btn" onclick="event.preventDefault(); sendFeedback('${sId}', '${sType}', 'dislike', this)" title="Не корисне">👎 <span style="font-size:11px">${source.dislikes || 0}</span></button>
            </div>
        </summary>
        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(127, 127, 127, 0.2);">
            <div><span class="source-label">Відповідь:</span> ${aText}</div>
            <div style="margin-top:6px;">
                <span class="source-label">Score:</span> ${scoreVal} 
                <span style="opacity: 0.6; font-size: 11px;">(Лайків: ${likesVal})</span>
            </div>
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

let cometInterval = setInterval(spawnComet, 2500);
initShips();
checkApi();

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    clearInterval(cometInterval);
    document.body.classList.add("paused-animation");
  } else {
    cometInterval = setInterval(spawnComet, 2500);
    document.body.classList.remove("paused-animation");
  }
});

addMessage(
  "Вітаю! Я чат-бот університету. Постав запитання щодо вступу, навчання, розкладу або документів.",
  "bot",
  { mode: "greeting", confidence: 1.0 }
);



/* ---------------- ФІДБЕК ---------------- */
window.sendFeedback = async function (pointId, sourceType, action, btnElement) {
  if (btnElement.classList.contains("acted")) return; // Захист від повтору

  const container = btnElement.parentElement;
  Array.from(container.children).forEach(btn => btn.classList.add("acted")); // Блокуємо обидві кнопки

  btnElement.style.background = action === 'like' ? 'rgba(74, 222, 128, 0.3)' : 'rgba(248, 113, 113, 0.3)';

  try {
    const response = await fetch("https://frecs-chat.up.railway.app/api/chat/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: pointId, source_type: sourceType, action: action })
    });

    const data = await response.json();

    // 🔥 Миттєво оновлюємо цифру на кнопці
    if (data.status === "success") {
      const span = btnElement.querySelector("span");
      if (span) {
        span.innerText = action === 'like' ? data.likes : data.dislikes;
      }
    }
  } catch (error) {
    console.error("Помилка відправки:", error);
  }
};

/* ---------------- INTRO SCREEN (МІКРОСХЕМА) ---------------- */
const introScreen = document.getElementById("intro-screen");

if (introScreen) {
  introScreen.addEventListener("click", () => {
    // Плавно приховуємо екран
    introScreen.classList.add("hidden");

    // Повністю видаляємо його з DOM через 600мс (після завершення анімації зникнення),
    // щоб він не заважав клікати на елементи чату
    setTimeout(() => {
      introScreen.remove();
      // Можна додати автофокус на поле вводу, щоб користувач одразу міг писати
      qInput.focus();
    }, 600);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  // Вступна анімація мікросхеми (drawSignal, powerUp) триває приблизно 5с.
  // Вмикаємо логіку імпульсів через 5.2с.
  setTimeout(() => {
    const pulseGroup = document.querySelector('.microchip-svg .pulses');
    if (pulseGroup) {
      // Вмикаємо видимість усієї групи
      pulseGroup.style.display = 'block';

      const pulsePaths = pulseGroup.querySelectorAll('.signal-pulse');

      pulsePaths.forEach(pulse => {
        // 🔥 Нові налаштування:
        // Тривалість циклу: 15с (дуже довго, для рідкої появи)
        const duration = 15;

        // Хаотична початкова затримка: від 0 до 12с.
        // Це розподіляє появу імпульсів у часі, щоб вони не clump up.
        const randomDelay = (Math.random() * 12).toFixed(2);

        // Застосовуємо анімацію runPulse
        pulse.style.animation = `runPulse ${duration}s ${randomDelay}s infinite linear`;
      });
    }
  }, 5200); // Починаємо логіку після завершення вступу
});