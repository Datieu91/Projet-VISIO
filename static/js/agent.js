// --- State & Navigation ---
let imagesProcessed = 0;
let startTime = Date.now();
let pendingImages = [];
let currentImageIndex = 0;
let chartInstance = null;

// --- DOM Elements ---
const targetImage = document.getElementById('target-image');
const pendingCountEl = document.getElementById('pending-count');
const avgTimeEl = document.getElementById('avg-time');
const btnLeft = document.getElementById('btn-left');
const btnSpace = document.getElementById('btn-space');
const btnRight = document.getElementById('btn-right');

// Navigation
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    // Update active class
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    
    // Switch view
    const targetId = link.getAttribute('data-target');
    document.querySelectorAll('.view-section').forEach(v => {
      v.classList.remove('active', 'd-flex');
      v.classList.add('d-none');
    });
    
    const targetView = document.getElementById(targetId);
    targetView.classList.remove('d-none');
    // Moderation is flex row, Dashboard is flex column
    targetView.classList.add(targetId === 'view-moderation' ? 'd-flex' : 'd-flex');

    // Update Title
    document.getElementById('current-view-title').innerText = link.innerText.trim();

    // Render chart if dashboard
    if (targetId === 'view-dashboard') {
      initChart();
    }
  });
});

// --- API & Logic ---

async function fetchPendingImages() {
  try {
    const response = await fetch('/api/images/pending');
    pendingImages = await response.json();
    updateDashboardStats();
    
    if (pendingImages.length > 0) {
      loadCurrentImage();
    } else {
      showEmptyState();
    }
  } catch (e) {
    console.error("Erreur chargement images", e);
  }
}

function updateDashboardStats() {
  pendingCountEl.innerText = pendingImages.length - currentImageIndex;
  
  if (imagesProcessed > 0) {
    const elapsedSeconds = (Date.now() - startTime) / 1000;
    const avg = (elapsedSeconds / imagesProcessed).toFixed(1);
    avgTimeEl.innerText = `${avg} s`;
    avgTimeEl.classList.toggle('text-success', avg < 2.0);
  }
}

function showEmptyState() {
  targetImage.src = '';
  targetImage.alt = 'Aucune image en attente';
  document.getElementById('pred-text').innerText = `Terminé`;
  document.getElementById('pred-conf').innerText = `-`;
  document.getElementById('meta-id').innerText = `#--`;
  document.getElementById('meta-gps').innerText = `--`;
  document.getElementById('meta-size').innerText = `-- Ko`;
  document.getElementById('meta-color-text').innerHTML = `-- <div id="meta-color-box" class="border rounded" style="width: 20px; height: 20px; background: transparent;"></div>`;
  document.getElementById('meta-tags').innerHTML = '<span class="text-secondary small">Aucun signalement en attente</span>';
}

function loadCurrentImage() {
  if (currentImageIndex >= pendingImages.length) {
    fetchPendingImages(); // Refresh if empty
    return;
  }

  const imgData = pendingImages[currentImageIndex];
  
  // Set Image
  targetImage.src = imgData.filepath;
  
  // Update Badge
  const pred = imgData.ai_prediction || 'Inconnu';
  document.getElementById('pred-text').innerText = `Prédiction : ${pred}`;
  const confBadge = document.getElementById('pred-conf');
  confBadge.innerText = `${imgData.ai_confidence || 0}%`;
  confBadge.className = `badge rounded-pill ai-confidence ${pred === 'Pleine' ? 'text-bg-danger' : 'text-bg-success'}`;
  
  // Update Fixed Right Panel Metadata
  document.getElementById('meta-id').innerText = `#WDP-${imgData.id}`;
  document.getElementById('meta-gps').innerText = imgData.lat ? `${imgData.lat}, ${imgData.lng}` : 'Inconnu';
  document.getElementById('meta-size').innerText = `${imgData.file_size_kb || 0} Ko`;
  
  const color = imgData.avg_color_hex || '#000000';
  document.getElementById('meta-color-text').innerHTML = `${color} <div id="meta-color-box" class="border rounded" style="width: 20px; height: 20px; background: ${color};"></div>`;
  
  const tags = imgData.citizen_tags;
  document.getElementById('meta-tags').innerHTML = tags 
    ? `<span class="badge text-bg-danger bg-opacity-25 border border-danger text-danger fs-6 px-3 py-2">${tags}</span>`
    : '<span class="text-secondary small">Aucun tag</span>';

  // Preload next image
  if (currentImageIndex + 1 < pendingImages.length) {
    const nextImg = new Image();
    nextImg.src = pendingImages[currentImageIndex + 1].filepath;
  }
}

async function sendAnnotation(id, annotation) {
  try {
    await fetch(`/api/images/${id}/annotate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ annotation })
    });
  } catch (e) {
    console.error("Erreur annotation", e);
  }
}

function processAction(action, btnElement, animationClass) {
  if (currentImageIndex >= pendingImages.length) return;

  btnElement.classList.add('active');
  targetImage.classList.add(animationClass);

  const imgData = pendingImages[currentImageIndex];
  sendAnnotation(imgData.id, action);

  setTimeout(() => {
    btnElement.classList.remove('active');
    targetImage.classList.remove(animationClass);
    
    imagesProcessed++;
    currentImageIndex++;
    updateDashboardStats();
    loadCurrentImage();
  }, 300);
}

// --- Event Listeners ---

document.addEventListener('keydown', (e) => {
  if (e.repeat) return;
  // Only trigger if we are on the moderation view
  if (!document.getElementById('view-moderation').classList.contains('active')) return;

  switch(e.code) {
    case 'ArrowLeft': processAction('Vide', btnLeft, 'swipe-left'); break;
    case 'ArrowRight': processAction('Pleine', btnRight, 'swipe-right'); break;
    case 'Space': processAction('Skip', btnSpace, 'swipe-up'); break;
  }
});

btnLeft.addEventListener('click', () => processAction('Vide', btnLeft, 'swipe-left'));
btnRight.addEventListener('click', () => processAction('Pleine', btnRight, 'swipe-right'));
btnSpace.addEventListener('click', () => processAction('Skip', btnSpace, 'swipe-up'));

// --- Dashboard Chart (Mock Data) ---
function initChart() {
  const ctx = document.getElementById('trendChart').getContext('2d');
  
  if (chartInstance) {
    chartInstance.destroy();
  }

  const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
  const textColor = isDark ? '#94a3b8' : '#64748b';
  const gridColor = isDark ? '#1e293b' : '#e2e8f0';

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
      datasets: [
        {
          label: 'Poubelles Pleines',
          data: [65, 59, 80, 81, 56, 120, 140],
          borderColor: '#dc3545',
          backgroundColor: 'rgba(220, 53, 69, 0.1)',
          fill: true,
          tension: 0.4
        },
        {
          label: 'Poubelles Vides/Ok',
          data: [28, 48, 40, 19, 86, 27, 40],
          borderColor: '#198754',
          backgroundColor: 'rgba(25, 135, 84, 0.1)',
          fill: true,
          tension: 0.4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: textColor } }
      },
      scales: {
        y: { grid: { color: gridColor }, ticks: { color: textColor } },
        x: { grid: { color: gridColor }, ticks: { color: textColor } }
      }
    }
  });
}

// Init
fetchPendingImages();
