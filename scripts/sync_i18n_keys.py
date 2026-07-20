#!/usr/bin/env python3
"""Auto-add missing i18n keys to locale files and sync locale pairs.

Usage:
    python scripts/sync_i18n_keys.py           # add missing keys, sync es
    python scripts/sync_i18n_keys.py --check   # only show what would change
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Directories to scan
SCAN_DIRS = ["routes", "src", "core", "companion", "services", "static/js", "static/editor"]

FILE_PATTERNS = {d: "*.py" if d in ("routes", "src", "core", "companion", "services") else "*.js" for d in SCAN_DIRS}

# Patterns to find translation keys
T_PATTERN = re.compile(r'(?<![a-zA-Z])t\s*\(\s*["\']([^"\']+)["\']')
HTML_ATTR_PATTERN = re.compile(r'data-i18n(?:-\w+)?\s*=\s*"([^"]+)"')
TN_PATTERN = re.compile(r'(?<![a-zA-Z])tn\s*\(\s*["\']([^"\']+)["\']')

def extract_code_keys():
    """Scan source files for t('...'), tn('...'), data-i18n='...'.
    Returns (py_keys, js_html_keys).
    """
    py_keys = set()
    js_html_keys = set()
    for dirname in SCAN_DIRS:
        dirpath = REPO / dirname
        if not dirpath.exists():
            continue
        pattern = FILE_PATTERNS.get(dirname, "*.*")
        is_python = pattern.endswith(".py")
        for path in sorted(dirpath.rglob(pattern)):
            if "node_modules" in str(path) or ".test." in path.name:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue
            target = py_keys if is_python else js_html_keys
            for p in [T_PATTERN, HTML_ATTR_PATTERN, TN_PATTERN]:
                for m in p.finditer(content):
                    target.add(m.group(1))
    return py_keys, js_html_keys


def generate_value(key):
    """Generate a readable English value from a dot-key."""
    last = key.split(".")[-1]
    # Convert snake_case to Title Case
    return last.replace("_", " ").title()


def deep_set(d, key_parts, value):
    """Set a value in a nested dict, creating intermediate dicts as needed."""
    for part in key_parts[:-1]:
        if part not in d:
            d[part] = {}
        elif not isinstance(d[part], dict):
            # Key collision: existing value is a string, can't nest further
            # Remove the string and create a dict
            d[part] = {}
        d = d[part]
    d[key_parts[-1]] = value


def _load_locale_dir(dir_path):
    """Load all JSON files in a locale directory and merge."""
    merged = {}
    if not dir_path.is_dir():
        return merged
    for fname in sorted(dir_path.iterdir()):
        if not fname.name.endswith(".json"):
            continue
        try:
            data = json.loads(fname.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                merged.update(data)
        except (OSError, json.JSONDecodeError):
            pass
    return merged


def _write_locale_dir(dir_path, data):
    """Write a merged locale dict back into per-namespace files."""
    dir_path.mkdir(parents=True, exist_ok=True)
    for fname in list(dir_path.iterdir()):
        if fname.name.endswith(".json"):
            fname.unlink()
    for namespace in sorted(data):
        ns_file = dir_path / f"{namespace}.json"
        with open(ns_file, "w", encoding="utf-8") as f:
            json.dump({namespace: data[namespace]}, f, indent=2, ensure_ascii=False)
            f.write("\n")


def add_keys_to_nested(locale, keys):
    """Add dot-notation keys to a nested locale dict."""
    added = []
    for key in sorted(keys):
        parts = key.split(".")
        # Navigate: we need to put the value at the leaf
        # Check if the intermediate path exists and is a string (collision)
        d = locale
        collision = False
        for part in parts[:-1]:
            if part in d and isinstance(d[part], str):
                collision = True
                break
            if part not in d:
                d[part] = {}
            d = d[part]
        if collision:
            print(f"  SKIP {key} — path collision in nested locale")
            continue
        if parts[-1] in d:
            continue  # already exists
        val = generate_value(key)
        d[parts[-1]] = val
        added.append(key)
    return added


def add_keys_to_flat(locale, keys):
    """Add dot-notation keys to a flat (single-level) locale dict."""
    added = []
    for key in sorted(keys):
        if key in locale:
            continue
        val = generate_value(key)
        locale[key] = val
        added.append(key)
    return added


def sync_locale_pair(en_path, es_path):
    """Sync es locale to match en keys and interpolation vars."""
    en = _load_locale_dir(en_path)
    es = _load_locale_dir(es_path)

    is_nested = isinstance(next(iter(en.values())), (dict, str)) and not isinstance(next(iter(en.values())), str)

    def leaf_pairs(obj, prefix=""):
        pairs = []
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            if isinstance(v, str):
                pairs.append((full, v))
            elif isinstance(v, dict):
                pairs.extend(leaf_pairs(v, full))
        return pairs

    def resolve(obj, key):
        parts = key.split(".")
        for p in parts:
            if isinstance(obj, dict) and p in obj:
                obj = obj[p]
            else:
                return None
        return obj if isinstance(obj, str) else None

    def set_nested(obj, key, value):
        parts = key.split(".")
        for p in parts[:-1]:
            if p not in obj:
                obj[p] = {}
            obj = obj[p]
        if parts[-1] not in obj:
            obj[parts[-1]] = value
        return obj[parts[-1]]

    def set_flat(obj, key, value):
        if key not in obj:
            obj[key] = value

    setter = set_nested if is_nested else set_flat

    changed = 0
    for en_key, en_val in leaf_pairs(en):
        es_val = resolve(es, en_key)
        if es_val is None:
            # Add missing key to es
            setter(es, en_key, en_val)
            changed += 1
        else:
            # Check interpolation vars
            en_vars = set(re.findall(r"\{\{(\w+)\}\}", en_val))
            es_vars = set(re.findall(r"\{\{(\w+)\}\}", es_val))
            if en_vars != es_vars:
                # Update es to match en's interpolation pattern
                resolve(es, en_key)  # confirm it exists
                parts = en_key.split(".")
                d = es
                for p in parts[:-1]:
                    d = d[p]
                d[parts[-1]] = en_val
                changed += 1

    _write_locale_dir(es_path, es)
    return changed


def main():
    parser = argparse.ArgumentParser(description="Add missing i18n keys and sync locale pairs")
    parser.add_argument("--check", action="store_true", help="Only show what would change, don't modify files")
    args = parser.parse_args()

    py_keys, js_html_keys = extract_code_keys()
    print(f"Python code keys: {len(py_keys)}")
    print(f"JS/HTML code keys: {len(js_html_keys)}")

    # Frontend locale (nested JSON)
    fe_en_path = REPO / "static" / "locales" / "en"
    fe_es_path = REPO / "static" / "locales" / "es"
    fe_en = _load_locale_dir(fe_en_path)

    # Compute missing FE keys
    def leaf_keys(obj, prefix=""):
        keys = set()
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            if isinstance(v, str):
                keys.add(full)
            elif isinstance(v, dict):
                keys |= leaf_keys(v, full)
        return keys

    fe_existing = leaf_keys(fe_en)
    fe_missing = js_html_keys - fe_existing
    print(f"\nFrontend missing keys: {len(fe_missing)}")

    if not args.check and fe_missing:
        added = add_keys_to_nested(fe_en, fe_missing)
        _write_locale_dir(fe_en_path, fe_en)
        print(f"  Added {len(added)} keys to {fe_en_path}")

    # Backend locale (flat JSON)
    be_en_path = REPO / "locales" / "en"
    be_es_path = REPO / "locales" / "es"
    be_en = _load_locale_dir(be_en_path)

    be_existing = set(be_en.keys())
    be_missing = py_keys - be_existing
    print(f"\nBackend missing keys: {len(be_missing)}")
    # Filter out keys that already exist as nested in backend (shouldn't happen but just in case)
    be_keys_from_code = set()
    for k in py_keys:
        if '.' not in k:
            continue  # keys must have dots for backend
        be_keys_from_code.add(k)

    if not args.check and be_missing:
        added = add_keys_to_flat(be_en, be_missing)
        _write_locale_dir(be_en_path, be_en)
        print(f"  Added {len(added)} keys to {be_en_path}")

    # Sync es files
    print(f"\nSyncing es locale files...")
    fe_changed = sync_locale_pair(fe_en_path, fe_es_path)
    be_changed = sync_locale_pair(be_en_path, be_es_path)
    print(f"  Frontend es/: {fe_changed} changes")
    print(f"  Backend es/: {be_changed} changes")

    print("\nDone!")


if __name__ == "__main__":
    main()
