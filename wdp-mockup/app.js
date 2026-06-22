// View Navigation
function switchView(viewId) {
  // Update buttons
  document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');

  // Update views
  document.querySelectorAll('.view').forEach(view => {
    view.classList.remove('active');
  });
  
  const targetView = document.getElementById(`view-${viewId}`);
  targetView.classList.add('active');

  // Re-render map if switching to dashboard to fix Leaflet sizing issue
  if (viewId === 'dashboard' && map) {
    setTimeout(() => {
      map.invalidateSize();
    }, 100);
  }
}

// --- CITIZEN VIEW LOGIC ---
function simulateUpload() {
  const uploadZone = document.getElementById('uploadZone');
  const loader = document.getElementById('uploadLoader');
  const success = document.getElementById('uploadSuccess');

  uploadZone.style.display = 'none';
  loader.style.display = 'flex';
  success.style.display = 'none';

  // Simulate network & background processing delay
  setTimeout(() => {
    loader.style.display = 'none';
    success.style.display = 'block';
    
    // Reset after 4 seconds
    setTimeout(() => {
      success.style.display = 'none';
      uploadZone.style.display = 'block';
      document.getElementById('fileInput').value = ''; // clear input
    }, 4000);
  }, 2000);
}

// Drag and drop simulation
const dropZone = document.getElementById('uploadZone');
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
  dropZone.addEventListener(eventName, preventDefaults, false);
});
function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}
['dragenter', 'dragover'].forEach(eventName => {
  dropZone.addEventListener(eventName, () => dropZone.style.borderColor = 'var(--accent)', false);
});
['dragleave', 'drop'].forEach(eventName => {
  dropZone.addEventListener(eventName, () => dropZone.style.borderColor = 'var(--border-color)', false);
});
dropZone.addEventListener('drop', (e) => {
  let dt = e.dataTransfer;
  let files = dt.files;
  if(files.length > 0) simulateUpload();
}, false);


// --- AGENT VIEW LOGIC ---
function nextImage() {
  // Simulate loading next image instantly
  const img = document.querySelector('.image-viewer img');
  img.style.opacity = '0.5';
  setTimeout(() => {
    img.style.opacity = '1';
    // In a real app, src would change here.
  }, 150);
}

// Keyboard shortcuts for Agent
document.addEventListener('keydown', (e) => {
  if (document.getElementById('view-agent').classList.contains('active')) {
    if (e.key.toLowerCase() === 'p') {
      nextImage(); // Pleine
    } else if (e.key.toLowerCase() === 'v') {
      nextImage(); // Vide
    } else if (e.key === 'ArrowRight') {
      nextImage(); // Skip
    }
  }
});


// --- DASHBOARD VIEW LOGIC ---

// 1. Chart.js Setup
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = 'Inter';

const ctx = document.getElementById('trendChart').getContext('2d');
const gradient = ctx.createLinearGradient(0, 0, 0, 400);
gradient.addColorStop(0, 'rgba(16, 185, 129, 0.5)'); // Accent color
gradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
    datasets: [{
      label: 'Signalements Pleines',
      data: [12, 19, 15, 25, 42, 58, 30],
      borderColor: '#10b981',
      backgroundColor: gradient,
      borderWidth: 3,
      tension: 0.4,
      fill: true,
      pointBackgroundColor: '#10b981',
      pointBorderColor: '#fff',
      pointHoverRadius: 6
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false }
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(255, 255, 255, 0.05)' }
      },
      x: {
        grid: { display: false }
      }
    }
  }
});

// 2. Leaflet.js Setup
// Initialize map centered on Paris
let map = L.map('map', {
  center: [48.8566, 2.3522],
  zoom: 13,
  zoomControl: false // Customizing UI
});

L.control.zoom({ position: 'bottomright' }).addTo(map);

// Dark Theme Map Tiles (CartoDB Dark Matter)
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
  subdomains: 'abcd',
  maxZoom: 20
}).addTo(map);

// Simulate Heatmap Data (Level 3 specific feature)
// Coordinates around Paris
const heatData = [
  [48.86, 2.35, 0.8], // [lat, lng, intensity]
  [48.861, 2.352, 0.9],
  [48.858, 2.349, 0.7],
  [48.859, 2.355, 1.0],
  [48.865, 2.36, 0.6],
  [48.864, 2.362, 0.8],
  [48.87, 2.34, 0.9],
  [48.872, 2.341, 0.5]
];

// Add Heatmap Layer
const heatLayer = L.heatLayer(heatData, {
  radius: 25,
  blur: 15,
  maxZoom: 14,
  gradient: {
    0.4: 'blue',
    0.6: 'cyan',
    0.7: 'lime',
    0.8: 'yellow',
    1.0: 'red'
  }
}).addTo(map);

// Simulate Live Data (WebSocket simulation)
setInterval(() => {
  if (document.getElementById('view-dashboard').classList.contains('active')) {
    // Add a random point near center
    const lat = 48.85 + (Math.random() * 0.04 - 0.02);
    const lng = 2.35 + (Math.random() * 0.04 - 0.02);
    heatLayer.addLatLng([lat, lng, 0.5]);
    
    // Update KPI with animation
    const kpi = document.getElementById('kpi-signalements');
    let val = parseInt(kpi.innerText.replace(',', ''));
    val++;
    kpi.innerText = val.toLocaleString();
    kpi.style.transform = 'scale(1.1)';
    kpi.style.color = '#fff';
    setTimeout(() => {
      kpi.style.transform = 'scale(1)';
      kpi.style.color = 'var(--accent)';
    }, 300);
  }
}, 5000);

// Layer Toggles
document.getElementById('layer-heatmap').addEventListener('change', (e) => {
  if(e.target.checked) map.addLayer(heatLayer);
  else map.removeLayer(heatLayer);
});
