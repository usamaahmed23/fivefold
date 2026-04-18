#!/usr/bin/env python3
"""Enrich champions.json with mechanical fields from Data Dragon + curated kit_tags.

Deterministic fills (no LLM, no scraping of rank sites):
  - structural_tags.range from attack range
  - structural_tags.damage_profile from Riot class tags
  - structural_tags.frontline from Tank/Fighter class tags
  - kit_tags from a hand-curated map (sub-role + mechanical kit features)

Run from repo root:
    python3 scripts/enrich_data.py

Writes back to data/champions.json.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "champions.json"
ARCHETYPES_FILE = Path(__file__).resolve().parents[1] / "data" / "archetypes.json"

DDRAGON_VERSIONS = "https://ddragon.leagueoflegends.com/api/versions.json"


def latest_ddragon_version() -> str:
    with urllib.request.urlopen(DDRAGON_VERSIONS, timeout=10) as r:
        return json.load(r)[0]


def fetch_champion_full(version: str) -> dict:
    url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/championFull.json"
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def normalize(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def classify_range(attack_range: float) -> str:
    if attack_range <= 200:
        return "melee"
    if attack_range <= 500:
        return "medium"
    return "long"


def classify_damage_profile(tags: list[str]) -> str:
    t = set(tags)
    if "Tank" in t and "Fighter" not in t and "Mage" not in t:
        return "tank"
    if "Marksman" in t:
        return "ad"
    if "Mage" in t and "Fighter" not in t and "Assassin" not in t:
        return "ap"
    if "Fighter" in t and "Mage" in t:
        return "mixed"
    if "Assassin" in t and "Mage" in t:
        return "ap"
    if "Assassin" in t:
        return "ad"
    if "Fighter" in t:
        return "ad"
    if "Tank" in t:
        return "tank"
    if "Support" in t:
        return "ap"
    return "mixed"


def classify_frontline(tags: list[str]) -> str:
    t = set(tags)
    if "Tank" in t:
        return "high"
    if "Fighter" in t:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Curated kit_tags. Hand-maintained; vocabulary is a closed set (see VOCAB).
# Each champion gets a small set of tags describing the archetypes/mechanics
# of their kit. These feed synergy + counter scoring and live entirely
# separate from patch winrate data.
# ---------------------------------------------------------------------------
VOCAB = {
    # Sub-role archetypes
    "enchanter", "peel_support", "hook_support", "engage_support", "poke_support",
    "engage_tank", "juggernaut", "diver", "skirmisher", "assassin",
    "burst_mage", "battle_mage", "control_mage", "artillery",
    "marksman", "hypercarry", "splitpusher", "farming_jungler", "early_ganker",
    # Mechanical kit features
    "knockup", "reliable_knockup_chain", "spell_shield", "global_ult",
    "cleanse_self", "execute", "untargetable", "stealth",
    "hard_engage_cc", "point_click_cc", "heal_cut", "anti_heal",
    "high_mobility", "low_mobility", "reset_mechanic",
    "aoe_teamfight_ult", "pick_threat", "anti_frontline_on_hit",
    "displacement", "airborne_chain", "backline_access", "self_peel",
    "scaling_hyper",
}

KIT_TAGS: dict[str, list[str]] = {
    # --- Top laners
    "aatrox": ["juggernaut", "skirmisher", "displacement", "anti_heal"],
    "akshan": ["marksman", "skirmisher", "high_mobility", "stealth", "global_ult"],
    "ambessa": ["diver", "skirmisher", "high_mobility", "displacement"],
    "camille": ["diver", "splitpusher", "high_mobility", "hard_engage_cc", "backline_access"],
    "chogath": ["engage_tank", "control_mage", "execute", "knockup", "hard_engage_cc"],
    "darius": ["juggernaut", "execute", "displacement"],
    "drmundo": ["juggernaut", "scaling_hyper"],
    "fiora": ["skirmisher", "splitpusher", "self_peel", "high_mobility"],
    "gangplank": ["splitpusher", "global_ult", "scaling_hyper", "cleanse_self"],
    "garen": ["juggernaut", "execute", "cleanse_self"],
    "gnar": ["marksman", "knockup", "aoe_teamfight_ult", "displacement"],
    "gragas": ["battle_mage", "engage_tank", "knockup", "displacement", "hard_engage_cc"],
    "gwen": ["skirmisher", "splitpusher", "anti_frontline_on_hit", "untargetable"],
    "illaoi": ["juggernaut", "splitpusher", "displacement"],
    "irelia": ["diver", "skirmisher", "high_mobility", "reset_mechanic", "hard_engage_cc"],
    "jax": ["splitpusher", "skirmisher", "scaling_hyper", "knockup"],
    "jayce": ["artillery", "poke_support", "displacement"],
    "kayle": ["hypercarry", "scaling_hyper", "untargetable", "marksman"],
    "kennen": ["aoe_teamfight_ult", "burst_mage", "knockup", "hard_engage_cc"],
    "kled": ["juggernaut", "diver", "execute"],
    "ksante": ["engage_tank", "juggernaut", "displacement", "hard_engage_cc"],
    "malphite": ["engage_tank", "aoe_teamfight_ult", "hard_engage_cc", "knockup"],
    "mordekaiser": ["juggernaut", "battle_mage", "pick_threat"],
    "nasus": ["juggernaut", "splitpusher", "scaling_hyper", "point_click_cc"],
    "olaf": ["juggernaut", "skirmisher", "cleanse_self", "anti_heal"],
    "ornn": ["engage_tank", "aoe_teamfight_ult", "knockup", "hard_engage_cc", "displacement"],
    "pantheon": ["diver", "global_ult", "hard_engage_cc", "poke_support"],
    "poppy": ["engage_tank", "diver", "hard_engage_cc", "displacement", "self_peel"],
    "quinn": ["marksman", "splitpusher", "global_ult", "high_mobility"],
    "renekton": ["diver", "juggernaut", "hard_engage_cc"],
    "riven": ["diver", "skirmisher", "high_mobility", "knockup"],
    "rumble": ["battle_mage", "aoe_teamfight_ult", "zone_control"] if False else ["battle_mage", "aoe_teamfight_ult"],
    "sett": ["juggernaut", "diver", "displacement", "knockup"],
    "shen": ["engage_tank", "global_ult", "hard_engage_cc", "knockup", "peel_support"],
    "singed": ["juggernaut", "splitpusher", "displacement"],
    "sion": ["engage_tank", "juggernaut", "hard_engage_cc", "knockup"],
    "teemo": ["marksman", "stealth", "poke_support"],
    "trundle": ["juggernaut", "anti_frontline_on_hit", "displacement"],
    "tryndamere": ["skirmisher", "splitpusher", "scaling_hyper", "cleanse_self"],
    "urgot": ["juggernaut", "execute", "displacement"],
    "volibear": ["diver", "juggernaut", "hard_engage_cc"],
    "warwick": ["diver", "early_ganker", "hard_engage_cc"],
    "yorick": ["juggernaut", "splitpusher", "displacement"],

    # --- Junglers
    "amumu": ["engage_tank", "aoe_teamfight_ult", "hard_engage_cc", "point_click_cc"],
    "belveth": ["skirmisher", "anti_frontline_on_hit", "displacement"],
    "briar": ["diver", "skirmisher", "early_ganker", "cleanse_self"],
    "diana": ["assassin", "reliable_knockup_chain", "knockup", "aoe_teamfight_ult"],
    "elise": ["early_ganker", "burst_mage", "high_mobility"],
    "evelynn": ["assassin", "stealth", "burst_mage"],
    "fiddlesticks": ["aoe_teamfight_ult", "control_mage", "hard_engage_cc"],
    "graves": ["marksman", "farming_jungler", "skirmisher"],
    "hecarim": ["diver", "engage_tank", "displacement", "high_mobility", "hard_engage_cc"],
    "ivern": ["enchanter", "peel_support", "farming_jungler", "knockup"],
    "jarvaniv": ["diver", "engage_tank", "knockup", "hard_engage_cc", "early_ganker"],
    "karthus": ["farming_jungler", "scaling_hyper", "global_ult", "execute", "control_mage"],
    "kayn": ["assassin", "diver", "high_mobility", "farming_jungler"],
    "khazix": ["assassin", "high_mobility", "reset_mechanic"],
    "kindred": ["marksman", "farming_jungler", "peel_support", "self_peel"],
    "leesin": ["diver", "early_ganker", "displacement", "hard_engage_cc"],
    "lillia": ["battle_mage", "farming_jungler", "scaling_hyper", "high_mobility"],
    "masteryi": ["skirmisher", "scaling_hyper", "reset_mechanic", "cleanse_self"],
    "nidalee": ["poke_support", "early_ganker", "high_mobility"],
    "nocturne": ["assassin", "diver", "global_ult", "spell_shield"],
    "nunu": ["engage_tank", "peel_support", "early_ganker", "knockup"],
    "rammus": ["engage_tank", "hard_engage_cc", "point_click_cc"],
    "reksai": ["diver", "early_ganker", "knockup", "hard_engage_cc"],
    "rengar": ["assassin", "stealth", "reset_mechanic", "high_mobility"],
    "sejuani": ["engage_tank", "aoe_teamfight_ult", "hard_engage_cc", "knockup"],
    "shaco": ["assassin", "stealth", "early_ganker"],
    "shyvana": ["farming_jungler", "scaling_hyper", "splitpusher"],
    "skarner": ["engage_tank", "aoe_teamfight_ult", "displacement", "hard_engage_cc"],
    "taliyah": ["control_mage", "displacement", "hard_engage_cc", "knockup"],
    "udyr": ["diver", "juggernaut", "point_click_cc"],
    "vi": ["diver", "early_ganker", "hard_engage_cc", "point_click_cc", "knockup"],
    "viego": ["assassin", "skirmisher", "reset_mechanic"],
    "xinzhao": ["diver", "early_ganker", "knockup", "self_peel"],
    "zac": ["engage_tank", "aoe_teamfight_ult", "hard_engage_cc", "displacement", "knockup"],

    # --- Mids
    "ahri": ["burst_mage", "assassin", "high_mobility", "point_click_cc"],
    "akali": ["assassin", "high_mobility", "untargetable", "reset_mechanic"],
    "anivia": ["control_mage", "burst_mage", "hard_engage_cc", "knockup"],
    "annie": ["burst_mage", "hard_engage_cc", "aoe_teamfight_ult", "point_click_cc"],
    "aurelionsol": ["control_mage", "scaling_hyper", "global_ult", "knockup", "displacement"],
    "aurora": ["burst_mage", "skirmisher", "displacement"],
    "azir": ["control_mage", "aoe_teamfight_ult", "knockup", "displacement", "scaling_hyper"],
    "cassiopeia": ["battle_mage", "scaling_hyper", "hard_engage_cc"],
    "corki": ["marksman", "artillery", "global_ult"],
    "ekko": ["assassin", "high_mobility", "aoe_teamfight_ult", "hard_engage_cc"],
    "fizz": ["assassin", "untargetable", "high_mobility", "knockup"],
    "galio": ["engage_tank", "global_ult", "aoe_teamfight_ult", "knockup", "hard_engage_cc", "spell_shield"],
    "heimerdinger": ["poke_support", "control_mage", "splitpusher"],
    "hwei": ["control_mage", "burst_mage", "artillery"],
    "kassadin": ["assassin", "scaling_hyper", "high_mobility"],
    "katarina": ["assassin", "reset_mechanic", "aoe_teamfight_ult", "anti_heal"],
    "leblanc": ["assassin", "burst_mage", "high_mobility"],
    "lissandra": ["control_mage", "hard_engage_cc", "point_click_cc", "untargetable"],
    "lux": ["artillery", "burst_mage", "global_ult", "hard_engage_cc"],
    "malzahar": ["control_mage", "point_click_cc", "spell_shield", "hard_engage_cc"],
    "mel": ["battle_mage", "spell_shield"],
    "naafiri": ["assassin", "early_ganker", "high_mobility"],
    "neeko": ["burst_mage", "aoe_teamfight_ult", "hard_engage_cc"],
    "orianna": ["control_mage", "aoe_teamfight_ult", "knockup", "displacement", "peel_support"],
    "qiyana": ["assassin", "high_mobility", "hard_engage_cc", "displacement", "knockup"],
    "ryze": ["battle_mage", "scaling_hyper", "point_click_cc", "global_ult"],
    "sylas": ["skirmisher", "diver", "high_mobility"],
    "syndra": ["burst_mage", "control_mage", "hard_engage_cc", "knockup"],
    "talon": ["assassin", "high_mobility"],
    "twistedfate": ["burst_mage", "global_ult", "point_click_cc"],
    "veigar": ["burst_mage", "scaling_hyper", "hard_engage_cc", "execute"],
    "velkoz": ["artillery", "control_mage", "hard_engage_cc"],
    "vex": ["burst_mage", "control_mage", "hard_engage_cc"],
    "viktor": ["control_mage", "burst_mage", "hard_engage_cc", "scaling_hyper"],
    "vladimir": ["battle_mage", "scaling_hyper", "untargetable"],
    "xerath": ["artillery", "poke_support", "hard_engage_cc"],
    "yasuo": ["skirmisher", "airborne_chain", "spell_shield", "high_mobility", "knockup"],
    "yone": ["skirmisher", "airborne_chain", "high_mobility", "knockup"],
    "zaahen": ["control_mage", "burst_mage"],
    "zed": ["assassin", "high_mobility", "reset_mechanic"],
    "ziggs": ["artillery", "poke_support", "global_ult"],
    "zoe": ["burst_mage", "poke_support", "point_click_cc"],

    # --- ADCs
    "aphelios": ["marksman", "hypercarry", "scaling_hyper"],
    "ashe": ["marksman", "global_ult", "hard_engage_cc", "point_click_cc"],
    "caitlyn": ["marksman", "poke_support", "self_peel"],
    "draven": ["marksman", "global_ult", "high_mobility"],
    "ezreal": ["marksman", "artillery", "global_ult", "high_mobility"],
    "jhin": ["marksman", "artillery", "global_ult", "hard_engage_cc"],
    "jinx": ["marksman", "hypercarry", "reset_mechanic", "scaling_hyper", "global_ult"],
    "kaisa": ["marksman", "hypercarry", "scaling_hyper", "high_mobility", "backline_access"],
    "kalista": ["marksman", "self_peel", "peel_support", "high_mobility"],
    "kogmaw": ["marksman", "hypercarry", "scaling_hyper", "anti_frontline_on_hit"],
    "lucian": ["marksman", "high_mobility"],
    "missfortune": ["marksman", "aoe_teamfight_ult", "anti_heal"],
    "nilah": ["marksman", "self_peel", "skirmisher"],
    "samira": ["marksman", "skirmisher", "reset_mechanic", "cleanse_self"],
    "senna": ["marksman", "enchanter", "global_ult", "scaling_hyper"],
    "sivir": ["marksman", "spell_shield", "engage_support"],
    "smolder": ["marksman", "hypercarry", "scaling_hyper", "execute"],
    "tristana": ["marksman", "displacement", "reset_mechanic", "self_peel"],
    "twitch": ["marksman", "hypercarry", "stealth", "scaling_hyper"],
    "varus": ["marksman", "artillery", "hard_engage_cc", "heal_cut"],
    "vayne": ["marksman", "hypercarry", "anti_frontline_on_hit", "self_peel", "untargetable"],
    "xayah": ["marksman", "self_peel", "untargetable", "hard_engage_cc"],
    "yunara": ["marksman", "hypercarry", "scaling_hyper"],
    "zeri": ["marksman", "high_mobility", "hypercarry"],

    # --- Supports
    "alistar": ["engage_support", "engage_tank", "cleanse_self", "knockup", "displacement", "peel_support"],
    "bard": ["poke_support", "peel_support", "global_ult", "hard_engage_cc"],
    "blitzcrank": ["hook_support", "pick_threat", "displacement", "knockup"],
    "braum": ["peel_support", "engage_tank", "knockup", "hard_engage_cc"],
    "brand": ["poke_support", "burst_mage", "hard_engage_cc"],
    "janna": ["enchanter", "peel_support", "cleanse_self", "knockup", "displacement"],
    "karma": ["enchanter", "poke_support", "peel_support", "hard_engage_cc"],
    "leona": ["engage_support", "engage_tank", "hard_engage_cc", "aoe_teamfight_ult", "point_click_cc"],
    "lulu": ["enchanter", "peel_support", "knockup"],
    "milio": ["enchanter", "peel_support", "cleanse_self"],
    "morgana": ["poke_support", "spell_shield", "hard_engage_cc", "point_click_cc"],
    "nami": ["enchanter", "peel_support", "knockup", "hard_engage_cc"],
    "nautilus": ["hook_support", "engage_support", "engage_tank", "hard_engage_cc", "point_click_cc", "knockup"],
    "pyke": ["hook_support", "assassin", "execute", "reset_mechanic", "stealth", "hard_engage_cc"],
    "rakan": ["engage_support", "enchanter", "high_mobility", "knockup", "hard_engage_cc"],
    "rell": ["engage_support", "engage_tank", "hard_engage_cc", "knockup", "displacement"],
    "renataglasc": ["enchanter", "peel_support", "cleanse_self"],
    "seraphine": ["enchanter", "poke_support", "aoe_teamfight_ult", "hard_engage_cc"],
    "sona": ["enchanter", "peel_support", "aoe_teamfight_ult", "hard_engage_cc"],
    "soraka": ["enchanter", "peel_support", "cleanse_self", "global_ult"],
    "swain": ["battle_mage", "hook_support", "displacement"],
    "tahmkench": ["peel_support", "engage_tank", "global_ult"],
    "taric": ["enchanter", "peel_support", "hard_engage_cc", "untargetable"],
    "thresh": ["hook_support", "engage_support", "peel_support", "displacement", "hard_engage_cc"],
    "yuumi": ["enchanter", "peel_support", "untargetable"],
    "zilean": ["enchanter", "peel_support", "cleanse_self", "knockup"],
    "zyra": ["poke_support", "burst_mage", "knockup", "hard_engage_cc"],

    # --- Misc / fills
    "maokai": ["engage_tank", "knockup", "hard_engage_cc", "displacement", "aoe_teamfight_ult"],
    "wukong": ["diver", "knockup", "aoe_teamfight_ult", "stealth", "displacement"],
}


def enrich(champ: dict, dd_entry: dict | None) -> dict:
    if dd_entry is not None:
        stats = dd_entry.get("stats", {})
        tags = dd_entry.get("tags", [])
        st = champ.get("structural_tags") or {}
        attack_range = float(stats.get("attackrange") or 0)
        if attack_range:
            st["range"] = classify_range(attack_range)
        if tags:
            st["damage_profile"] = classify_damage_profile(tags)
            st["frontline"] = classify_frontline(tags)
        champ["structural_tags"] = st

    cid = champ["id"]
    kit = KIT_TAGS.get(cid) or KIT_TAGS.get(cid.replace("_", ""))
    if kit:
        champ["kit_tags"] = sorted(set(kit))
    elif "kit_tags" not in champ:
        champ["kit_tags"] = []
    return champ


ARCHETYPES = [
    # --- Synergy archetypes (our team) ------------------------------------
    {
        "id": "yasuo_knockup_chain",
        "name": "Yasuo / Yone Airborne Chain",
        "kind": "synergy",
        "description": (
            "Yasuo and Yone's ult requires an airborne target. Reliable knockup"
            " setups dramatically raise their value."
        ),
        "members": [
            "yasuo", "yone",
            "ornn", "gragas", "alistar", "malphite", "sejuani", "nautilus",
            "azir", "gnar", "rell", "rakan", "taliyah", "maokai", "zac",
            "diana", "xinzhao", "janna", "jarvaniv", "wukong", "volibear",
            "kennen", "chogath", "riven", "syndra", "nami", "orianna",
        ],
    },
    {
        "id": "global_ult_pressure",
        "name": "Global Ult Map Pressure",
        "kind": "synergy",
        "description": (
            "Multiple global / near-global ults give side-lane freedom,"
            " objective tempo, and cross-map plays."
        ),
        "members": [
            "shen", "twistedfate", "pantheon", "karthus", "ashe", "nocturne",
            "galio", "soraka", "gangplank", "corki", "draven", "ezreal",
            "jhin", "jinx", "lux", "ryze", "senna", "akshan", "quinn",
            "aurelionsol", "bard",
        ],
    },
    {
        "id": "protect_the_carry",
        "name": "Protect the Carry",
        "kind": "synergy",
        "description": (
            "Hyper-scaling marksman + layered enchanter peel to buy time into"
            " 2-3 items, then win every teamfight that reaches 4v5 peel."
        ),
        "members": [
            "jinx", "kogmaw", "twitch", "vayne", "aphelios", "kaisa",
            "smolder", "yunara", "kayle", "zeri", "jhin",
            "lulu", "milio", "janna", "soraka", "nami", "yuumi",
            "karma", "sona", "seraphine", "renataglasc", "taric",
        ],
    },
    {
        "id": "wombo_engage",
        "name": "Wombo Engage",
        "kind": "synergy",
        "description": (
            "AoE initiator + AoE follow-up. Win one 5v5 in mid, end the game."
        ),
        "members": [
            "malphite", "orianna", "kennen", "amumu", "missfortune", "galio",
            "yasuo", "yone", "wukong", "sejuani", "maokai", "zac", "rell",
            "seraphine", "sona", "nunu", "skarner", "ornn", "fiddlesticks",
            "katarina",
        ],
    },
    {
        "id": "pick_comp",
        "name": "Pick Composition",
        "kind": "synergy",
        "description": (
            "Hook / grab supports + burst mid/jungle to delete a caught target"
            " before their team can respond. Wins 4v5 teamfights off picks."
        ),
        "members": [
            "blitzcrank", "thresh", "nautilus", "pyke", "morgana",
            "leblanc", "syndra", "veigar", "zed", "talon", "katarina",
            "khazix", "evelynn", "fizz", "ahri", "vex",
        ],
    },
    {
        "id": "dive_comp",
        "name": "Dive Composition",
        "kind": "synergy",
        "description": (
            "Engage tanks + divers collapse on enemy backline under their"
            " tower. Hard counter to immobile carries and poke comps."
        ),
        "members": [
            "malphite", "leona", "nautilus", "rell", "alistar", "amumu",
            "jarvaniv", "vi", "leesin", "camille", "irelia", "diana",
            "wukong", "xinzhao", "hecarim", "warwick", "viego", "renekton",
            "kennen", "sejuani", "zac", "sett", "akali", "ekko",
        ],
    },
    {
        "id": "poke_siege",
        "name": "Poke & Siege",
        "kind": "synergy",
        "description": (
            "Long-range poke to chunk health before engaging or taking an"
            " objective. Wants disengage/peel backing it up."
        ),
        "members": [
            "xerath", "ziggs", "lux", "jayce", "varus", "nidalee", "velkoz",
            "jhin", "zoe", "caitlyn", "ezreal", "morgana", "karma",
            "brand", "corki", "hwei", "seraphine",
        ],
    },
    {
        "id": "split_push",
        "name": "1-3-1 Split Push",
        "kind": "synergy",
        "description": (
            "One side-lane duelist + a 4-man group with waveclear/disengage."
            " Applies pressure on two map sides simultaneously."
        ),
        "members": [
            "tryndamere", "fiora", "camille", "jax", "yorick", "nasus",
            "illaoi", "gnar", "gangplank", "quinn", "shen",
            "akshan", "akali",
        ],
    },

    # --- Counter archetypes (vs enemy kit features) -----------------------
    {
        "id": "spell_shield_vs_chain_cc",
        "name": "Spell Shields vs Chain CC",
        "kind": "counter",
        "description": (
            "Spell shields cancel the first hook / chain-stun / suppression."
            " Very high value against CC-dependent comps."
        ),
        "members": ["morgana", "sivir", "nocturne", "yasuo", "malzahar", "mel", "galio"],
        "targets": ["hook_support", "hard_engage_cc", "point_click_cc", "pick_threat"],
    },
    {
        "id": "peel_vs_divers",
        "name": "Peel vs Divers / Assassins",
        "kind": "counter",
        "description": (
            "Strong peel + disengage shuts down dive and assassin threats on"
            " the carry."
        ),
        "members": [
            "janna", "lulu", "milio", "nami", "soraka", "karma", "braum",
            "taric", "thresh", "morgana", "renataglasc", "alistar", "tahmkench",
            "poppy", "kindred",
        ],
        "targets": ["diver", "assassin", "backline_access", "high_mobility", "reset_mechanic"],
    },
    {
        "id": "anti_mobility_lock",
        "name": "Anti-Mobility Lock-down",
        "kind": "counter",
        "description": (
            "Hard point-and-click / unconditional CC pins down high-mobility"
            " skirmishers and assassins."
        ),
        "members": [
            "malzahar", "lissandra", "morgana", "rammus", "nautilus", "ashe",
            "amumu", "warwick", "taliyah", "anivia", "veigar", "zoe",
            "urgot", "vi",
        ],
        "targets": ["high_mobility", "skirmisher", "assassin", "diver"],
    },
    {
        "id": "anti_scaling_tempo",
        "name": "Anti-Scaling Tempo",
        "kind": "counter",
        "description": (
            "Early aggression and burn-it-down kits punish scaling comps"
            " before they reach their power spikes."
        ),
        "members": [
            "draven", "pantheon", "renekton", "darius", "leblanc", "talon",
            "zed", "leesin", "elise", "xinzhao", "jarvaniv", "nidalee",
            "kled", "caitlyn", "lucian",
        ],
        "targets": ["scaling_hyper", "hypercarry", "farming_jungler", "battle_mage"],
    },
    {
        "id": "anti_heal_kit",
        "name": "Built-in Anti-Heal",
        "kind": "counter",
        "description": (
            "Kit-integrated grievous wounds / healing reduction neutralize"
            " sustain-heavy comps."
        ),
        "members": ["varus", "missfortune", "katarina", "olaf", "aatrox"],
        "targets": ["enchanter", "juggernaut", "battle_mage", "hypercarry"],
    },
    {
        "id": "anti_frontline_meltdown",
        "name": "Anti-Frontline Meltdown",
        "kind": "counter",
        "description": (
            "Percent-health / on-hit damage dealers melt stacked tanks and"
            " juggernauts faster than they can engage."
        ),
        "members": [
            "vayne", "kogmaw", "gwen", "fiora", "kaisa", "smolder",
            "chogath", "trundle", "kayle",
        ],
        "targets": ["engage_tank", "juggernaut"],
    },
    {
        "id": "aoe_vs_stacked",
        "name": "AoE vs Stacked Formations",
        "kind": "counter",
        "description": (
            "AoE teamfight ults punish grouped compositions — particularly"
            " enchanter-protect and dive stacks."
        ),
        "members": [
            "orianna", "yasuo", "malphite", "kennen", "missfortune", "galio",
            "amumu", "katarina", "karthus", "neeko", "seraphine", "wukong",
            "sona", "fiddlesticks",
        ],
        "targets": ["enchanter", "engage_tank", "juggernaut", "battle_mage"],
    },
]


def main() -> int:
    if not DATA_FILE.exists():
        print(f"champions.json not found at {DATA_FILE}", file=sys.stderr)
        return 1

    try:
        version = latest_ddragon_version()
    except Exception as e:
        print(f"could not fetch DDragon version: {e}", file=sys.stderr)
        return 2

    print(f"Using Data Dragon {version}")
    ddragon = fetch_champion_full(version)
    dd_by_norm_name: dict[str, dict] = {}
    for entry in ddragon["data"].values():
        dd_by_norm_name[normalize(entry["name"])] = entry

    with DATA_FILE.open() as f:
        doc = json.load(f)

    missing_ddragon: list[str] = []
    missing_kit: list[str] = []
    unknown_tags: list[tuple[str, str]] = []

    for champ in doc["champions"]:
        key = normalize(champ["name"])
        dd = dd_by_norm_name.get(key)
        if dd is None:
            missing_ddragon.append(champ["name"])
        enrich(champ, dd)
        if not champ.get("kit_tags"):
            missing_kit.append(champ["id"])
        for tag in champ.get("kit_tags", []):
            if tag not in VOCAB:
                unknown_tags.append((champ["id"], tag))

    with DATA_FILE.open("w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")

    # Map archetype members (which may use normalized no-underscore IDs) to
    # real champion IDs as stored in champions.json.
    id_by_norm = {normalize(c["id"]): c["id"] for c in doc["champions"]}
    known_ids = {c["id"] for c in doc["champions"]}
    unresolved: list[tuple[str, str]] = []
    archetypes_out = []
    for arch in ARCHETYPES:
        members_resolved = []
        for m in arch.get("members", []):
            if m in known_ids:
                members_resolved.append(m)
            elif m in id_by_norm:
                members_resolved.append(id_by_norm[m])
            else:
                unresolved.append((arch["id"], m))
        archetypes_out.append({**arch, "members": sorted(set(members_resolved))})

    with ARCHETYPES_FILE.open("w") as f:
        json.dump({"archetypes": archetypes_out}, f, indent=2)
        f.write("\n")

    print(f"Enriched {len(doc['champions'])} champions")
    if missing_ddragon:
        print(f"  {len(missing_ddragon)} champions not found in DDragon: {missing_ddragon}")
    if missing_kit:
        print(f"  {len(missing_kit)} champions without curated kit_tags: {missing_kit}")
    if unknown_tags:
        print(f"  {len(unknown_tags)} tag values outside VOCAB: {unknown_tags}")
    if unresolved:
        print(f"  {len(unresolved)} unresolved archetype members: {unresolved}")
    print(f"Wrote archetypes to {ARCHETYPES_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
