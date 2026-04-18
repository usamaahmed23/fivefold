#!/usr/bin/env python3
"""
Fivefold — Phase 0 Champion Tagging CLI
Walks through champions missing Fivefold-specific fields and lets you tag them interactively.
Saves after every champion. Fully resumable.

Usage:
    python tag.py                    # Tag next untagged champion
    python tag.py --champion ahri    # Jump to a specific champion
    python tag.py --list             # Show completion status
    python tag.py --stats            # Show tag distribution stats
"""

import json
import os
import sys
import argparse
import shutil
from collections import Counter

DATA_FILE = "champions_complete.json"
BACKUP_FILE = "champions_complete.backup.json"

# ── Color helpers ──────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
GRAY   = "\033[90m"

COLOR_DISPLAY = {
    "R": f"{RED}R(Red){RESET}",
    "G": f"{GREEN}G(Green){RESET}",
    "U": f"{BLUE}U(Blue){RESET}",
    "W": f"{WHITE}W(White){RESET}",
    "B": f"{GRAY}B(Black){RESET}",
    "C": f"{YELLOW}C(Colorless){RESET}",
}

def fmt_colors(colors):
    return " ".join(COLOR_DISPLAY.get(c, c) for c in colors) if colors else f"{GRAY}(none){RESET}"

def header(text):
    w = shutil.get_terminal_size((80, 20)).columns
    print(f"\n{BOLD}{CYAN}{'─' * w}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * w}{RESET}")

def hint(text):
    print(f"  {GRAY}{text}{RESET}")

def ask(prompt, default=None, allow_skip=True):
    """Prompt user for input. Returns None if skipped."""
    skip_hint = f" {GRAY}[Enter to skip, q to quit]{RESET}" if allow_skip else ""
    val = input(f"  {YELLOW}→{RESET} {prompt}{skip_hint}: ").strip()
    if val.lower() == "q":
        print(f"\n{YELLOW}Progress saved. Run again to continue.{RESET}\n")
        sys.exit(0)
    if val == "" and default is not None:
        return default
    return val if val else None

def ask_list(prompt, vocabulary=None, allow_skip=True):
    """Ask for a comma-separated list. Returns list or None."""
    if vocabulary:
        hint(f"Options: {', '.join(vocabulary)}")
    val = ask(prompt, allow_skip=allow_skip)
    if val is None:
        return None
    return [v.strip().lower().replace(" ", "_") for v in val.split(",") if v.strip()]

def ask_choice(prompt, choices):
    """Ask user to pick from a numbered list."""
    for i, c in enumerate(choices, 1):
        print(f"    {GRAY}{i}.{RESET} {c}")
    while True:
        val = ask(prompt)
        if val is None:
            return None
        if val.isdigit() and 1 <= int(val) <= len(choices):
            return choices[int(val) - 1]
        # allow typing the value directly
        if val.lower() in [c.lower() for c in choices]:
            return val.lower()
        print(f"  {RED}Invalid choice. Enter a number or the value.{RESET}")

# ── Vocabularies ───────────────────────────────────────────────────────────────
ROLES = ["top", "jungle", "mid", "bot", "support"]

WIN_CONDITION_TAGS = [
    "scaling", "pick", "teamfight", "split_push", "poke_siege",
    "engage_dive", "protect_the_carry", "skirmish", "global_pressure",
    "roam", "lane_bully", "objective_control", "wombo",
]

STRUCTURAL_DAMAGE = ["burst_magic", "burst_physical", "sustained_magic",
                      "sustained_physical", "mixed", "true_damage_focus", "utility_damage"]
STRUCTURAL_RANGE  = ["melee", "short", "medium", "long", "extreme"]
STRUCTURAL_LEVEL  = ["none", "low", "medium", "high"]
STRUCTURAL_SCALING = ["early", "mid", "late", "hyper_late"]

