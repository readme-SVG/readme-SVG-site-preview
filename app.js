let currentUrl = null;
let currentTab = 'markdown';
let badgeUrl = '';
let refreshInterval = null;
let refreshCount = 0;

function syncColor(pickerId, textId) {
  const picker = document.getElementById(pickerId);
  const text = document.getElementById(textId);
  if(!picker || !text) return;
  picker.addEventListener('input', () => { text.value = picker.value; });
  text.addEventListener('input', () => {
    if (/^#[0-9a-fA-F]{6}$/.test(text.value)) picker.value = text.value;
  });
}

function syncSlider(sliderId, displayId, isFloat = true) {
  const slider = document.getElementById(sliderId);
  const display = document.getElementById(displayId);
  if (slider && display) {
      slider.addEventListener('input', () => {
        display.textContent = isFloat ? parseFloat(slider.value).toFixed(2) : slider.value;
      });
  }
}

syncColor('bg-color-picker', 'bg-color-text');
syncColor('title-color-picker', 'title-color-text');
syncColor('plate-color-picker', 'plate-color-text');
syncColor('border-color-picker', 'border-color-text');

syncSlider('title-opacity-input', 'title-opacity-val', true);
syncSlider('plate-opacity-input', 'plate-opacity-val', true);
syncSlider('scale-input', 'scale-val', true);
syncSlider('offset-x-input', 'offset-x-val', false);

document.getElementById('url-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') generate();
});

function showError(msg) {
  const el = document.getElementById('error-msg');
  el.textContent = msg;
  el.classList.add('visible');
}

function hideError() {
  document.getElementById('error-msg').classList.remove('visible');
}

async function generate() {
  let url = document.getElementById('url-input').value.trim();
  if (!url) { showError('Please enter a website URL'); return; }
  
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url;
  }

  hideError();
  document.getElementById('result-card').classList.remove('visible');
  document.getElementById('loading').classList.add('visible');
  document.getElementById('gen-btn').disabled = true;

  try {
    const infoResp = await fetch(`/info?url=${encodeURIComponent(url)}`);
    if (!infoResp.ok) { throw new Error('Could not fetch website info.'); }
    const info = await infoResp.json();
    currentUrl = info.url;

    const width = document.getElementById('width-input').value || 320;
    const height = document.getElementById('height-input').value || 0;
    const radius = document.getElementById('radius-input').value || 0;
    const bg = document.getElementById('bg-color-text').value.replace('#', '');
    const titleColor = document.getElementById('title-color-text').value.replace('#', '');
    const plateColor = document.getElementById('plate-color-text').value.replace('#', '');
    const titleOpacity = document.getElementById('title-opacity-input').value || 1;
    const plateOpacity = document.getElementById('plate-opacity-input').value || 0.78;
    const titlePosition = document.getElementById('title-position-input').value || 'overlay_bottom';
    const borderWidth = document.getElementById('border-width-input').value || 2;
    const borderColor = document.getElementById('border-color-text').value.replace('#', '');
    
    const scale = document.getElementById('scale-input').value || 1.0;
    const offsetX = document.getElementById('offset-x-input').value || 0;

    const customTitleEl = document.getElementById('custom-title-input');
    const customTitle = customTitleEl ? customTitleEl.value.trim() : '';

    badgeUrl = `/badge?url=${encodeURIComponent(currentUrl)}&width=${width}&height=${height}&radius=${radius}&bg=${bg}&title_color=${titleColor}&title_opacity=${titleOpacity}&plate_color=${plateColor}&plate_opacity=${plateOpacity}&title_position=${titlePosition}&border_width=${borderWidth}&border_color=${borderColor}&image_scale=${scale}&image_offset_x=${offsetX}`;
    
    if (customTitle) {
        badgeUrl += `&custom_title=${encodeURIComponent(customTitle)}`;
    }

    const previewImg = document.getElementById('preview-img');
    previewImg.src = badgeUrl + '&_t=' + Date.now();

    updateCode(currentUrl);

    document.getElementById('loading').classList.remove('visible');
    document.getElementById('result-card').classList.add('visible');

    clearInterval(refreshInterval);
    refreshCount = 0;
    refreshInterval = setInterval(() => {
        refreshCount++;
        previewImg.src = badgeUrl + '&_t=' + Date.now();
        if (refreshCount >= 3) {
            clearInterval(refreshInterval);
        }
    }, 6000);

  } catch (err) {
    document.getElementById('loading').classList.remove('visible');
    showError(err.message || 'Something went wrong');
  } finally {
    document.getElementById('gen-btn').disabled = false;
  }
}

function updateCode(targetUrl) {
  const absUrl = window.location.origin + badgeUrl;
  let code = '';
  if (currentTab === 'markdown') {
    code = `[![Website preview](${absUrl})](${targetUrl})`;
  } else if (currentTab === 'html') {
    code = `<a href="${targetUrl}" target="_blank">\n  <img src="${absUrl}" alt="Website preview" />\n</a>`;
  } else {
    code = absUrl;
  }
  document.getElementById('code-output').textContent = code;
}

function setTab(tab, btn) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  if (currentUrl) {
    updateCode(currentUrl);
  }
}

function copyCode() {
  const code = document.getElementById('code-output').textContent;
  navigator.clipboard.writeText(code).then(() => {
    const btn = document.getElementById('copy-btn');
    btn.textContent = 'Copied';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = 'Copy';
      btn.classList.remove('copied');
    }, 2000);
  });
}

window.generate = generate;
window.setTab = setTab;
window.copyCode = copyCode;
