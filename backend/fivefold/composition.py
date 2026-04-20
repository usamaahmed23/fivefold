"""Composition analysis for a side's current picks.

Derives declared color weights, structural aggregates, and holes. These are
used by the scoring axes in `engine.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import contextual
from .models import Champion, DraftState

COLORS = ("R", "G", "U", "W", "B", "C")

# Weight of off-colors when computing declared identity. Off-colors are
# build-dependent; they shade the identity but don't define it.
OFF_COLOR_WEIGHT = 0.35

# Aggregate level conversions (structural_tags values -> numeric).
LEVEL_VALUES = {"none": 0.0, "low": 0.33, "medium": 0.67, "high": 1.0}
RANGE_VALUES = {"melee": 0.0, "short": 0.25, "medium": 0.6, "long": 1.0}
SCALING_VALUES = {"early": 0.2, "mid": 0.55, "late": 0.9}
STRUCTURAL_FIELDS = ("engage", "peel", "frontline", "waveclear")

# Unified lookup used by the engine when checking candidate coverage of holes.
# Handles both Level and RangeLevel values in one map.
ALL_FIELD_VALUES: dict[str, float] = {
    **LEVEL_VALUES,
    **RANGE_VALUES,
    **{k: v for k, v in SCALING_VALUES.items()},
}

HIGH_ENGAGE_TAGS = {"engage_tank", "engage_support", "hard_engage_cc", "reliable_knockup_chain"}
MEDIUM_ENGAGE_TAGS = {"diver", "knockup", "displacement", "point_click_cc", "pick_threat", "aoe_teamfight_ult"}

HIGH_PEEL_TAGS = {"enchanter", "peel_support"}
MEDIUM_PEEL_TAGS = {"self_peel", "spell_shield", "point_click_cc", "knockup", "displacement"}

HIGH_WAVECLEAR_TAGS = {"artillery", "control_mage", "battle_mage", "aoe_teamfight_ult"}
MEDIUM_WAVECLEAR_TAGS = {"burst_mage", "marksman", "splitpusher", "poke_support"}

LATE_SCALING_TAGS = {"scaling_hyper", "hypercarry", "control_mage", "battle_mage"}
EARLY_SCALING_TAGS = {"early_ganker", "engage_support"}


@dataclass
class Composition:
    declared_colors: dict[str, float] = field(default_factory=lambda: {c: 0.0 for c in COLORS})
    primary_colors: list[str] = field(default_factory=list)  # up to 2 dominant
    structural_avg: dict[str, float] = field(default_factory=dict)
    scaling_avg: Optional[float] = None
    holes: list[str] = field(default_factory=list)
    n_tagged: int = 0

    @property
    def total_color_mass(self) -> float:
        return sum(self.declared_colors.values())


def infer_structural_level(champion: Champion, field: str) -> str | None:
    """Best-effort structural fallback derived from kit_tags + LS color identity.

    The live data currently fills only a subset of structural_tags for every
    champion. These fallbacks keep the structural axis usable without treating
    sparse data as "no signal".
    """
    kit = set(champion.kit_tags or [])
    main = set(champion.colors_main or [])

    if field == "engage":
        if kit & HIGH_ENGAGE_TAGS:
            return "high"
        if kit & MEDIUM_ENGAGE_TAGS:
            return "medium"
        if "R" in main:
            return "medium"
        return "low"

    if field == "peel":
        if kit & HIGH_PEEL_TAGS:
            return "high"
        if kit & MEDIUM_PEEL_TAGS or "W" in main:
            return "medium"
        return "low"

    if field == "waveclear":
        if kit & HIGH_WAVECLEAR_TAGS:
            return "high"
        if kit & MEDIUM_WAVECLEAR_TAGS or "U" in main:
            return "medium"
        return "low"

    if field == "scaling":
        if kit & LATE_SCALING_TAGS:
            return "late"
        # LS-style shortcut: U/G shells tend toward inevitability and
        # synergy/item-spike scaling unless the kit is clearly early-bound.
        if ("U" in main or "G" in main) and not (kit & EARLY_SCALING_TAGS):
            return "late"
        if kit & EARLY_SCALING_TAGS:
            return "early"
        if "R" in main and "U" not in main and "G" not in main:
            return "early"
        return "mid"

    return None


def get_structural_value(champion: Champion, field: str) -> str | None:
    st = champion.structural_tags
    if st is not None:
        direct = getattr(st, field, None)
        if direct is not None:
            return direct
    return infer_structural_level(champion, field)


def analyze(picks: list[str], champions: dict[str, Champion], state: DraftState) -> Composition:
    comp = Composition()
    if not picks:
        return comp

    all_fields = STRUCTURAL_FIELDS + ("range", "scaling")
    structural_totals = {f: 0.0 for f in all_fields}
    structural_count = {f: 0 for f in all_fields}

    for pid in picks:
        ch = champions.get(pid)
        if ch is None:
            continue
        ch = contextual.resolve(ch, state)
        for c in ch.colors_main:
            comp.declared_colors[c] += 1.0
        for c in ch.colors_off:
            comp.declared_colors[c] += OFF_COLOR_WEIGHT

        st = ch.structural_tags
        if st is not None:
            comp.n_tagged += 1
            for f in STRUCTURAL_FIELDS:
                v = get_structural_value(ch, f)
                if v is not None:
                    structural_totals[f] += ALL_FIELD_VALUES.get(v, 0.0)
                    structural_count[f] += 1
            # Range and scaling use their own value maps.
            if st.range is not None:
                structural_totals["range"] += RANGE_VALUES.get(st.range, 0.0)
                structural_count["range"] += 1
            scaling = get_structural_value(ch, "scaling")
            if scaling is not None:
                structural_totals["scaling"] += SCALING_VALUES.get(scaling, 0.55)
                structural_count["scaling"] += 1

    # Primary colors = top two declared (with mass > 0).
    ranked = sorted(
        (c for c in COLORS if comp.declared_colors[c] > 0),
        key=lambda c: comp.declared_colors[c],
        reverse=True,
    )
    comp.primary_colors = ranked[:2]

    for f in all_fields:
        if structural_count[f] > 0:
            comp.structural_avg[f] = structural_totals[f] / structural_count[f]

    # Holes: structural fields where aggregate is below threshold.
    # Range and scaling use lower thresholds — early-only or all-melee comps
    # flag as holes so picks providing range/inevitability are rewarded.
    _HOLE_THRESHOLDS: dict[str, float] = {"range": 0.35, "scaling": 0.35}
    if comp.structural_avg:
        comp.holes = [
            f for f, v in comp.structural_avg.items()
            if v < _HOLE_THRESHOLDS.get(f, 0.4)
        ]

    # Explicit AD-source hole: if 2+ picks have no AD damage source, flag it.
    # This surfaces an ADC / AD bruiser recommendation independently of the
    # structural_avg analysis, which only tracks engage/peel/waveclear/range/scaling.
    if len(picks) >= 2:
        ad_picks = [
            pid for pid in picks
            if (ch := champions.get(pid)) and
               ch.structural_tags is not None and
               ch.structural_tags.damage_profile in ("ad", "mixed")
        ]
        tagged_picks = [
            pid for pid in picks
            if (ch := champions.get(pid)) and ch.structural_tags is not None
        ]
        # Only flag the hole if we have enough structural data to be confident.
        if len(tagged_picks) >= 2 and len(ad_picks) == 0:
            comp.holes.append("ad_source")

    # Explicit ranged-AD hole: a lone melee AD source (e.g. Yone) often does
    # not solve the comp's need for ranged physical DPS / backline threat.
    # This helps prevent the engine from repeatedly rounding out W/U/AP shells
    # with yet another magic teamfight piece when the draft still lacks a real
    # ranged AD angle.
    if len(picks) >= 3:
        tagged_picks = [
            pid for pid in picks
            if (ch := champions.get(pid)) and ch.structural_tags is not None
        ]
        ranged_ad_picks = [
            pid for pid in picks
            if (ch := champions.get(pid))
            and ch.structural_tags is not None
            and ch.structural_tags.damage_profile in ("ad", "mixed")
            and ch.structural_tags.range in ("short", "medium", "long")
        ]
        if len(tagged_picks) >= 3 and len(ranged_ad_picks) == 0:
            comp.holes.append("ranged_ad_source")

    return comp
