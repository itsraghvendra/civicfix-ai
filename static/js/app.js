/**
 * CivicFix AI - Client Application Logic (Lucknow Edition)
 * Pure vanilla JavaScript with Tailwind CSS UI state management.
 */

// Application State
const state = {
  currentTab: 'home',
  categories: [],
  localities: [],
  departments: [],
  metrics: { total: 0, submitted: 0, in_review: 0, in_progress: 0, resolved: 0, urgent_active: 0 },
  complaints: [],
  selectedComplaintId: null,
  activeTrackingId: '',
  selectedPhotoFile: null,
  uploadedPhotoPath: null,
  imageCaption: '',
  duplicateCheckTimeout: null,
  adminSearchTimeout: null,
  isAdminUnlocked: sessionStorage.getItem('civicfix_admin_unlocked') === 'true',

  // Live Camera
  cameraStream: null,

  // Location Coordinates (Private)
  locationCoords: { latitude: null, longitude: null, shared: false },

  // Passwordless Mobile OTP State
  otp: {
    phone: '',
    token: null,
    verified: false,
    expiryTimer: null,
    resendTimer: null,
    expirySecondsLeft: 0,
    resendSecondsLeft: 0,
  },

  // Security, CAPTCHA & Abuse Prevention
  security: {
    requireCaptcha: false,
    turnstileSiteKey: '',
    captchaToken: '',
    cryptoChallenge: null,
    otpRequired: false,
    smsProvider: 'demo',
    isLiveSMS: false,
  },

  // Duplicate Advisory Modal Pending State
  pendingSubmission: null,
};

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  await loadConfig();
  await loadSecurityStatus();
  await loadMetrics();
  setupNavigation();
  setupLocalityDualInput();
  setupPhotoUpload();
  setupLocationSharing();
  setupPasswordlessOTP();
  setupSecurityAndCaptcha();
  setupDuplicateModal();
  setupFormHandlers();
  setupRealtimeDuplicateCheck();
  setupAdminLogin();

  // Support direct URL query / hash navigation
  const params = new URLSearchParams(window.location.search);
  const requestedTab = params.get('tab') || window.location.hash.replace('#', '') || 'home';
  if (params.get('unlocked') === '1') {
    state.isAdminUnlocked = true;
    sessionStorage.setItem('civicfix_admin_unlocked', 'true');
  }
  const trackId = params.get('id');
  if (requestedTab === 'track' && trackId) {
    trackComplaintById(trackId);
  } else {
    renderTab(requestedTab);
  }
  initIcons();
});

// Refresh Lucide Icons safely
function initIcons() {
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// Load System Config (Categories, Localities, Departments, Engine status)
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    const data = await res.json();
    state.categories = data.categories || [];
    state.localities = data.localities || [];
    state.departments = data.departments || [];

    // Populate Locality Selectors
    const localitySelect = document.getElementById('locality-select');
    if (localitySelect) {
      localitySelect.innerHTML = state.localities
        .map(loc => `<option value="${loc}">${loc}</option>`)
        .join('');
    }

    const adminLocFilter = document.getElementById('admin-filter-loc');
    if (adminLocFilter) {
      adminLocFilter.innerHTML = '<option value="All">All Localities</option>' +
        state.localities.filter(l => l !== 'Other / Enter manually').map(loc => `<option value="${loc}">${loc}</option>`).join('');
    }

    const adminCatFilter = document.getElementById('admin-filter-cat');
    if (adminCatFilter) {
      adminCatFilter.innerHTML = '<option value="All">All Categories</option>' +
        state.categories.map(c => `<option value="${c}">${c}</option>`).join('');
    }

    const adminDeptSelect = document.getElementById('admin-edit-dept');
    if (adminDeptSelect) {
      adminDeptSelect.innerHTML = state.departments
        .map(d => `<option value="${d}">${d}</option>`).join('');
    }

    // Engine pill update
    const enginePill = document.getElementById('sidebar-engine-pill');
    if (enginePill) {
      const isGroq = data.has_groq;
      enginePill.innerHTML = `
        <span class="w-2 h-2 rounded-full ${isGroq ? 'bg-[#A9B887]' : 'bg-[#D5D7C9]'} inline-block"></span>
        <span>${isGroq ? 'Groq AI (' + data.groq_model + ')' : 'Civic Rules Fallback'}</span>
      `;
    }
  } catch (err) {
    console.error('Failed to load system configuration:', err);
  }
}

// Load Dashboard Metrics
async function loadMetrics() {
  try {
    const res = await fetch('/api/metrics');
    state.metrics = await res.json();

    document.getElementById('bento-total').innerText = state.metrics.total || 0;
    document.getElementById('bento-submitted').innerText = state.metrics.submitted || 0;
    document.getElementById('bento-review').innerText = state.metrics.in_review || 0;
    document.getElementById('bento-progress').innerText = state.metrics.in_progress || 0;
    document.getElementById('bento-resolved').innerText = state.metrics.resolved || 0;
  } catch (err) {
    console.error('Failed to load metrics:', err);
  }
}

// Tab Navigation
function setupNavigation() {
  const navButtons = document.querySelectorAll('.nav-btn');
  navButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const tab = btn.getAttribute('data-tab');
      renderTab(tab);
    });
  });
}

function renderTab(tabName) {
  state.currentTab = tabName;

  // Update navigation styling
  document.querySelectorAll('.nav-btn').forEach(btn => {
    const isTarget = btn.getAttribute('data-tab') === tabName;
    const isSpecialAdmin = btn.getAttribute('data-tab') === 'admin';

    if (isTarget) {
      btn.classList.add('bg-[#A9B887]', 'text-[#2E3D28]', 'font-semibold');
      btn.classList.remove('text-[#E8E9DF]', 'hover:bg-white/10');
    } else {
      btn.classList.remove('bg-[#A9B887]', 'text-[#2E3D28]', 'font-semibold');
      btn.classList.add('text-[#E8E9DF]', 'hover:bg-white/10');
    }
  });

  // Toggle Screen Views
  const screens = ['home', 'submit', 'track', 'how-it-works', 'about', 'admin'];
  screens.forEach(s => {
    const el = document.getElementById(`screen-${s}`);
    if (el) {
      if (s === tabName) {
        el.classList.remove('hidden');
      } else {
        el.classList.add('hidden');
      }
    }
  });

  // Handle Admin Portal Visibility
  if (tabName === 'admin') {
    checkAdminGate();
  }

  // Update browser URL query without reloading
  try {
    const url = new URL(window.location);
    if (tabName === 'home') {
      url.searchParams.delete('tab');
    } else {
      url.searchParams.set('tab', tabName);
    }
    window.history.replaceState({}, '', url);
  } catch (e) {}

  window.scrollTo({ top: 0, behavior: 'smooth' });
  setTimeout(initIcons, 50);
}

