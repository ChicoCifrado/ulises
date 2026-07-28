"""i18n API — serves merged locale JSON for the frontend."""
import json
import os

from fastapi import APIRouter
from starlette.responses import JSONResponse

FRONTEND_LOCALES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "static", "locales"
)


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


def setup_i18n_routes() -> APIRouter:
    router = APIRouter()

    @router.get("/api/i18n/{lang}")
    async def serve_i18n(lang: str):
        merged = _load_frontend_translations(lang)
        return JSONResponse(merged)

    return router
