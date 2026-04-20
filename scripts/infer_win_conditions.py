#!/usr/bin/env python3
"""Infer win_condition_tags conservatively from kit_tags + archetypes.

Default mode is preview-only so we don't trample hand-curated data.

Usage:
    python3 scripts/infer_win_conditions.py
    python3 scripts/infer_win_conditions.py --champion jinx
    python3 scripts/infer_win_conditions.py --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fivefold.loader import load_archetypes, load_champions  # noqa: E402
from fivefold.win_conditions import infer_win_condition_tags  # noqa: E402

DATA_FILE = ROOT / "data" / "champions.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write inferred tags into champions.json.")
    parser.add_argument("--champion", help="Limit output to one champion id.")
    args = parser.parse_args()

    raw = json.loads(DATA_FILE.read_text())
    champions_raw = raw["champions"]
    champions = load_champions(DATA_FILE)
    archetypes = load_archetypes()

    updated = 0
    preview_rows: list[tuple[str, list[str]]] = []

    for entry in champions_raw:
        cid = entry["id"]
        if args.champion and cid != args.champion:
            continue
        if entry.get("win_condition_tags"):
            continue
        inferred = infer_win_condition_tags(champions[cid], archetypes)
        if not inferred:
            continue
        preview_rows.append((cid, inferred))
        if args.apply:
            entry["win_condition_tags"] = inferred
            updated += 1

    if args.apply:
        DATA_FILE.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
        print(f"Applied inferred win_condition_tags to {updated} champions.")
    else:
        print("Preview only. Use --apply to write changes.")

    if not preview_rows:
        print("No missing champions matched the requested scope.")
        return 0

    for cid, inferred in preview_rows[:50]:
        print(f"{cid}: {', '.join(inferred)}")
    if len(preview_rows) > 50:
        print(f"... and {len(preview_rows) - 50} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
