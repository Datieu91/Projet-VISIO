let pendingReports = [];
let currentIndex = 0;
let processed = 0;
let startTime = Date.now();

const topPending = document.getElementById("topPending");
const avgTime = document.getElementById("avgTime");
const agentEmpty = document.getElementById("agentEmpty");
const agentImage = document.getElementById("agentImage");
const aiBadge = document.getElementById("aiBadge");
const aiText = document.getElementById("aiText");
const recentAnnotations = document.getElementById("recentAnnotations");
const refreshRecentButton = document.getElementById("refreshRecentButton");

const detailId = document.getElementById("detailId");
const detailLocation = document.getElementById("detailLocation");
const detailFileSize = document.getElementById("detailFileSize");
const detailColor = document.getElementById("detailColor");
const detailDimensions = document.getElementById("detailDimensions");
const detailContrast = document.getElementById("detailContrast");
const detailPrediction = document.getElementById("detailPrediction");
const detailRisk = document.getElementById("detailRisk");
const detailQuality = document.getElementById("detailQuality");
const detailTags = document.getElementById("detailTags");
const colorSwatch = document.getElementById("colorSwatch");

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || "Erreur serveur.");
  }

  return data;
}

async function loadPending() {
  try {
    pendingReports = await fetchJson("/api/images/pending");
    currentIndex = 0;
    renderCurrent();
  } catch (error) {
    alert(error.message);
  }
}

function updateMetrics() {
  topPending.textContent = pendingReports.length;
  if (processed === 0) {
    avgTime.textContent = "-- s";
  } else {
    const seconds = (Date.now() - startTime) / 1000;
    avgTime.textContent = `${(seconds / processed).toFixed(1)} s`;
  }
}

function renderCurrent() {
  updateMetrics();

  if (pendingReports.length === 0) {
    agentImage.hidden = true;
    agentImage.removeAttribute("src");
    aiBadge.hidden = true;
    agentEmpty.hidden = false;
    clearDetails();
    return;
  }

  const report = pendingReports[currentIndex];
  agentEmpty.hidden = true;
  agentImage.hidden = false;
  aiBadge.hidden = false;
  agentImage.src = report.image_url;
  aiText.textContent = `Prédiction : ${report.ai_prediction || "--"} · ${report.ai_confidence ?? "--"}%`;

  detailId.textContent = `#${report.id}`;
  detailLocation.textContent = report.lat && report.lng ? `${Number(report.lat).toFixed(5)}, ${Number(report.lng).toFixed(5)}` : "--";
  detailFileSize.textContent = `${report.file_size_kb || "--"} Ko`;
  detailColor.textContent = report.avg_color_hex || "--";
  detailDimensions.textContent = report.dimensions || "--";
  detailContrast.textContent = report.contrast_level ?? "--";
  detailPrediction.textContent = report.ai_prediction ? `${report.ai_prediction} · ${report.ai_confidence}%` : "--";
  detailRisk.textContent = report.risk_score !== null ? `${report.risk_score}/100 · ${report.risk_level}` : "--";
  detailQuality.textContent = report.quality_score !== null ? `${report.quality_score}/100 · ${report.quality_warning}` : "--";
  detailTags.textContent = report.citizen_tags || "Aucun tag";
  colorSwatch.style.background = report.avg_color_hex || "transparent";
}

function clearDetails() {
  detailId.textContent = "#--";
  detailLocation.textContent = "--";
  detailFileSize.textContent = "-- Ko";
  detailColor.textContent = "--";
  detailDimensions.textContent = "--";
  detailContrast.textContent = "--";
  detailPrediction.textContent = "--";
  detailRisk.textContent = "--";
  detailQuality.textContent = "--";
  detailTags.textContent = "Aucun signalement en attente";
  colorSwatch.style.background = "transparent";
}

function statusLabel(report) {
  if (report.status === "Validated") return report.agent_annotation || "Validé";
  if (report.status === "Ignored") return "Ignoré";
  return report.status || "--";
}

function renderRecentAnnotations(reports) {
  if (!recentAnnotations) return;

  if (!reports.length) {
    recentAnnotations.innerHTML = `<p class="muted-note">Aucune annotation récente.</p>`;
    return;
  }

  recentAnnotations.innerHTML = reports.map((report) => `
    <article class="recent-item" data-id="${report.id}">
      <img src="${report.image_url}" alt="Signalement ${report.id}" loading="lazy">
      <div class="recent-main">
        <strong>#${report.id} · ${statusLabel(report)}</strong>
        <small>${report.timestamp} · IA ${report.ai_prediction || "--"} ${report.ai_confidence ? `(${report.ai_confidence}%)` : ""}</small>
        <div class="recent-actions">
          <button type="button" class="mini-action empty" data-edit="Vide">Vide</button>
          <button type="button" class="mini-action full" data-edit="Pleine">Pleine</button>
          <button type="button" class="mini-action undo" data-reset="true">Annuler</button>
        </div>
      </div>
    </article>
  `).join("");
}

async function loadRecentAnnotations() {
  if (!recentAnnotations) return;

  try {
    const reports = await fetchJson("/api/images/recent-annotations?limit=8");
    renderRecentAnnotations(reports);
  } catch (error) {
    recentAnnotations.innerHTML = `<p class="muted-note">${error.message}</p>`;
  }
}

async function annotate(annotation, animationClass = "swipe-up") {
  if (pendingReports.length === 0) return;
  const report = pendingReports[currentIndex];

  agentImage.classList.add(animationClass);

  try {
    await fetchJson(`/api/images/${report.id}/annotate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ annotation })
    });
  } catch (error) {
    alert(error.message);
    agentImage.classList.remove(animationClass);
    return;
  }

  setTimeout(() => {
    agentImage.classList.remove(animationClass);
    processed += 1;
    pendingReports.splice(currentIndex, 1);
    if (currentIndex >= pendingReports.length) currentIndex = 0;
    renderCurrent();
    loadRecentAnnotations();
  }, 250);
}

async function editAnnotation(reportId, annotation) {
  try {
    await fetchJson(`/api/images/${reportId}/annotate`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ annotation })
    });
    await loadRecentAnnotations();
    await loadPending();
  } catch (error) {
    alert(error.message);
  }
}

async function resetAnnotation(reportId) {
  try {
    const data = await fetchJson(`/api/images/${reportId}/reset-annotation`, { method: "POST" });
    if (!pendingReports.some((report) => report.id === data.report.id)) {
      pendingReports.unshift(data.report);
    }
    currentIndex = 0;
    renderCurrent();
    await loadRecentAnnotations();
  } catch (error) {
    alert(error.message);
  }
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => {
    const action = button.dataset.action;
    if (action === "Vide") annotate(action, "swipe-left");
    else if (action === "Pleine") annotate(action, "swipe-right");
    else annotate(action, "swipe-up");
  });
});

if (recentAnnotations) {
  recentAnnotations.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    const item = event.target.closest(".recent-item");
    if (!button || !item) return;

    const reportId = Number(item.dataset.id);
    if (button.dataset.edit) editAnnotation(reportId, button.dataset.edit);
    if (button.dataset.reset) resetAnnotation(reportId);
  });
}

if (refreshRecentButton) refreshRecentButton.addEventListener("click", loadRecentAnnotations);

document.addEventListener("keydown", (event) => {
  if (event.repeat) return;
  if (event.key === "ArrowLeft") annotate("Vide", "swipe-left");
  if (event.key === "ArrowRight") annotate("Pleine", "swipe-right");
  if (event.code === "Space") {
    event.preventDefault();
    annotate("Ignored", "swipe-up");
  }
});

loadPending();
loadRecentAnnotations();