COUNTER_TAGS = [
    # damage-type counters
    "true_damage", "percent_health_damage", "anti_sustain", "grievous_wounds",
    "burst_before_heal_shield", "burst_before_shield",
    # mobility counters
    "anti_mobility", "anti_dash_cc", "hard_cc_on_engage", "hard_cc_on_dash",
    "hard_cc_before_ult", "hard_cc_during_ult", "cc_chain_before_heal",
    # engagement style counters
    "long_range_poke", "long_range_poke_adc", "outrange_medium_range",
    "poke_before_engage", "kite_outrange", "disengage_support",
    "sustained_damage_no_burst", "sustained_tank_damage",
    # dive / assassin counters
    "assassin_dive", "assassin_gap_close", "gap_close_to_backline",
    "one_shot_burst", "hard_engage_reaches_backline",
    # lane / jungle counters
    "early_lane_bully", "early_invade_pressure", "farm_denial",
    "objective_control", "split_push_outscale",
    # specific mechanic counters
    "hook_threat", "displacement_support", "spell_shield",
    "aoe_clears_minions", "aoe_cc_teamfight", "non_projectile_damage",
    "non_projectile_cc", "shield_penetration",
    # special
    "punish_immobile_mage", "punish_short_range_engage",
]

# ── Data helpers ───────────────────────────────────────────────────────────────
def load():
    with open(DATA_FILE) as f:
        return json.load(f)

def save(data):
    shutil.copy(DATA_FILE, BACKUP_FILE)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_tagged(champ):
    """Returns True if all Fivefold fields are present and non-empty."""
    return (
        champ.get("roles")
        and champ.get("win_condition_tags")
        and champ.get("structural_tags")
        and champ.get("counter_tags")
    )

def color_overlap(a, b):
    """Number of shared main colors between two champions."""
    return len(set(a.get("colors_main", [])) & set(b.get("colors_main", [])))

def find_similar(champ, all_champs, n=3):
    """Return the n already-fully-tagged champions with the most color overlap."""
    candidates = [
        c for c in all_champs
        if c["id"] != champ["id"] and is_tagged(c)
    ]
    candidates.sort(key=lambda c: color_overlap(champ, c), reverse=True)
    return candidates[:n]

