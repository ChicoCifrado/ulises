# Ulises — AI Agent Guide

## Stack
Python 3.10+ · FastAPI · SQLAlchemy 2.0+ (SQLite) · ChromaDB · vanilla ES6 modules

## Layout
| Directory | Purpose |
|-----------|---------|
| `routes/` | FastAPI route handlers (one per domain) |
| `src/` | Business logic (LLM, RAG, search, tools, memory) |
| `core/` | Shared abstractions (db, auth, middleware, models) |
| `services/` | Subsystems (memory, search, research, TTS, STT, shell) |
| `static/js/` | Frontend ES6 modules (~90 files, no build step) |
| `tests/` | pytest tests (~600 files, asyncio_mode=auto) |

## Conventions
- **snake_case** for Python identifiers, **kebab-case** for URL paths
- Route modules export `setup_*_routes(...)` factory returning `APIRouter`
- Auth guard: `require_admin(request)` from `core/middleware`
- i18n: `t("namespace.key")` in Python, `t('namespace.key')` in JS
- Error responses: `{"error": "CODE", "message": "..."}` or `HTTPException`

## Run
```bash
python -m uvicorn app:app --host 127.0.0.1 --port 7000
```

## Test
```bash
python -m pytest tests/ -v -x
```

## i18n
See [MULTILANG.md](MULTILANG.md) for the multilanguage system.

## Work State

### Objective
Get CI green across all test suites and Docker build for the Ulises project.

### Known Issues
- **CI test failures**: 61 failures after committed fixes (down from 93). Clusters around workspace confinement, web_fetch size caps, locale-loading edge cases. Most recent commits fixed Docker build and glob/grep escape handling; need a CI run to confirm current count.

### Completed
- `{{var}}` → `{var}` in both locale files for Python `.format()` compat.
- Added `cookbook.diagnosis.*` (21 keys) + `invalid_remote_host` to both locales.
- Fixed validator namespace (`validation.*` → `validators.*`).
- Registered `ADMIN_TOOL_HANDLERS` in `TOOL_HANDLERS`.
- Fixed `_active_document_relevant` NameError in `src/agent_loop.py`.
- Standardised file-too-large error messages across chat_helpers, upload_handler, upload_limits.
- Added `start_time`/`end_time` to calendar alias list; `query_raw` partial-range rejection.
- `read_byte_limit_env` falls back to legacy `ODYSSEUS_*` vars.
- Restored `vet_workspace()` in `src/tool_execution.py`.
- Updated test paths for memory_routes shim; fixed upload-limits assertion.
- `WebFetchTool.execute` prepends `[partial content: ...]` when `result.truncated`.
- Webhook tests assert `X-Ulises-Event` (not `X-Odysseus-Event`).
- Workspace confinement: grep/glob/ls tools receive `workspace` in ctx.
- Locale files split from 4 monolithic JSONs into per-namespace directories.
- `core/translations.py` loads from directory using `dict.update()`.
- `GET /api/i18n/{lang}` endpoint; `static/js/i18n.js` fetches from API.
- `./i18n.js` import stubbed in markdown JS test harnesses.
- `GlobTool._glob` wraps `p.relative_to(base)` in `try/except ValueError` → `continue`.
- `WebFetchTool.execute` parses `full` param and passes `max_bytes=WEB_FETCH_HARD_MAX_BYTES`.
- `numpy<2.0.0` → `numpy<3.0.0` in requirements.txt; `chromadb-client<1.0.0` → `<2.0.0` so Docker build resolves on Python 3.13.
- `str | None` → `Optional[str]` in `core/translations.py:48` for Python 3.9 compat.
- `GlobTool`: fall back to workspace root (instead of error) when `_resolve_search_root` rejects escaping paths; catch `NotImplementedError` from `rglob` with absolute patterns → treat as no match.
- `GrepTool`: reverted to returning `exit_code: 1` for out-of-workspace paths (consistent with `LsTool`; test expects explicit error for grep/ls, but silent no-match for glob).
- `bytes | str` → `Union[bytes, str]` in `src/llm_core.py` (two function signatures) for Python 3.9 compat; unblocks test collection blocked when conftest.py → core.models → src.llm_core.
