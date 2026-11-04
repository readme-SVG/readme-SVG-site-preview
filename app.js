import {
  defaultTranslations,
  loadTranslations,
  supportedLanguages,
} from './i18n/index.js';

const REFRESH_DELAY = 6000;
const MAX_REFRESHES = 3;
const INFO_TIMEOUT = 10000;

let currentLang = 'en';
let translations = defaultTranslations;
let languageRequest = 0;
let currentUrl = null;
let currentTab = 'markdown';
let badgeUrl = '';
let refreshTimer = null;
let refreshCount = 0;
let copyTimer = null;
let infoController = null;
let generation = 0;
let imageGeneration = 0;
let elements = {};

function getT(lang, key) {
  return translations[key] ?? defaultTranslations[key] ?? '';
}

async function changeLanguage(lang) {
  const requestId = ++languageRequest;
  const locale = supportedLanguages.includes(lang) ? lang : 'en';
  try {
    const loaded = await loadTranslations(locale);
    if (requestId !== languageRequest) return;
    translations = loaded;
    currentLang = locale;
    document.documentElement.lang = locale;
    document.getElementById('lang-select').value = locale;
    elements.translated.forEach((element) => {
      element.textContent = getT(currentLang, element.dataset.i18n);
    });
    elements.placeholders.forEach((element) => {
      element.placeholder = getT(currentLang, element.dataset.i18nPlaceholder);
    });
    elements.copyBtn.textContent = getT(
      currentLang,
      elements.copyBtn.classList.contains('copied') ? 'copied' : 'copy',
    );
  } catch {
    if (requestId === languageRequest) {
      document.getElementById('lang-select').value = currentLang;
      showError(getT(currentLang, 'error_generic'));
    }
  }
}

function syncColor(pickerId, textId) {
  const picker = document.getElementById(pickerId);
  const text = document.getElementById(textId);
  picker.addEventListener('input', () => {
    text.value = picker.value;
  });
  text.addEventListener('input', () => {
    if (/^#[0-9a-f]{6}$/i.test(text.value)) picker.value = text.value;
  });
}

function syncSlider(sliderId, displayId, isFloat = true) {
  const slider = document.getElementById(sliderId);
  const display = document.getElementById(displayId);
  slider.addEventListener('input', () => {
    display.textContent = isFloat
      ? Number(slider.value).toFixed(2)
      : slider.value;
  });
}

export function normalizeWebsiteInput(value) {
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > 2048) throw new Error('Invalid website URL');
  const candidate = /^[a-z][a-z\d+.-]*:\/\//i.test(trimmed)
    ? trimmed
    : `https://${trimmed}`;
  const url = new URL(candidate);
  if (
    !['http:', 'https:'].includes(url.protocol) ||
    url.username ||
    url.password
  ) {
    throw new Error('Invalid website URL');
  }
  return url.href;
}

function escapeHtml(value) {
  return value.replace(
    /[&<>"']/g,
    (character) =>
      ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      })[character],
  );
}

export function buildEmbedCode(tab, badge, target) {
  const absoluteBadge = new URL(badge, window.location.origin).href;
  if (tab === 'html') {
    return `<a href="${escapeHtml(target)}" target="_blank" rel="noopener noreferrer">\n  <img src="${escapeHtml(absoluteBadge)}" alt="Website preview" />\n</a>`;
  }
  if (tab === 'url') return absoluteBadge;
  const markdownUrl = (value) =>
    value.replace(
      /[\\()\[\]<>]/g,
      (character) => `%${character.charCodeAt(0).toString(16).toUpperCase()}`,
    );
  return `[![Website preview](${markdownUrl(absoluteBadge)})](${markdownUrl(target)})`;
}

function showError(message) {
  elements.error.textContent = message;
  elements.error.classList.add('visible');
}

function stopRefresh() {
  clearTimeout(refreshTimer);
  refreshTimer = null;
}

function scheduleRefresh(requestGeneration) {
  stopRefresh();
  if (requestGeneration !== generation || refreshCount >= MAX_REFRESHES) return;
  refreshTimer = setTimeout(() => {
    if (requestGeneration !== generation) return;
    refreshCount += 1;
    imageGeneration = requestGeneration;
    elements.previewImg.src = `${badgeUrl}&_t=${Date.now()}`;
  }, REFRESH_DELAY);
}