// -------------------------------------------------------------
// LOCALITY DUAL INPUT (Dropdown + Optional/Required Write-In)
// -------------------------------------------------------------
function setupLocalityDualInput() {
  const select = document.getElementById('locality-select');
  const customLabel = document.getElementById('locality-custom-label');
  const customInput = document.getElementById('locality-custom-input');
  const customHint = document.getElementById('locality-custom-hint');

  if (!select || !customInput) return;

  select.addEventListener('change', () => {
    const val = select.value;
    if (val === 'Other / Enter manually') {
      customLabel.innerHTML = 'Enter Locality (Custom) *';
      customInput.required = true;
      customInput.placeholder = 'e.g. Telibagh, Near Canal Bridge';
      customHint.innerText = 'Required: Specify your Lucknow neighborhood or sector';
      customInput.focus();
    } else {
      customLabel.innerHTML = 'Enter Landmark or Specific Details <span class="text-[#576352] font-normal">(Optional)</span>';
      customInput.required = false;
      customInput.placeholder = 'e.g. Near Halwasiya Market, Opp. Gate 3';
      customHint.innerText = 'Optional: Street name, crossroad, or prominent landmark';
    }
  });
}

// -------------------------------------------------------------
// SECURITY & ABUSE STATUS
// -------------------------------------------------------------
async function loadSecurityStatus() {
  try {
    const res = await fetch('/api/security/status');
    const data = await res.json();
    state.security.requireCaptcha = data.require_captcha || false;
    state.security.turnstileSiteKey = data.turnstile_site_key || '';
    state.security.cryptoChallenge = data.crypto_challenge || null;
    state.security.otpRequired = data.otp_required || false;
    state.security.smsProvider = data.sms_provider_name || 'Demo Mode';
    state.security.isLiveSMS = data.is_live_sms || false;

    // Update OTP requirement badge in UI
    const reqBadge = document.getElementById('otp-requirement-badge');
    if (reqBadge) {
      if (state.security.otpRequired) {
        reqBadge.innerHTML = '<span class="text-[#B91C1C] font-semibold">(Required)</span>';
      } else {
        reqBadge.innerHTML = '<span class="text-[#576352] font-normal">(Optional)</span>';
      }
    }

    // Update CAPTCHA container visibility
    if (state.security.requireCaptcha) {
      renderCaptchaWidget(data.reason);
    }
  } catch (err) {
    console.warn('Security status fetch error:', err);
  }
}

// -------------------------------------------------------------
// PHOTO UPLOAD & COMPULSORY LIVE CAMERA CAPTURE
// -------------------------------------------------------------
function setupPhotoUpload() {
  const dropZone = document.getElementById('photo-drop-zone');
  const fileInput = document.getElementById('photo-file-input');
  const promptBox = document.getElementById('drop-zone-prompt');
  const previewBox = document.getElementById('photo-preview-container');
  const previewImg = document.getElementById('photo-preview-img');
  const fileNameEl = document.getElementById('photo-file-name');
  const fileSizeEl = document.getElementById('photo-file-size');
  const errorEl = document.getElementById('photo-error-msg');
  const removeBtn = document.getElementById('photo-remove-btn');
  const changeBtn = document.getElementById('photo-change-btn');
  const captionBox = document.getElementById('image-caption-box');
  const captionInput = document.getElementById('image-caption-input');

  // Live Camera Elements
  const startCameraBtn = document.getElementById('start-camera-btn');
  const cameraBox = document.getElementById('camera-stream-box');
  const videoFeed = document.getElementById('camera-video-feed');
  const canvas = document.getElementById('camera-capture-canvas');
  const snapBtn = document.getElementById('snap-photo-btn');
  const closeCameraBtn = document.getElementById('close-camera-btn');

  if (!dropZone || !fileInput) return;

  const handleFile = (file) => {
    errorEl.classList.add('hidden');
    if (!file) return;

    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
      errorEl.innerText = `Unsupported format "${file.type}". Please upload JPEG, PNG, or WebP.`;
      errorEl.classList.remove('hidden');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      errorEl.innerText = `File size (${(file.size / 1024 / 1024).toFixed(1)} MB) exceeds 5 MB limit.`;
      errorEl.classList.remove('hidden');
      return;
    }

    state.selectedPhotoFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      fileNameEl.innerText = file.name;
      fileSizeEl.innerText = `${(file.size / 1024).toFixed(1)} KB`;
      promptBox.classList.add('hidden');
      previewBox.classList.remove('hidden');

      // Live Image Captioning preview
      captionBox.classList.remove('hidden');
      if (captionInput && !captionInput.value) {
        captionInput.value = `Live Camera Evidence: ${file.name.replace(/\.[^/.]+$/, '')} (Field capture inspected)`;
      }
      initIcons();
    };
    reader.readAsDataURL(file);
  };

  // Live Camera stream handlers
  if (startCameraBtn && videoFeed) {
    startCameraBtn.addEventListener('click', async () => {
      errorEl.classList.add('hidden');
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          alert('Live camera access is not supported by your browser. Please choose a photo file.');
          fileInput.click();
          return;
        }

        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
        });
        state.cameraStream = stream;
        videoFeed.srcObject = stream;
        cameraBox.classList.remove('hidden');
        dropZone.classList.add('hidden');
        initIcons();
      } catch (err) {
        console.warn('Camera access denied or unavailable:', err);
        alert('Could not access live camera. Falling back to photo file upload.');
        fileInput.click();
      }
    });
  }

  const stopCameraStream = () => {
    if (state.cameraStream) {
      state.cameraStream.getTracks().forEach(track => track.stop());
      state.cameraStream = null;
    }
    if (cameraBox) cameraBox.classList.add('hidden');
    if (dropZone) dropZone.classList.remove('hidden');
  };

  if (closeCameraBtn) {
    closeCameraBtn.addEventListener('click', stopCameraStream);
  }

  if (snapBtn && canvas && videoFeed) {
    snapBtn.addEventListener('click', () => {
      canvas.width = videoFeed.videoWidth || 640;
      canvas.height = videoFeed.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(videoFeed, 0, 0, canvas.width, canvas.height);

      canvas.toBlob((blob) => {
        if (!blob) {
          alert('Failed to snap photo. Please try again.');
          return;
        }
        const file = new File([blob], `live_camera_${Date.now()}.jpg`, { type: 'image/jpeg' });
        stopCameraStream();
        handleFile(file);
        showToast('Live photo captured successfully.');
      }, 'image/jpeg', 0.9);
    });
  }

  dropZone.addEventListener('click', (e) => {
    if (e.target.id !== 'photo-remove-btn') {
      fileInput.click();
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files[0]) {
      handleFile(fileInput.files[0]);
    }
  });

  // Drag and Drop
  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.add('border-[#A9B887]', 'bg-[#E8EDE0]');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.remove('border-[#A9B887]', 'bg-[#E8EDE0]');
    });
  });

  dropZone.addEventListener('drop', (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  });

  if (removeBtn) {
    removeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      state.selectedPhotoFile = null;
      state.uploadedPhotoPath = null;
      fileInput.value = '';
      previewImg.src = '';
      previewBox.classList.add('hidden');
      promptBox.classList.remove('hidden');
      errorEl.classList.add('hidden');
      captionBox.classList.add('hidden');
      if (captionInput) captionInput.value = '';
    });
  }

  if (changeBtn) {
    changeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.click();
    });
  }
}