# ── Tagging flow ───────────────────────────────────────────────────────────────
def tag_champion(champ, all_champs):
    header(f"{champ['name']}  —  {champ['id']}")

    print(f"\n  Main colors : {fmt_colors(champ.get('colors_main', []))}")
    if champ.get("colors_off"):
        print(f"  Off colors  : {fmt_colors(champ['colors_off'])}")
    if champ.get("ls_notes"):
        print(f"  LS notes    : {CYAN}{champ['ls_notes']}{RESET}")
    if champ.get("source") == "owner":
        print(f"  Source      : {YELLOW}owner-tagged{RESET}")

    # Show similar tagged champions as calibration anchors
    similar = find_similar(champ, all_champs)
    if similar:
        print(f"\n  {BOLD}Similar tagged champions (calibration anchors):{RESET}")
        for s in similar:
            shared = set(champ.get("colors_main", [])) & set(s.get("colors_main", []))
            print(f"    {BOLD}{s['name']}{RESET}  {fmt_colors(s['colors_main'])}  {GRAY}(shared: {', '.join(shared) or 'none'}){RESET}")
            print(f"      roles     : {', '.join(s.get('roles', []))}")
            print(f"      win_conds : {', '.join(s.get('win_condition_tags', []))}")
            st = s.get("structural_tags", {})
            print(f"      structure : engage={st.get('engage','?')}  frontline={st.get('frontline','?')}  scaling={st.get('scaling','?')}")
            print(f"      counters  : {', '.join(s.get('counter_tags', [])[:4])}...")
    else:
        print(f"\n  {GRAY}(No fully-tagged champions yet — you're blazing the trail){RESET}")

    print()

    # ── 1. Roles ──
    print(f"\n{BOLD}1. ROLES{RESET}")
    hint("Which roles can this champion be played in the draft?")
    existing_roles = champ.get("roles")
    if existing_roles:
        print(f"  Current: {', '.join(existing_roles)}")
        change = ask("Change? (y/n)", default="n")
        if change and change.lower() == "y":
            existing_roles = None

    if not existing_roles:
        roles = ask_list("Roles", vocabulary=ROLES)
        if roles:
            # validate
            roles = [r for r in roles if r in ROLES]
            champ["roles"] = roles

    # ── 2. Win condition tags ──
    print(f"\n{BOLD}2. WIN CONDITION TAGS{RESET}")
    hint("What does this champion want to DO to win the game?")
    existing_wc = champ.get("win_condition_tags")
    if existing_wc:
        print(f"  Current: {', '.join(existing_wc)}")
        change = ask("Change? (y/n)", default="n")
        if change and change.lower() == "y":
            existing_wc = None

    if not existing_wc:
        wc = ask_list("Win condition tags", vocabulary=WIN_CONDITION_TAGS)
        if wc:
            champ["win_condition_tags"] = wc

    # ── 3. Structural tags ──
    print(f"\n{BOLD}3. STRUCTURAL TAGS{RESET}")
    hint("Describes the role this champion fills in a composition.")
    st = champ.get("structural_tags", {})
    needs_structural = not st

    if not needs_structural:
        print(f"  Current: {st}")
        change = ask("Change? (y/n)", default="n")
        needs_structural = change and change.lower() == "y"

    if needs_structural:
        print(f"\n  {BOLD}Damage profile:{RESET}")
        dp = ask_choice("  Pick one", STRUCTURAL_DAMAGE)
        if dp: st["damage_profile"] = dp

        print(f"\n  {BOLD}Range:{RESET}")
        rng = ask_choice("  Pick one", STRUCTURAL_RANGE)
        if rng: st["range"] = rng

        print(f"\n  {BOLD}Engage level:{RESET}")
        hint("How much hard initiation does this champion provide?")
        eng = ask_choice("  Pick one", STRUCTURAL_LEVEL)
        if eng: st["engage"] = eng

        print(f"\n  {BOLD}Peel level:{RESET}")
        hint("How much protection can this champion provide to allies?")
        peel = ask_choice("  Pick one", STRUCTURAL_LEVEL)
        if peel: st["peel"] = peel

        print(f"\n  {BOLD}Frontline level:{RESET}")
        hint("How much of a tank / body-block presence does this champion have?")
        fl = ask_choice("  Pick one", STRUCTURAL_LEVEL)
        if fl: st["frontline"] = fl

        print(f"\n  {BOLD}Waveclear level:{RESET}")
        wc_level = ask_choice("  Pick one", STRUCTURAL_LEVEL)
        if wc_level: st["waveclear"] = wc_level

        print(f"\n  {BOLD}Scaling:{RESET}")
        hint("When does this champion hit their power spike?")
        sc = ask_choice("  Pick one", STRUCTURAL_SCALING)
        if sc: st["scaling"] = sc

        if st:
            champ["structural_tags"] = st

    # ── 4. Counter tags ──
    print(f"\n{BOLD}4. COUNTER TAGS{RESET}")
    hint("What MECHANICS beat this champion? (not champion names — the underlying reason)")
    existing_ct = champ.get("counter_tags")
    if existing_ct:
        print(f"  Current: {', '.join(existing_ct)}")
        change = ask("Change? (y/n)", default="n")
        if change and change.lower() == "y":
            existing_ct = None

    if not existing_ct:
        ct = ask_list("Counter tags", vocabulary=COUNTER_TAGS)
        if ct:
            champ["counter_tags"] = ct

    return champ

