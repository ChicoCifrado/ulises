#!/usr/bin/env python3
"""Extract all i18n keys from source code and compare against locale files.

Usage:
    python scripts/check_i18n_keys.py            # full check, human-readable
    python scripts/check_i18n_keys.py --json      # machine-readable JSON output
    python scripts/check_i18n_keys.py --ci        # exit 1 on any issue

Checks:
  - Keys used in code but missing from en.json (frontend / backend)
  - Keys in en.json but never used in code (orphaned)
  - Keys in es.json but not in en.json (extra)
  - Interpolation variable parity between en/es
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Directories to scan for t("...") calls
SCAN_DIRS = [
    "routes",
    "src",
    "core",
    "companion",
    "services",
    "static/js",
    "static/editor",
]

# File patterns per directory
FILE_PATTERNS = {
    "routes": "*.py",
    "src": "*.py",
    "core": "*.py",
    "companion": "*.py",
    "services": "*.py",
    "static/js": "*.js",
    "static/editor": "*.js",
}

# Patterns to find translation keys
# Use (?<![a-zA-Z])t instead of \bt to avoid matching e.g. host(, import(, object(
PY_PATTERN = re.compile(r'(?<![a-zA-Z])t\s*\(\s*["\']([^"\']+)["\']')
JS_PATTERN = re.compile(r'(?<![a-zA-Z])t\s*\(\s*["\']([^"\']+)["\']')
HTML_ATTR_PATTERN = re.compile(r'data-i18n(?:-\w+)?\s*=\s*"([^"]+)"')
TN_PATTERN = re.compile(r'(?<![a-zA-Z])tn\s*\(\s*["\']([^"\']+)["\']')


def _leaf_keys(obj, prefix=""):
    """Recursively extract all leaf keys from a nested dict."""
    keys = set()
    for k, v in obj.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, str):
            keys.add(full)
        elif isinstance(v, dict):
            keys |= _leaf_keys(v, full)
    return keys


def _interpolation_vars(value):
    return set(re.findall(r"\{\{(\w+)\}\}", value))


def extract_code_keys():
    """Scan all source files for t('...'), tn('...'), and data-i18n='...'.

    Returns two sets: (python_keys, js_html_keys) so we can validate
    backend keys against Python sources and frontend keys against JS/HTML.
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
            for p in [PY_PATTERN, JS_PATTERN, HTML_ATTR_PATTERN, TN_PATTERN]:
                for m in p.finditer(content):
                    target.add(m.group(1))
    return py_keys, js_html_keys


def _load_locale_dir(dir_path: Path) -> dict:
    """Load all JSON files in a locale directory and merge."""
    merged: dict = {}
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


def check_locale(code_keys, locale_path, label):
    """Compare code keys against a locale directory. Returns list of issue strings."""
    issues = []
    data = _load_locale_dir(locale_path)
    if not data:
        issues.append(f"ERROR: Cannot load locale from {locale_path}")
        return issues

    locale_keys = _leaf_keys(data)

    # Keys in code but not in locale (missing)
    missing = code_keys - locale_keys
    for k in sorted(missing):
        issues.append(f"MISSING {label}: key '{k}' used in code, not in {locale_path.name}")

    # Keys in locale but not in code (orphaned)
    orphaned = locale_keys - code_keys
    # Filter out internal keys not expected in code (lang_name, lang_native)
    non_code_prefixes = ("lang_name", "lang_native")
    for k in sorted(orphaned):
        if k.startswith(non_code_prefixes):
            continue
        issues.append(f"ORPHANED {label}: key '{k}' in {locale_path.name} but never used in code")

    return issues


