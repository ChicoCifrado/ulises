"""i18n API — serves merged locale JSON for the frontend.

The locale files under ``static/locales/{lang}/`` are read at request time but
never change while the process runs, so the merged dicts are cached in memory
(keyed by lang) and responses carry ``Cache-Control``/``ETag`` headers. The
browser can then cache the locale payload and revalidate cheaply, which matters
on every page load because the frontend fetches ``/api/i18n/{lang}`` in each
session.
"""
import hashlib
import json
import os
from typing import Dict, Tuple

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse, Response

FRONTEND_LOCALES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "static", "locales"
)

# In-memory cache: lang -> (etag, merged_dict). Locale files are static for
# the lifetime of the process, so this never goes stale.
_CACHE: Dict[str, Tuple[str, dict]] = {}


def _load_frontend_translations(lang: str) -> dict:
    """Load frontend locale files from ``static/locales/{lang}/`` and merge them."""
    dir_path = os.path.join(FRONTEND_LOCALES_DIR, lang)
    if not os.path.isdir(dir_path):
        dir_path = os.path.join(FRONTEND_LOCALES_DIR, "en")
    if not os.path.isdir(dir_path):
        return {}
    merged: dict = {}
    for fname in sorted(os.listdir(dir_path)):
        if not fname.endswith(".json"):
            continue
        fp = os.path.join(dir_path, fname)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                merged.update(data)
        except (OSError, json.JSONDecodeError):
            pass
    return merged


def _cached_translations(lang: str) -> Tuple[str, dict]:
    """Return (etag, merged_dict) for ``lang``, computing once per process."""
    cached = _CACHE.get(lang)
    if cached is not None:
        return cached
    merged = _load_frontend_translations(lang)
    body = json.dumps(merged, ensure_ascii=False, sort_keys=True)
    etag = '"%s"' % hashlib.sha1(body.encode("utf-8")).hexdigest()[:16]
    cached = (etag, merged)
    _CACHE[lang] = cached
    return cached


def _available_languages() -> list:
    """List of {"code", "native"} for every language dir in static/locales/.

    The native name comes from each dir's ``lang_native.json`` (e.g. es ->
    "Español"); without one, the code itself is used as the label. This keeps
    the settings language selector data-driven: adding a new locale directory
    is enough to surface it in the UI.
    """
    if not os.path.isdir(FRONTEND_LOCALES_DIR):
        return []
    langs = []
    for name in sorted(os.listdir(FRONTEND_LOCALES_DIR)):
        dir_path = os.path.join(FRONTEND_LOCALES_DIR, name)
        if not os.path.isdir(dir_path):
            continue
        native = name
        native_fp = os.path.join(dir_path, "lang_native.json")
        try:
            with open(native_fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("lang_native"):
                native = data["lang_native"]
        except (OSError, json.JSONDecodeError):
            pass
        langs.append({"code": name, "native": native})
    return langs


def setup_i18n_routes() -> APIRouter:
    router = APIRouter()

    @router.get("/api/i18n/languages")
    async def list_languages():
        return JSONResponse(_available_languages())

    @router.get("/api/i18n/{lang}")
    async def serve_i18n(lang: str, request: Request):
        etag, merged = _cached_translations(lang)
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and etag in if_none_match:
            return Response(status_code=304, headers={"ETag": etag})
        return JSONResponse(
            merged,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=3600",
            },
        )

    return router
