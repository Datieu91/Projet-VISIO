let selectedImage = null;
let latitude = null;
let longitude = null;
let citizenMap = null;
let citizenMarker = null;

const form = document.getElementById("uploadForm");
const imageInput = document.getElementById("imageInput");
const preview = document.getElementById("preview");
const gpsStatus = document.getElementById("gpsStatus");
const resetButton = document.getElementById("resetButton");
const resultCard = document.getElementById("resultCard");
const resultContent = document.getElementById("resultContent");
const sizeOriginal = document.getElementById("sizeOriginal");
const sizeOptimized = document.getElementById("sizeOptimized");
const citizenStatus = document.getElementById("citizenStatus");
const defaultPosition = [48.8566, 2.3522];

const modernMapTiles = {
  dark: L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 20,
    attribution: '&copy; OpenStreetMap &copy; CARTO'
  }),
  light: L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 20,
    attribution: '&copy; OpenStreetMap &copy; CARTO'
  })
};

const citizenIcon = L.divIcon({
  className: "citizen-pin",
  html: "<span>📍</span>",
  iconSize: [42, 42],
  iconAnchor: [21, 42],
  popupAnchor: [0, -38]
});

function formatSize(bytes) {
  if (!bytes) return "--";
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} Mo`;
}

function updateLocation(lat, lng, shouldMoveMap = true) {
  latitude = lat;
  longitude = lng;
  gpsStatus.textContent = `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;

  if (!citizenMap || !citizenMarker) return;
  citizenMarker.setLatLng([latitude, longitude]);
  if (shouldMoveMap) citizenMap.setView([latitude, longitude], 16);
}

function initCitizenMap() {
  const mapElement = document.getElementById("citizenMap");
  if (!mapElement || typeof L === "undefined") {
    if (gpsStatus) gpsStatus.textContent = "Carte indisponible";
    return;
  }

  citizenMap = L.map(mapElement, {
    zoomControl: true,
    scrollWheelZoom: true
  }).setView(defaultPosition, 13);

  modernMapTiles.dark.addTo(citizenMap);
  L.control.layers(
    { "Mode sombre": modernMapTiles.dark, "Mode clair": modernMapTiles.light },
    {},
    { position: "bottomright", collapsed: false }
  ).addTo(citizenMap);

  citizenMarker = L.marker(defaultPosition, { draggable: true, icon: citizenIcon }).addTo(citizenMap);
  citizenMarker.bindPopup("Position du signalement<br>Déplacez le marqueur si besoin.").openPopup();

  citizenMarker.on("dragend", () => {
    const position = citizenMarker.getLatLng();
    updateLocation(position.lat, position.lng, false);
  });

  citizenMap.on("click", (event) => {
    updateLocation(event.latlng.lat, event.latlng.lng, false);
  });

  updateLocation(defaultPosition[0], defaultPosition[1], false);
}

imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (!file) return;
  selectedImage = file;
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  sizeOriginal.textContent = formatSize(file.size);
  sizeOptimized.textContent = "Envoyée telle quelle";
  citizenStatus.textContent = "Image prête";
  resultCard.hidden = true;
});

resetButton.addEventListener("click", () => {
  selectedImage = null;
  imageInput.value = "";
  preview.hidden = true;
  resultCard.hidden = true;
  sizeOriginal.textContent = "--";
  sizeOptimized.textContent = "--";
  citizenStatus.textContent = "Prêt";
});

initCitizenMap();

if ("geolocation" in navigator) {
  navigator.geolocation.getCurrentPosition(
    (position) => {
      updateLocation(position.coords.latitude, position.coords.longitude, true);
      citizenStatus.textContent = "GPS trouvé";
    },
    () => {
      gpsStatus.textContent = `${defaultPosition[0].toFixed(5)}, ${defaultPosition[1].toFixed(5)} · GPS indisponible`;
    },
    { enableHighAccuracy: true, timeout: 8000 }
  );
} else {
  gpsStatus.textContent = `${defaultPosition[0].toFixed(5)}, ${defaultPosition[1].toFixed(5)} · GPS non supporté`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedImage) {
    alert("Ajoute d'abord une image.");
    return;
  }

  citizenStatus.textContent = "Envoi…";
  const tags = Array.from(document.querySelectorAll(".tag-box input:checked")).map((tag) => tag.value);
  const formData = new FormData();
  formData.append("image", selectedImage);
  if (latitude !== null) formData.append("lat", latitude);
  if (longitude !== null) formData.append("lng", longitude);
  formData.append("tags", tags.join(", "));

  const response = await fetch("/api/upload", { method: "POST", body: formData });
  const data = await response.json();

  if (!response.ok) {
    citizenStatus.textContent = "Erreur";
    alert(data.error || "Erreur lors de l'envoi.");
    return;
  }

  const report = data.report;
  citizenStatus.textContent = "Transmis";
  resultContent.innerHTML = `
    <p><strong>ID :</strong> #${report.id}</p>
    <p><strong>Localisation :</strong> ${report.lat?.toFixed ? report.lat.toFixed(5) : report.lat}, ${report.lng?.toFixed ? report.lng.toFixed(5) : report.lng}</p>
    <p><strong>Prédiction :</strong> ${report.ai_prediction} (${report.ai_confidence}%)</p>
    <p><strong>Score de risque :</strong> ${report.risk_score}/100 · ${report.risk_level}</p>
    <p><strong>Qualité image :</strong> ${report.quality_score}/100 · ${report.quality_warning}</p>
    <p><strong>Dimensions :</strong> ${report.dimensions} · ${report.file_size_kb} Ko</p>
    <p><strong>Couleur moyenne :</strong> ${report.avg_color_hex}</p>
  `;
  resultCard.hidden = false;
  resultCard.scrollIntoView({ behavior: "smooth" });
});