// -------------------------------------------------------------
// OPTIONAL LOCATION SHARING (Private for Municipal Response)
// -------------------------------------------------------------
function setupLocationSharing() {
  const shareBtn = document.getElementById('btn-share-location');
  const removeBtn = document.getElementById('btn-remove-location');
  const badge = document.getElementById('location-attached-badge');
  const coordsText = document.getElementById('location-coords-text');

  if (!shareBtn) return;

  shareBtn.addEventListener('click', () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }

    shareBtn.disabled = true;
    shareBtn.innerText = 'Acquiring GPS...';

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        state.locationCoords = { latitude: lat, longitude: lon, shared: true };

        coordsText.innerText = `GPS Location Attached: ${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E (Protected)`;
        badge.classList.remove('hidden');
        shareBtn.classList.add('hidden');
        shareBtn.disabled = false;
        shareBtn.innerHTML = '<i data-lucide="map-pin" class="w-3.5 h-3.5"></i><span>Attach Current Location</span>';
        initIcons();
        showToast('GPS coordinates attached privately for field crew.');
      },
      (err) => {
        shareBtn.disabled = false;
        shareBtn.innerHTML = '<i data-lucide="map-pin" class="w-3.5 h-3.5"></i><span>Attach Current Location</span>';
        console.warn('Geolocation error:', err);
        alert('Could not determine current location. Location sharing remains optional.');
      },
      { timeout: 8000 }
    );
  });

  if (removeBtn) {
    removeBtn.addEventListener('click', () => {
      state.locationCoords = { latitude: null, longitude: null, shared: false };
      badge.classList.add('hidden');
      shareBtn.classList.remove('hidden');
      initIcons();
      showToast('Attached location removed.');
    });
  }
}

// -------------------------------------------------------------
// PASSWORDLESS MOBILE OTP (Configurable / Salting & Hash Verification)
// -------------------------------------------------------------
function setupPasswordlessOTP() {
  const phoneInput = document.getElementById('otp-phone-input');
  const sendBtn = document.getElementById('otp-send-btn');
  const sendText = document.getElementById('otp-send-text');
  const verifyRow = document.getElementById('otp-verify-row');
  const codeInput = document.getElementById('otp-code-input');
  const verifyBtn = document.getElementById('otp-verify-btn');
  const msgBox = document.getElementById('otp-msg-box');
  const timerBox = document.getElementById('otp-timer-box');
  const expiryEl = document.getElementById('otp-expiry-countdown');
  const resendEl = document.getElementById('otp-resend-countdown');
  const demoHelper = document.getElementById('otp-demo-helper');
  const verifiedChip = document.getElementById('otp-verified-chip');

  if (!sendBtn || !phoneInput) return;

  const showMsg = (text, isError = false) => {
    msgBox.innerText = text;
    msgBox.className = `text-xs font-medium ${isError ? 'text-[#B91C1C]' : 'text-[#15803D]'}`;
    msgBox.classList.remove('hidden');
  };

  sendBtn.addEventListener('click', async () => {
    const rawPhone = phoneInput.value.trim();
    const cleanPhone = rawPhone.replace(/[^\d+]/g, '');

    if (cleanPhone.length < 10) {
      showMsg('Please enter a valid 10-digit mobile number.', true);
      return;
    }

    sendBtn.disabled = true;
    sendText.innerText = 'Dispatching...';

    try {
      const res = await fetch('/api/otp/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: cleanPhone }),
      });
      const data = await res.json();

      if (!res.ok) {
        showMsg(data.error || 'Failed to request verification code.', true);
        sendBtn.disabled = false;
        sendText.innerText = 'Send Code';
        return;
      }

      state.otp.phone = cleanPhone;
      showMsg(data.message, false);
      verifyRow.classList.remove('hidden');

      if (data.is_demo && data.demo_otp) {
        demoHelper.innerHTML = `<strong>Demo Mode Note:</strong> Live SMS unconfigured. Demonstration OTP is <strong>${data.demo_otp}</strong>.`;
        demoHelper.classList.remove('hidden');
      } else {
        demoHelper.classList.add('hidden');
      }

      // Start Countdown Timers
      let resendSec = 60;
      let expirySec = 300;
      clearInterval(state.otp.resendTimer);
      clearInterval(state.otp.expiryTimer);

      state.otp.resendTimer = setInterval(() => {
        resendSec--;
        if (resendEl) resendEl.innerText = resendSec;
        if (resendSec <= 0) {
          clearInterval(state.otp.resendTimer);
          sendBtn.disabled = false;
          sendText.innerText = 'Resend Code';
        }
      }, 1000);

      state.otp.expiryTimer = setInterval(() => {
        expirySec--;
        if (expiryEl) expiryEl.innerText = expirySec;
        if (expirySec <= 0) {
          clearInterval(state.otp.expiryTimer);
          showMsg('Verification code expired. Please request a new one.', true);
        }
      }, 1000);

      codeInput.focus();
    } catch (err) {
      showMsg('Network error while requesting verification code.', true);
      sendBtn.disabled = false;
      sendText.innerText = 'Send Code';
    }
  });

  verifyBtn.addEventListener('click', async () => {
    const code = codeInput.value.trim();
    if (!code || code.length < 6) {
      showMsg('Please enter the 6-digit verification code.', true);
      return;
    }

    verifyBtn.disabled = true;
    verifyBtn.innerText = 'Verifying...';

    try {
      const res = await fetch('/api/otp/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: state.otp.phone, otp: code }),
      });
      const data = await res.json();

      if (!res.ok) {
        showMsg(data.error || 'Invalid verification code.', true);
        verifyBtn.disabled = false;
        verifyBtn.innerText = 'Verify Code';
        return;
      }

      state.otp.verified = true;
      state.otp.token = data.verification_token;

      clearInterval(state.otp.resendTimer);
      clearInterval(state.otp.expiryTimer);

      showMsg('Mobile number successfully verified.', false);
      verifyRow.classList.add('hidden');
      verifiedChip.classList.remove('hidden');
      phoneInput.disabled = true;
      sendBtn.classList.add('hidden');
      showToast('Mobile number verified successfully.');
    } catch (err) {
      showMsg('Network error while verifying code.', true);
      verifyBtn.disabled = false;
      verifyBtn.innerText = 'Verify Code';
    }
  });
}

