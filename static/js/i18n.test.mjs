// Unit tests for i18n.js core logic (resolve + interpolate)
// Run with: node --test static/js/i18n.test.mjs
// No DOM, no fetch, no storage needed — pure function tests.

import { describe, it, mock } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(__dirname, '..', '..');

// --- Functions under test (mirror i18n.js internals) ---

function _resolve(obj, path) {
  const parts = path.split('.');
  for (const p of parts) {
    if (!obj || typeof obj !== 'object') return null;
    obj = obj[p];
  }
  return obj !== undefined ? obj : null;
}

function _interpolate(str, vars) {
  if (!vars) return str;
  return str.replace(/\{\{(\w+)\}\}/g, (_, k) =>
    vars[k] !== undefined ? String(vars[k]) : `{{${k}}}`
  );
}

function _t(locale, key, vars) {
  if (!locale) return key;
  let val = _resolve(locale, key);
  if (val === null) return key;
  return _interpolate(val, vars);
}

// --- Load real locale data (merge all files from per-namespace dirs) ---
import { readdirSync, existsSync } from 'node:fs';
function _loadLocaleDir(dirPath) {
  const merged = {};
  if (!existsSync(dirPath)) return merged;
  for (const entry of readdirSync(dirPath).sort()) {
    if (!entry.endsWith('.json')) continue;
    const data = JSON.parse(readFileSync(join(dirPath, entry), 'utf-8'));
    Object.assign(merged, data);
  }
  return merged;
}
const enLocale = _loadLocaleDir(join(REPO, 'static', 'locales', 'en'));
const esLocale = _loadLocaleDir(join(REPO, 'static', 'locales', 'es'));

// --- describe('i18n _resolve') ---
describe('i18n _resolve', () => {
  it('resolves simple key', () => {
    assert.equal(_resolve({ a: 'hello' }, 'a'), 'hello');
  });

  it('resolves nested key', () => {
    assert.equal(_resolve({ a: { b: { c: 'deep' } } }, 'a.b.c'), 'deep');
  });

  it('returns null for missing key', () => {
    assert.equal(_resolve({ a: {} }, 'a.b'), null);
  });

  it('returns null for entirely missing path', () => {
    assert.equal(_resolve({}, 'x.y.z'), null);
  });

  it('returns object for non-string leaf (matches JS behavior)', () => {
    assert.deepEqual(_resolve({ a: { b: {} } }, 'a.b'), {});
  });

  it('handles null root', () => {
    assert.equal(_resolve(null, 'a.b'), null);
  });
});

// --- describe('i18n _interpolate') ---
describe('i18n _interpolate', () => {
  it('returns string unchanged when no vars', () => {
    assert.equal(_interpolate('Hello', null), 'Hello');
    assert.equal(_interpolate('Hello', undefined), 'Hello');
  });

  it('substitutes single variable', () => {
    assert.equal(_interpolate('Hello {{name}}', { name: 'World' }), 'Hello World');
  });

  it('substitutes multiple variables', () => {
    assert.equal(
      _interpolate('{{greeting}} {{name}}!', { greeting: 'Hi', name: 'Alice' }),
      'Hi Alice!'
    );
  });

  it('leaves unmatched variables as-is', () => {
    assert.equal(_interpolate('{{a}} {{b}}', { a: 'x' }), 'x {{b}}');
  });

  it('handles empty string', () => {
    assert.equal(_interpolate('', { a: 1 }), '');
  });

  it('coerces vars to string', () => {
    assert.equal(_interpolate('count={{n}}', { n: 0 }), 'count=0');
    assert.equal(_interpolate('ok={{ok}}', { ok: true }), 'ok=true');
  });
});

// --- describe('i18n _t (t function simulation)') ---
describe('i18n _t', () => {
  it('returns correct English string for existing key', () => {
    assert.equal(_t(enLocale, 'common.close'), 'Close');
  });

  it('returns correct Spanish string for existing key', () => {
    assert.equal(_t(esLocale, 'common.close'), 'Cerrar');
  });

  it('returns key when key not found', () => {
    assert.equal(_t(enLocale, 'nonexistent.key'), 'nonexistent.key');
  });

  it('returns key when locale is null', () => {
    assert.equal(_t(null, 'some.key'), 'some.key');
  });

  it('interpolates variables', () => {
    const val = _t(enLocale, 'auth.version', { version: '1.0' });
    assert.equal(val, 'v1.0');
  });

  it('interpolates with vars in key', () => {
    const val = _t(enLocale, 'chat.errors.session_not_found', { name: 'my-session' });
    assert.equal(val, "Session 'my-session' not found");
  });

  it('handles multiple interpolation variables', () => {
    const val = _t(enLocale, 'cookbook.errors.installed', {
      names: 'llama-cpp-python',
      host: 'myserver'
    });
    assert.equal(val, 'Installed llama-cpp-python on myserver. Refreshing...');
  });
});

