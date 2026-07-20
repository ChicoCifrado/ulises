"""i18n API — serves merged locale JSON for the frontend."""
from fastapi import APIRouter
from starlette.responses import JSONResponse

from core.translations import _load_translations


def setup_i18n_routes() -> APIRouter:
    router = APIRouter()

    @router.get("/api/i18n/{lang}")
    async def serve_i18n(lang: str):
        merged = _load_translations(lang)
        return JSONResponse(merged)

    return router
