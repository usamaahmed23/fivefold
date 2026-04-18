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


def analyze(picks: list[str], champions: dict[str, Champion], state: DraftState) -> Composition:
    comp = Composition()
    if not picks:
        return comp

    all_fields = STRUCTURAL_FIELDS + ("range",)
    structural_totals = {f: 0.0 for f in all_fields}
    structural_count = {f: 0 for f in all_fields}
    scaling_total = 0.0
    scaling_count = 0

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
                v = getattr(st, f)
                if v is not None:
                    structural_totals[f] += LEVEL_VALUES.get(v, 0.0)
                    structural_count[f] += 1
            # Range uses its own value map (melee/short/medium/long).
            if st.range is not None:
                structural_totals["range"] += RANGE_VALUES.get(st.range, 0.0)
                structural_count["range"] += 1
            if st.scaling is not None:
                scaling_total += SCALING_VALUES.get(st.scaling, 0.5)
                scaling_count += 1

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
    if scaling_count > 0:
        comp.scaling_avg = scaling_total / scaling_count

    # Holes: structural fields where aggregate < 0.4 (if we have any tag data).
    # Range threshold is slightly lower (< 0.35) — a comp with one medium-range
    # champion among melees is not yet a hole, but all-melee always is.
    if comp.structural_avg:
        comp.holes = [
            f for f, v in comp.structural_avg.items()
            if v < (0.35 if f == "range" else 0.4)
        ]

    return comp
