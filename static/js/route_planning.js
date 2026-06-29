let routeMap = null;
let routeLayer = null;
let stopsLayer = null;

const routeSummary = document.getElementById("routeSummary");
const routeStops = document.getElementById("routeStops");
const refreshRouteButton = document.getElementById("refreshRouteButton");

const defaultCenter = [48.8566, 2.3522];

function createTileLayer() {
  return L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap &copy; CARTO'
  });
}

function initRouteMap() {
  const el = document.getElementById("routeMap");
  if (!el || typeof L === "undefined") return;
  routeMap = L.map(el, { zoomControl: false, preferCanvas: true }).setView(defaultCenter, 13);
  createTileLayer().addTo(routeMap);
  L.control.zoom({ position: "bottomright" }).addTo(routeMap);
  routeLayer = L.layerGroup().addTo(routeMap);
  stopsLayer = L.layerGroup().addTo(routeMap);
  setTimeout(() => routeMap.invalidateSize(), 250);
}

function priorityClass(priority) {
  const p = String(priority || "").toLowerCase();
  if (p.includes("critique")) return "critical";
  if (p.includes("haute")) return "high";
  if (p.includes("moyenne")) return "medium";
  return "normal";
}

async function markCollected(reportId) {
  const response = await fetch(`/api/images/${reportId}/collect`, { method: "POST" });
  if (!response.ok) {
    alert("Impossible de marquer ce point comme collecté.");
    return;
  }
  await loadRoute();
}

function renderStops(route) {
  if (!routeStops) return;
  if (!route.stops.length) {
    routeStops.innerHTML = `<div class="empty-state compact"><strong>Aucune poubelle à collecter</strong><small>La carte opérationnelle ne contient actuellement aucun point plein ou critique.</small></div>`;
    return;
  }

  routeStops.innerHTML = route.stops.map((stop, index) => `
    <article class="route-stop ${priorityClass(stop.priority_level)}">
      <span class="route-rank">${index + 1}</span>
      <div class="route-stop-main">
        <strong>${stop.bin_location_name || `Signalement #${stop.id}`}</strong>
        <small>#${stop.id} · ${stop.location_type === "wild_dump" ? "Dépôt sauvage / hors emplacement" : "Poubelle officielle"} · ${stop.risk_score}/100 · ${stop.priority_level || stop.risk_level}</small>
        <small>Distance depuis précédent : ${stop.distance_from_previous_m || 0} m</small>
      </div>
      <button class="btn success small" data-collect="${stop.id}" type="button">Collecté</button>
    </article>
  `).join("");

  routeStops.querySelectorAll("[data-collect]").forEach((button) => {
    button.addEventListener("click", () => markCollected(button.dataset.collect));
  });
}

function renderMap(route) {
  if (!routeMap || !routeLayer || !stopsLayer) return;
  routeLayer.clearLayers();
  stopsLayer.clearLayers();

  const points = [[route.start.lat, route.start.lng], ...route.stops.map((stop) => [stop.lat, stop.lng])];

  L.circleMarker([route.start.lat, route.start.lng], {
    radius: 9, color: "white", weight: 2, fillColor: "#1ea7ff", fillOpacity: 0.9
  }).bindPopup("Départ tournée").addTo(stopsLayer);

  route.stops.forEach((stop, index) => {
    const color = stop.priority_level === "Critique" ? "#e11d48" : stop.priority_level === "Haute" ? "#f97316" : "#22c55e";
    L.circleMarker([stop.lat, stop.lng], {
      radius: 8 + Math.min(index, 5), color: "white", weight: 2, fillColor: color, fillOpacity: 0.92
    }).bindPopup(`
      <strong>${index + 1}. ${stop.bin_location_name || `Signalement #${stop.id}`}</strong><br>
      ${stop.location_type === "wild_dump" ? "Dépôt sauvage / hors emplacement" : "Poubelle officielle"}<br>
      Priorité : ${stop.priority_level || stop.risk_level}<br>
      Risque : ${stop.risk_score}/100
    `).addTo(stopsLayer);
  });

  if (points.length > 1) {
    L.polyline(points, { weight: 5, opacity: 0.76 }).addTo(routeLayer);
    routeMap.fitBounds(points, { padding: [40, 40], maxZoom: 15 });
  } else {
    routeMap.setView(defaultCenter, 13);
  }
}

async function loadRoute() {
  if (routeSummary) routeSummary.textContent = "Calcul…";
  const response = await fetch("/api/route-plan?limit=20");
  if (!response.ok) return;
  const route = await response.json();
  if (routeSummary) routeSummary.textContent = `${route.stop_count} arrêt(s) · ${route.total_distance_km} km`;
  renderMap(route);
  renderStops(route);
}

initRouteMap();
if (refreshRouteButton) refreshRouteButton.addEventListener("click", loadRoute);
loadRoute();
