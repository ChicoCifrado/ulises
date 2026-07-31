"""Route-level tests for GET /api/i18n/{lang}.

Covers the merged-locale payload, the unknown-language fallback, the ETag
revalidation path (304), and the Cache-Control header. Uses a FastAPI +
TestClient like the other route-level suites; skipped cleanly when the
optional deps aren't installed.
"""
import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("starlette.testclient")

from fastapi import FastAPI
from starlette.testclient import TestClient

i18n_routes = pytest.importorskip("routes.i18n_routes")


@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.include_router(i18n_routes.setup_i18n_routes())
    return TestClient(app, raise_server_exceptions=False)


def test_serves_known_language_payload(client):
    r = client.get("/api/i18n/en")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict) and "auth" in body
    assert body["auth"]["username"] == "Username"


def test_serves_spanish_when_available(client):
    r = client.get("/api/i18n/es")
    assert r.status_code == 200
    body = r.json()
    assert body["auth"]["username"] == "Usuario"


def test_unknown_language_falls_back_to_english(client):
    r = client.get("/api/i18n/xx")
    assert r.status_code == 200
    body = r.json()
    assert body["auth"]["username"] == "Username"


def test_response_has_cache_control(client):
    r = client.get("/api/i18n/en")
    assert "max-age" in r.headers.get("cache-control", "")


def test_etag_round_trip(client):
    first = client.get("/api/i18n/en")
    etag = first.headers.get("etag")
    assert etag
    revalidated = client.get(
        "/api/i18n/en", headers={"If-None-Match": etag}
    )
    assert revalidated.status_code == 304
    assert revalidated.headers.get("etag") == etag


def test_languages_endpoint_lists_native_names(client):
    r = client.get("/api/i18n/languages")
    assert r.status_code == 200
    langs = r.json()
    assert isinstance(langs, list) and langs
    by_code = {lang["code"]: lang["native"] for lang in langs}
    assert "en" in by_code
    assert "es" in by_code
    assert by_code["es"] == "Español"