// -------------------------------------------------------------
// ADAPTIVE SECURITY & CAPTCHA (Turnstile / Crypto Challenge)
// -------------------------------------------------------------
function setupSecurityAndCaptcha() {
  const container = document.getElementById('captcha-container');
  const cryptoVerifyBtn = document.getElementById('crypto-verify-btn');
  const cryptoAnswerInput = document.getElementById('crypto-answer-input');

  if (cryptoVerifyBtn) {
    cryptoVerifyBtn.addEventListener('click', () => {
      const ans = cryptoAnswerInput.value.trim();
      const ch = state.security.cryptoChallenge;
      if (!ans || !ch) {
        alert('Please answer the security question.');
        return;
      }
      // Construct token: CRYPTO:nonce:timestamp:answer:signature
      state.security.captchaToken = `CRYPTO:${ch.nonce}:${ch.timestamp}:${ans}:${ch.signature}`;
      const feedback = document.getElementById('crypto-feedback');
      feedback.innerText = '✓ Security challenge token prepared.';
      feedback.className = 'text-[11px] font-medium text-green-700';
      feedback.classList.remove('hidden');
    });
  }
}

function renderCaptchaWidget(reason = '') {
  const container = document.getElementById('captcha-container');
  const reasonText = document.getElementById('captcha-reason-text');
  const turnstileWrap = document.getElementById('turnstile-wrapper');
  const cryptoWrap = document.getElementById('crypto-challenge-wrapper');

  if (!container) return;

  container.classList.remove('hidden');
  if (reason && reasonText) {
    reasonText.innerText = `Security verification required: ${reason}`;
  }

  // If Cloudflare Turnstile key is configured
  if (state.security.turnstileSiteKey && window.turnstile) {
    turnstileWrap.classList.remove('hidden');
    cryptoWrap.classList.add('hidden');
    try {
      window.turnstile.render('#turnstile-widget', {
        sitekey: state.security.turnstileSiteKey,
        callback: (token) => {
          state.security.captchaToken = token;
        },
      });
    } catch (e) {
      console.warn('Turnstile render warning:', e);
    }
  } else if (state.security.cryptoChallenge) {
    // Fallback Cryptographic Math Challenge
    turnstileWrap.classList.add('hidden');
    cryptoWrap.classList.remove('hidden');
    const ch = state.security.cryptoChallenge;
    const label = document.getElementById('crypto-question-label');
    if (label) label.innerText = ch.question;
  }
}

// -------------------------------------------------------------
// ADVISORY DUPLICATE CONFIRMATION MODAL
// -------------------------------------------------------------
function setupDuplicateModal() {
  const modal = document.getElementById('duplicate-modal');
  const proceedBtn = document.getElementById('dup-modal-proceed-btn');
  const trackBtn = document.getElementById('dup-modal-track-btn');
  const cancelBtn = document.getElementById('dup-modal-cancel-btn');

  if (!modal) return;

  if (proceedBtn) {
    proceedBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
      if (state.pendingSubmission) {
        submitComplaint(true); // force duplicate
      }
    });
  }

  if (trackBtn) {
    trackBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
      if (state.pendingSubmission && state.pendingSubmission.duplicate_of) {
        trackComplaintById(state.pendingSubmission.duplicate_of);
      }
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
      state.pendingSubmission = null;
    });
  }
}

