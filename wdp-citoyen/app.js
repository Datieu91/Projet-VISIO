// --- State Management ---
function switchState(stateId) {
  document.querySelectorAll('.state').forEach(el => el.classList.remove('active'));
  document.getElementById(`state-${stateId}`).classList.add('active');
}

function resetApp() {
  document.getElementById('camera-input').value = '';
  document.getElementById('image-preview').src = '';
  document.getElementById('btn-submit').disabled = true;
  document.getElementById('location-value').innerText = 'Recherche GPS...';
  switchState('initial');
}

// --- DOM Elements ---
const cameraInput = document.getElementById('camera-input');
const canvas = document.getElementById('compression-canvas');
const ctx = canvas.getContext('2d');
let compressedImageBlob = null;
let imageLocation = null;

// --- 1. Camera Input & Image Processing ---
cameraInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  // Show processing state
  switchState('processing');
  document.getElementById('loading-text').innerText = "Analyse de l'image...";
  document.getElementById('sub-loading-text').innerText = "Optimisation Green IT en cours";

  // Display original size
  const originalSizeMB = (file.size / (1024 * 1024)).toFixed(2);
  document.getElementById('size-original').innerText = `${originalSizeMB} Mo`;

  // Start Geolocation in parallel
  fetchLocation();

  // Read and compress image
  const reader = new FileReader();
  reader.onload = (event) => {
    const img = new Image();
    img.onload = () => {
      // Set target dimensions (e.g., max 1080p for Green IT)
      const MAX_WIDTH = 1080;
      const MAX_HEIGHT = 1080;
      let width = img.width;
      let height = img.height;

      if (width > height) {
        if (width > MAX_WIDTH) {
          height *= MAX_WIDTH / width;
          width = MAX_WIDTH;
        }
      } else {
        if (height > MAX_HEIGHT) {
          width *= MAX_HEIGHT / height;
          height = MAX_HEIGHT;
        }
      }

      canvas.width = width;
      canvas.height = height;

      // Draw and compress (WebP format is more efficient)
      ctx.drawImage(img, 0, 0, width, height);
      
      canvas.toBlob((blob) => {
        compressedImageBlob = blob;
        
        // Calculate new size
        const optimizedSizeKB = (blob.size / 1024).toFixed(0);
        document.getElementById('size-optimized').innerText = `${optimizedSizeKB} Ko`;
        
        // Show preview
        document.getElementById('image-preview').src = URL.createObjectURL(blob);
        
        // Move to preview state
        setTimeout(() => {
          switchState('preview');
          document.getElementById('btn-submit').disabled = false;
        }, 1000); // Artificial delay to show the loader (UX)

      }, 'image/webp', 0.7); // 70% quality WebP
    };
    img.src = event.target.result;
  };
  reader.readAsDataURL(file);
});

// --- 2. HTML5 Geolocation ---
function fetchLocation() {
  const locEl = document.getElementById('location-value');
  
  if (!navigator.geolocation) {
    locEl.innerText = "GPS non supporté";
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude.toFixed(4);
      const lng = position.coords.longitude.toFixed(4);
      imageLocation = { lat, lng };
      locEl.innerText = `${lat}, ${lng} (Précision: ${Math.round(position.coords.accuracy)}m)`;
      locEl.style.color = "var(--accent-color)";
    },
    (error) => {
      console.warn("Erreur GPS:", error.message);
      locEl.innerText = "Position introuvable";
      locEl.style.color = "var(--error-color)";
    },
    { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
  );
}

// --- 3. Submission Simulation ---
function submitReport() {
  switchState('processing');
  document.getElementById('loading-text').innerText = "Envoi du signalement...";
  document.getElementById('sub-loading-text').innerText = "Connexion sécurisée...";

  // Simulate network request
  setTimeout(() => {
    // Calculate CO2 saved (arbitrary conversion for gamification: 1MB saved = 1.5g CO2)
    const originalSize = parseFloat(document.getElementById('size-original').innerText);
    const optimizedSize = parseFloat(document.getElementById('size-optimized').innerText) / 1024; // to MB
    const savedMB = originalSize - optimizedSize;
    const co2Saved = (savedMB * 1.5).toFixed(1);
    
    document.getElementById('co2-saved').innerText = `${co2Saved} g`;
    switchState('success');
  }, 1500);
}
