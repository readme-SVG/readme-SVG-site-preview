import { I18N_KEYS } from './keys.js';
import en from './locales/en.js';
import zh from './locales/zh.js';
import es from './locales/es.js';
import fr from './locales/fr.js';
import pt from './locales/pt.js';
import ru from './locales/ru.js';
import ja from './locales/ja.js';
import de from './locales/de.js';
import uk from './locales/uk.js';
import pl from './locales/pl.js';
import nl from './locales/nl.js';
import kk from './locales/kk.js';
import sv from './locales/sv.js';
import cs from './locales/cs.js';

export const translations = {
  en,
  zh,
  es,
  fr,
  pt,
  ru,
  ja,
  de,
  uk,
  pl,
  nl,
  kk,
  sv,
  cs
};

function getMissingKeys(locale, data) {
  return I18N_KEYS.filter((key) => !(key in data));
}

function getExtraKeys(data) {
  return Object.keys(data).filter((key) => !I18N_KEYS.includes(key));
}

export function assertTranslationsAreSynced() {
  const issues = [];

  for (const [locale, data] of Object.entries(translations)) {
    const missingKeys = getMissingKeys(locale, data);
    const extraKeys = getExtraKeys(data);

    if (missingKeys.length > 0 || extraKeys.length > 0) {
      issues.push({ locale, missingKeys, extraKeys });
    }
  }

  if (issues.length > 0) {
    const details = issues
      .map(({ locale, missingKeys, extraKeys }) => {
        const missing = missingKeys.length ? `missing: ${missingKeys.join(', ')}` : '';
        const extra = extraKeys.length ? `extra: ${extraKeys.join(', ')}` : '';
        return `${locale} { ${[missing, extra].filter(Boolean).join(' | ')} }`;
      })
      .join('; ');

    throw new Error(`Translation key mismatch detected: ${details}`);
  }
}

assertTranslationsAreSynced();