async function generate() {
  let url;
  try {
    url = normalizeWebsiteInput(elements.url.value);
  } catch {
    showError(
      getT(
        currentLang,
        elements.url.value.trim() ? 'error_generic' : 'error_enter_url',
      ),
    );
    return;
  }

  const requestGeneration = ++generation;
  infoController?.abort();
  stopRefresh();
  elements.result.classList.remove('visible');
  elements.error.classList.remove('visible');

  const controller = new AbortController();
  infoController = controller;
  const timeout = setTimeout(() => controller.abort(), INFO_TIMEOUT);
  elements.loading.classList.add('visible');
  elements.grid.classList.add('has-results');
  elements.generateBtn.disabled = true;

  try {
    const response = await fetch(`/info?url=${encodeURIComponent(url)}`, {
      signal: controller.signal,
    });
    if (!response.ok) throw new Error('Could not fetch website info');
    const info = await response.json();
    if (requestGeneration !== generation) return;
    currentUrl = normalizeWebsiteInput(info.url);

    const params = new URLSearchParams({
      url: currentUrl,
      width: elements.width.value || '320',
      height: elements.height.value || '0',
      radius: elements.radius.value || '0',
      title_color: elements.titleColor.value.replace(/^#/, ''),
      title_opacity: elements.titleOpacity.value || '1',
      plate_color: elements.plateColor.value.replace(/^#/, ''),
      plate_opacity: elements.plateOpacity.value || '0.78',
      title_position: elements.titlePosition.value,
      border_width: elements.borderWidth.value || '2',
      border_color: elements.borderColor.value.replace(/^#/, ''),
      image_scale: elements.scale.value || '1',
      image_offset_x: elements.offsetX.value || '0',
      image_offset_y: elements.offsetY.value || '0',
    });
    const customTitle = elements.customTitle.value.trim();
    if (customTitle) params.set('custom_title', customTitle.slice(0, 300));
    badgeUrl = `/badge?${params}`;
    refreshCount = 0;
    elements.previewLink.href = currentUrl;
    imageGeneration = requestGeneration;
    elements.previewImg.src = `${badgeUrl}&_t=${Date.now()}`;
    updateCode();
    elements.loading.classList.remove('visible');
    elements.result.classList.add('visible');
    scheduleRefresh(requestGeneration);
  } catch {
    if (requestGeneration === generation) {
      elements.loading.classList.remove('visible');
      showError(getT(currentLang, 'error_generic'));
    }
  } finally {
    clearTimeout(timeout);
    if (requestGeneration === generation) {
      elements.generateBtn.disabled = false;
      infoController = null;
    }
  }
}

function updateCode() {
  elements.code.textContent = currentUrl
    ? buildEmbedCode(currentTab, badgeUrl, currentUrl)
    : '';
}

function setTab(tab, button) {
  currentTab = tab;
  elements.tabs.forEach((item) => {
    const active = item === button;
    item.classList.toggle('active', active);
    item.setAttribute('aria-pressed', String(active));
  });
  updateCode();
}

async function copyCode() {
  try {
    await navigator.clipboard.writeText(elements.code.textContent);
    clearTimeout(copyTimer);
    elements.copyBtn.textContent = getT(currentLang, 'copied');
    elements.copyBtn.classList.add('copied');
    copyTimer = setTimeout(() => {
      elements.copyBtn.textContent = getT(currentLang, 'copy');
      elements.copyBtn.classList.remove('copied');
    }, 2000);
  } catch {
    showError(getT(currentLang, 'error_generic'));
  }
}

function initialize() {
  const byId = (id) => document.getElementById(id);
  elements = {
    url: byId('url-input'),
    customTitle: byId('custom-title-input'),
    width: byId('width-input'),
    height: byId('height-input'),
    radius: byId('radius-input'),
    titleColor: byId('title-color-text'),
    plateColor: byId('plate-color-text'),
    borderColor: byId('border-color-text'),
    titleOpacity: byId('title-opacity-input'),
    plateOpacity: byId('plate-opacity-input'),
    titlePosition: byId('title-position-input'),
    borderWidth: byId('border-width-input'),
    scale: byId('scale-input'),
    offsetX: byId('offset-x-input'),
    offsetY: byId('offset-y-input'),
    error: byId('error-msg'),
    loading: byId('loading'),
    result: byId('result-card'),
    grid: document.querySelector('.layout-grid'),
    generateBtn: byId('gen-btn'),
    previewImg: byId('preview-img'),
    previewLink: byId('preview-link'),
    code: byId('code-output'),
    copyBtn: byId('copy-btn'),
    translated: document.querySelectorAll('[data-i18n]'),
    placeholders: document.querySelectorAll('[data-i18n-placeholder]'),
    tabs: document.querySelectorAll('.tab'),
  };

  syncColor('title-color-picker', 'title-color-text');
  syncColor('plate-color-picker', 'plate-color-text');
  syncColor('border-color-picker', 'border-color-text');
  syncSlider('title-opacity-input', 'title-opacity-val');
  syncSlider('plate-opacity-input', 'plate-opacity-val');
  syncSlider('scale-input', 'scale-val');
  syncSlider('offset-x-input', 'offset-x-val', false);
  syncSlider('offset-y-input', 'offset-y-val', false);

  elements.url.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.repeat) {
      event.preventDefault();
      generate();
    }
  });
  elements.generateBtn.addEventListener('click', generate);
  elements.copyBtn.addEventListener('click', copyCode);
  elements.tabs.forEach((button) =>
    button.addEventListener('click', () => setTab(button.dataset.tab, button)),
  );
  byId('lang-select').addEventListener('change', (event) =>
    changeLanguage(event.target.value),
  );
  elements.previewImg.addEventListener('load', () =>
    scheduleRefresh(imageGeneration),
  );
  elements.previewImg.addEventListener('error', () =>
    scheduleRefresh(imageGeneration),
  );
  window.addEventListener('pagehide', () => {
    generation += 1;
    infoController?.abort();
    stopRefresh();
    clearTimeout(copyTimer);
  });
  window.addEventListener('pageshow', (event) => {
    if (!event.persisted) return;
    elements.generateBtn.disabled = false;
    elements.loading.classList.remove('visible');
    if (elements.result.classList.contains('visible')) {
      imageGeneration = generation;
      scheduleRefresh(generation);
    }
  });
  changeLanguage(byId('lang-select').value);
}

if (typeof document !== 'undefined') initialize();