# ── Commands ───────────────────────────────────────────────────────────────────
def cmd_list(data):
    champs = data["champions"]
    total = len(champs)
    done = sum(1 for c in champs if is_tagged(c))
    print(f"\n{BOLD}Fivefold Champion Tagging Status{RESET}  —  {done}/{total} complete\n")

    tagged = [c for c in champs if is_tagged(c)]
    untagged = [c for c in champs if not is_tagged(c)]

    if tagged:
        print(f"{GREEN}✓ Tagged ({len(tagged)}):{RESET}")
        for c in tagged:
            print(f"  {c['name']}")

    if untagged:
        print(f"\n{YELLOW}○ Untagged ({len(untagged)}):{RESET}")
        for c in untagged:
            missing = []
            if not c.get("roles"): missing.append("roles")
            if not c.get("win_condition_tags"): missing.append("win_conds")
            if not c.get("structural_tags"): missing.append("structure")
            if not c.get("counter_tags"): missing.append("counters")
            print(f"  {c['name']:<20} {GRAY}missing: {', '.join(missing)}{RESET}")

def cmd_stats(data):
    champs = data["champions"]
    tagged = [c for c in champs if is_tagged(c)]
    print(f"\n{BOLD}Tag Distribution ({len(tagged)} tagged champions){RESET}\n")

    wc_counter = Counter()
    for c in tagged:
        for t in c.get("win_condition_tags", []):
            wc_counter[t] += 1
    print(f"{BOLD}Win condition tags:{RESET}")
    for tag, count in wc_counter.most_common():
        print(f"  {tag:<30} {count}")

    role_counter = Counter()
    for c in tagged:
        for r in c.get("roles", []):
            role_counter[r] += 1
    print(f"\n{BOLD}Roles:{RESET}")
    for role, count in role_counter.most_common():
        print(f"  {role:<20} {count}")

def cmd_tag(data, champion_id=None):
    champs = data["champions"]
    total = len(champs)
    done = sum(1 for c in champs if is_tagged(c))
    remaining = total - done

    print(f"\n{BOLD}Fivefold Tagging CLI{RESET}  {GRAY}—  {done}/{total} complete  ({remaining} remaining){RESET}")
    print(f"{GRAY}  At any prompt: Enter to skip field  |  q to quit and save{RESET}")

    if champion_id:
        targets = [c for c in champs if c["id"] == champion_id or c["name"].lower() == champion_id.lower()]
        if not targets:
            print(f"{RED}Champion '{champion_id}' not found.{RESET}")
            return
    else:
        targets = [c for c in champs if not is_tagged(c)]
        if not targets:
            print(f"\n{GREEN}{BOLD}All {total} champions are fully tagged! 🎉{RESET}\n")
            return

    for champ in targets:
        idx = champs.index(champ)
        updated = tag_champion(champ, champs)
        champs[idx] = updated
        data["champions"] = champs
        save(data)
        done_now = sum(1 for c in champs if is_tagged(c))
        print(f"\n  {GREEN}✓ Saved.{RESET}  {done_now}/{total} complete.")

        if champion_id:
            break  # Only tag the one specified

        if len(targets) > 1:
            cont = ask(f"\nContinue to next champion? (y/n)", default="y")
            if not cont or cont.lower() != "y":
                print(f"\n{YELLOW}Progress saved. Run again to continue.{RESET}\n")
                return

    print(f"\n{GREEN}Session complete.{RESET}\n")

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Fivefold Phase 0 Champion Tagging CLI")
    parser.add_argument("--champion", "-c", help="Tag a specific champion by name or id")
    parser.add_argument("--list", "-l", action="store_true", help="Show tagging completion status")
    parser.add_argument("--stats", "-s", action="store_true", help="Show tag distribution stats")
    args = parser.parse_args()

    if not os.path.exists(DATA_FILE):
        print(f"{RED}champions_complete.json not found. Run from the project data directory.{RESET}")
        sys.exit(1)

    data = load()

    if args.list:
        cmd_list(data)
    elif args.stats:
        cmd_stats(data)
    else:
        cmd_tag(data, champion_id=args.champion)

if __name__ == "__main__":
    main()