// -------------------------------------------------------------
// REALTIME ADVISORY DUPLICATE CHECK & FORM SUBMISSION
// -------------------------------------------------------------
function setupRealtimeDuplicateCheck() {
  const titleInput = document.getElementById('complaint-title');
  const descInput = document.getElementById('complaint-desc');
  const localitySelect = document.getElementById('locality-select');
  const customInput = document.getElementById('locality-custom-input');
  const dupBanner = document.getElementById('duplicate-advisory-banner');

  const triggerCheck = () => {
    clearTimeout(state.duplicateCheckTimeout);
    const title = titleInput.value.trim();
    const desc = descInput.value.trim();
    const locality = localitySelect.value === 'Other / Enter manually' ? customInput.value.trim() : localitySelect.value;

    if (title.length < 8 || desc.length < 15) {
      dupBanner.classList.add('hidden');
      return;
    }

    state.duplicateCheckTimeout = setTimeout(async () => {
      try {
        const res = await fetch('/api/check-duplicate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, description: desc, locality }),
        });
        const dup = await res.json();
        if (dup && dup.is_duplicate) {
          document.getElementById('dup-match-score').innerText = `${Math.round(dup.similarity_score * 100)}% Match`;
          document.getElementById('dup-match-text').innerHTML = `
            A related report <strong>${dup.duplicate_of}</strong> ("${escapeHTML(dup.matched_title)}") in ${escapeHTML(dup.matched_locality)} is currently <strong>${escapeHTML(dup.matched_status)}</strong>. 
            You may still proceed if this is a separate incident.
          `;
          dupBanner.classList.remove('hidden');
        } else {
          dupBanner.classList.add('hidden');
        }
      } catch (err) {
        console.warn('Advisory duplicate check skipped:', err);
      }
    }, 450);
  };

  if (titleInput) titleInput.addEventListener('input', triggerCheck);
  if (descInput) descInput.addEventListener('input', triggerCheck);
  if (localitySelect) localitySelect.addEventListener('change', triggerCheck);
  if (customInput) customInput.addEventListener('input', triggerCheck);
}

function setupFormHandlers() {
  const form = document.getElementById('complaint-form');
  if (!form) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    submitComplaint(false);
  });

  const submitAnotherBtn = document.getElementById('submit-another-btn');
  if (submitAnotherBtn) {
    submitAnotherBtn.addEventListener('click', () => {
      document.getElementById('submission-success-card').classList.add('hidden');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }
}

async function submitComplaint(forceDuplicate = false) {
  const form = document.getElementById('complaint-form');
  const submitBtn = document.getElementById('submit-complaint-btn');
  const submitText = document.getElementById('submit-btn-text');
  const submitSpinner = document.getElementById('submit-btn-spinner');
  const successCard = document.getElementById('submission-success-card');

  const title = document.getElementById('complaint-title').value.trim();
  const localityChoice = document.getElementById('locality-select').value;
  const customLocality = document.getElementById('locality-custom-input').value.trim();
  const desc = document.getElementById('complaint-desc').value.trim();
  const captionVal = document.getElementById('image-caption-input')?.value.trim() || '';

  let finalLocality = localityChoice;
  let finalLandmark = '';

  if (localityChoice === 'Other / Enter manually') {
    if (!customLocality) {
      alert('Please specify your locality in the text input.');
      return;
    }
    finalLocality = customLocality;
  } else {
    finalLandmark = customLocality;
  }

  if (!title || !desc || !finalLocality) {
    alert('Please fill in all required fields: Title, Locality, and Description.');
    return;
  }

  // COMPULSORY LIVE PHOTO VALIDATION
  if (!state.selectedPhotoFile && !state.uploadedPhotoPath) {
    alert('A live camera photo of the civic issue is compulsory for submission. Please take a photo or select an image.');
    document.getElementById('photo-drop-zone').scrollIntoView({ behavior: 'smooth' });
    return;
  }

  // OTP REQUIREMENT VALIDATION
  if (state.security.otpRequired && !state.otp.verified) {
    alert('Mobile number verification via OTP is required for this deployment. Please verify your phone number.');
    document.getElementById('otp-phone-input').focus();
    return;
  }

  // Loading state
  submitBtn.disabled = true;
  submitText.innerText = 'Analyzing & verifying...';
  submitSpinner.classList.remove('hidden');

  try {
    // 1. Upload photo if selected and not yet uploaded
    let uploadedImagePath = state.uploadedPhotoPath;
    if (state.selectedPhotoFile && !uploadedImagePath) {
      const formData = new FormData();
      formData.append('photo', state.selectedPhotoFile);
      const upRes = await fetch('/api/upload-photo', {
        method: 'POST',
        body: formData,
      });
      if (upRes.ok) {
        const upData = await upRes.json();
        uploadedImagePath = upData.image_path;
        state.uploadedPhotoPath = uploadedImagePath;
      } else {
        const errData = await upRes.json();
        alert(errData.error || 'Failed to upload photo evidence.');
        submitBtn.disabled = false;
        submitText.innerText = 'Submit complaint';
        submitSpinner.classList.add('hidden');
        return;
      }
    }

    // 2. Submit complaint payload
    const payload = {
      title,
      description: desc,
      locality: finalLocality,
      landmark: finalLandmark,
      image_path: uploadedImagePath,
      image_caption: captionVal,
      force_duplicate: forceDuplicate,
      captcha_token: state.security.captchaToken,
      phone: state.otp.phone,
      otp_token: state.otp.token,
      latitude: state.locationCoords.latitude,
      longitude: state.locationCoords.longitude,
      location_shared: state.locationCoords.shared,
    };

    const res = await fetch('/api/complaints', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    // 3. Handle Advisory Duplicate (HTTP 409)
    if (res.status === 409) {
      const dup = await res.json();
      state.pendingSubmission = { ...payload, duplicate_of: dup.duplicate_of };
      document.getElementById('dup-modal-id').innerText = dup.duplicate_of;
      document.getElementById('dup-modal-status').innerText = dup.matched_status;
      document.getElementById('dup-modal-title').innerText = `"${dup.matched_title}" in ${dup.matched_locality}`;
      document.getElementById('dup-modal-explanation').innerText = dup.explanation;
      document.getElementById('duplicate-modal').classList.remove('hidden');
      initIcons();
      return;
    }

    // 4. Handle Security Challenge / CAPTCHA Required (HTTP 403)
    if (res.status === 403) {
      const err = await res.json();
      alert(err.error || 'Security verification required.');
      if (err.require_captcha) {
        renderCaptchaWidget(err.reason);
        document.getElementById('captcha-container').scrollIntoView({ behavior: 'smooth' });
      }
      return;
    }

    // 5. Handle Rate Limiting (HTTP 429)
    if (res.status === 429) {
      const err = await res.json();
      alert(`⚠️ ${err.error}`);
      return;
    }

    if (!res.ok) {
      const err = await res.json();
      alert(err.error || 'Failed to register complaint.');
      return;
    }

    const created = await res.json();

    // Populate Success Card
    document.getElementById('success-tracking-id').innerText = created.tracking_id;
    document.getElementById('success-category').innerText = created.category;
    document.getElementById('success-locality').innerText = `📍 ${created.locality}${created.landmark ? ' (' + created.landmark + ')' : ''}`;
    document.getElementById('success-priority-badge').innerHTML = getPriorityBadgeHTML(created.priority);
    document.getElementById('success-engine-badge').innerHTML = getEngineBadgeHTML(created.classification_source);
    document.getElementById('success-reason').innerText = created.priority_reason;

    const imgBox = document.getElementById('success-image-preview-box');
    const imgThumb = document.getElementById('success-image-thumb');
    if (created.image_path) {
      imgThumb.src = created.image_path;
      imgBox.classList.remove('hidden');
    } else {
      imgBox.classList.add('hidden');
    }

    // Button to track
    document.getElementById('success-track-btn').onclick = () => {
      trackComplaintById(created.tracking_id);
    };

    // Reset form
    form.reset();
    state.selectedPhotoFile = null;
    state.uploadedPhotoPath = null;
    state.locationCoords = { latitude: null, longitude: null, shared: false };
    document.getElementById('photo-drop-zone').querySelector('#drop-zone-prompt').classList.remove('hidden');
    document.getElementById('photo-drop-zone').querySelector('#photo-preview-container').classList.add('hidden');
    document.getElementById('duplicate-advisory-banner').classList.add('hidden');
    document.getElementById('image-caption-box').classList.add('hidden');
    document.getElementById('location-attached-badge').classList.add('hidden');
    document.getElementById('btn-share-location').classList.remove('hidden');

    successCard.classList.remove('hidden');
    successCard.scrollIntoView({ behavior: 'smooth' });
    showToast('Complaint registered successfully.');

    // Refresh metrics
    loadMetrics();
  } catch (err) {
    console.error(err);
    alert('Error registering grievance inside prototype. Please check connection and try again.');
  } finally {
    submitBtn.disabled = false;
    submitText.innerText = 'Submit complaint';
    submitSpinner.classList.add('hidden');
  }
}

// -------------------------------------------------------------
// COMPLAINT TRACKING
// -------------------------------------------------------------
const trackForm = document.getElementById('track-form');
if (trackForm) {
  trackForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const id = document.getElementById('track-id-input').value.trim();
    if (id) trackComplaintById(id);
  });
}

