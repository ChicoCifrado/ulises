#!/usr/bin/env python3
"""One-shot migration: split monolithic locale JSON files into per-namespace files.

Reads locales/{lang}.json (backend) and static/locales/{lang}.json (frontend),
writes locales/{lang}/{namespace}.json and static/locales/{lang}/{namespace}.json,
then deletes the old monolithic files.
"""

import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def split_locale(mono_path: Path, out_dir: Path) -> int:
    """Split a monolithic locale file into per-namespace files.

    Returns the number of namespace files written.
    """
    with open(mono_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for namespace, values in sorted(data.items()):
        ns_file = out_dir / f"{namespace}.json"
        with open(ns_file, "w", encoding="utf-8") as f:
            json.dump({namespace: values}, f, indent=2, ensure_ascii=False)
            f.write("\n")
        count += 1
    return count


def main():
    pairs = [
        ("Backend EN", REPO / "locales" / "en.json", REPO / "locales" / "en"),
        ("Backend ES", REPO / "locales" / "es.json", REPO / "locales" / "es"),
        ("Frontend EN", REPO / "static" / "locales" / "en.json", REPO / "static" / "locales" / "en"),
        ("Frontend ES", REPO / "static" / "locales" / "es.json", REPO / "static" / "locales" / "es"),
    ]

    for label, mono, out_dir in pairs:
        if not mono.exists():
            print(f"SKIP {label}: {mono} not found")
            continue
        print(f"Splitting {label}: {mono} -> {out_dir}/")
        if out_dir.exists():
            shutil.rmtree(out_dir)
        count = split_locale(mono, out_dir)
        mono.unlink()
        print(f"  Wrote {count} namespace files, removed {mono.name}")

    print("\nDone. All locale files migrated to per-namespace directories.")


if __name__ == "__main__":
    main()
