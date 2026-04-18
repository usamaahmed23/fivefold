"""Re-resolve contextual champion identity against a DraftState.

A contextual champion (e.g., Rakan with Xayah) flips its colors based on
teammates or enemies present. This module returns a COPY of the champion
with colors adjusted — the source Champion is never mutated.
"""
from __future__ import annotations

from .models import Champion, DraftState, Side


def _allies_enemies(champion_id: str, state: DraftState) -> tuple[list[str], list[str]]:
    """Given a champion ID and draft state, figure out which side the champ is on
    and return (allies, enemies). If the champion isn't placed yet, treat the
    side_to_act as allies."""
    if champion_id in state.blue_picks:
        return state.blue_picks, state.red_picks
    if champion_id in state.red_picks:
        return state.red_picks, state.blue_picks
    allies = state.our_picks
    enemies = state.enemy_picks
    return allies, enemies


def resolve(champion: Champion, state: DraftState) -> Champion:
    """Return a champion view with context_rules applied."""
    if not champion.contextual or not champion.context_rules:
        return champion

    allies, enemies = _allies_enemies(champion.id, state)
    main = list(champion.colors_main)
    off = list(champion.colors_off)

    for rule in champion.context_rules:
        pool = allies if rule.condition == "ally_has_champion" else enemies
        if rule.value not in pool:
            continue
        if rule.effect == "add_main_color" and rule.color not in main:
            main.append(rule.color)
        elif rule.effect == "add_off_color" and rule.color not in off:
            off.append(rule.color)
        elif rule.effect == "remove_main_color" and rule.color in main:
            main.remove(rule.color)

    return champion.model_copy(update={"colors_main": main, "colors_off": off})
