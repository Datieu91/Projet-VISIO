let binsMap = null;
let binsLayer = null;

const binsList = document.getElementById("binsList");
const binForm = document.getElementById("binForm");
const binLat = document.getElementById("binLat");
const binLng = document.getElementById("binLng");

function createTileLayer() {
  return L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap &copy; CARTO'
  });
}

function initBinsMap() {
  const el = document.getElementById("binsMap");
  if (!el || typeof L === "undefined") return;
  binsMap = L.map(el, { zoomControl: false, preferCanvas: true }).setView([48.78975, 2.36926], 14);
  createTileLayer().addTo(binsMap);
  L.control.zoom({ position: "bottomright" }).addTo(binsMap);
  binsLayer = L.layerGroup().addTo(binsMap);
  binsMap.on("click", (event) => {
    if (binLat) binLat.value = event.latlng.lat.toFixed(6);
    if (binLng) binLng.value = event.latlng.lng.toFixed(6);
  });
  setTimeout(() => binsMap.invalidateSize(), 250);
}

async function loadBins() {
  const response = await fetch("/api/bin-locations");
  if (!response.ok) return;
  const bins = await response.json();

  if (binsLayer) binsLayer.clearLayers();
  const bounds = [];

  bins.forEach((bin) => {
    bounds.push([bin.lat, bin.lng]);
    if (binsLayer) {
      L.circleMarker([bin.lat, bin.lng], {
        radius: 8,
        color: "white",
        weight: 2,
        fillColor: bin.full_active_count ? "#ef4444" : "#22c55e",
        fillOpacity: 0.9
      }).bindPopup(`
        <strong>${bin.name}</strong><br>
        Zone : ${bin.zone || "--"}<br>
        Type : ${bin.bin_type}<br>
        Signalements actifs : ${bin.active_report_count || 0}
      `).addTo(binsLayer);
    }
  });

  if (binsMap && bounds.length) binsMap.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });

  if (binsList) {
    binsList.innerHTML = bins.map((bin) => `
      <article class="bin-history-card">
        <strong>${bin.name}</strong>
        <small>${bin.zone || "Zone non renseignée"} · ${bin.bin_type} · ${bin.capacity_l || "--"} L</small>
        <div class="ops-grid compact">
          <div><span>${bin.report_count || 0}</span><small>Historique</small></div>
          <div><span>${bin.active_report_count || 0}</span><small>Actifs</small></div>
          <div><span>${bin.full_active_count || 0}</span><small>Pleines</small></div>
        </div>
      </article>
    `).join("") || `<p class="muted-text">Aucune poubelle officielle enregistrée.</p>`;
  }
}

if (binForm) {
  binForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(binForm);
    const payload = Object.fromEntries(formData.entries());
    const response = await fetch("/api/bin-locations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      alert(data.error || "Impossible d’ajouter l’emplacement.");
      return;
    }

    binForm.reset();
    await loadBins();
  });
}

initBinsMap();
loadBins();
