"""Load champion + meta-tier data from the project's JSON files."""
from __future__ import annotations

import json
from pathlib import Path

from .models import Archetype, Archetypes, Champion, MetaTiers

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_champions(path: Path | str | None = None) -> dict[str, Champion]:
    p = Path(path) if path else DEFAULT_DATA_DIR / "champions.json"
    raw = json.loads(p.read_text())
    entries = raw["champions"] if isinstance(raw, dict) and "champions" in raw else raw
    out: dict[str, Champion] = {}
    for entry in entries:
        ch = Champion.model_validate(entry)
        out[ch.id] = ch
    return out


def load_meta_tiers(path: Path | str | None = None) -> MetaTiers:
    p = Path(path) if path else DEFAULT_DATA_DIR / "meta_tiers.json"
    if not p.exists():
        return MetaTiers()
    raw = json.loads(p.read_text())
    raw.pop("_comment", None)
    return MetaTiers.model_validate(raw)


def load_archetypes(path: Path | str | None = None) -> list[Archetype]:
    p = Path(path) if path else DEFAULT_DATA_DIR / "archetypes.json"
    if not p.exists():
        return []
    raw = json.loads(p.read_text())
    return Archetypes.model_validate(raw).archetypes
