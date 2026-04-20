"""Load champion + meta-tier data from the project's JSON files."""
from __future__ import annotations

import json
from pathlib import Path

from .models import Archetype, Archetypes, Champion, MetaTiers


def _default_data_dir() -> Path:
    """Find bundled data for both local dev and hosted backend deploys.

    In local development the canonical files live at repo-root `data/`.
    In hosted backend-only deploys (for example Vercel Services/FastAPI), the
    service may only include the `backend/` subtree, so we also support a
    colocated `backend/data/` bundle.
    """
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "data",  # backend/data
        here.parents[2] / "data",  # repo-root data
        Path.cwd() / "data",
    ]
    for candidate in candidates:
        if (candidate / "champions.json").exists():
            return candidate
    return candidates[0]


DEFAULT_DATA_DIR = _default_data_dir()


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
