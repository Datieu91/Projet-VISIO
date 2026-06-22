// --- State & Metrics ---
let imagesProcessed = 0;
let startTime = Date.now();
const TARGET_QUOTA = 500;

// Fake database of images for the demo
const demoImages = [
  { src: "assets/trash_sample.png", pred: "Pleine", conf: 92, tags: "⚠️ Dangereux" },
  { src: "assets/trash_sample.png", pred: "Vide", conf: 88, tags: "Aucun" },
  { src: "assets/trash_sample.png", pred: "Pleine", conf: 99, tags: "🪑 Encombrants" },
];
let currentImageIndex = 0;

// --- DOM Elements ---
const targetImage = document.getElementById('target-image');
const sessionCountEl = document.getElementById('session-count');
const avgTimeEl = document.getElementById('avg-time');
const metaOverlay = document.getElementById('meta-overlay');
const aiBadge = document.getElementById('ai-badge');

// Button visual references
const btnLeft = document.getElementById('btn-left');
const btnSpace = document.getElementById('btn-space');
const btnRight = document.getElementById('btn-right');

// --- Initialization ---
function init() {
  updateDashboard();
  loadCurrentImage();
}

function updateDashboard() {
  sessionCountEl.innerText = `${imagesProcessed} / ${TARGET_QUOTA}`;
  
  if (imagesProcessed > 0) {
    const elapsedSeconds = (Date.now() - startTime) / 1000;
    const avg = (elapsedSeconds / imagesProcessed).toFixed(1);
    avgTimeEl.innerText = `${avg} s`;
    // Green if under 2 seconds
    avgTimeEl.style.color = avg < 2.0 ? 'var(--accent-color)' : 'var(--text-primary)';
  }
}

function loadCurrentImage() {
  // In a real app, this would load the pre-fetched image blob
  const imgData = demoImages[currentImageIndex % demoImages.length];
  
  // Update AI Badge
  document.querySelector('.ai-text').innerText = `Prédiction : ${imgData.pred}`;
  document.querySelector('.ai-confidence').innerText = `${imgData.conf}% Confiance`;
  document.querySelector('.ai-confidence').style.color = imgData.pred === 'Pleine' ? 'var(--accent-danger)' : 'var(--accent-color)';
  
  // Update Metadata overlay
  document.querySelector('.meta-val:last-child').innerHTML = imgData.tags !== "Aucun" 
    ? `<span style="background: rgba(239, 68, 68, 0.2); color: #ef4444; padding: 0.2rem 0.5rem; border-radius: 4px;">${imgData.tags}</span>`
    : '<span style="color: var(--text-secondary);">Aucun tag</span>';

  // Pre-load next image invisibly (Simulation)
  const nextImg = new Image();
  nextImg.src = demoImages[(currentImageIndex + 1) % demoImages.length].src;
}

// --- Action Logic (The "Swipe") ---
function processAction(action, btnElement, animationClass) {
  // Visual feedback on the button
  btnElement.classList.add('active');
  
  // Animate the image out
  targetImage.classList.add(animationClass);

  setTimeout(() => {
    // Cleanup
    btnElement.classList.remove('active');
    targetImage.classList.remove(animationClass);
    
    // Logic
    imagesProcessed++;
    currentImageIndex++;
    updateDashboard();
    loadCurrentImage();

  }, 300); // Wait for CSS animation to finish
}

// --- Event Listeners ---

// Keyboard Shortcuts
document.addEventListener('keydown', (e) => {
  // Prevent repeated triggers on hold
  if (e.repeat) return;

  switch(e.code) {
    case 'ArrowLeft':
      processAction('Vide', btnLeft, 'swipe-left');
      break;
    case 'ArrowRight':
      processAction('Pleine', btnRight, 'swipe-right');
      break;
    case 'Space':
      processAction('Skip', btnSpace, 'swipe-up');
      break;
    case 'ShiftLeft':
    case 'ShiftRight':
      metaOverlay.classList.add('visible');
      targetImage.style.filter = 'blur(5px) brightness(0.5)';
      aiBadge.style.opacity = '0';
      break;
  }
});

document.addEventListener('keyup', (e) => {
  if (e.code === 'ShiftLeft' || e.code === 'ShiftRight') {
    metaOverlay.classList.remove('visible');
    targetImage.style.filter = 'none';
    aiBadge.style.opacity = '1';
  }
});

// Click fallbacks
btnLeft.addEventListener('click', () => processAction('Vide', btnLeft, 'swipe-left'));
btnRight.addEventListener('click', () => processAction('Pleine', btnRight, 'swipe-right'));
btnSpace.addEventListener('click', () => processAction('Skip', btnSpace, 'swipe-up'));

init();
