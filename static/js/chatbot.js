(() => {
  const widget = document.querySelector("[data-chatbot-widget]");
  if (!widget) return;

  const toggle = widget.querySelector(".chatbot-toggle");
  const panel = widget.querySelector(".chatbot-panel");
  const closeButton = widget.querySelector(".chatbot-close");
  const messagesEl = widget.querySelector("[data-chatbot-messages]");
  const quickRepliesEl = widget.querySelector("[data-chatbot-quick-replies]");
  const form = widget.querySelector("[data-chatbot-form]");
  const input = widget.querySelector("[data-chatbot-input]");

  let rulesPayload = null;

  function normalise(text) {
    return String(text || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .trim();
  }

  function addMessage(role, text) {
    const message = document.createElement("div");
    message.className = `chatbot-message ${role}`;
    message.textContent = text;
    messagesEl.appendChild(message);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function renderQuickReplies(replies = []) {
    quickRepliesEl.innerHTML = "";
    replies.slice(0, 5).forEach((reply) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = reply;
      button.addEventListener("click", () => {
        addMessage("user", reply);
        respond(reply);
      });
      quickRepliesEl.appendChild(button);
    });
  }

  function findAnswer(rawQuestion) {
    if (!rulesPayload) return null;
    const question = normalise(rawQuestion);

    let bestMatch = null;
    let bestScore = 0;

    for (const rule of rulesPayload.rules || []) {
      let score = 0;
      for (const keyword of rule.keywords || []) {
        const normalizedKeyword = normalise(keyword);
        if (!normalizedKeyword) continue;
        if (question.includes(normalizedKeyword)) {
          score += Math.max(1, normalizedKeyword.length);
        }
      }
      if (score > bestScore) {
        bestScore = score;
        bestMatch = rule;
      }
    }

    return bestMatch || rulesPayload.fallback;
  }

  function respond(question) {
    const answer = findAnswer(question);
    if (!answer) {
      addMessage("bot", "Chargement de l’assistant en cours…");
      return;
    }
    addMessage("bot", answer.answer);
    renderQuickReplies(answer.quick_replies || []);
  }

  async function loadRules() {
    if (rulesPayload) return rulesPayload;

    try {
      const response = await fetch(window.GREENBIN_CHATBOT_RULES_URL || "/static/data/chatbot_rules.json", {
        cache: "no-store"
      });
      rulesPayload = await response.json();
    } catch (error) {
      rulesPayload = {
        fallback: {
          answer: "Assistant indisponible pour le moment. Les réponses sont chargées depuis un fichier JSON local.",
          quick_replies: []
        },
        welcome: {
          answer: "Assistant GreenBin indisponible pour le moment.",
          quick_replies: []
        },
        rules: []
      };
    }

    return rulesPayload;
  }

  async function openPanel() {
    panel.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
    widget.classList.add("open");

    await loadRules();

    if (!messagesEl.dataset.initialized) {
      addMessage("bot", rulesPayload.welcome.answer);
      renderQuickReplies(rulesPayload.welcome.quick_replies || []);
      messagesEl.dataset.initialized = "true";
    }

    setTimeout(() => input.focus(), 50);
  }

  function closePanel() {
    panel.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    widget.classList.remove("open");
  }

  toggle.addEventListener("click", () => {
    if (panel.hidden) openPanel();
    else closePanel();
  });

  closeButton.addEventListener("click", closePanel);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    input.value = "";
    addMessage("user", question);

    await loadRules();
    respond(question);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) closePanel();
  });
})();
