let selectedImage = null;
let latitude = null;
let longitude = null;
let citizenMap = null;
let citizenMarker = null;
let userMarker = null;
let accuracyCircle = null;
let binLayer = null;
let qualityAssessment = { blocking: false, warnings: [] };

const form = document.getElementById("uploadForm");
const imageInput = document.getElementById("imageInput");
const preview = document.getElementById("preview");
const gpsStatus = document.getElementById("gpsStatus");
const gpsAvailability = document.getElementById("gpsAvailability");
const gpsDetail = document.getElementById("gpsDetail");
const resetButton = document.getElementById("resetButton");
const sendButton = document.getElementById("sendButton");
const resultCard = document.getElementById("resultCard");
const resultContent = document.getElementById("resultContent");
const sizeOriginal = document.getElementById("sizeOriginal");
const sizeOptimized = document.getElementById("sizeOptimized");
const citizenStatus = document.getElementById("citizenStatus");
const qualityPanel = document.getElementById("qualityPanel");
const qualityMessage = document.getElementById("qualityMessage");
const qualityList = document.getElementById("qualityList");
const uploadPreviewPanel = document.getElementById("uploadPreviewPanel");
const uploadCard = document.querySelector(".upload-card");
const uploadForm = document.getElementById("uploadForm");
const floatingUploadButton = document.getElementById("floatingUploadButton");
const optionsCard = document.getElementById("optionsCard");

const MAX_SIZE_BYTES = 5 * 1024 * 1024;
const MIN_WIDTH = 300;
const MIN_HEIGHT = 300;
const defaultPosition = [48.8566, 2.3522];

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

const reportIcon = L.divIcon({
  className: "citizen-pin",
  html: "<span></span>",
  iconSize: [26, 34],
  iconAnchor: [13, 34],
  popupAnchor: [0, -30]
});

const userIcon = L.divIcon({
  className: "user-position-pin",
  html: "<span></span>",
  iconSize: [14, 14],
  iconAnchor: [7, 7]
});


const officialBinIcon = L.divIcon({
  className: "official-bin-pin",
  html: "<span>🗑️</span>",
  iconSize: [30, 30],
  iconAnchor: [15, 15]
});


