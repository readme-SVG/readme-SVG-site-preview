// Локализация
const translations = {
  en: {
    built_by: "Built by",
    title: "Website Badge<br/>Generator",
    subtitle: "Paste any website URL to generate a dynamic SVG preview board.",
    website_url: "Website URL",
    custom_title: "Custom Title (optional)",
    custom_title_placeholder: "Leave empty to use website title",
    width: "Width (px)",
    height: "Height (px, 0 = auto)",
    scale: "Image Scale: ",
    offset_x: "Image X Offset: ",
    offset_y: "Image Y Offset: ",
    radius: "Border Radius",
    border_width: "Border Width (px)",
    bg_color: "Background Color",
    border_color: "Border Color",
    title_color: "Title Color",
    plate_color: "Title Plate Color",
    title_opacity: "Text Opacity: ",
    plate_opacity: "Plate Opacity: ",
    title_position: "Title Position",
    pos_outside_top: "Very Top (above preview)",
    pos_overlay_top: "Top (overlay)",
    pos_overlay_bottom: "Bottom (overlay)",
    pos_outside_bottom: "Very Bottom (below preview)",
    generate_btn: "GENERATE BOARD",
    processing: "Processing layout...",
    output_preview: "Output Preview",
    preview_notice: "If image shows placeholder, please wait a few seconds. It will auto-refresh.",
    integration_code: "Integration Code",
    tab_markdown: "Markdown",
    tab_html: "HTML",
    tab_url: "URL",
    copy: "Copy",
    copied: "Copied"
  },
  ru: {
    built_by: "Создано",
    title: "Генератор<br/>Превью Сайтов",
    subtitle: "Вставьте URL любого сайта, чтобы сгенерировать динамическую SVG-карточку.",
    website_url: "URL сайта",
    custom_title: "Свой заголовок (необязательно)",
    custom_title_placeholder: "Оставьте пустым (возьмет заголовок сайта)",
    width: "Ширина (px)",
    height: "Высота (px, 0 = авто)",
    scale: "Масштаб: ",
    offset_x: "Сдвиг по X: ",
    offset_y: "Сдвиг по Y: ",
    radius: "Скругление углов",
    border_width: "Толщина рамки (px)",
    bg_color: "Цвет фона",
    border_color: "Цвет рамки",
    title_color: "Цвет текста",
    plate_color: "Цвет подложки текста",
    title_opacity: "Прозрачность текста: ",
    plate_opacity: "Прозрачность подложки: ",
    title_position: "Позиция заголовка",
    pos_outside_top: "Сверху (над превью)",
    pos_overlay_top: "Сверху (поверх)",
    pos_overlay_bottom: "Снизу (поверх)",
    pos_outside_bottom: "Снизу (под превью)",
    generate_btn: "СГЕНЕРИРОВАТЬ",
    processing: "Обработка макета...",
    output_preview: "Предпросмотр",
    preview_notice: "Если вместо картинки заглушка, подождите пару секунд. Она обновится автоматически.",
    integration_code: "Код для вставки",
    tab_markdown: "Markdown",
    tab_html: "HTML",
    tab_url: "Ссылка",
    copy: "Копировать",
    copied: "Скопировано"
  }
};

let currentLang = 'en';

function changeLanguage(lang) {
  currentLang = lang;
  
  // Обновляем обычные элементы с текстом
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (translations[lang][key]) {
      el.innerHTML = translations[lang][key];
    }
  });
  
  // Обновляем плейсхолдеры в инпутах
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (translations[lang][key]) {
      el.placeholder = translations[lang][key];
    }
  });

  // Обновляем кнопку копирования, если она не в статусе "Copied"
  const copyBtn = document.getElementById('copy-btn');
  if (copyBtn && !copyBtn.classList.contains('copied')) {
    copyBtn.textContent = translations[lang]['copy'];
  } else if (copyBtn && copyBtn.classList.contains('copied')) {
    copyBtn.textContent = translations[lang]['copied'];
  }
}

// Глобальные переменные генератора
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
syncSlider('offset-y-input', 'offset-y-val', false);

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
  if (!url) { 
    showError(currentLang === 'ru' ? 'Пожалуйста, введите URL сайта' : 'Please enter a website URL'); 
    return; 
  }
  
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
    const offsetY = document.getElementById('offset-y-input').value || 0;

    const customTitleEl = document.getElementById('custom-title-input');
    const customTitle = customTitleEl ? customTitleEl.value.trim() : '';

    badgeUrl = `/badge?url=${encodeURIComponent(currentUrl)}&width=${width}&height=${height}&radius=${radius}&bg=${bg}&title_color=${titleColor}&title_opacity=${titleOpacity}&plate_color=${plateColor}&plate_opacity=${plateOpacity}&title_position=${titlePosition}&border_width=${borderWidth}&border_color=${borderColor}&image_scale=${scale}&image_offset_x=${offsetX}&image_offset_y=${offsetY}`;
    
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
    showError(currentLang === 'ru' ? 'Что-то пошло не так' : 'Something went wrong');
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
    btn.textContent = translations[currentLang]['copied'];
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = translations[currentLang]['copy'];
      btn.classList.remove('copied');
    }, 2000);
  });
}

// Экспорт функций
window.changeLanguage = changeLanguage;
window.generate = generate;
window.setTab = setTab;
window.copyCode = copyCode;
