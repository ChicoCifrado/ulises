# Translation / i18n Migration TODO

## Architecture

```
Frontend:  static/js/i18n.js      →  static/locales/{lang}.json
Backend:   core/translations.py   →  locales/{lang}.json
           (from core.translations import t)
```

## ALL DONE ✅

### Infrastructure ✅
- [x] `static/js/i18n.js` — frontend translation engine
- [x] `static/locales/en.json` — 1192 frontend source strings
- [x] `static/locales/es.json` — full Spanish translation (1192 keys)
- [x] `core/translations.py` — Python `t()` with ContextVar, `lru_cache`
- [x] `locales/en.json` — 468 backend source strings
- [x] `locales/es.json` — full Spanish backend translation (468 keys)
- [x] `core/middleware.py` — `LanguageMiddleware` (Accept-Language → ContextVar)
- [x] `app.py` — middleware registered, `i18n.init()` on boot
- [x] `src/settings.py` — `"app_language"` in defaults + per-user keys
- [x] `static/index.html` — 738 data-i18n attributes
- [x] `static/login.html` — data-i18n + module script + inline `window._t()`
- [x] `static/js/settings.js` — language selector init + `initLanguageSettings()`
- [x] `static/app.js` — i18n import + init + global reapply
- [x] `static/js/ui.js` — showToast wrapped with `t()`
- [x] `static/js/chat.js` — chat toasts wrapped with `t()`
- [x] Login page inline script — dynamic strings use `_t('key', 'fallback')`

### Python Routes — All ~45 files ✅
- [x] `routes/gallery_routes.py`, `routes/document_routes.py`, `routes/auth_routes.py`
- [x] `routes/task_routes.py`, `routes/codex_routes.py`, `routes/session_routes.py`
- [x] `routes/research_routes.py`, `routes/calendar_routes.py`, `routes/skills_routes.py`
- [x] `routes/history_routes.py`, `routes/upload_routes.py`, `routes/note_routes.py`
- [x] `routes/webhook_routes.py`, `routes/chat_routes.py`, `routes/embedding_routes.py`
- [x] `routes/mcp_routes.py`, `routes/memory_routes.py`, `routes/model_routes.py`
- [x] `routes/signature_routes.py`, `routes/assistant_routes.py`, `routes/personal_routes.py`
- [x] `routes/compare_routes.py`, `routes/shell_routes.py`, `routes/api_token_routes.py`
- [x] `routes/editor_draft_routes.py`, `routes/email_helpers.py`, `routes/tts_routes.py`
- [x] `routes/cookbook_routes.py`, `routes/stt_routes.py`, `routes/copilot_routes.py`
- [x] `routes/chat_helpers.py`, `routes/_validators.py`, `routes/cookbook_helpers.py`
- [x] `routes/admin_wipe_routes.py`, `routes/backup_routes.py`, `routes/cleanup_routes.py`
- [x] `routes/diagnostics_routes.py`, `routes/workspace_routes.py`
- [x] `routes/contacts_routes.py`, `routes/hwfit_routes.py`, `routes/preset_routes.py`
- [x] `routes/chatgpt_subscription_routes.py`, `routes/device_flow.py`

### Python `src/` files ✅
- [x] `src/chat_helpers.py`, `src/llm_core.py`, `src/upload_handler.py`
- [x] `src/auth_helpers.py`, `src/integrations.py`, `src/generated_images.py`
- [x] `src/chat_handler.py`, `src/rate_limiter.py`, `src/upload_limits.py`

### Other Python ✅
- [x] `app.py` — 7 strings wrapped
- [x] `core/middleware.py` — 3 strings wrapped
- [x] `companion/routes.py` — HTML + strings wrapped

### JavaScript Modules — All 50+ files ✅
- [x] `document.js`, `notes.js`, `documentLibrary.js`, `gallery.js`, `galleryEditor.js`
- [x] `cookbook.js`, `cookbookRunning.js`, `cookbookServe.js`, `cookbookDownload.js`, `cookbookSchedule.js`, `cookbook-hwfit.js`
- [x] `emailLibrary.js`, `emailInbox.js`
- [x] `tasks.js`, `calendar.js`, `admin.js`, `settings.js`, `chat.js`
- [x] `memory.js`, `sessions.js`, `skills.js`, `ui.js`
- [x] `voiceRecorder.js`, `presets.js`, `chatRenderer.js`, `assistant.js`
- [x] `group.js`, `codeRunner.js`, `modelPicker.js`, `workspace.js`, `fileHandler.js`
- [x] `editor/ai-inpaint.js`, `editor/ai-tool-runner.js`, `editor/clipboard-and-drop.js`
- [x] `editor/keyboard-shortcuts.js`, `editor/layer-panel.js`, `editor/wire-import.js`
- [x] `editor/wire-inpaint-controls.js`, `editor/wire-merge-buttons.js`
- [x] `editor/wire-selection-controls.js`, `editor/wire-topbar.js`, `editor/wire-topbar-menus.js`
- [x] `editor/ai-tools-misc.js`
- [x] `compare/index.js`, `compare/panes.js`, `compare/probe.js`, `compare/selector.js`, `compare/stream.js`
- [x] `calendar/reminders.js`
- [x] `keyboard-shortcuts.js`, `markdown.js`, `models.js`, `research/panel.js`, `theme.js`
- [x] `rag.js`, `signature.js`

### Embedded HTML in Python Routes ✅
- [x] `routes/mcp_routes.py` — 29 strings wrapped in OAuth HTML pages
- [x] `companion/routes.py` — 5 strings wrapped in pairing HTML
- [x] `routes/session_routes.py` — 3 strings wrapped in export template
- [x] `routes/email_routes.py` — 108 strings wrapped (email headers + errors)

### Locale Key Validation ✅
- [x] Frontend: 1192 keys in en.json = 1192 keys in es.json (0 missing, 0 extra)
- [x] Backend: 468 keys in en.json = 468 keys in es.json (0 missing, 0 extra)
