# core/translations.py
# Lightweight translation engine for the Python backend.
# Loads JSON locale files and provides gettext-style `_()` lookups.

import json
import os
import re
import logging
import locale as _locale_mod
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locales")


@lru_cache(maxsize=16)
def _load_translations(lang: str) -> dict:
    """Load locale files from a per-language directory, falling back to English.

    Reads all ``*.json`` files from ``locales/{lang}/`` and merges them.
    Each file should contain one top-level key matching its filename
    (e.g. ``auth.json`` → ``{"auth": ...}``). Simple ``dict.update()``
    is safe because top-level keys are unique namespaces.
    """
    dir_path = os.path.join(LOCALES_DIR, lang)
    if not os.path.isdir(dir_path):
        if lang != "en":
            logger.warning("Locale dir not found for '%s', falling back to 'en'", lang)
            return _load_translations("en")
        logger.warning("Locale directory not found at %s, using empty fallback", dir_path)
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
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to parse locale file %s: %s", fp, e)
    return merged


def _resolve(obj: dict, key: str) -> Optional[str]:
    """Resolve a dot-separated key in a nested dict."""
    parts = key.split(".")
    for p in parts:
        if isinstance(obj, dict) and p in obj:
            obj = obj[p]
        else:
            return None
    if isinstance(obj, str):
        return obj
    return None


def get_translator(lang: str = "en"):
    """Return a `_(key)` callable for the given language.

    Usage::

        from core.translations import get_translator

        _ = get_translator("es")
        detail = _("auth.login_failed")
    """
    locale = _load_translations(lang)
    fallback = _load_translations("en") if lang != "en" else locale

    def _(key: str) -> str:
        val = _resolve(locale, key)
        if val is not None:
            return val
        val = _resolve(fallback, key)
        if val is not None:
            return val
        return key

    return _


# Module-level context: set once per request via middleware.
from contextvars import ContextVar

current_language: ContextVar[str] = ContextVar("current_language", default="en")


def t(key: str) -> str:
    """Translate `key` using the current request's language.

    Intended for use in route handlers after the language middleware
    has run::

        from core.translations import t

        raise HTTPException(404, detail=t("chat.session_not_found"))
    """
    lang = current_language.get()
    translator = get_translator(lang)
    return translator(key)


# --- Pluralisation ---

_PLURAL_SPLIT = re.compile(r"(?<!\\)\|")


def tn(key: str, count: int, **vars) -> str:
    """Translate a pluralised key.

    Locale value uses pipe syntax::

        "items": "{{count}} item|{{count}} items"

    The first segment is singular (count=1), the second is plural (count≠1).

    Additional ``**vars`` are substituted into the chosen form with
    ``.format()`` (single-brace syntax).
    """
    msg = t(key)
    parts = _PLURAL_SPLIT.split(msg)
    form = parts[1] if count != 1 and len(parts) > 1 else parts[0]
    return form.format(count=count, **vars)


# --- Number / date formatting ---


def format_number(value, decimals: int = 0) -> str:
    """Format a number with the current language's grouping and decimal rules."""
    lang = current_language.get()
    lang_to_locale = {"en": "en_US.UTF-8", "es": "es_ES.UTF-8", "fr": "fr_FR.UTF-8",
                      "de": "de_DE.UTF-8", "it": "it_IT.UTF-8",
                      "pt": "pt_BR.UTF-8", "ja": "ja_JP.UTF-8",
                      "zh": "zh_CN.UTF-8", "ko": "ko_KR.UTF-8",
                      "ru": "ru_RU.UTF-8", "ar": "ar_AE.UTF-8"}
    loc = lang_to_locale.get(lang, "en_US.UTF-8")
    try:
        old = _locale_mod.setlocale(_locale_mod.LC_NUMERIC, loc)
        formatted = _locale_mod.format_string(f"%.{decimals}f", value, grouping=True)
        _locale_mod.setlocale(_locale_mod.LC_NUMERIC, old)
        return formatted
    except Exception:
        return f"{value:.{decimals}f}"


def format_date(date, fmt: str = "short") -> str:
    """Format a date using the current language's conventions.

    ``fmt`` is one of ``"short"``, ``"medium"``, ``"long"``, or a custom
    strftime pattern.  When not a known short name the value is passed
    directly to ``strftime``.
    """
    import time as _time
    lang = current_language.get()
    lang_to_locale = {"en": "C", "es": "es_ES.UTF-8", "fr": "fr_FR.UTF-8",
                      "de": "de_DE.UTF-8", "it": "it_IT.UTF-8",
                      "pt": "pt_BR.UTF-8", "ja": "ja_JP.UTF-8",
                      "zh": "zh_CN.UTF-8", "ko": "ko_KR.UTF-8",
                      "ru": "ru_RU.UTF-8", "ar": "ar_AE.UTF-8"}
    patterns = {"short": "%x", "medium": "%x %H:%M", "long": "%c"}
    strf = patterns.get(fmt, fmt)
    loc = lang_to_locale.get(lang, "C")
    try:
        old = _locale_mod.setlocale(_locale_mod.LC_TIME, loc)
        result = date.strftime(strf)
        _locale_mod.setlocale(_locale_mod.LC_TIME, old)
        return result
    except Exception:
        try:
            return date.strftime(strf)
        except Exception:
            return str(date)