function formatSize(bytes) {
  if (!bytes) return "--";
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} Mo`;
}

function updateQualityPanel(state, message, items = []) {
  if (!qualityPanel) return;
  qualityPanel.classList.remove("neutral", "ok", "warning", "error");
  qualityPanel.classList.add(state);
  qualityMessage.textContent = message;
  qualityList.innerHTML = items.map((item) => `<li>${item}</li>`).join("");
}

function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    const url = URL.createObjectURL(file);
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Impossible de lire l'image."));
    };
    image.src = url;
  });
}

function computeSimpleQuality(image, file) {
  const blocking = [];
  const warnings = [];
  let brightness = 0;
  let blurScore = 999;

  if (!file.type.startsWith("image/")) blocking.push("Le fichier sélectionné n'est pas une image.");
  if (file.size > MAX_SIZE_BYTES) blocking.push("Image trop lourde : limite 5 Mo.");
  if (image.naturalWidth < MIN_WIDTH || image.naturalHeight < MIN_HEIGHT) {
    blocking.push(`Image trop petite : minimum conseillé ${MIN_WIDTH}×${MIN_HEIGHT}px.`);
  }

  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  const sampleSize = 96;
  canvas.width = sampleSize;
  canvas.height = sampleSize;
  ctx.drawImage(image, 0, 0, sampleSize, sampleSize);
  const { data } = ctx.getImageData(0, 0, sampleSize, sampleSize);

  let totalBrightness = 0;
  const gray = new Float32Array(sampleSize * sampleSize);
  for (let i = 0, px = 0; i < data.length; i += 4, px += 1) {
    const lum = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    gray[px] = lum;
    totalBrightness += lum;
  }
  brightness = totalBrightness / gray.length;

  let edgeSum = 0;
  let count = 0;
  for (let y = 1; y < sampleSize - 1; y += 1) {
    for (let x = 1; x < sampleSize - 1; x += 1) {
      const idx = y * sampleSize + x;
      const gx = Math.abs(gray[idx - 1] - gray[idx + 1]);
      const gy = Math.abs(gray[idx - sampleSize] - gray[idx + sampleSize]);
      edgeSum += gx + gy;
      count += 1;
    }
  }
  blurScore = edgeSum / Math.max(count, 1);

  if (brightness < 45) warnings.push("Image très sombre : la prédiction peut être moins fiable.");
  if (blurScore < 8) warnings.push("Image possiblement floue : vérifiez le cadrage avant l'envoi.");

  return {
    blocking: blocking.length > 0,
    blockingReasons: blocking,
    warnings,
    width: image.naturalWidth,
    height: image.naturalHeight,
    brightness: Math.round(brightness),
    blurScore: Math.round(blurScore * 10) / 10
  };
}

async function validateSelectedImage(file) {
  try {
    const image = await loadImageFromFile(file);
    const assessment = computeSimpleQuality(image, file);
    qualityAssessment = assessment;

    if (assessment.blocking) {
      updateQualityPanel("error", "Image refusée avant envoi.", assessment.blockingReasons);
      sendButton.disabled = true;
      return assessment;
    }

    const info = [`Dimensions : ${assessment.width}×${assessment.height}px`, `Luminosité : ${assessment.brightness}/255`];
    if (assessment.warnings.length) {
      updateQualityPanel("warning", "Image acceptée avec avertissement.", [...assessment.warnings, ...info]);
    } else {
      updateQualityPanel("ok", "Image exploitable pour l'analyse.", info);
    }

    sendButton.disabled = false;
    return assessment;
  } catch (error) {
    qualityAssessment = { blocking: true, blockingReasons: [error.message], warnings: [] };
    updateQualityPanel("error", "Image illisible.", [error.message]);
    sendButton.disabled = true;
    return qualityAssessment;
  }
}

function updateLocation(lat, lng, shouldMoveMap = true) {
  latitude = lat;
  longitude = lng;
  gpsStatus.textContent = `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;

  if (!citizenMap || !citizenMarker) return;
  citizenMarker.setLatLng([latitude, longitude]);
  if (shouldMoveMap) citizenMap.setView([latitude, longitude], 17, { animate: true });
}

function updateUserPosition(lat, lng, accuracy) {
  if (!citizenMap) return;
  const coords = [lat, lng];

  if (!userMarker) {
    userMarker = L.marker(coords, { icon: userIcon, interactive: false }).addTo(citizenMap);
  } else {
    userMarker.setLatLng(coords);
  }

  if (accuracyCircle) {
    accuracyCircle.remove();
    accuracyCircle = null;
  }
}


async function loadOfficialBins() {
  if (!citizenMap || typeof L === "undefined") return;
  try {
    const response = await fetch("/api/bin-locations");
    if (!response.ok) return;
    const bins = await response.json();
    if (binLayer) binLayer.remove();
    binLayer = L.layerGroup().addTo(citizenMap);
    bins.forEach((bin) => {
      L.marker([bin.lat, bin.lng], { icon: officialBinIcon, interactive: true })
        .bindPopup(`<strong>${bin.name}</strong><br>${bin.zone || "Emplacement officiel"}<br>${bin.bin_type}`)
        .addTo(binLayer);
    });
  } catch (error) {
    console.warn("Emplacements officiels indisponibles", error);
  }
}

function initCitizenMap() {
  const mapElement = document.getElementById("citizenMap");
  if (!mapElement || typeof L === "undefined") {
    if (gpsAvailability) gpsAvailability.textContent = "Carte indisponible";
    if (gpsStatus) gpsStatus.textContent = "Aucune prévisualisation cartographique";
    return;
  }

  citizenMap = L.map(mapElement, {
    zoomControl: false,
    scrollWheelZoom: false,
    tap: true,
    preferCanvas: true,
    zoomAnimation: true,
    fadeAnimation: true
  }).setView(defaultPosition, 16);

  createTileLayer().addTo(citizenMap);
  L.control.zoom({ position: "bottomright" }).addTo(citizenMap);

  citizenMarker = L.marker(defaultPosition, { draggable: true, icon: reportIcon }).addTo(citizenMap);
  citizenMarker.bindPopup("Position du signalement<br>Déplacez le marqueur si besoin.");

  citizenMarker.on("dragend", () => {
    const position = citizenMarker.getLatLng();
    updateLocation(position.lat, position.lng, false);
  });

  citizenMap.on("click", (event) => {
    updateLocation(event.latlng.lat, event.latlng.lng, false);
  });

  updateLocation(defaultPosition[0], defaultPosition[1], false);
  loadOfficialBins();
  setTimeout(() => citizenMap.invalidateSize(), 250);
}

