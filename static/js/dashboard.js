const topPending = document.getElementById("topPending");
const topCadence = document.getElementById("topCadence");
const weeklyTotal = document.getElementById("weeklyTotal");
const fullRate = document.getElementById("fullRate");
const avgProcessingTime = document.getElementById("avgProcessingTime");
const emptyCount = document.getElementById("emptyCount");
const fullCount = document.getElementById("fullCount");
const highRiskCount = document.getElementById("highRiskCount");
const barEmpty = document.getElementById("barEmpty");
const barFull = document.getElementById("barFull");
const barHighRisk = document.getElementById("barHighRisk");
const reportsTable = document.getElementById("reportsTable");
const validatedCount = document.getElementById("validatedCount");
const ignoredCount = document.getElementById("ignoredCount");
const riskAvg = document.getElementById("riskAvg");
const refreshButton = document.getElementById("refreshButton");
const refreshMapButton = document.getElementById("refreshMapButton");
const canvas = document.getElementById("signalementsChart");

const filterForm = document.getElementById("dashboardFilters");
const resetFiltersButton = document.getElementById("resetFiltersButton");
const exportCsvButton = document.getElementById("exportCsvButton");
const heatmapToggle = document.getElementById("heatmapToggle");

let dashboardMap = null;
let markerLayer = null;
let heatLayer = null;
let canvasRenderer = null;

const defaultMapCenter = [48.8566, 2.3522];
const emptySeries = {
  labels: ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
  full: [0, 0, 0, 0, 0, 0, 0],
  empty: [0, 0, 0, 0, 0, 0, 0]
};

function createTileLayer() {
  return L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
    minZoom: 4,
    updateWhenIdle: true,
    updateWhenZooming: false,
    keepBuffer: 1,
    attribution: '&copy; OpenStreetMap &copy; CARTO'
  });
}

function pct(value, total) {
  return total ? Math.round((value / total) * 100) : 0;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("fr-FR");
}

function getFilterParams() {
  const params = new URLSearchParams();
  if (!filterForm) return params;

  new FormData(filterForm).forEach((value, key) => {
    const cleaned = String(value || "").trim();
    if (cleaned) params.append(key, cleaned);
  });

  return params;
}

function withFilters(url, extra = {}) {
  const params = getFilterParams();
  Object.entries(extra).forEach(([key, value]) => params.set(key, value));
  const query = params.toString();
  return query ? `${url}?${query}` : url;
}

function syncExportLink() {
  if (exportCsvButton) {
    exportCsvButton.href = withFilters("/exports/reports.csv");
  }
}

function dayLabel(dateString) {
  const date = new Date(String(dateString || "").replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return null;
  return ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"][date.getDay()];
}

function buildWeeklySeries(reports) {
  const labels = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
  const full = Object.fromEntries(labels.map((label) => [label, 0]));
  const empty = Object.fromEntries(labels.map((label) => [label, 0]));

  reports.forEach((report) => {
    const label = dayLabel(report.timestamp);
    if (!label) return;
    const finalLabel = report.agent_annotation || report.ai_prediction;
    if (finalLabel === "Pleine") full[label] += 1;
    if (finalLabel === "Vide") empty[label] += 1;
  });

  return {
    labels,
    full: labels.map((label) => full[label]),
    empty: labels.map((label) => empty[label])
  };
}

function drawSmoothLine(ctx, points, color, fillColor) {
  if (!points.length) return;

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);

  for (let i = 0; i < points.length - 1; i += 1) {
    const current = points[i];
    const next = points[i + 1];
    const midX = (current.x + next.x) / 2;
    ctx.bezierCurveTo(midX, current.y, midX, next.y, next.x, next.y);
  }

  ctx.strokeStyle = color;
  ctx.lineWidth = 4;
  ctx.stroke();

  ctx.lineTo(points[points.length - 1].x, ctx.canvas.height / (window.devicePixelRatio || 1) - 32);
  ctx.lineTo(points[0].x, ctx.canvas.height / (window.devicePixelRatio || 1) - 32);
  ctx.closePath();
  ctx.fillStyle = fillColor;
  ctx.fill();

  points.forEach((point) => {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = "#0f172a";
    ctx.lineWidth = 2;
    ctx.stroke();
  });
}

