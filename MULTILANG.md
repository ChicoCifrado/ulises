# Multilanguage (i18n) System

Ulises has **two independent translation engines** — one for the Python backend and one for the vanilla-JS frontend. Both use dot-path keys and JSON locale files with the same structure but **different key inventories**.

## Architecture

```
                    ┌──────────────────────┐
                    │   Frontend (JS/HTML)  │
                    │  static/js/i18n.js    │
                    │  static/locales/*.json│
                    └──────┬───────────────┘
                           │ fetch() at runtime
                           │
                    ┌──────▼────────────────┐
                    │  static/locales/es.json│
                    │  static/locales/en.json│  ← 1197 keys
                    └───────────────────────┘

                    ┌──────────────────────┐
                    │   Backend (Python)    │
                    │ core/translations.py  │
                    │ locales/*.json        │
                    └──────┬───────────────┘
                           │ loaded at import
                           │
                    ┌──────▼────────────────┐
                    │  locales/es.json       │
                    │  locales/en.json       │  ← 473 keys (diff set)
                    └───────────────────────┘
```

### Key difference

The frontend loads locale files via `fetch()` at runtime (so you can hot-reload translations). The backend loads them from disk at import time (cached by `@lru_cache`).

Neither engine uses a build step. Zero external dependencies.

## Frontend (`static/js/i18n.js`)

### Initialization

```js
import { init, t, setLanguage, reapply } from '/static/js/i18n.js';
window._t = t;           // expose globally for inline <script> blocks
init();                  // detects browser language, loads locale, applies data-i18n
```

- `static/index.html`: imported indirectly via `static/app.js` (ESM `import`)
- `static/login.html`: imported directly via `<script type="module">`

### Language detection order

1. `localStorage` key `ulises-lang` (set by `setLanguage()`)
2. `navigator.language` (browser language, split on `-` to get base)
3. Fallback: `en`

### Usage in JS

```js
import { t, tn, formatNumber, formatDate } from './js/i18n.js';

t('common.close')                     // → "Close"
t('chat.welcome', { name: 'Alice' })  // → "Welcome, Alice"
tn('items', 1)                        // → "1 item"   (pipe: "{{count}} item|{{count}} items")
tn('items', 5)                        // → "5 items"
formatNumber(1234.5)                  // → "1,234.5"  (locale-aware via Intl)
formatDate(new Date(), { dateStyle: 'full' })
```

### Usage in HTML (`data-i18n` attributes)

Put the translation key in an attribute and `init()` / `reapply()` will fill it in:

```html
<!-- text content -->
<span data-i18n="common.close"></span>

<!-- attributes -->
<input data-i18n-placeholder="common.search">
<div data-i18n-title="common.settings">
<button data-i18n-aria-label="common.close">
```

Supported attributes: `data-i18n`, `data-i18n-placeholder`, `data-i18n-title`, `data-i18n-aria-label`, `data-i18n-value`.

Call `reapply(root)` after dynamically inserting DOM to translate the new elements.

### Interpolation

Use `{{variableName}}` in locale values. Pass an object as the second argument to `t()`:

```json
{ "greeting": "Hello, {{name}}!" }
```

```js
t('greeting', { name: 'World' })  // → "Hello, World!"
```

### Pluralisation (`tn()`)

Locale values use pipe syntax: singular before `|`, plural after:

```json
{ "files": "{{count}} file|{{count}} files" }
```

```js
tn('files', 1)   // → "1 file"
tn('files', 10)  // → "10 files"
```

For languages with complex plural rules (Russian, Arabic), extend the `tn()` function with CLDR plural forms.

### Formatting

Powered by the `Intl` browser API:

```js
formatNumber(1234.5, { style: 'currency', currency: 'EUR' })
formatDate('2025-01-15', { dateStyle: 'long' })
```

## Backend (`core/translations.py`)

### Initialization

Registered as Starlette middleware in `app.py`:

```python
from core.middleware import LanguageMiddleware
app.add_middleware(LanguageMiddleware)
```

### Language detection order

1. `Accept-Language` HTTP header (parsed: lang from first entry, base only)
2. Fallback: `en`
3. TODO: per-user `app_language` setting from `src/settings.py` is stored but middleware doesn't read it yet

The language is stored in a `ContextVar` (`current_language`) so it's request-scoped and thread-safe.

### Usage in Python

```python
from core.translations import t, tn, format_number, format_date

t('auth.login_failed')                         # → "Login failed"
t('document.create_failed', error='timeout')   # → "Failed to create document: timeout"
tn('items', 5)                                 # → "5 items"
format_number(1234.5, 2)                       # → "1,234.50"
format_date(date, 'short')                     # → "01/15/25"
```

**Important:** Python routes never import `get_translator()` directly. Use the module-level `t()` which reads `current_language` automatically.

### Interpolation

Use `{{variableName}}` in locale values. Pass variables as keyword args to `.format()` via `t()` — the engine delegates to Python `str.format()`:

```python
t('greeting', name='World')  # locale value: "Hello, {{name}}!"
```

### Pluralisation (`tn()`)

Same pipe syntax as frontend:

```json
{ "files": "{{count}} file|{{count}} files" }
```

```python
from core.translations import tn
tn('files', 1)    # → "1 file"
tn('files', 10)   # → "10 files"
```

## Locale files

### Frontend: `static/locales/{lang}.json`

Nested JSON structure. Keys use dots to navigate the tree:

