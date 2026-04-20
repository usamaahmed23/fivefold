from __future__ import annotations

from fivefold import loader
from fivefold.win_conditions import infer_win_condition_tags


CHAMPIONS = loader.load_champions()
ARCHETYPES = loader.load_archetypes()


def test_jinx_infers_scaling_and_protect_the_carry():
    tags = infer_win_condition_tags(CHAMPIONS["jinx"], ARCHETYPES)
    assert "scaling" in tags
    assert "protect_the_carry" in tags


def test_jayce_infers_poke_siege():
    tags = infer_win_condition_tags(CHAMPIONS["jayce"], ARCHETYPES)
    assert "poke_siege" in tags


def test_camille_infers_split_push_and_engage_dive():
    tags = infer_win_condition_tags(CHAMPIONS["camille"], ARCHETYPES)
    assert "split_push" in tags
    assert "engage_dive" in tags


def test_twisted_fate_infers_global_pressure_and_roam():
    tags = infer_win_condition_tags(CHAMPIONS["twisted_fate"], ARCHETYPES)
    assert "global_pressure" in tags
    assert "roam" in tags


def test_ornn_infers_teamfight_or_wombo():
    tags = infer_win_condition_tags(CHAMPIONS["ornn"], ARCHETYPES)
    assert "teamfight" in tags or "wombo" in tags