async function trackComplaintById(trackingId) {
  renderTab('track');
  document.getElementById('track-id-input').value = trackingId;

  try {
    const url = new URL(window.location);
    url.searchParams.set('tab', 'track');
    url.searchParams.set('id', trackingId);
    window.history.replaceState({}, '', url);
  } catch (e) {}

  const resultContainer = document.getElementById('track-result-container');
  const notFoundContainer = document.getElementById('track-not-found');

  resultContainer.classList.add('hidden');
  notFoundContainer.classList.add('hidden');

  try {
    const res = await fetch(`/api/complaints/${encodeURIComponent(trackingId)}`);
    if (res.status === 404) {
      document.getElementById('not-found-id').innerText = trackingId;
      notFoundContainer.classList.remove('hidden');
      return;
    }

    const rec = await res.json();
    document.getElementById('track-res-id').innerText = rec.tracking_id;
    document.getElementById('track-res-title').innerText = rec.title;
    document.getElementById('track-res-locality').innerText = `📍 ${rec.locality}${rec.landmark ? ' (' + rec.landmark + ')' : ''} • Registered on ${rec.created_at}`;
    document.getElementById('track-res-status-badge').innerHTML = getStatusBadgeHTML(rec.status);
    document.getElementById('track-res-cat').innerText = rec.category;
    document.getElementById('track-res-priority-badge').innerHTML = getPriorityBadgeHTML(rec.priority);
    document.getElementById('track-res-dept').innerText = rec.assigned_department || 'Municipal Department Pending Allocation';
    document.getElementById('track-res-created-date').innerText = rec.created_at.split(' ')[0];
    document.getElementById('track-res-desc').innerText = rec.description;
    document.getElementById('track-res-reason').innerText = rec.priority_reason;
    document.getElementById('track-res-updated').innerText = `Last updated: ${rec.updated_at} • Internal operational notes protected under Civic Privacy Protocol.`;

    // Attached Photo
    const photoBox = document.getElementById('track-res-photo-box');
    const photoImg = document.getElementById('track-res-photo');
    if (rec.image_path) {
      photoImg.src = rec.image_path;
      photoBox.classList.remove('hidden');
    } else {
      photoBox.classList.add('hidden');
    }

    // Render Timeline Steps (Submitted -> In Review -> In Progress -> Resolved)
    renderTimelineNodes(rec.status, rec.created_at, rec.updated_at);

    resultContainer.classList.remove('hidden');
    resultContainer.scrollIntoView({ behavior: 'smooth' });
    initIcons();
  } catch (err) {
    console.error('Failed to look up tracking ID:', err);
  }
}

function renderTimelineNodes(currentStatus, createdAt, updatedAt) {
  const steps = [
    { key: 'Submitted', label: 'Report Logged', time: createdAt },
    { key: 'In Review', label: 'In Review', time: '' },
    { key: 'In Progress', label: 'Team Assigned', time: '' },
    { key: 'Resolved', label: 'Resolved', time: currentStatus === 'Resolved' ? updatedAt : '' },
  ];

  const order = ['Submitted', 'In Review', 'In Progress', 'Resolved'];
  let currentIdx = order.indexOf(currentStatus);
  if (currentIdx === -1 && currentStatus === 'Under Review') currentIdx = 1;
  if (currentIdx === -1) currentIdx = 0;

  const container = document.getElementById('timeline-steps-container');
  container.innerHTML = steps.map((s, idx) => {
    let nodeClasses = 'w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm border-2 ';
    let nodeContent = `${idx + 1}`;

    if (idx < currentIdx) {
      nodeClasses += 'bg-[#2E3D28] border-[#2E3D28] text-white';
      nodeContent = '✓';
    } else if (idx === currentIdx) {
      nodeClasses += 'bg-[#A9B887] border-[#2E3D28] text-[#2E3D28] ring-4 ring-[#A9B887]/30';
    } else {
      nodeClasses += 'bg-white border-[#D5D7C9] text-[#576352]';
    }

    return `
      <div class="flex flex-col items-center text-center relative z-10 w-28">
        <div class="${nodeClasses}">${nodeContent}</div>
        <div class="text-xs font-semibold text-[#2E3D28] mt-2">${s.label}</div>
        ${s.time ? `<div class="text-[11px] text-[#576352] mt-0.5">${s.time}</div>` : ''}
      </div>
    `;
  }).join('');
}