```json
{
  "common": {
    "close": "Close",
    "errors": {
      "generic": "Something went wrong"
    }
  },
  "chat": {
    "title": "Ulises Chat",
    "model_picker": {
      "switch": "Switch model"
    }
  }
}
```

### Backend: `locales/{lang}.json`

Also nested JSON, same convention. Different key set focused on API errors / server messages:

```json
{
  "lang_name": "English",
  "lang_native": "English",
  "auth": {
    "login_failed": "Login failed",
    "not_authenticated": "Not authenticated"
  },
  "shell": {
    "admin_only": "Admin only",
    "no_command": "No command provided"
  }
}
```

The top-level metadata keys `lang_name` and `lang_native` are used in the language-picker UI but are not expected in the code scanner (ignored as orphans).

Both locale files are served from `GET /static/locales/{lang}.json` — the backend locale files are **not** exposed to the frontend.

## How to add a new key

### 1. Use the key in code

```python
# Python
raise HTTPException(403, detail=t("admin.user_suspended"))
```

```js
// JavaScript
element.textContent = t('admin.user_suspended')
```

```html
<!-- HTML attribute -->
<span data-i18n="admin.user_suspended"></span>
```

### 2. Add to `en.json`

For the frontend locale (`static/locales/en.json`):

```json
{
  "admin": {
    "user_suspended": "User is suspended",
    ...
  }
}
```

For the backend locale (`locales/en.json`):

```json
{
  "admin.user_suspended": "User is suspended",
  ...
}
```

### 3. Add to `es.json` (and other language files)

Same key path, translated value.

### 4. Verify

```bash
python scripts/check_i18n_keys.py
python -m pytest tests/test_locale_files.py -v
python -m pytest tests/test_translations.py -v
```

### Auto-add missing keys

The quick way to bulk-add missing keys with generated English placeholders:

```bash
python scripts/sync_i18n_keys.py
```

This scans all code for `t()` / `tn()` / `data-i18n` calls, finds keys not in `en.json`, adds them (with a Title-Cased guess as the value), and syncs `es.json`.

Use `--check` to preview without writing:

```bash
python scripts/sync_i18n_keys.py --check
```

## How to add a new language

### 1. Create the locale file

**Frontend:** `static/locales/fr.json` — copy `en.json` and translate all values.

**Backend:** `locales/fr.json` — copy `en.json` and translate all values.

### 2. Register in the backend

Add the locale mapping in `core/translations.py`:

- `format_number()`: add `"fr": "fr_FR.UTF-8"` to the `lang_to_locale` dict (line ~125)
- `format_date()`: same mapping, different dict (line ~149)

### 3. Register in the middleware

Add the language code to the allow-list in `core/middleware.py` line 38:

```python
if lang not in ("en", "es", "fr", ...):
    lang = "en"
```

### 4. Add to frontend language picker

The settings UI in `static/index.html` or JS modules that offer language selection.

### 5. Verify

```bash
python scripts/check_i18n_keys.py
python -m pytest tests/test_locale_files.py -v
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/check_i18n_keys.py` | Scan code for t() calls and compare against locale files. Reports missing (used-but-not-defined), orphaned (defined-but-not-used), and interpolation variable parity. |
| `scripts/sync_i18n_keys.py` | Auto-add missing keys to en.json with generated English values, then sync es.json. |

### check_i18n_keys.py options

```
--json    Machine-readable JSON output (for tooling)
--ci      Exit code 1 if any issues found (for CI pipelines)
```

## Testing

### Locale file integrity

```bash
python -m pytest tests/test_locale_files.py -v
```

Tests: JSON validity for all 4 files, key parity (es has same keys as en), interpolation variable parity (en and es use the same `{{vars}}`).

### Translation engine unit tests

```bash
python -m pytest tests/test_translations.py -v
```

Tests (15): `_load_translations`, `_resolve`, `get_translator`, `t()` with ContextVar isolation.

### JS engine tests (Node)

```bash
node --test static/js/i18n.test.mjs
```

Tests (36): key resolution, interpolation, locale lookups, `tn()` pluralisation, `formatNumber`, `formatDate`, fallback chain.

## Key naming conventions

- **Format:** `namespace.descriptive_name`
- **Namespace** matches the route/feature name: `auth`, `chat`, `document`, `admin`, `cookbook`, `common`, etc.
- **Snake case** for the descriptor: `login_failed`, `session_not_found`
- **Error grouping:** Error-related keys should be nested under `errors`:
  `{"auth": {"errors": {"login_failed": "..."}}}`
- **Prefixes:** Group features with clear prefixes to avoid collisions
- **Orphan keys** (in locale but never in code) usually mean the code path was removed — consider cleaning them up, but some are expected (menu structures, layout labels referenced only in `data-i18n` in `index.html` which is not in the scan paths)

## Architecture notes

- The two engines are **deliberately independent** — a unified engine would couple the backend to the frontend's fetch-based loading.
- Python keys and JS keys may overlap (`auth.login_failed` exists in both locales but with different nesting depth). That's fine — they're resolved in different contexts.
- `static/index.html` is NOT scanned by the checker for data-i18n keys because it's a template file, not in a scan directory. Many orphaned "frontend" keys are actually used in `index.html`.
- The `login.html` page uses `window._t` (exposed via inline `<script>`) and calls `reapply()` when it dynamically creates TOTP form elements.
- CSP nonces prevent inline scripts except on `login.html` (which uses `<script type="module" nonce="{{CSP_NONCE}}">`).
