import en from './locales/en.js';

const loaders = {
  en: async () => en,
  zh: () => import('./locales/zh.js'),
  es: () => import('./locales/es.js'),
  fr: () => import('./locales/fr.js'),
  pt: () => import('./locales/pt.js'),
  ru: () => import('./locales/ru.js'),
  ja: () => import('./locales/ja.js'),
  de: () => import('./locales/de.js'),
  uk: () => import('./locales/uk.js'),
  pl: () => import('./locales/pl.js'),
  nl: () => import('./locales/nl.js'),
  kk: () => import('./locales/kk.js'),
  sv: () => import('./locales/sv.js'),
  cs: () => import('./locales/cs.js'),
};
const cache = new Map([['en', en]]);
const pending = new Map();

export const defaultTranslations = en;
export const supportedLanguages = Object.keys(loaders);

export async function loadTranslations(lang) {
  const locale = Object.hasOwn(loaders, lang) ? lang : 'en';
  if (cache.has(locale)) return cache.get(locale);
  if (!pending.has(locale)) {
    const request = loaders[locale]()
      .then((module) => {
        cache.set(locale, module.default);
        return module.default;
      })
      .finally(() => pending.delete(locale));
    pending.set(locale, request);
  }
  return pending.get(locale);
}
