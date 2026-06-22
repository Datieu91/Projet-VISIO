let reportCount = parseInt(localStorage.getItem('wdp_report_count')) || 0;
let imageLocation = null;

function updateGamification() {
  const badgeEl = document.getElementById('gamification-text');
  if (reportCount === 1) {
    badgeEl.innerHTML = "⭐ C'est votre 1er signalement !";
  } else if (reportCount === 5) {
    badgeEl.innerHTML = "🏆 5 signalements ! Vous êtes une Sentinelle.";
  } else {
    badgeEl.innerHTML = `⭐ Merci pour votre ${reportCount}ème signalement !`;
  }
}

function switchState(stateId) {
  document.querySelectorAll('.state').forEach(el => {
    el.classList.remove('active');
    el.classList.add('d-none');
  });
  const target = document.getElementById(`state-${stateId}`);
  target.classList.remove('d-none');
  target.classList.add('active');
}

function resetApp() {
  document.getElementById('camera-input').value = '';
  document.getElementById('image-preview').src = '';
  document.getElementById('btn-submit').disabled = true;
  document.getElementById('location-value').innerText = 'Recherche...';
  document.querySelectorAll('.chip').forEach(c => {
    c.classList.remove('bg-success');
    c.classList.remove('text-white');
  });
  switchState('initial');
}

const cameraInput = document.getElementById('camera-input');
const canvas = document.getElementById('compression-canvas');
const ctx = canvas.getContext('2d');
let compressedImageBlob = null;
let originalFileSize = 0;

cameraInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  originalFileSize = file.size;
  switchState('processing');
  fetchLocation();

  const reader = new FileReader();
  reader.onload = (event) => {
    const img = new Image();
    img.onload = () => {
      const MAX_WIDTH = 1080;
      const MAX_HEIGHT = 1080;
      let width = img.width;
      let height = img.height;

      if (width > height) {
        if (width > MAX_WIDTH) { height *= MAX_WIDTH / width; width = MAX_WIDTH; }
      } else {
        if (height > MAX_HEIGHT) { width *= MAX_HEIGHT / height; height = MAX_HEIGHT; }
      }

      canvas.width = width;
      canvas.height = height;
      ctx.drawImage(img, 0, 0, width, height);
      
      canvas.toBlob((blob) => {
        compressedImageBlob = blob;
        
        const originalMB = originalFileSize / (1024 * 1024);
        const optimizedMB = blob.size / (1024 * 1024);
        const savedMB = (originalMB - optimizedMB).toFixed(1);
        
        if (savedMB > 0) {
          document.getElementById('subtle-eco-text').innerText = `✨ Image compressée (-${savedMB} Mo) • Démarche éco-responsable`;
        }

        document.getElementById('image-preview').src = URL.createObjectURL(blob);
        
        setTimeout(() => {
          switchState('preview');
          document.getElementById('btn-submit').disabled = false;
        }, 800);
      }, 'image/jpeg', 0.8); 
    };
    img.src = event.target.result;
  };
  reader.readAsDataURL(file);
});

function fetchLocation() {
  const locEl = document.getElementById('location-value');
  if (!navigator.geolocation) {
    locEl.innerText = "Non supporté";
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (position) => {
      imageLocation = { lat: position.coords.latitude, lng: position.coords.longitude };
      locEl.innerText = `${imageLocation.lat.toFixed(4)}, ${imageLocation.lng.toFixed(4)}`;
    },
    (error) => {
      locEl.innerText = "Position introuvable";
      locEl.classList.replace('text-success', 'text-danger');
    },
    { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
  );
}

async function submitReport() {
  switchState('processing');
  document.getElementById('loading-text').innerText = "Envoi au serveur...";

  const selectedTags = Array.from(document.querySelectorAll('.chip.bg-success')).map(el => el.innerText).join(', ');

  const formData = new FormData();
  formData.append('image', compressedImageBlob, 'capture.jpg');
  if (imageLocation) {
    formData.append('lat', imageLocation.lat);
    formData.append('lng', imageLocation.lng);
  }
  formData.append('tags', selectedTags);

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });

    if (response.ok) {
      reportCount++;
      localStorage.setItem('wdp_report_count', reportCount);
      updateGamification();
      switchState('success');
    } else {
      alert("Erreur lors de l'envoi.");
      resetApp();
    }
  } catch (err) {
    console.error(err);
    alert("Erreur réseau.");
    resetApp();
  }
}
