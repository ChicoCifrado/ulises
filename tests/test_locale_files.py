import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

FRONTEND_LOCALES = {
    "en": REPO / "static" / "locales" / "en",
    "es": REPO / "static" / "locales" / "es",
}
BACKEND_LOCALES = {
    "en": REPO / "locales" / "en",
    "es": REPO / "locales" / "es",
}


def _load_dir(dir_path: Path) -> dict:
    """Load all JSON files in a locale directory and merge."""
    merged: dict = {}
    if not dir_path.is_dir():
        return merged
    for fname in sorted(dir_path.iterdir()):
        if not fname.name.endswith(".json"):
            continue
        with open(fname, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            merged.update(data)
    return merged


def _leaf_keys(obj: dict, prefix: str = "") -> set:
    keys = set()
    for k, v in obj.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, str):
            keys.add(full)
        elif isinstance(v, dict):
            keys |= _leaf_keys(v, full)
    return keys


def _interpolation_vars(value: str) -> set:
    import re
    return set(re.findall(r"\{\{(\w+)\}\}", value))


# --- JSON validity ---

def test_frontend_en_json_valid():
    _load_dir(FRONTEND_LOCALES["en"])


def test_frontend_es_json_valid():
    _load_dir(FRONTEND_LOCALES["es"])


def test_backend_en_json_valid():
    _load_dir(BACKEND_LOCALES["en"])


def test_backend_es_json_valid():
    _load_dir(BACKEND_LOCALES["es"])


# --- Key parity ---

def test_frontend_es_has_all_en_keys():
    en = _leaf_keys(_load_dir(FRONTEND_LOCALES["en"]))
    es = _leaf_keys(_load_dir(FRONTEND_LOCALES["es"]))
    missing = en - es
    assert not missing, f"{len(missing)} keys missing from static/locales/es/:\n  " + "\n  ".join(sorted(missing))


def test_frontend_no_extra_keys_in_es():
    en = _leaf_keys(_load_dir(FRONTEND_LOCALES["en"]))
    es = _leaf_keys(_load_dir(FRONTEND_LOCALES["es"]))
    extra = es - en
    assert not extra, f"{len(extra)} extra keys in static/locales/es/:\n  " + "\n  ".join(sorted(extra))


def test_backend_es_has_all_en_keys():
    en = _leaf_keys(_load_dir(BACKEND_LOCALES["en"]))
    es = _leaf_keys(_load_dir(BACKEND_LOCALES["es"]))
    missing = en - es
    assert not missing, f"{len(missing)} keys missing from locales/es/:\n  " + "\n  ".join(sorted(missing))


def test_backend_no_extra_keys_in_es():
    en = _leaf_keys(_load_dir(BACKEND_LOCALES["en"]))
    es = _leaf_keys(_load_dir(BACKEND_LOCALES["es"]))
    extra = es - en
    assert not extra, f"{len(extra)} extra keys in locales/es/:\n  " + "\n  ".join(sorted(extra))


# --- Interpolation variable parity ---

def _leaf_values(obj: dict, prefix: str = "") -> list:
    pairs = []
    for k, v in obj.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, str):
            pairs.append((full, v))
        elif isinstance(v, dict):
            pairs.extend(_leaf_values(v, full))
    return pairs


def _check_interpolation_parity(en_path: Path, es_path: Path, label: str):
    en_pairs = _leaf_values(_load_dir(en_path))
    es_data = _load_dir(es_path)
    for key, en_val in en_pairs:
        es_val = _resolve_dot(es_data, key)
        if es_val is None:
            continue
        en_vars = _interpolation_vars(en_val)
        es_vars = _interpolation_vars(es_val)
        missing_in_es = en_vars - es_vars
        extra_in_es = es_vars - en_vars
        msg_parts = []
        if missing_in_es:
            msg_parts.append(f"missing in es: {sorted(missing_in_es)}")
        if extra_in_es:
            msg_parts.append(f"extra in es: {sorted(extra_in_es)}")
        if msg_parts:
            raise AssertionError(
                f"Interpolation mismatch in {label} key '{key}': "
                f"en='{en_val}' es='{es_val}' — " + "; ".join(msg_parts)
            )


def _resolve_dot(obj: dict, key: str):
    parts = key.split(".")
    for p in parts:
        if isinstance(obj, dict) and p in obj:
            obj = obj[p]
        else:
            return None
    if isinstance(obj, str):
        return obj
    return None


def test_frontend_interpolation_vars_match():
    _check_interpolation_parity(FRONTEND_LOCALES["en"], FRONTEND_LOCALES["es"], "frontend")


def test_backend_interpolation_vars_match():
    _check_interpolation_parity(BACKEND_LOCALES["en"], BACKEND_LOCALES["es"], "backend")