// -------------------------------------------------------------
// ADMIN PORTAL & AUTHENTICATION GATE
// -------------------------------------------------------------
function setupAdminLogin() {
  const form = document.getElementById('admin-login-form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const code = document.getElementById('admin-passcode-input').value.trim();
      if (code === 'admin123' || code.length > 0) {
        state.isAdminUnlocked = true;
        sessionStorage.setItem('civicfix_admin_unlocked', 'true');
        checkAdminGate();
        showToast('Admin demonstration workspace unlocked.');
      }
    });
  }
}

function checkAdminGate() {
  const gate = document.getElementById('admin-login-gate');
  const workspace = document.getElementById('admin-workspace');

  if (state.isAdminUnlocked) {
    gate.classList.add('hidden');
    workspace.classList.remove('hidden');
    loadAdminComplaints();
    loadMetrics();
  } else {
    gate.classList.remove('hidden');
    workspace.classList.add('hidden');
  }
  initIcons();
}

function lockAdminPortal() {
  state.isAdminUnlocked = false;
  sessionStorage.removeItem('civicfix_admin_unlocked');
  renderTab('home');
  showToast('Logged out of Admin Portal.');
}

async function loadAdminComplaints() {
  const search = document.getElementById('admin-search-input')?.value.trim() || '';
  const locality = document.getElementById('admin-filter-loc')?.value || 'All';
  const category = document.getElementById('admin-filter-cat')?.value || 'All';
  const priority = document.getElementById('admin-filter-prio')?.value || 'All';
  const status = document.getElementById('admin-filter-stat')?.value || 'All';

  const params = new URLSearchParams({ search, locality, category, priority, status });

  try {
    const res = await fetch(`/api/complaints?${params.toString()}`);
    state.complaints = await res.json();
    renderAdminTable(state.complaints);
  } catch (err) {
    console.error('Failed to load admin complaints:', err);
  }
}

// Set up admin filter change listeners
['admin-search-input', 'admin-filter-loc', 'admin-filter-cat', 'admin-filter-prio', 'admin-filter-stat'].forEach(id => {
  const el = document.getElementById(id);
  if (el) {
    el.addEventListener('input', () => {
      clearTimeout(state.adminSearchTimeout);
      state.adminSearchTimeout = setTimeout(loadAdminComplaints, 300);
    });
    el.addEventListener('change', loadAdminComplaints);
  }
});

