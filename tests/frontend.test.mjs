import test from 'node:test';
import assert from 'node:assert/strict';
import { I18N_KEYS } from '../i18n/keys.js';
import {
  defaultTranslations,
  loadTranslations,
  supportedLanguages,
} from '../i18n/index.js';
import { buildEmbedCode, normalizeWebsiteInput } from '../app.js';

globalThis.window = { location: { origin: 'https://preview.example' } };

test('all locales expose exactly the shared keys', async () => {
  for (const locale of supportedLanguages) {
    const translations = await loadTranslations(locale);
    assert.deepEqual(
      Object.keys(translations).sort(),
      [...I18N_KEYS].sort(),
      locale,
    );
    assert.ok(
      Object.values(translations).every((value) => typeof value === 'string'),
      locale,
    );
  }
});

test('locale loading is cached and unknown locales fall back', async () => {
  assert.equal(await loadTranslations('en'), defaultTranslations);
  assert.equal(await loadTranslations('uk'), await loadTranslations('uk'));
  assert.equal(await loadTranslations('constructor'), defaultTranslations);
});

test('URL input rejects dangerous schemes and credentials', () => {
  assert.equal(normalizeWebsiteInput('example.com'), 'https://example.com/');
  for (const value of [
    '',
    'javascript:alert(1)',
    'file:///etc/passwd',
    'https://user:pass@example.com',
  ]) {
    assert.throws(() => normalizeWebsiteInput(value));
  }
});

test('HTML embed escapes attribute delimiters', () => {
  const code = buildEmbedCode(
    'html',
    '/badge?url=example.com',
    'https://example.com/?q="x"&y=<z>',
  );
  assert.ok(code.includes('&quot;'));
  assert.ok(code.includes('&amp;'));
  assert.ok(code.includes('&lt;'));
  assert.ok(code.includes('rel="noopener noreferrer"'));
  assert.ok(!code.includes('href="https://example.com/?q="'));
});

test('Markdown embed escapes URL delimiters', () => {
  const code = buildEmbedCode(
    'markdown',
    '/badge?title=a(b)',
    'https://example.com/a(b)',
  );
  assert.ok(code.includes('%28'));
  assert.ok(code.includes('%29'));
  assert.equal(
    buildEmbedCode('url', '/badge?url=x', 'https://example.com'),
    'https://preview.example/badge?url=x',
  );
});
