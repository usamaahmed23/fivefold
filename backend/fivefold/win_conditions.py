"""Deterministic win-condition inference.

These tags are intentionally higher-level than `kit_tags`. The goal is not to
perfectly summarize a champion in isolation, but to estimate what kind of
"deck" that champion naturally belongs in using LS-style ideas:

- blue/green shells tend toward inevitability and scaling
- red-heavy shells tend toward forcing, tempo, and skirmishing
- white-heavy shells are often versatile support pieces
- black-heavy shells often add conditions or pressure patterns

This module is conservative on purpose. It should provide plausible draft
semantics without overwriting hand-authored nuance.
"""
from __future__ import annotations

from .models import Archetype, Champion

WIN_CONDITION_PRIORITY = [
    "protect_the_carry",
    "poke_siege",
    "split_push",
    "engage_dive",
    "wombo",
    "pick",
    "global_pressure",
    "roam",
    "scaling",
    "teamfight",
    "skirmish",
    "objective_control",
    "lane_bully",
]

ARCHETYPE_TO_TAG = {
    "global_ult_pressure": "global_pressure",
    "protect_the_carry": "protect_the_carry",
    "wombo_engage": "wombo",
    "pick_comp": "pick",
    "dive_comp": "engage_dive",
    "poke_siege": "poke_siege",
    "split_push": "split_push",
    # Yasuo/Yone airborne chains are usually teamfight/wombo tools.
    "yasuo_knockup_chain": "teamfight",
}


def _sort_tags(tags: set[str]) -> list[str]:
    ranked = [tag for tag in WIN_CONDITION_PRIORITY if tag in tags]
    leftovers = sorted(tag for tag in tags if tag not in WIN_CONDITION_PRIORITY)
    return ranked + leftovers


def infer_win_condition_tags(champion: Champion, archetypes: list[Archetype]) -> list[str]:
    tags: set[str] = set(champion.win_condition_tags or [])
    kit = set(champion.kit_tags or [])
    main = set(champion.colors_main or [])

    # Archetypes are the strongest source because they already describe
    # comp-level patterns rather than just raw mechanics.
    for arch in archetypes:
        if arch.kind != "synergy":
            continue
        if champion.id not in arch.members:
            continue
        mapped = ARCHETYPE_TO_TAG.get(arch.id)
        if mapped:
            tags.add(mapped)

    # Kit-driven rules.
    if "splitpusher" in kit:
        tags.add("split_push")

    if {"artillery", "poke_support"} & kit:
        tags.add("poke_siege")

    if {"hook_support", "pick_threat", "assassin"} & kit:
        tags.add("pick")

    if {"engage_tank", "engage_support", "diver", "backline_access"} & kit:
        tags.add("engage_dive")

    if "aoe_teamfight_ult" in kit:
        tags.add("teamfight")
        if {"engage_tank", "engage_support", "knockup", "hard_engage_cc"} & kit:
            tags.add("wombo")

    if {"hypercarry", "scaling_hyper", "control_mage", "battle_mage", "farming_jungler"} & kit:
        tags.add("scaling")

    if "global_ult" in kit:
        tags.add("global_pressure")

    if "early_ganker" in kit or (
        "global_ult" in kit
        and {"high_mobility", "point_click_cc", "burst_mage", "engage_support", "diver", "hard_engage_cc"} & kit
    ):
        tags.add("roam")

    if {"skirmisher", "reset_mechanic"} & kit:
        tags.add("skirmish")

    if {"control_mage", "farming_jungler", "engage_tank"} & kit:
        tags.add("objective_control")

    # Early forcing / beatdown heuristics. We keep these broad rather than
    # pretending to know exact lane matchups.
    if "R" in main and {"marksman", "assassin", "diver", "early_ganker", "juggernaut"} & kit:
        if not ({"hypercarry", "scaling_hyper"} & kit and "marksman" in kit):
            tags.add("skirmish")

    if (
        "R" in main
        and "U" not in main
        and {"marksman", "juggernaut", "poke_support"} & kit
        and not ({"hypercarry", "scaling_hyper"} & kit and "marksman" in kit)
    ):
        tags.add("lane_bully")

    # LS-style inevitability shortcut: U/G shells often want the game to keep
    # going unless the kit is explicitly early-bound.
    if ("U" in main or "G" in main) and "early_ganker" not in kit:
        if {"hypercarry", "control_mage", "battle_mage", "marksman", "enchanter"} & kit:
            tags.add("scaling")

    # Protect-the-carry is a comp plan, but some champions are clearly pieces
    # of it even in isolation.
    if {"hypercarry", "enchanter"} & kit:
        tags.add("protect_the_carry")

    # Reasonable cap so we don't turn every champ into a 7-tag soup.
    ordered = _sort_tags(tags)
    return ordered[:4]