// --- describe('Real locale file structure') ---
describe('Real locale file structure', () => {
  it('en.json has common keys', () => {
    assert.ok(_t(enLocale, 'common.close'));
    assert.ok(_t(enLocale, 'common.save'));
    assert.ok(_t(enLocale, 'common.cancel'));
  });

  it('es.json has corresponding common keys', () => {
    assert.ok(_t(esLocale, 'common.close'));
    assert.ok(_t(esLocale, 'common.save'));
    assert.ok(_t(esLocale, 'common.cancel'));
  });

  it('es.json translations differ from en.json', () => {
    assert.notEqual(_t(esLocale, 'common.close'), _t(enLocale, 'common.close'));
  });

  it('all es.json leaf keys exist in en.json', () => {
    function leafKeys(obj, prefix = '') {
      let keys = new Set();
      for (const [k, v] of Object.entries(obj)) {
        const full = prefix ? `${prefix}.${k}` : k;
        if (typeof v === 'string') keys.add(full);
        else if (v && typeof v === 'object') {
          const nested = leafKeys(v, full);
          nested.forEach(k => keys.add(k));
        }
      }
      return keys;
    }
    const enKeys = leafKeys(enLocale);
    const esKeys = leafKeys(esLocale);
    const missing = [...esKeys].filter(k => !enKeys.has(k));
    assert.equal(missing.length, 0, `Keys in es.json but not in en.json: ${missing.join(', ')}`);
  });
});

// --- tn() pluralisation ---

function _tn(locale, key, count, vars) {
  const msg = _t(locale, key);
  if (!msg || msg === key) return msg;
  const parts = msg.split('|');
  const form = count === 1 ? parts[0] : (parts[1] || parts[0]);
  const allVars = Object.assign({}, vars, { count });
  return form.replace(/\{\{(\w+)\}\}/g, (_, k) =>
    allVars[k] !== undefined ? String(allVars[k]) : `{{${k}}}`
  );
}

describe('i18n tn (pluralisation)', () => {
  it('returns singular for count=1', () => {
    const locale = { items: '{{count}} item|{{count}} items' };
    assert.equal(_tn(locale, 'items', 1), '1 item');
  });

  it('returns plural for count=0', () => {
    const locale = { items: '{{count}} item|{{count}} items' };
    assert.equal(_tn(locale, 'items', 0), '0 items');
  });

  it('returns plural for count=5', () => {
    const locale = { items: '{{count}} item|{{count}} items' };
    assert.equal(_tn(locale, 'items', 5), '5 items');
  });

  it('falls back to singular when no pipe', () => {
    const locale = { items: '{{count}} items' };
    assert.equal(_tn(locale, 'items', 1), '1 items');
  });

  it('forwards additional vars', () => {
    const locale = { result: '{{count}} {{name}}|{{count}} {{name}}s' };
    assert.equal(_tn(locale, 'result', 3, { name: 'file' }), '3 files');
  });

  it('returns key when missing from locale', () => {
    assert.equal(_tn({}, 'missing.key', 2), 'missing.key');
  });

  it('handles real locale keys with | syntax', () => {
    // Inject a test plural key into a copy of enLocale
    const copy = JSON.parse(JSON.stringify(enLocale));
    copy.common = copy.common || {};
    copy.common.items = '{{count}} item|{{count}} items';
    assert.equal(_tn(copy, 'common.items', 1), '1 item');
    assert.equal(_tn(copy, 'common.items', 10), '10 items');
  });
});

// --- formatNumber ---

function _formatNumber(lang, value, options) {
  try {
    return new Intl.NumberFormat(lang, options).format(value);
  } catch {
    return String(value);
  }
}

describe('i18n formatNumber', () => {
  it('formats integer with default locale en', () => {
    assert.equal(_formatNumber('en', 1234567), '1,234,567');
  });

  it('formats decimal with locale es', () => {
    const result = _formatNumber('es', 1234567.89);
    assert.match(result, /1\.\d{3}\.\d{3},\d{2}/);
  });

  it('handles NaN gracefully', () => {
    assert.equal(_formatNumber('en', NaN), 'NaN');
  });
});

// --- formatDate ---

function _formatDate(lang, date, options) {
  try {
    const d = date instanceof Date ? date : new Date(date);
    return new Intl.DateTimeFormat(lang, options).format(d);
  } catch {
    return String(date);
  }
}

describe('i18n formatDate', () => {
  it('formats short date in en', () => {
    const d = new Date(2026, 6, 12);
    const result = _formatDate('en', d, { dateStyle: 'short' });
    assert.match(result, /7\/12\/2026|7\/12\/26/);
  });

  it('formats short date in es', () => {
    const d = new Date(2026, 6, 12);
    const result = _formatDate('es', d, { dateStyle: 'short' });
    assert.match(result, /12\/7\/2026|12\/7\/26/);
  });

  it('formats full date in en', () => {
    const d = new Date(2026, 6, 12);
    const result = _formatDate('en', d, { dateStyle: 'full' });
    assert.ok(result.includes('July') || result.includes('Sunday'));
  });
});
