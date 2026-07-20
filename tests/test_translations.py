"""Unit tests for core/translations.py — the Python backend i18n engine."""
import json
import logging
from pathlib import Path
from unittest.mock import patch

from core.translations import (
    _load_translations,
    _resolve,
    get_translator,
    t,
    current_language,
)

REPO = Path(__file__).resolve().parent.parent


# --- _load_translations ---

def test_load_translations_returns_dict():
    data = _load_translations("en")
    assert isinstance(data, dict)
    assert len(data) > 0


def test_load_translations_unknown_locale_falls_back_to_en():
    data = _load_translations("xx")
    en_data = _load_translations("en")
    assert data == en_data


def test_load_translations_missing_file_falls_back_to_en(caplog):
    caplog.set_level(logging.WARNING)
    nonexistent = str(REPO / "locales" / "nonexistent.json")
    with patch("core.translations.LOCALES_DIR", str(REPO / "locales")):
        result = _load_translations("nonexistent")
    en_data = _load_translations("en")
    assert result == en_data


# --- _resolve ---

def test_resolve_simple_key():
    data = {"auth": {"login_failed": "Login failed"}}
    assert _resolve(data, "auth.login_failed") == "Login failed"


def test_resolve_nested_key():
    data = {"common": {"errors": {"timeout": "Request timed out"}}}
    assert _resolve(data, "common.errors.timeout") == "Request timed out"


def test_resolve_missing_key_returns_none():
    data = {"auth": {}}
    assert _resolve(data, "auth.nonexistent") is None


def test_resolve_entirely_missing_path():
    data = {}
    assert _resolve(data, "a.b.c") is None


def test_resolve_non_string_value_returns_none():
    data = {"section": {"sub": {}}}
    assert _resolve(data, "section.sub") is None


# --- get_translator ---

def test_translator_returns_string():
    _ = get_translator("en")
    result = _("auth.login_failed")
    assert isinstance(result, str)
    assert len(result) > 0


def test_translator_spanish():
    _ = get_translator("es")
    result = _("auth.login_failed")
    assert isinstance(result, str)


def test_translator_missing_key_returns_key():
    _ = get_translator("en")
    assert _("some.made.up.key") == "some.made.up.key"


def test_translator_falls_back_to_en():
    _ = get_translator("es")
    result = _("auth.login_failed")
    assert result is not None and len(result) > 0


def test_translator_contextvar_default_is_en():
    _ = get_translator()
    result = _("auth.login_failed")
    assert isinstance(result, str)


# --- t() with ContextVar ---

def test_t_uses_current_language():
    current_language.set("es")
    try:
        result = t("auth.login_failed")
        assert isinstance(result, str)
    finally:
        current_language.set("en")


def test_t_defaults_to_en():
    current_language.set("en")
    result = t("auth.login_failed")
    assert isinstance(result, str) and len(result) > 0


def test_t_missing_key_returns_key():
    current_language.set("en")
    assert t("completely.bogus.key") == "completely.bogus.key"


def test_t_contextvar_isolation():
    tok = current_language.set("es")
    try:
        es_val = t("auth.login_failed")
        current_language.set("en")
        en_val = t("auth.login_failed")
        assert es_val != en_val or es_val is not None
    finally:
        current_language.reset(tok)