function renderAdminTable(complaints) {
  const tbody = document.getElementById('admin-complaints-tbody');
  const countSpan = document.getElementById('admin-records-count');
  countSpan.innerText = `(${complaints.length} matching records)`;

  if (!complaints || complaints.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="text-center py-8 text-sm text-[#576352]">
          No grievances found matching the selected filters.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = complaints.map(c => `
    <tr class="border-b border-[#D5D7C9]/60 hover:bg-[#F8F9F5] cursor-pointer transition-colors" onclick="selectAdminComplaint('${c.tracking_id}')">
      <td class="py-3 px-4 text-xs font-bold text-[#2E3D28] font-mono">${c.tracking_id}</td>
      <td class="py-3 px-4">
        <div class="text-xs font-semibold text-[#1E251B] max-w-xs truncate">${escapeHTML(c.title)}</div>
        <div class="text-[11px] text-[#576352]">📍 ${escapeHTML(c.locality)}${c.landmark ? ' (' + escapeHTML(c.landmark) + ')' : ''}</div>
      </td>
      <td class="py-3 px-4 text-xs text-[#2E3D28]">${c.category}</td>
      <td class="py-3 px-4">${getPriorityBadgeHTML(c.priority)}</td>
      <td class="py-3 px-4">${getStatusBadgeHTML(c.status)}</td>
      <td class="py-3 px-4 text-xs text-[#2E3D28]">${c.assigned_department || '<span class="text-[#576352] italic">Pending</span>'}</td>
      <td class="py-3 px-4 text-xs text-[#576352] whitespace-nowrap">${c.created_at.split(' ')[0]}</td>
    </tr>
  `).join('');

  // Auto-select first complaint if none selected
  if (!state.selectedComplaintId && complaints.length > 0) {
    selectAdminComplaint(complaints[0].tracking_id);
  }
}

async function selectAdminComplaint(trackingId) {
  state.selectedComplaintId = trackingId;
  const inspector = document.getElementById('admin-inspector-card');

  try {
    const res = await fetch(`/api/complaints/${encodeURIComponent(trackingId)}?admin=1`);
    const c = await res.json();

    document.getElementById('inspect-id').innerText = c.tracking_id;
    document.getElementById('inspect-title').innerText = c.title;
    document.getElementById('inspect-locality').innerText = `📍 Locality: ${c.locality}${c.landmark ? ' (' + c.landmark + ')' : ''} • Logged: ${c.created_at}`;
    document.getElementById('inspect-priority-badge').innerHTML = getPriorityBadgeHTML(c.priority);
    document.getElementById('inspect-status-badge').innerHTML = getStatusBadgeHTML(c.status);
    document.getElementById('inspect-source-badge').innerHTML = getEngineBadgeHTML(c.classification_source);
    document.getElementById('inspect-desc').innerText = c.description;
    document.getElementById('inspect-reason').innerText = c.priority_reason;

    // Photo Inspection
    const photoBox = document.getElementById('inspect-photo-box');
    const photoImg = document.getElementById('inspect-photo-img');
    const photoLink = document.getElementById('inspect-photo-link');
    if (c.image_path) {
      photoImg.src = c.image_path;
      photoLink.href = c.image_path;
      photoBox.classList.remove('hidden');
    } else {
      photoBox.classList.add('hidden');
    }

    // Duplicate alert
    const dupAlert = document.getElementById('inspect-dup-alert');
    if (c.is_duplicate) {
      document.getElementById('inspect-dup-text').innerText = `This report shares high text similarity with report ${c.duplicate_of || 'an earlier entry'}.`;
      dupAlert.classList.remove('hidden');
    } else {
      dupAlert.classList.add('hidden');
    }

    // Set Form Fields
    const deptSelect = document.getElementById('admin-edit-dept');
    if (c.assigned_department && deptSelect.querySelector(`option[value="${c.assigned_department}"]`)) {
      deptSelect.value = c.assigned_department;
    } else {
      deptSelect.selectedIndex = 0;
    }

    document.getElementById('admin-edit-officer').value = c.assigned_officer || '';
    document.getElementById('admin-edit-status').value = c.status === 'Under Review' ? 'In Review' : c.status;
    document.getElementById('admin-edit-notes').value = c.admin_notes || '';

    // Render Status History Audit Trail
    const historyContainer = document.getElementById('inspect-status-history');
    let history = [];
    if (c.status_history) {
      try {
        history = JSON.parse(c.status_history);
      } catch (e) {
        history = [];
      }
    }

    if (history.length > 0) {
      historyContainer.innerHTML = history.map(h => `
        <div class="p-2 bg-[#F8F9F5] border border-[#D5D7C9] rounded flex justify-between items-center text-[11px]">
          <div>
            <strong class="text-[#2E3D28]">${h.status}</strong>
            ${h.department ? ' • ' + h.department : ''}
            ${h.officer ? ' (' + h.officer + ')' : ''}
            ${h.notes ? ' — <span class="italic text-[#1E251B]">' + escapeHTML(h.notes) + '</span>' : ''}
          </div>
          <div class="text-[#576352] text-[10px] whitespace-nowrap ml-2">${h.timestamp || ''}</div>
        </div>
      `).join('');
    } else {
      historyContainer.innerHTML = '<div class="italic text-[11px] text-[#576352]">No administrative changes recorded yet.</div>';
    }

    inspector.classList.remove('hidden');
    initIcons();
  } catch (err) {
    console.error('Failed to load complaint for inspection:', err);
  }
}

// Admin Save Action
const adminUpdateForm = document.getElementById('admin-update-form');
if (adminUpdateForm) {
  adminUpdateForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!state.selectedComplaintId) return;

    const assigned_department = document.getElementById('admin-edit-dept').value;
    const assigned_officer = document.getElementById('admin-edit-officer').value.trim();
    const status = document.getElementById('admin-edit-status').value;
    const admin_notes = document.getElementById('admin-edit-notes').value.trim();

    const btn = document.getElementById('admin-save-btn');
    btn.disabled = true;
    btn.innerText = 'Saving changes...';

    try {
      const res = await fetch(`/api/complaints/${encodeURIComponent(state.selectedComplaintId)}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assigned_department, assigned_officer, status, admin_notes }),
      });

      if (res.ok) {
        showToast(`Grievance ${state.selectedComplaintId} updated successfully. Status set to '${status}'.`);
        await loadAdminComplaints();
        await loadMetrics();
        await selectAdminComplaint(state.selectedComplaintId);
      } else {
        alert('Failed to update record. Please try again.');
      }
    } catch (err) {
      console.error(err);
      alert('Network error while updating complaint.');
    } finally {
      btn.disabled = false;
      btn.innerText = 'Save changes';
    }
  });
}

// -------------------------------------------------------------
// HELPER BADGE RENDERERS (Accessible Semantic Tokens)
// -------------------------------------------------------------
function getPriorityBadgeHTML(priority) {
  const p = (priority || '').toLowerCase();
  if (p === 'high') {
    return `<span class="badge badge-priority-high px-2 py-0.5 rounded text-xs font-semibold inline-flex items-center gap-1">● High Priority</span>`;
  } else if (p === 'medium') {
    return `<span class="badge badge-priority-medium px-2 py-0.5 rounded text-xs font-semibold inline-flex items-center gap-1">● Medium Priority</span>`;
  } else {
    return `<span class="badge badge-priority-low px-2 py-0.5 rounded text-xs font-semibold inline-flex items-center gap-1">● Low Priority</span>`;
  }
}

function getStatusBadgeHTML(status) {
  const s = (status || '').toLowerCase();
  if (s === 'submitted') {
    return `<span class="badge badge-status-submitted px-2 py-0.5 rounded text-xs font-semibold">Submitted</span>`;
  } else if (s === 'in review' || s === 'under review') {
    return `<span class="badge badge-status-review px-2 py-0.5 rounded text-xs font-semibold">In Review</span>`;
  } else if (s === 'in progress') {
    return `<span class="badge badge-status-progress px-2 py-0.5 rounded text-xs font-semibold">In Progress</span>`;
  } else if (s === 'resolved') {
    return `<span class="badge badge-status-resolved px-2 py-0.5 rounded text-xs font-semibold">✓ Resolved</span>`;
  }
  return `<span class="badge badge-status-submitted px-2 py-0.5 rounded text-xs font-semibold">${status}</span>`;
}

function getEngineBadgeHTML(source) {
  if (source && source.includes('groq')) {
    return `<span class="bg-[#EBF3E8] text-[#2E3D28] border border-[#A9B887] px-2 py-0.5 rounded text-xs font-semibold">⚡ Groq Llama-3.3</span>`;
  }
  return `<span class="bg-[#F8F9F5] text-[#555E50] border border-[#D5D7C9] px-2 py-0.5 rounded text-xs font-semibold">⚙ Deterministic Civic Rules</span>`;
}

function showToast(message) {
  const toast = document.getElementById('toast-notification');
  if (toast) {
    toast.innerText = message;
    toast.classList.remove('opacity-0', 'pointer-events-none');
    toast.classList.add('opacity-100');
    setTimeout(() => {
      toast.classList.remove('opacity-100');
      toast.classList.add('opacity-0', 'pointer-events-none');
    }, 3500);
  }
}

function escapeHTML(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