imageInput.addEventListener("change", async () => {
  const file = imageInput.files[0];
  if (!file) return;
  selectedImage = file;
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  if (uploadPreviewPanel) uploadPreviewPanel.hidden = false;
  if (uploadForm) uploadForm.classList.add("has-image");
  if (floatingUploadButton) floatingUploadButton.hidden = true;
  if (uploadCard) { uploadCard.classList.remove("empty-upload"); uploadCard.classList.add("has-image"); }
  if (optionsCard) optionsCard.hidden = false;
  sizeOriginal.textContent = formatSize(file.size);
  sizeOptimized.textContent = "Optimisation serveur";
  resultCard.hidden = true;
  updateQualityPanel("neutral", "Analyse de la qualité en cours…", []);
  sendButton.disabled = true;
  await validateSelectedImage(file);
});

resetButton.addEventListener("click", () => {
  selectedImage = null;
  qualityAssessment = { blocking: false, warnings: [] };
  imageInput.value = "";
  preview.hidden = true;
  if (uploadPreviewPanel) uploadPreviewPanel.hidden = true;
  if (uploadForm) uploadForm.classList.remove("has-image");
  if (floatingUploadButton) floatingUploadButton.hidden = false;
  if (uploadCard) { uploadCard.classList.add("empty-upload"); uploadCard.classList.remove("has-image"); }
  if (optionsCard) optionsCard.hidden = true;
  resultCard.hidden = true;
  sizeOriginal.textContent = "--";
  sizeOptimized.textContent = "--";
  sendButton.disabled = false;
  updateQualityPanel("neutral", "Ajoutez une image pour vérifier sa qualité avant l’envoi.", []);
});

initCitizenMap();

if ("geolocation" in navigator) {
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;
      updateLocation(lat, lng, true);
      updateUserPosition(lat, lng, position.coords.accuracy);
      if (gpsAvailability) gpsAvailability.textContent = "GPS trouvé";
            gpsStatus.textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)} · votre position`;
    },
    () => {
      if (gpsAvailability) gpsAvailability.textContent = "GPS indisponible";
            gpsStatus.textContent = `${defaultPosition[0].toFixed(5)}, ${defaultPosition[1].toFixed(5)} · position par défaut`;
    },
    { enableHighAccuracy: false, timeout: 4500, maximumAge: 60000 }
  );
} else {
  if (gpsAvailability) gpsAvailability.textContent = "GPS non supporté";
    gpsStatus.textContent = `${defaultPosition[0].toFixed(5)}, ${defaultPosition[1].toFixed(5)} · position par défaut`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedImage) {
    alert("Ajoute d'abord une image.");
    return;
  }

  if (qualityAssessment.blocking) {
    alert("Cette image est refusée. Choisis une image plus nette, plus grande ou moins lourde.");
    return;
  }

  if (qualityAssessment.warnings?.length) {
    const proceed = confirm(`Attention : ${qualityAssessment.warnings.join(" ")}\n\nEnvoyer quand même ?`);
    if (!proceed) return;
  }

  sendButton.disabled = true;
  const tags = Array.from(document.querySelectorAll(".tag-box input:checked")).map((tag) => tag.value);
  const formData = new FormData();
  formData.append("image", selectedImage);
  if (latitude !== null) formData.append("lat", latitude);
  if (longitude !== null) formData.append("lng", longitude);
  formData.append("tags", tags.join(", "));

  const response = await fetch("/api/upload", { method: "POST", body: formData });
  const data = await response.json();

  if (!response.ok) {
    sendButton.disabled = false;
    alert(data.error || "Erreur lors de l'envoi.");
    return;
  }

  const report = data.report;
  sendButton.disabled = false;
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