def check_interpolation_parity(en_path, es_path, label):
    """Check that interpolation variables match between en and es."""
    issues = []
    en = _load_locale_dir(en_path)
    es = _load_locale_dir(es_path)
    if not en or not es:
        issues.append(f"ERROR: Cannot load locale pair: {en_path}, {es_path}")
        return issues

    def _leaf_pairs(obj, prefix=""):
        pairs = []
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            if isinstance(v, str):
                pairs.append((full, v))
            elif isinstance(v, dict):
                pairs.extend(_leaf_pairs(v, full))
        return pairs

    def _resolve_dot(obj, key):
        parts = key.split(".")
        for p in parts:
            if isinstance(obj, dict) and p in obj:
                obj = obj[p]
            else:
                return None
        return obj if isinstance(obj, str) else None

    en_pairs = _leaf_pairs(en)
    for key, en_val in en_pairs:
        es_val = _resolve_dot(es, key)
        if es_val is None:
            continue
        en_vars = _interpolation_vars(en_val)
        es_vars = _interpolation_vars(es_val)
        missing = en_vars - es_vars
        extra = es_vars - en_vars
        if missing:
            issues.append(
                f"PARITY {label}: key '{key}' missing vars in es: {sorted(missing)}"
            )
        if extra:
            issues.append(
                f"PARITY {label}: key '{key}' extra vars in es: {sorted(extra)}"
            )
    return issues


def format_report(issues, label):
    if not issues:
        return f"  ✅ {label}: no issues"
    lines = [f"  ❌ {label}: {len(issues)} issue(s)"]
    for issue in issues[:20]:
        lines.append(f"    {issue}")
    if len(issues) > 20:
        lines.append(f"    ... and {len(issues) - 20} more")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Check i18n key coverage")
    parser.add_argument("--ci", action="store_true", help="Exit with code 1 on issues")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    py_keys, js_html_keys = extract_code_keys()
    all_issues = []

    # Frontend check: JS/HTML keys against static/locales/en/
    fe_en = REPO / "static" / "locales" / "en"
    fe_es = REPO / "static" / "locales" / "es"
    fe_issues = check_locale(js_html_keys, fe_en, "FE")
    fe_en_data = _load_locale_dir(fe_en)
    fe_es_data = _load_locale_dir(fe_es)
    es_key_count = len(_leaf_keys(fe_es_data))
    en_key_count = len(_leaf_keys(fe_en_data))
    all_issues.extend(fe_issues)
    all_issues.extend(check_interpolation_parity(fe_en, fe_es, "FE"))

    # Backend check: Python keys against locales/en/
    be_en = REPO / "locales" / "en"
    be_es = REPO / "locales" / "es"
    be_issues = check_locale(py_keys, be_en, "BE")
    all_issues.extend(be_issues)
    all_issues.extend(check_interpolation_parity(be_en, be_es, "BE"))

    # Summary
    total_issues = len(all_issues)

    if args.json:
        be_en_data = _load_locale_dir(be_en)
        be_es_data = _load_locale_dir(be_es)
        print(json.dumps({
            "python_code_keys": len(py_keys),
            "js_html_code_keys": len(js_html_keys),
            "frontend_en_keys": en_key_count,
            "frontend_es_keys": es_key_count,
            "backend_en_keys": len(_leaf_keys(be_en_data)),
            "backend_es_keys": len(_leaf_keys(be_es_data)),
            "issues": total_issues,
            "details": all_issues,
        }, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"i18n Key Coverage Report")
        print(f"{'='*60}")
        print(f"\nPython code keys:    {len(py_keys)}")
        print(f"JS/HTML code keys:   {len(js_html_keys)}")
        print(f"Frontend en keys:    {en_key_count}")
        print(f"Frontend es keys:    {es_key_count}")
        be_en_data = _load_locale_dir(be_en)
        be_es_data = _load_locale_dir(be_es)
        print(f"Backend en keys:     {len(_leaf_keys(be_en_data))}")
        print(f"Backend es keys:     {len(_leaf_keys(be_es_data))}")
        print()

        if fe_issues:
            print(format_report(fe_issues, "Frontend"))
            print()
        else:
            print("  ✅ Frontend: no issues")
            print()

        if be_issues:
            print(format_report(be_issues, "Backend"))
            print()
        else:
            print("  ✅ Backend: no issues")
            print()

        # Count missing vs orphaned
        missing_count = sum(1 for i in all_issues if i.startswith("MISSING"))
        orphaned_count = sum(1 for i in all_issues if i.startswith("ORPHANED"))
        parity_count = sum(1 for i in all_issues if i.startswith("PARITY"))

        print(f"\nSummary: {total_issues} total issues "
              f"({missing_count} missing, {orphaned_count} orphaned, {parity_count} parity)")
        if total_issues == 0:
            print("🎉 All keys in sync!")

    if args.ci and total_issues > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
