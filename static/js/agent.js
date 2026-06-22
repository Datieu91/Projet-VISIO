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

async function loadPending() {
  const response = await fetch("/api/images/pending");
  pendingReports = await response.json();
  currentIndex = 0;
  renderCurrent();
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
  aiText.textContent = `Prédiction : ${report.ai_prediction} · ${report.ai_confidence}%`;

  detailId.textContent = `#${report.id}`;
  detailLocation.textContent = report.lat && report.lng ? `${report.lat.toFixed(5)}, ${report.lng.toFixed(5)}` : "--";
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

async function annotate(annotation, animationClass = "swipe-up") {
  if (pendingReports.length === 0) return;
  const report = pendingReports[currentIndex];

  agentImage.classList.add(animationClass);

  const response = await fetch(`/api/images/${report.id}/annotate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ annotation })
  });

  if (!response.ok) {
    const error = await response.json();
    alert(error.error || "Erreur d'annotation.");
    agentImage.classList.remove(animationClass);
    return;
  }

  setTimeout(() => {
    agentImage.classList.remove(animationClass);
    processed += 1;
    pendingReports.splice(currentIndex, 1);
    if (currentIndex >= pendingReports.length) currentIndex = 0;
    renderCurrent();
  }, 250);
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => {
    const action = button.dataset.action;
    if (action === "Vide") annotate(action, "swipe-left");
    else if (action === "Pleine" || action === "Débordante") annotate(action, "swipe-right");
    else annotate(action, "swipe-up");
  });
});

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
