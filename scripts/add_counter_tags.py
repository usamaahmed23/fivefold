#!/usr/bin/env python3
"""
One-time script to add counter_tags to all LS-sheet champions
and normalize schema (add missing source, contextual fields).
"""

import json
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "champions.json")

# Counter tags for each LS-sheet champion based on kit knowledge.
# These describe what strategies/tools are effective AGAINST the champion.
COUNTER_TAGS = {
    "aatrox": ["anti_sustain", "kite_outrange", "true_damage", "percent_health_damage"],
    "ahri": ["hard_cc_on_engage", "sustained_tank_damage", "outrange_medium_range"],
    "akali": ["hard_cc_on_engage", "sustained_tank_damage", "reveal_stealth", "aoe_zone_control"],
    "alistar": ["disengage_support", "kite_outrange", "poke_before_engage"],
    "amumu": ["early_invade_pressure", "kite_outrange", "anti_mobility"],
    "anivia": ["assassin_dive", "hard_engage_reaches_backline", "early_lane_bully"],
    "annie": ["outrange_medium_range", "disengage_support", "sustained_poke"],
    "aphelios": ["hard_engage_on_adc", "assassin_dive", "early_lane_bully"],
    "ashe": ["hard_engage_on_adc", "assassin_dive", "hook_threat"],
    "aurelion_sol": ["assassin_dive", "hard_engage_reaches_backline", "early_lane_bully"],
    "azir": ["assassin_dive", "hard_engage_before_scale", "early_lane_bully", "anti_dash_cc"],
    "bard": ["hard_engage_all_in", "early_lane_bully", "punish_roam"],
    "blitzcrank": ["spell_shield", "disengage_support", "long_range_poke", "minion_block"],
    "brand": ["hard_engage_on_adc", "assassin_dive", "outrange_medium_range"],
    "braum": ["poke_before_engage", "sustained_damage_no_burst", "anti_sustain"],
    "caitlyn": ["hard_engage_on_adc", "hook_threat", "assassin_dive"],
    "camille": ["hard_cc_on_engage", "anti_mobility", "kite_outrange", "sustained_tank_damage"],
    "cassiopeia": ["hard_engage_reaches_backline", "assassin_dive", "outrange_medium_range"],
    "chogath": ["kite_outrange", "percent_health_damage", "true_damage", "anti_sustain"],
    "corki": ["hard_engage_reaches_backline", "assassin_dive", "early_lane_bully"],
    "darius": ["kite_outrange", "long_range_poke", "anti_mobility", "disengage_support"],
    "diana": ["kite_outrange", "hard_cc_on_engage", "disengage_support"],
    "dr_mundo": ["anti_sustain", "percent_health_damage", "true_damage", "kite_outrange"],
    "draven": ["hard_engage_on_adc", "hook_threat", "outrange_pre_ult", "hard_cc_on_engage"],
    "ekko": ["hard_cc_on_engage", "sustained_tank_damage", "zone_control"],
    "elise": ["sustained_tank_damage", "hard_cc_on_engage", "early_invade_pressure"],
    "evelynn": ["reveal_stealth", "early_invade_pressure", "group_deny_picks"],
    "ezreal": ["hard_engage_on_adc", "sustained_tank_damage", "hook_threat"],
    "fiddlesticks": ["early_invade_pressure", "reveal_stealth", "hard_cc_on_engage", "disengage_support"],
    "fiora": ["hard_cc_on_engage", "kite_outrange", "aoe_cc_teamfight", "ranged_harass"],
    "fizz": ["hard_cc_on_engage", "sustained_tank_damage", "outrange_medium_range"],
    "galio": ["sustained_damage_no_burst", "split_push_outscale", "kite_outrange"],
    "gangplank": ["early_all_in", "hard_engage_before_scale", "dive_pre_stack"],
    "garen": ["kite_outrange", "true_damage", "percent_health_damage"],
    "gnar": ["hard_engage_before_scale", "sustained_damage_no_burst", "anti_mobility"],
    "gragas": ["sustained_damage_no_burst", "kite_outrange", "anti_sustain"],
    "graves": ["hard_cc_on_engage", "kite_outrange", "sustained_tank_damage"],
    "hecarim": ["hard_cc_on_engage", "disengage_support", "kite_outrange"],
    "heimerdinger": ["long_range_poke", "hard_engage_reaches_backline", "aoe_clears_minions"],
    "illaoi": ["kite_outrange", "anti_mobility", "long_range_poke"],
    "irelia": ["hard_cc_on_engage", "kite_outrange", "sustained_tank_damage"],
    "ivern": ["early_invade_pressure", "hard_engage_all_in", "anti_sustain"],
    "janna": ["hard_engage_all_in", "sustained_damage_no_burst", "hook_threat"],
    "jarvan_iv": ["anti_dash_cc", "disengage_support", "kite_outrange"],
    "jax": ["kite_outrange", "hard_cc_on_engage", "ranged_harass", "early_lane_bully"],
    "jayce": ["hard_engage_reaches_backline", "sustained_tank_damage", "outscale_late"],
    "jhin": ["hard_engage_on_adc", "assassin_dive", "hook_threat"],
    "jinx": ["hard_engage_on_adc", "assassin_dive", "hook_threat", "early_lane_bully"],
    "kaisa": ["hard_engage_on_adc", "early_lane_bully", "long_range_poke_adc"],
    "kalista": ["hard_cc_on_engage", "burst_before_kite", "anti_mobility"],
    "karma": ["hard_engage_all_in", "assassin_dive", "outscale_late"],
    "karthus": ["early_invade_pressure", "assassin_dive", "hard_engage_before_scale"],
    "kassadin": ["early_lane_bully", "hard_cc_on_engage", "hard_engage_before_scale"],
    "katarina": ["hard_cc_on_engage", "sustained_tank_damage", "aoe_zone_control"],
    "kayle": ["early_lane_bully", "hard_engage_before_scale", "dive_pre_stack", "farm_denial"],
    "kayn": ["hard_cc_on_engage", "early_invade_pressure", "sustained_tank_damage"],
    "kennen": ["hard_engage_before_scale", "outrange_medium_range", "disengage_support"],
    "khazix": ["group_deny_picks", "reveal_stealth", "hard_cc_on_engage", "sustained_tank_damage"],
    "kindred": ["early_invade_pressure", "hard_cc_on_engage", "aoe_zone_control"],
    "kled": ["kite_outrange", "disengage_support", "sustained_tank_damage"],
    "kogmaw": ["hard_engage_on_adc", "assassin_dive", "hook_threat", "early_lane_bully"],
    "leblanc": ["hard_cc_on_engage", "sustained_tank_damage", "outscale_late"],
    "lee_sin": ["sustained_tank_damage", "outscale_late", "hard_cc_on_engage"],
    "leona": ["disengage_support", "kite_outrange", "poke_before_engage"],
    "lissandra": ["outrange_medium_range", "sustained_damage_no_burst", "split_push_outscale"],
    "lucian": ["outscale_late", "hard_engage_on_adc", "sustained_tank_damage"],
    "lulu": ["hard_engage_all_in", "assassin_dive", "burst_before_heal_shield"],
    "lux": ["hard_engage_reaches_backline", "assassin_dive", "anti_dash_cc"],
    "malphite": ["sustained_damage_no_burst", "kite_outrange", "split_push_outscale"],
    "malzahar": ["spell_shield", "hard_engage_reaches_backline", "early_lane_bully"],
    "maokai": ["kite_outrange", "anti_sustain", "percent_health_damage"],
    "master_yi": ["hard_cc_on_engage", "burst_before_kite", "aoe_cc_teamfight"],
    "miss_fortune": ["hard_engage_on_adc", "assassin_dive", "hook_threat"],
    "mordekaiser": ["kite_outrange", "percent_health_damage", "true_damage"],
    "morgana": ["hard_engage_all_in", "sustained_damage_no_burst", "displacement_support"],
    "nami": ["hard_engage_all_in", "hook_threat", "assassin_dive"],
    "nasus": ["kite_outrange", "early_lane_bully", "farm_denial", "percent_health_damage"],
    "nautilus": ["disengage_support", "long_range_poke", "kite_outrange"],
    "neeko": ["sustained_damage_no_burst", "outrange_medium_range", "split_push_outscale"],
    "nidalee": ["hard_engage_all_in", "sustained_tank_damage", "outscale_late"],
    "nocturne": ["hard_cc_on_engage", "group_deny_picks", "disengage_support"],
    "nunu": ["early_invade_pressure", "anti_sustain", "kite_outrange"],
    "olaf": ["kite_outrange", "outscale_late", "disengage_support"],
    "orianna": ["assassin_dive", "hard_engage_reaches_backline", "early_lane_bully"],
    "ornn": ["percent_health_damage", "true_damage", "kite_outrange", "sustained_damage_no_burst"],
    "pantheon": ["outscale_late", "sustained_tank_damage", "kite_outrange"],
    "poppy": ["sustained_damage_no_burst", "kite_outrange", "outrange_medium_range"],
    "pyke": ["sustained_tank_damage", "hard_cc_on_engage", "group_deny_picks"],
    "qiyana": ["hard_cc_on_engage", "sustained_tank_damage", "outrange_medium_range"],
    "quinn": ["hard_engage_reaches_backline", "sustained_tank_damage", "outscale_late"],
    "rakan": ["hard_cc_on_engage", "disengage_support", "poke_before_engage"],
    "rammus": ["sustained_damage_no_burst", "kite_outrange", "true_damage"],
    "reksai": ["kite_outrange", "outscale_late", "hard_cc_on_engage"],
    "renekton": ["kite_outrange", "outscale_late", "sustained_tank_damage"],
    "rengar": ["hard_cc_on_engage", "reveal_stealth", "group_deny_picks", "sustained_tank_damage"],
    "riven": ["hard_cc_on_engage", "kite_outrange", "sustained_tank_damage"],
    "rumble": ["hard_engage_reaches_backline", "outrange_medium_range", "sustained_tank_damage"],
    "ryze": ["early_lane_bully", "hard_engage_before_scale", "assassin_dive"],
    "sejuani": ["sustained_damage_no_burst", "kite_outrange", "percent_health_damage"],
    "senna": ["hard_engage_on_adc", "assassin_dive", "hook_threat"],
    "sett": ["kite_outrange", "true_damage", "percent_health_damage"],
    "shaco": ["reveal_stealth", "group_deny_picks", "sustained_tank_damage", "aoe_zone_control"],
    "shen": ["sustained_damage_no_burst", "split_push_outscale", "kite_outrange"],
    "shyvana": ["kite_outrange", "hard_cc_on_engage", "early_invade_pressure"],
    "singed": ["kite_outrange", "long_range_poke", "hard_cc_on_engage"],
    "sion": ["kite_outrange", "percent_health_damage", "true_damage", "anti_mobility"],
    "sivir": ["hard_engage_on_adc", "assassin_dive", "outscale_late"],
    "skarner": ["kite_outrange", "spell_shield", "disengage_support"],
    "sona": ["hard_engage_all_in", "assassin_dive", "burst_before_heal_shield"],
    "soraka": ["anti_sustain", "hard_engage_all_in", "assassin_dive", "burst_before_heal_shield"],
    "swain": ["outrange_medium_range", "anti_sustain", "kite_outrange"],
    "sylas": ["hard_cc_on_engage", "anti_sustain", "kite_outrange"],
    "syndra": ["hard_engage_reaches_backline", "assassin_dive", "sustained_tank_damage"],
    "tahm_kench": ["percent_health_damage", "true_damage", "kite_outrange", "anti_sustain"],
    "taliyah": ["hard_engage_reaches_backline", "assassin_dive", "anti_dash_cc"],
    "talon": ["hard_cc_on_engage", "sustained_tank_damage", "group_deny_picks"],
    "taric": ["poke_before_engage", "kite_outrange", "burst_before_heal_shield"],
    "teemo": ["hard_engage_all_in", "sustained_tank_damage", "oracle_sweep"],
    "thresh": ["disengage_support", "long_range_poke", "spell_shield"],
    "tristana": ["hard_cc_on_engage", "sustained_tank_damage", "early_lane_bully"],
    "trundle": ["kite_outrange", "percent_health_damage", "true_damage"],
    "tryndamere": ["hard_cc_on_engage", "kite_outrange", "aoe_cc_teamfight"],
    "twisted_fate": ["hard_engage_reaches_backline", "assassin_dive", "punish_roam"],
    "twitch": ["reveal_stealth", "hard_engage_on_adc", "early_lane_bully"],
    "udyr": ["kite_outrange", "hard_cc_on_engage", "disengage_support"],
    "urgot": ["kite_outrange", "outrange_medium_range", "percent_health_damage"],
    "varus": ["hard_engage_on_adc", "assassin_dive", "hook_threat"],
    "vayne": ["hard_cc_on_engage", "early_lane_bully", "burst_before_kite"],
    "veigar": ["hard_engage_reaches_backline", "assassin_dive", "early_lane_bully"],
    "velkoz": ["hard_engage_reaches_backline", "assassin_dive", "anti_dash_cc"],
    "vi": ["disengage_support", "kite_outrange", "hard_cc_on_engage"],
    "victor": ["assassin_dive", "hard_engage_reaches_backline", "early_lane_bully"],
    "vladimir": ["anti_sustain", "hard_engage_before_scale", "early_lane_bully", "burst_before_heal_shield"],
    "volibear": ["kite_outrange", "percent_health_damage", "true_damage"],
    "warwick": ["kite_outrange", "anti_sustain", "hard_cc_on_engage"],
    "wukong": ["hard_cc_on_engage", "kite_outrange", "disengage_support"],
    "xayah": ["hard_engage_on_adc", "sustained_tank_damage", "outrange_pre_ult"],
    "xerath": ["hard_engage_reaches_backline", "assassin_dive", "anti_dash_cc"],
    "xin_zhao": ["kite_outrange", "disengage_support", "outscale_late"],
    "yasuo": ["hard_cc_on_engage", "sustained_tank_damage", "non_projectile_cc"],
    "yorick": ["aoe_clears_minions", "hard_engage_reaches_backline", "kite_outrange"],
    "yuumi": ["hard_engage_all_in", "anti_sustain", "burst_before_heal_shield"],
    "zac": ["anti_sustain", "kite_outrange", "disengage_support"],
    "zed": ["hard_cc_on_engage", "sustained_tank_damage", "group_deny_picks"],
    "ziggs": ["hard_engage_reaches_backline", "assassin_dive", "anti_dash_cc"],
    "zilean": ["anti_sustain", "hard_engage_all_in", "burst_before_heal_shield"],
    "zoe": ["spell_shield", "sustained_tank_damage", "hard_engage_reaches_backline"],
    "zyra": ["hard_engage_all_in", "assassin_dive", "aoe_clears_minions"],
}

def main():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    updated = 0
    normalized = 0

    for champ in data["champions"]:
        cid = champ["id"]

        # Normalize: ensure every champion has source, contextual fields
        if "source" not in champ:
            champ["source"] = "ls_sheet"
            normalized += 1
        if "contextual" not in champ:
            champ["contextual"] = False

        # Add counter_tags if missing
        if "counter_tags" not in champ:
            if cid in COUNTER_TAGS:
                champ["counter_tags"] = COUNTER_TAGS[cid]
                updated += 1
            else:
                print(f"WARNING: No counter_tags defined for {cid}")
                champ["counter_tags"] = []

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Done. Added counter_tags to {updated} champions. Normalized {normalized} entries.")

    # Verify
    missing = [c["id"] for c in data["champions"] if not c.get("counter_tags")]
    if missing:
        print(f"Still missing counter_tags: {missing}")
    else:
        print("All 167 champions now have counter_tags.")

if __name__ == "__main__":
    main()