function drawChart(series) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(rect.width, 320);
  const height = 320;

  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.height = `${height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const padding = { top: 28, right: 28, bottom: 44, left: 44 };
  const maxValue = Math.max(5, ...series.full, ...series.empty);
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const labels = series.labels;

  ctx.clearRect(0, 0, width, height);
  ctx.clearRect(0, 0, width, height);

  ctx.strokeStyle = "rgba(30, 167, 255, 0.16)";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#5b7895";
  ctx.font = "12px Inter, Segoe UI, Arial";

  for (let i = 0; i <= 5; i += 1) {
    const y = padding.top + (chartHeight / 5) * i;
    const value = Math.round(maxValue - (maxValue / 5) * i);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    ctx.fillText(String(value), 10, y + 4);
  }

  labels.forEach((label, i) => {
    const x = padding.left + (chartWidth / Math.max(labels.length - 1, 1)) * i;
    ctx.beginPath();
    ctx.moveTo(x, padding.top);
    ctx.lineTo(x, height - padding.bottom);
    ctx.stroke();
    ctx.fillText(label, x - 10, height - 14);
  });

  const toPoints = (values) => values.map((value, i) => ({
    x: padding.left + (chartWidth / Math.max(values.length - 1, 1)) * i,
    y: padding.top + chartHeight - (value / maxValue) * chartHeight
  }));

  drawSmoothLine(ctx, toPoints(series.empty), "#22c55e", "rgba(34, 197, 94, 0.16)");
  drawSmoothLine(ctx, toPoints(series.full), "#ef3b55", "rgba(239, 59, 85, 0.16)");
}

function markerStyle(report) {
  if (report.status === "Pending") return { color: "#94a3b8", radius: 7 };
  if (report.risk_level === "Élevé") return { color: "#ef4444", radius: 9 };
  if (report.risk_level === "Moyen" || report.agent_annotation === "Pleine") return { color: "#f59e0b", radius: 8 };
  return { color: "#22c55e", radius: 7 };
}

function initDashboardMap() {
  const mapElement = document.getElementById("dashboardMap");
  if (!mapElement || typeof L === "undefined") return;

  canvasRenderer = L.canvas({ padding: 0.5 });
  dashboardMap = L.map(mapElement, {
    zoomControl: false,
    scrollWheelZoom: false,
    preferCanvas: true,
    zoomAnimation: false,
    fadeAnimation: false,
    renderer: canvasRenderer
  }).setView(defaultMapCenter, 13);

  createTileLayer().addTo(dashboardMap);
  L.control.zoom({ position: "bottomright" }).addTo(dashboardMap);
  markerLayer = L.layerGroup().addTo(dashboardMap);
  setTimeout(() => dashboardMap.invalidateSize(), 250);
}

function updateHeatmap(reports) {
  if (!dashboardMap || typeof L === "undefined" || typeof L.heatLayer !== "function") return;
  if (heatLayer) {
    dashboardMap.removeLayer(heatLayer);
    heatLayer = null;
  }

  if (heatmapToggle && !heatmapToggle.checked) return;

  const heatPoints = reports
    .filter((report) => report.lat !== null && report.lng !== null)
    .map((report) => [Number(report.lat), Number(report.lng), Math.max(0.12, Math.min((Number(report.risk_score) || 0) / 100, 1))])
    .filter((point) => !Number.isNaN(point[0]) && !Number.isNaN(point[1]));

  if (!heatPoints.length) return;

  heatLayer = L.heatLayer(heatPoints, {
    radius: 34,
    blur: 24,
    maxZoom: 17,
    minOpacity: 0.22,
    gradient: {
      0.2: "#22c55e",
      0.45: "#f59e0b",
      0.75: "#ef4444",
      1.0: "#7f1d1d"
    }
  }).addTo(dashboardMap);
}

function updateDashboardMap(reports) {
  if (!dashboardMap || !markerLayer) return;
  markerLayer.clearLayers();

  const geolocatedReports = reports.filter((report) => report.lat !== null && report.lng !== null);

  if (!geolocatedReports.length) {
    dashboardMap.setView(defaultMapCenter, 13);
    return;
  }

  const bounds = [];
  geolocatedReports.forEach((report) => {
    const lat = Number(report.lat);
    const lng = Number(report.lng);
    if (Number.isNaN(lat) || Number.isNaN(lng)) return;

    const style = markerStyle(report);
    bounds.push([lat, lng]);

    L.circleMarker([lat, lng], {
      renderer: canvasRenderer,
      radius: style.radius,
      color: "rgba(255,255,255,.88)",
      weight: 2,
      fillColor: style.color,
      fillOpacity: 0.88
    })
      .bindPopup(`
        <div class="modern-popup">
          <div class="popup-title">Signalement #${report.id}</div>
          <div class="popup-grid">
            <span>Statut</span><strong>${report.status}</strong>
            <span>Agent</span><strong>${report.agent_annotation || "--"}</strong>
            <span>IA</span><strong>${report.ai_prediction || "--"} ${report.ai_confidence ? `(${report.ai_confidence}%)` : ""}</strong>
            <span>Risque</span><strong>${report.risk_score ?? 0}/100 · ${report.risk_level || "--"}</strong>
            <span>Priorité</span><strong>${report.priority_level || "--"}</strong>
            <span>Emplacement</span><strong>${report.location_type === "wild_dump" ? "Dépôt sauvage" : (report.bin_location_name || "Non rattaché")}</strong>
            <span>Tags</span><strong>${report.citizen_tags || "--"}</strong>
          </div>
          <button class="btn success small" data-dashboard-collect="${report.id}" type="button">Marquer collecté</button>
          <img src="${report.image_url}" alt="Signalement ${report.id}" class="popup-img" loading="lazy">
        </div>
      `)
      .addTo(markerLayer);
  });

  if (bounds.length === 1) {
    dashboardMap.setView(bounds[0], 16);
  } else if (bounds.length > 1) {
    dashboardMap.fitBounds(bounds, { padding: [30, 30], maxZoom: 16 });
  }

  updateHeatmap(geolocatedReports);
}

function renderReportsTable(reports) {
  reportsTable.innerHTML = reports.slice(0, 12).map((report) => `
    <tr>
      <td>#${report.id}</td>
      <td>${report.timestamp}</td>
      <td><img src="${report.image_url}" alt="Image ${report.id}" loading="lazy"></td>
      <td>${report.ai_prediction || "--"} ${report.ai_confidence ? `(${report.ai_confidence}%)` : ""}</td>
      <td>${report.risk_score ?? 0}/100 · ${report.risk_level || "--"}</td>
      <td>${report.status}</td>
      <td>${report.agent_annotation || "--"}</td>
    </tr>
  `).join("") || `<tr><td colspan="7">Aucun signalement ne correspond aux filtres.</td></tr>`;
}


async function collectFromDashboard(reportId) {
  const response = await fetch(`/api/images/${reportId}/collect`, { method: "POST" });
  if (!response.ok) {
    alert("Impossible de marquer ce signalement comme collecté.");
    return;
  }
  loadDashboard();
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-dashboard-collect]");
  if (!button) return;
  collectFromDashboard(button.dataset.dashboardCollect);
});

async function loadDashboard() {
  syncExportLink();
  const [statsResponse, reportsResponse, mapResponse] = await Promise.all([
    fetch(withFilters("/api/stats")),
    fetch(withFilters("/api/images", { limit: 100 })),
    fetch(withFilters("/api/map-reports", { limit: 250 }))
  ]);

  if (!statsResponse.ok || !reportsResponse.ok || !mapResponse.ok) return;

  const stats = await statsResponse.json();
  const reports = await reportsResponse.json();
  const mapReports = await mapResponse.json();
  const series = reports.length ? buildWeeklySeries(reports) : emptySeries;
  const fullPercent = stats.total ? pct(stats.full_count, stats.total) : 0;

  topPending.textContent = stats.pending || 0;
  topCadence.textContent = reports.length ? "1.8s" : "-- s";
  weeklyTotal.textContent = formatNumber(stats.total || 0);
  fullRate.textContent = `${fullPercent}%`;
  avgProcessingTime.textContent = reports.length ? "1.8s" : "-- s";

  emptyCount.textContent = stats.empty_count || 0;
  fullCount.textContent = stats.full_count || 0;
  highRiskCount.textContent = stats.high_risk || 0;
  validatedCount.textContent = stats.validated || 0;
  ignoredCount.textContent = stats.ignored || 0;
  riskAvg.textContent = `${stats.avg_risk || 0}/100`;

  barEmpty.style.width = `${pct(stats.empty_count, stats.total)}%`;
  barFull.style.width = `${pct(stats.full_count, stats.total)}%`;
  barHighRisk.style.width = `${pct(stats.high_risk, stats.total)}%`;

  drawChart(series);
  renderReportsTable(reports);
  updateDashboardMap(mapReports);
}

initDashboardMap();
if (refreshButton) refreshButton.addEventListener("click", loadDashboard);
if (refreshMapButton) refreshMapButton.addEventListener("click", loadDashboard);
if (heatmapToggle) heatmapToggle.addEventListener("change", loadDashboard);
if (filterForm) {
  filterForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loadDashboard();
  });

  filterForm.querySelectorAll("select, input").forEach((field) => {
    field.addEventListener("change", loadDashboard);
  });
}
if (resetFiltersButton && filterForm) {
  resetFiltersButton.addEventListener("click", () => {
    filterForm.reset();
    loadDashboard();
  });
}
window.addEventListener("resize", () => {
  drawChart(emptySeries);
  if (dashboardMap) dashboardMap.invalidateSize();
});
loadDashboard();
