"""Deterministic scoring engine.

Four axes: identity, denial, structural, survivability. Meta tiers only
influence survivability and the tiebreaker — they never drive identity or
denial scoring (see CLAUDE.md design principles).
"""
from __future__ import annotations

from . import composition, contextual
from .composition import (
    ALL_FIELD_VALUES,
    COLORS,
    LEVEL_VALUES,
    OFF_COLOR_WEIGHT,
    RANGE_VALUES,
    get_structural_value,
)
from .models import Archetype, CandidateScore, Champion, DraftState, MetaTiers

# ---------------------------------------------------------------------------
# Color-counter matrix — approximate MTG-theory-derived strength of how much
# the ROW color counters the COLUMN color. Values are rough priors meant to be
# tuned via snapshot tests, not learned.
# ---------------------------------------------------------------------------
COLOR_COUNTERS: dict[str, dict[str, float]] = {
    #      R    G    U    W    B    C
    "R": {"R": 0.25, "G": 0.70, "U": 0.65, "W": 0.20, "B": 0.35, "C": 0.40},
    "G": {"R": 0.25, "G": 0.30, "U": 0.35, "W": 0.30, "B": 0.55, "C": 0.35},
    "U": {"R": 0.65, "G": 0.55, "U": 0.30, "W": 0.30, "B": 0.60, "C": 0.45},
    "W": {"R": 0.75, "G": 0.40, "U": 0.25, "W": 0.30, "B": 0.35, "C": 0.50},
    "B": {"R": 0.35, "G": 0.45, "U": 0.60, "W": 0.55, "B": 0.30, "C": 0.55},
    "C": {"R": 0.35, "G": 0.35, "U": 0.40, "W": 0.40, "B": 0.35, "C": 0.35},
}

# Rough mapping: if a candidate is this color, what counter-tags does it tend
# to bring? This is used to match enemy vulnerabilities (their `counter_tags`)
# to what the candidate supplies. Data-derived from existing counter_tag
# vocabulary in data/champions.json.
COLOR_BRINGS: dict[str, set[str]] = {
    "R": {
        "early_all_in", "hard_engage_all_in", "hard_engage_burst",
        "hard_engage_before_scale", "hard_engage_on_adc",
        "hard_engage_reaches_backline", "assassin_dive", "assassin_gap_close",
        "early_invade_pressure", "early_lane_bully", "dive_pre_stack",
        "gap_close_to_backline", "short_cd_gap_close", "punish_roam",
    },
    "G": {
        "sustained_damage_no_burst", "sustained_tank_damage", "outscale_late",
        "split_push_outscale", "sustained_poke", "sustained_frontline_absorbs_poke",
        "tank_out_sustain_early",
    },
    "U": {
        "kite_outrange", "outrange_medium_range", "outrange_pre_ult",
        "outrange_passive_range", "long_range_poke", "long_range_poke_adc",
        "long_range_keeps_distance", "ranged_harass", "disengage_support",
        "anti_mobility", "anti_dash_cc", "reveal_stealth", "oracle_sweep",
        "group_deny_picks", "farm_denial", "zone_control", "aoe_zone_control",
        "aoe_clears_minions", "spell_shield", "kite_mobility", "objective_control",
    },
    "W": {
        "hard_cc_on_engage", "hard_cc_before_ult", "hard_cc_on_dash",
        "hard_cc_stops_charge", "hard_cc_during_ult", "hard_cc_outside_w_range",
        "cc_chain_before_heal", "displacement_support", "shield_peel",
        "hook_threat", "minion_block", "non_projectile_cc", "non_dash_gap_close",
        "aoe_cc_teamfight", "punish_short_range_engage",
    },
    "B": {
        "burst_before_heal_shield", "burst_before_kite", "burst_before_shield",
        "burst_before_scale", "burst_before_passive_reset",
        "anti_revive_burst", "anti_sustain", "one_shot_burst",
        "shield_penetration", "percent_health_damage", "true_damage",
        "burst_through_bailout", "punish_immobile_mage",
    },
    "C": {
        "shutdown_colorless_carry", "deny_void_coral",
        "aoe_damage_through_possession", "stat_steal_counters_possession",
        "sustained_tank_denies_snowball", "non_projectile_damage",
        "short_range_skirmisher",
    },
}

WEIGHTS_BY_PHASE: dict[str, dict[str, float]] = {
    "ban1":  {"identity": 0.40, "denial": 0.40, "structural": 0.10, "survivability": 0.10},
    "pick1": {"identity": 0.42, "denial": 0.32, "structural": 0.21, "survivability": 0.05},
    "ban2":  {"identity": 0.30, "denial": 0.40, "structural": 0.20, "survivability": 0.10},
    "pick2": {"identity": 0.22, "denial": 0.22, "structural": 0.46, "survivability": 0.10},
}

TIEBREAKER_TOLERANCE = 0.03

ALL_ROLES: tuple[str, ...] = ("top", "jungle", "mid", "bot", "support")

# ---------------------------------------------------------------------------
# Flex bonus — red side pick1 counter-pick ambiguity.
#
# Red side sees blue's first pick before locking their own. A flex champion
# (2+ roles) hides which lane you're filling until lock-in, denying blue
# the ability to react precisely. LS and PV explicitly flag flex picks as
# "really undervalued" on red side. Bonus scales with number of viable roles.
# Only applies to red side pick actions in pick1.
# ---------------------------------------------------------------------------
def _flex_bonus(cand: Champion, draft_state: DraftState) -> float:
    if (draft_state.action_to_take != "pick"
            or draft_state.side_to_act != "red"
            or draft_state.phase != "pick1"):
        return 0.0
    n = len(cand.roles)
    if n >= 4:
        return 0.08  # 4+ roles: maximum ambiguity (e.g. Ivern jungle/top/mid/support)
    if n == 3:
        return 0.05  # 3 roles: strong flex signal
    if n == 2:
        return 0.03  # 2 roles: standard flex pick
    return 0.0


# ---------------------------------------------------------------------------
# B-constraint modifier — B-primary picks in pick1 reveal conditions.
#
# B champions have conditions the team must accommodate (Karthus can't share
# magic damage, Tryndamere needs 4v5 enablers, Diana needs engage). Picking
# them in pick1 tells the enemy exactly what your team can't draft next,
# letting them deny those conditions in real time.
#
# Only applies when R is absent — R-heavy B picks (Draven B/R, Lucian R/B)
# are already penalised by the phase-fit modifier. Picks only.
# ---------------------------------------------------------------------------
def _b_constraint_modifier(colors_main: list[str], phase: str, action: str) -> float:
    if action == "ban" or phase != "pick1":
        return 0.0
    if "R" in colors_main:
        return 0.0  # already covered by phase-fit R penalty
    if "B" not in colors_main:
        return 0.0
    if colors_main[0] == "B":
        return -0.05  # B leads: conditions are the core identity, very constraining
    return -0.02      # B secondary: mild constraint, primary color provides clarity


# ---------------------------------------------------------------------------
# Phase-fit modifier — R-heavy picks are penalised in early phases.
#
# Because League drafts are fully face-up, anchoring pick1/ban1 with a
# linear R (or B/R) champion telegraphs your gameplan and lets the opponent
# sideboard in real time. LS calls this the "who's the beatdown" problem.
# R picks are best used in pick2 to close against a greedy enemy, not to
# define the draft identity early.
#
# Applied additively to the total score. Only affects pick actions — bans
# already score from the enemy's perspective so no modifier needed there.
# ---------------------------------------------------------------------------
_PHASE_FIT_EARLY = {"ban1", "pick1"}


def _phase_fit_modifier(colors_main: list[str], phase: str, action: str) -> float:
    if action == "ban" or not colors_main:
        return 0.0
    is_r = "R" in colors_main
    if not is_r:
        return 0.0
    only_rb = set(colors_main) <= {"R", "B"}
    mono_r = colors_main == ["R"]
    if phase in _PHASE_FIT_EARLY:
        if mono_r:
            return -0.10  # pure aggression: immediately reveals you're the beatdown
        if only_rb:
            return -0.06  # conditional aggression: still telegraphs a linear gameplan
        return -0.03      # R present but other colors add flex — mild signal
    if phase == "pick2":
        return +0.04      # pick2 closer: rewarded for waiting
    return 0.0


def _unfilled_roles(picks: list[str], champions: dict[str, Champion]) -> set[str]:
    """Return the roles this side can still fill given its current picks.

    We assign each pick to exactly one role using a deterministic greedy pass
    ordered by flexibility: single-role champs first (they have no choice),
    then flex champs claim their first declared role that isn't already
    taken. This matches how drafts actually play out — a pure support (Braum)
    locks support, then a flex pick (Karma) slides to a remaining open role
    like mid if support is already taken.
    """
    pick_champs = [champions.get(p) for p in picks]
    if not pick_champs or any(c is None or not c.roles for c in pick_champs):
        claimed = {c.roles[0] for c in pick_champs if c and c.roles}
        return set(ALL_ROLES) - claimed

    order = sorted(range(len(pick_champs)), key=lambda i: len(pick_champs[i].roles))  # type: ignore[arg-type]
    claimed: set[str] = set()
    fallback: set[str] = set()
    for i in order:
        ch = pick_champs[i]
        if ch is None or not ch.roles:
            continue
        for r in ch.roles:
            if r not in claimed:
                claimed.add(r)
                break
        else:
            # Every role this pick could play is already claimed — they must
            # be stealing someone's role, so record their primary for the
            # fallback set but don't claim a second role.
            fallback.add(ch.roles[0])
    return set(ALL_ROLES) - (claimed | fallback)


def _role_fits(cand: Champion, unfilled: set[str]) -> bool:
    if not cand.roles:
        return True
    return any(r in unfilled for r in cand.roles)


def _is_real_bot_anchor(cand: Champion) -> bool:
    """Whether this champion is a credible backline/bot anchor in LS terms.

    This is intentionally broader than "marksman only" so legitimate APC bot
    patterns remain available, but narrower than "anything with bot in roles".
    """
    if "bot" not in (cand.roles or []):
        return False

    kit = set(cand.kit_tags or [])
    win = set(cand.win_condition_tags or [])
    st = cand.structural_tags

    if "marksman" in kit:
        return True

    if st is None or st.range != "long":
        return False

    if {"protect_the_carry", "poke_siege", "scaling", "pick", "global_pressure"} & win:
        if {"artillery", "control_mage", "battle_mage", "poke_support", "enchanter", "burst_mage"} & kit:
            # Exclude low-structure all-in impostors that happen to have bot in
            # their role list but are not real backline anchors.
            if "engage_dive" in win and st.frontline == "low" and st.peel == "low":
                return False
            return True

    return False


def _is_real_support_anchor(cand: Champion) -> bool:
    """Whether this champion is a credible support anchor rather than a fringe slot."""
    if "support" not in (cand.roles or []):
        return False

    kit = set(cand.kit_tags or [])
    win = set(cand.win_condition_tags or [])
    st = cand.structural_tags

    if st is None:
        return False

    if {"enchanter", "peel_support", "engage_support", "hook_support"} & kit:
        return True

    if st.frontline == "high" and st.engage in ("medium", "high"):
        return True

    if st.peel == "high":
        return True

    if {"protect_the_carry", "pick", "teamfight", "objective_control"} & win and (
        st.peel in ("medium", "high") or st.engage in ("medium", "high")
    ):
        return True

    return False


def _is_real_mid_anchor(cand: Champion) -> bool:
    """Whether this champion is a credible mid-lane anchor for a control shell."""
    if "mid" not in (cand.roles or []):
        return False

    kit = set(cand.kit_tags or [])
    win = set(cand.win_condition_tags or [])
    st = cand.structural_tags

    if st is None:
        return False
    if st.range not in ("medium", "long"):
        return False
    if "assassin" in kit:
        return False

    if st.waveclear == "high":
        return True

    if {"control_mage", "artillery", "global_ult", "point_click_cc"} & kit:
        if {"scaling", "objective_control", "global_pressure", "pick", "poke_siege"} & win:
            return True

    if st.peel in ("medium", "high") and {"scaling", "teamfight", "objective_control"} & win:
        return True

    return False


def _is_support_enabler(cand: Champion) -> bool:
    """Support branch that meaningfully enables a carry shell."""
    if not _is_real_support_anchor(cand):
        return False
    kit = set(cand.kit_tags or [])
    win = set(cand.win_condition_tags or [])
    st = cand.structural_tags
    return bool(
        "protect_the_carry" in win
        or (
            st is not None
            and st.peel == "high"
            and bool({"enchanter", "peel_support"} & kit)
        )
    )


def _support_unlock_modifier(
    cand: Champion,
    draft_state: DraftState,
    champions: dict[str, Champion],
) -> float:
    """Reward explicit enchanter-unlocked melee carry lines.

    Some carries are not generically good late-game pieces, but become real
    draft branches once a white/enchanter ally is already committed. Keep this
    data-driven by requiring an explicit synergy edge in champion data.
    """
    if draft_state.action_to_take != "pick" or not draft_state.our_picks:
        return 0.0

    st = cand.structural_tags
    if st is None or st.damage_profile not in ("ad", "mixed") or st.range != "melee":
        return 0.0

    kit = set(cand.kit_tags or [])
    win = set(cand.win_condition_tags or [])
    if not ({"juggernaut", "skirmisher", "diver"} & kit):
        return 0.0
    if not ({"cleanse_self", "self_peel"} & kit):
        return 0.0
    if not ({"skirmish", "lane_bully", "split_push"} & win):
        return 0.0

    enchanter_allies = {
        pid
        for pid in draft_state.our_picks
        if (ally := champions.get(pid)) and {"enchanter", "peel_support"} & set(ally.kit_tags or [])
    }
    if not enchanter_allies:
        return 0.0

    explicit_unlocks = enchanter_allies & set(cand.synergy_with or [])
    if not explicit_unlocks:
        return 0.0

    bonus = 0.05
    if len(explicit_unlocks) >= 2:
        bonus += 0.015
    return min(0.08, bonus)


def _is_independent_side_laner(cand: Champion) -> bool:
    """Whether the champion creates real side-lane pressure in LS terms."""
    roles = set(cand.roles or [])
    if not roles or roles <= {"bot", "support"}:
        return False

    st = cand.structural_tags
    if st is None or st.damage_profile not in ("ad", "mixed"):
        return False

    kit = set(cand.kit_tags or [])
    win = set(cand.win_condition_tags or [])

    if not ({"split_push", "global_pressure"} & win):
        return False

    if not {"splitpusher", "skirmisher", "global_ult", "high_mobility", "self_peel", "cleanse_self"} & kit:
        return False

    return True


def _side_lane_branch_modifier(
    cand: Champion,
    draft_state: DraftState,
    champions: dict[str, Champion],
) -> float:
    """Reward independent side-lane branches once a real shell exists.

    LS-style drafts can branch into 1-4 or side-lane pressure lines, but only
    once the rest of the deck is stable enough to absorb it. This should not
    make Quinn/Fiora/Trynd blind-openers; it should make them appear more
    naturally once a four-man shell or scaling enemy gives them permission.
    """
    if draft_state.action_to_take != "pick":
        return 0.0
    if not _is_independent_side_laner(cand):
        return 0.0

    our_picks = draft_state.our_picks
    if len(our_picks) < 2:
        return -0.03

    comp = composition.analyze(our_picks, champions, draft_state)
    ally_win_tags = {
        tag
        for pid in our_picks
        if (ally := champions.get(pid))
        for tag in (ally.win_condition_tags or [])
    }

    stable_four_man = (
        comp.structural_avg.get("frontline", 0.0) >= 0.55
        or any(
            _is_real_support_anchor(champions[pid])
            or _is_real_mid_anchor(champions[pid])
            or _is_real_bot_anchor(champions[pid])
            for pid in our_picks
            if pid in champions
        )
    ) and bool({"teamfight", "objective_control", "protect_the_carry", "scaling"} & ally_win_tags)

    if not stable_four_man:
        return 0.0

    bonus = 0.04
    kit = set(cand.kit_tags or [])
    win = set(cand.win_condition_tags or [])
    if {"global_pressure", "roam"} & win or {"global_ult", "high_mobility"} & kit:
        bonus += 0.01

    enemy_confidence = _enemy_read_confidence(draft_state.enemy_picks)
    if enemy_confidence >= 0.66:
        enemy_win_tags = {
            tag
            for pid in draft_state.enemy_picks
            if (enemy := champions.get(pid))
            for tag in (enemy.win_condition_tags or [])
        }
        if {"protect_the_carry", "scaling", "objective_control", "teamfight"} & enemy_win_tags:
            bonus += 0.015

    return min(0.07, bonus)


def _ambiguous_roles(picks: list[str], champions: dict[str, Champion]) -> set[str]:
    """Roles that remain genuinely flexible across current picks."""
    role_counts: dict[str, int] = {r: 0 for r in ALL_ROLES}
    for pid in picks:
        ch = champions.get(pid)
        if ch is None or len(ch.roles) < 2:
            continue
        for role in ch.roles:
            role_counts[role] += 1
    return {role for role, count in role_counts.items() if count >= 2}


def _preserves_flex_branch(
    cand: Champion,
    unfilled_roles: set[str],
    ambiguous_roles: set[str],
) -> bool:
    roles = set(cand.roles or [])
    if len(roles) < 2:
        return False
    return bool(roles & unfilled_roles) and bool((roles - unfilled_roles) & ambiguous_roles)


def _primary_role(champ: Champion) -> str:
    return (champ.roles or ["misc"])[0]


def _recommendation_bucket(champ: Champion) -> str:
    """Coarse branch bucket used to keep diversified picks meaningfully distinct."""
    st = champ.structural_tags
    win = set(champ.win_condition_tags or [])

    if _is_support_enabler(champ):
        return "support_enabler"
    if _is_real_support_anchor(champ):
        return "support_anchor"
    if _is_real_bot_anchor(champ):
        return "bot_anchor"
    if _is_real_mid_anchor(champ):
        return "mid_anchor"
    if len(champ.roles or []) >= 2:
        return "flex"
    if "protect_the_carry" in win:
        return "protect"
    if "engage_dive" in win or (st and st.engage == "high"):
        return "engage"
    if st and st.frontline == "high":
        return "frontline"
    return _primary_role(champ)


def _pick_distinct_candidate(
    ranked: list[CandidateScore],
    champions: dict[str, Champion],
    seen_ids: set[str],
    used_roles: set[str],
    used_buckets: set[str],
    key_fn,
    tolerance: float = 0.04,
) -> CandidateScore | None:
    pool = [s for s in ranked if s.champion_id not in seen_ids]
    if not pool:
        return None

    pool.sort(key=lambda s: (-key_fn(s), -s.total, -s.meta_contribution))
    best_value = key_fn(pool[0])
    viable = [s for s in pool if best_value - key_fn(s) <= tolerance]

    for require_new_role, require_new_bucket in (
        (True, True),
        (False, True),
        (True, False),
        (False, False),
    ):
        for s in viable:
            champ = champions[s.champion_id]
            role = _primary_role(champ)
            bucket = _recommendation_bucket(champ)
            if require_new_role and role in used_roles:
                continue
            if require_new_bucket and bucket in used_buckets:
                continue
            return s

    return pool[0]


def _pick_denial_candidate(
    ranked: list[CandidateScore],
    champions: dict[str, Champion],
    seen_ids: set[str],
    used_roles: set[str],
    used_buckets: set[str],
    enemy_confidence: float,
) -> CandidateScore | None:
    pool = [s for s in ranked if s.champion_id not in seen_ids]
    if not pool:
        return None

    top_total = max(s.total for s in pool)
    if enemy_confidence <= 0.34:
        max_total_gap = 0.08
    elif enemy_confidence <= 0.67:
        max_total_gap = 0.12
    else:
        max_total_gap = 0.18

    viable = [s for s in pool if top_total - s.total <= max_total_gap]
    denial_weight = min(0.8, 0.55 + 0.25 * enemy_confidence)
    total_weight = 1.0 - denial_weight
    return _pick_distinct_candidate(
        viable or pool,
        champions,
        seen_ids,
        used_roles,
        used_buckets,
        key_fn=lambda s: denial_weight * s.denial + total_weight * s.total,
        tolerance=0.04 + 0.04 * enemy_confidence,
    )


_ROLE_RATIONALE_PREFIX = {
    "best_overall": "Best all-around fit at this point in the draft.",
    "structural_fill": "Structural branch — patches the biggest remaining comp holes.",
    "support_enabler": "Support branch — doubles down on enabling or protecting your carry line.",
    "flex_branch": "Flex branch — keeps lane assignments open and preserves counterpick leverage.",
    "best_denial": "Denial branch — pressures the enemy's currently declared line hardest.",
    "identity_anchor": "Identity branch — stays closest to your current LS color plan.",
    "alt": "Alternate branch — viable line if you want to pivot away from the top recommendation.",
}


# ---------------------------------------------------------------------------
# Archetype bonuses — kit-based synergy and counter lookups
# ---------------------------------------------------------------------------
def _synergy_bonus(
    cand_id: str,
    our_picks: list[str],
    archetypes: list[Archetype],
) -> float:
    """Return a 0..0.2 bonus if cand joins a synergy archetype already anchored
    by one of our picks. Scales with how many allies share the archetype."""
    if not our_picks or not archetypes:
        return 0.0
    our_set = set(our_picks)
    best = 0.0
    for arch in archetypes:
        if arch.kind != "synergy":
            continue
        members = set(arch.members)
        if cand_id not in members:
            continue
        allies_in = len(members & our_set)
        if allies_in >= 1:
            # Archetype fit should ramp with declared support, not behave like
            # a near-full combo reward the moment one ally happens to share a
            # bucket. This keeps pair/archetype logic as a late shaper rather
            # than an early anchor.
            if allies_in == 1:
                bonus = 0.04
            elif allies_in == 2:
                bonus = 0.08
            else:
                bonus = 0.11
            best = max(best, bonus)
    return best


def _counter_bonus(
    cand_id: str,
    enemy_picks: list[str],
    champions: dict[str, Champion],
    archetypes: list[Archetype],
) -> float:
    """Return a 0..0.25 bonus if cand belongs to a counter archetype whose
    targets overlap with tags present on the enemy team."""
    if not enemy_picks or not archetypes:
        return 0.0
    enemy_tags: set[str] = set()
    for pid in enemy_picks:
        ch = champions.get(pid)
        if ch:
            enemy_tags.update(ch.kit_tags)
    if not enemy_tags:
        return 0.0
    best = 0.0
    for arch in archetypes:
        if arch.kind != "counter":
            continue
        if cand_id not in set(arch.members):
            continue
        targets = set(arch.targets)
        overlap = len(targets & enemy_tags)
        if overlap:
            bonus = min(0.25, 0.10 + 0.08 * overlap)
            best = max(best, bonus)
    return best


def _enemy_read_confidence(enemy_picks: list[str]) -> float:
    """How much draft information do we actually have?

    A single revealed enemy champion should not let denial/counter logic act
    as though we fully understand the enemy's deck. Confidence ramps through
    the draft and reaches full strength once several picks are visible.
    """
    if not enemy_picks:
        return 0.0
    return min(1.0, len(enemy_picks) / 3.0)


def _opener_modifier(
    cand: Champion,
    draft_state: DraftState,
) -> float:
    """Reward stable early anchors, penalise setup-reliant early commits.

    Early picks should usually keep the draft open and let us adapt. We give a
    small bump to versatile/white/flex anchors and penalise picks whose value
    depends on heavy setup (e.g. Yasuo-style airborne chains or low-frontline
    wombo carries) before that setup exists.
    """
    if draft_state.action_to_take != "pick" or draft_state.phase != "pick1":
        return 0.0
    if len(draft_state.our_picks) >= 2:
        return 0.0

    context_scale = 1.0 if not draft_state.our_picks else 0.65

    st = cand.structural_tags
    main = set(cand.colors_main or [])
    kit = set(cand.kit_tags or [])
    win = set(cand.win_condition_tags or [])

    bonus = 0.0
    if "W" in main:
        bonus += 0.03
    if "adaptive_form" in kit:
        bonus += 0.015
    if len(cand.roles) >= 2:
        bonus += 0.02
    if st:
        if st.frontline == "high":
            bonus += 0.05
        elif st.frontline == "medium":
            bonus += 0.025
        if st.peel == "high":
            bonus += 0.03
        elif st.peel == "medium":
            bonus += 0.015
        if st.range in ("medium", "long") and st.damage_profile in ("ad", "mixed"):
            bonus += 0.015
    if {"marksman", "enchanter", "engage_tank", "peel_support"} & kit:
        bonus += 0.015

    penalty = 0.0
    if "airborne_chain" in kit:
        penalty += 0.10
    if "wombo" in win and st and st.frontline == "low" and st.peel == "low":
        penalty += 0.07
    if "engage_dive" in win and st and st.frontline == "low" and st.peel == "low":
        penalty += 0.04
    if "protect_the_carry" in win and st and st.frontline == "low" and not draft_state.our_picks:
        penalty += 0.03
    if "poke_siege" in win and st and st.frontline == "low" and st.peel == "low":
        penalty += 0.03
    if st and st.frontline == "low" and st.peel == "low":
        penalty += 0.02
    if "B" in main:
        penalty += 0.02
    if "B" in (cand.colors_off or []):
        penalty += 0.01

    return context_scale * (bonus - penalty)


def _conditional_pick_modifier(
    cand: Champion,
    draft_state: DraftState,
) -> float:
    """Penalise narrow exploit picks until the draft actually justifies them.

    LS-style drafting rewards stable, adaptable structure. Assassins, hard
    counter-junglers, and other binary exploit picks should not appear as
    generic recommendations when the enemy or our own shell is still only
    partially declared.
    """
    if draft_state.action_to_take != "pick":
        return 0.0

    enemy_confidence = _enemy_read_confidence(draft_state.enemy_picks)
    our_count = len(draft_state.our_picks)

    kit = set(cand.kit_tags or [])
    win = set(cand.win_condition_tags or [])
    st = cand.structural_tags

    penalty = 0.0

    if "counter_pick_specialist" in kit:
        penalty += 0.10 * (1.0 - enemy_confidence)

    if "assassin" in kit:
        assassin_penalty = 0.08 * (1.0 - enemy_confidence)
        if our_count < 4:
            assassin_penalty += 0.03
        if "adaptive_form" in kit:
            assassin_penalty *= 0.5
        penalty += assassin_penalty

    if {"pick", "skirmish"} & win and "high_mobility" in kit and "assassin" not in kit:
        penalty += 0.03 * (1.0 - enemy_confidence)

    # Solo-lane hyper-scalers should not anchor first rotation just because
    # they match a blue shell on paper. LS-style drafting prefers keeping the
    # draft open early, not revealing a weak early, XP-hungry inevitability
    # piece before the shell is actually secured.
    if (
        draft_state.phase == "pick1"
        and our_count < 3
        and st is not None
        and st.frontline == "low"
        and "scaling_hyper" in kit
        and "marksman" in kit
        and {"top", "mid"} & set(cand.roles or [])
    ):
        penalty += 0.12

    # Jungle-only engage tanks with very low independent utility are often
    # hard counter tools, not generic first-line recommendations.
    if (
        cand.roles == ["jungle"]
        and st is not None
        and st.frontline == "high"
        and st.waveclear == "low"
        and st.peel == "low"
        and "point_click_cc" in kit
    ):
        penalty += 0.06 * (1.0 - enemy_confidence)

    # Reward true control/scaling mids a little once a blue shell is actually
    # forming, so they stop losing ties to narrower exploit picks.
    if (
        st is not None
        and st.range == "long"
        and st.scaling == "late"
        and our_count >= 2
        and {"control_mage", "global_ult", "point_click_cc"} & kit
    ):
        main = set(cand.colors_main or [])
        if {"U", "W", "G"} & main:
            return max(-0.16, 0.03 - penalty)

    return max(-0.16, -penalty)


# ---------------------------------------------------------------------------
# Individual axis scores
# ---------------------------------------------------------------------------
def score_identity(
    cand: Champion, our_picks: list[str], champions: dict[str, Champion], state: DraftState
) -> float:
    if not our_picks:
        return 0.5
    comp = composition.analyze(our_picks, champions, state)
    total = comp.total_color_mass
    if total <= 0:
        return 0.5
    weights = {c: comp.declared_colors[c] / total for c in COLORS}
    cand_r = contextual.resolve(cand, state)

    score = 0.0
    for c in cand_r.colors_main:
        score += weights[c]
    for c in cand_r.colors_off:
        score += OFF_COLOR_WEIGHT * weights[c]

    return min(1.0, score)


def score_denial(
    cand: Champion, enemy_picks: list[str], champions: dict[str, Champion], state: DraftState
) -> float:
    if not enemy_picks:
        return 0.5
    enemy_comp = composition.analyze(enemy_picks, champions, state)
    total = enemy_comp.total_color_mass
    if total <= 0:
        return 0.5
    weights = {c: enemy_comp.declared_colors[c] / total for c in COLORS}
    cand_r = contextual.resolve(cand, state)

    # Average counter strength across candidate's main colors (so a 2-color
    # champ doesn't automatically dominate a 1-color champ). Off colors
    # contribute only a small additive bonus.
    n_main = max(1, len(cand_r.colors_main))
    main_sum = 0.0
    for cc in cand_r.colors_main:
        main_sum += sum(weights[ec] * COLOR_COUNTERS[cc][ec] for ec in COLORS)
    color_score = main_sum / n_main
    for cc in cand_r.colors_off:
        color_score += 0.15 * sum(
            weights[ec] * COLOR_COUNTERS[cc][ec] for ec in COLORS
        )
    color_score = min(1.0, color_score)

    # Tag capability match: do candidate's color-brought capabilities hit
    # tags the enemy is known to be vulnerable to?
    enemy_weaknesses: set[str] = set()
    for pid in enemy_picks:
        ch = champions.get(pid)
        if ch:
            enemy_weaknesses.update(ch.counter_tags)
    cand_brings: set[str] = set()
    for c in cand_r.colors_main:
        cand_brings |= COLOR_BRINGS.get(c, set())
    for c in cand_r.colors_off:
        cand_brings |= COLOR_BRINGS.get(c, set())
    if enemy_weaknesses:
        overlap = len(cand_brings & enemy_weaknesses)
        tag_score = min(1.0, overlap / max(2.0, len(enemy_picks) * 1.5))
    else:
        tag_score = 0.5

    confidence = _enemy_read_confidence(enemy_picks)

    # strong_against_tags: explicit "I beat comps with these vulnerabilities"
    # bonus on top of the color-derived score. Counter-pick specialists (e.g.
    # Sona) use this to express that their value is conditional on enemy shape.
    strong_against_bonus = 0.0
    if cand_r.strong_against_tags and enemy_weaknesses:
        explicit_overlap = len(set(cand_r.strong_against_tags) & enemy_weaknesses)
        strong_against_bonus = min(0.15, explicit_overlap * 0.05) * confidence

    # Explicit champion counters: if any enemy pick lists this candidate in
    # their countered_by, or candidate lists that enemy in its own countered_by
    # (meaning the enemy beats us — negative bonus as a pick, positive as denial
    # of that enemy's counter pick). Here we reward picking a champ that
    # explicitly counters someone on the enemy team (+0.05 per enemy, cap +0.15).
    counter_bonus = 0.0
    for pid in enemy_picks:
        enemy_ch = champions.get(pid)
        if enemy_ch and cand.id in enemy_ch.countered_by:
            counter_bonus += 0.05
    counter_bonus = min(0.15, counter_bonus) * confidence

    raw = 0.65 * color_score + 0.35 * tag_score + strong_against_bonus + counter_bonus
    # Interpolate back toward neutral when the enemy's identity is still only
    # partially revealed. This prevents "I saw one ADC, lock Yasuo" behaviour.
    return min(1.0, max(0.0, 0.5 + confidence * (raw - 0.5)))


def score_structural(
    cand: Champion, our_picks: list[str], champions: dict[str, Champion], state: DraftState
) -> float:
    cand_r = contextual.resolve(cand, state)
    comp = composition.analyze(our_picks, champions, state)
    unfilled_roles = _unfilled_roles(our_picks, champions)

    # Physical damage gap: if the team has 2+ picks with no AD source, reward AD candidates.
    ad_gap_bonus = 0.0
    if len(our_picks) >= 2:
        ad_count = sum(
            1 for pid in our_picks
            if (ch := champions.get(pid)) and
               ch.structural_tags is not None and
               ch.structural_tags.damage_profile in ("ad", "mixed")
        )
        if ad_count == 0 and cand_r.structural_tags is not None and cand_r.structural_tags.damage_profile in ("ad", "mixed"):
            ad_gap_bonus = 0.12
        elif ad_count == 0 and len(our_picks) >= 3 and cand_r.structural_tags is not None and cand_r.structural_tags.damage_profile in ("ad", "mixed"):
            ad_gap_bonus = 0.12

    bot_anchor_bonus = 0.0
    bot_anchor_penalty = 0.0
    if len(our_picks) >= 2 and "bot" in unfilled_roles:
        if _is_real_bot_anchor(cand_r):
            bot_anchor_bonus = 0.10
        elif "bot" in (cand_r.roles or []):
            # Candidate can technically go bot, but does not provide the kind of
            # backline anchor the draft still lacks.
            bot_anchor_penalty = 0.08

    support_anchor_bonus = 0.0
    support_anchor_penalty = 0.0
    if len(our_picks) >= 2 and "support" in unfilled_roles:
        if _is_real_support_anchor(cand_r):
            support_anchor_bonus = 0.08
        elif "support" in (cand_r.roles or []):
            support_anchor_penalty = 0.07

    mid_anchor_bonus = 0.0
    if len(our_picks) >= 2 and "mid" in unfilled_roles and _is_real_mid_anchor(cand_r):
        blue_mass = comp.declared_colors.get("U", 0.0) + comp.declared_colors.get("W", 0.0) + comp.declared_colors.get("G", 0.0)
        if blue_mass >= 1.35:
            mid_anchor_bonus = 0.08
        elif blue_mass >= 0.7:
            mid_anchor_bonus = 0.04

    # AP-saturation applies even without structural_tags on the candidate —
    # it's a kit-tag signal, independent of the candidate's own profile.
    solo_magic_penalty = 0.0
    if "requires_solo_magic" in (cand_r.kit_tags or []):
        ap_allies = sum(
            1 for pid in our_picks
            if (ch := champions.get(pid)) and
               ch.structural_tags is not None and
               ch.structural_tags.damage_profile == "ap"
        )
        solo_magic_penalty = min(0.40, ap_allies * 0.20)

    # Without any tag data to reason about, stay neutral (minus solo-magic).
    if cand_r.structural_tags is None or not comp.structural_avg:
        return max(
            0.0,
            (
                0.5
                - solo_magic_penalty
                + bot_anchor_bonus
                - bot_anchor_penalty
                + support_anchor_bonus
                - support_anchor_penalty
                + mid_anchor_bonus
            ),
        )

    cand_st = cand_r.structural_tags

    # Damage profile diversity: a comp should never be mono-AP or mono-AD.
    # Penalty starts at 1 same-profile ally so the engine nudges toward diversity
    # before the comp is already locked into a one-dimensional damage pattern.
    diversity_penalty = 0.0
    cand_profile = cand_st.damage_profile if cand_st else None
    if cand_profile in ("ap", "ad"):
        same_profile_allies = sum(
            1 for pid in our_picks
            if (ch := champions.get(pid)) and
               ch.structural_tags is not None and
               ch.structural_tags.damage_profile == cand_profile
        )
        if same_profile_allies >= 4:
            diversity_penalty = 0.50
        elif same_profile_allies == 3:
            diversity_penalty = 0.35
        elif same_profile_allies == 2:
            diversity_penalty = 0.20
        elif same_profile_allies == 1:
            diversity_penalty = 0.08

    # Share a cap between solo-magic and diversity — both punish AP overlap,
    # so take the larger signal rather than stacking them.
    penalty = max(solo_magic_penalty, diversity_penalty)

    # Range diversity: a comp with 3+ melee champions needs ranged coverage.
    cand_range = cand_st.range if cand_st else None
    if cand_range in ("melee", "short"):
        melee_allies = sum(
            1 for pid in our_picks
            if (ch := champions.get(pid)) and
               ch.structural_tags is not None and
               ch.structural_tags.range in ("melee", "short")
        )
        if melee_allies >= 4:
            penalty += 0.35
        elif melee_allies == 3:
            penalty += 0.20
        elif melee_allies == 2:
            penalty += 0.08

    if comp.holes:
        # Synthetic holes for damage-shape coverage.
        normal_holes = [f for f in comp.holes if f not in {"ad_source", "ranged_ad_source"}]
        ad_source_hole = "ad_source" in comp.holes
        ranged_ad_hole = "ranged_ad_source" in comp.holes
        ad_source_fill = (
            ad_source_hole
            and cand_r.structural_tags is not None
            and cand_r.structural_tags.damage_profile in ("ad", "mixed")
        )
        ranged_ad_fill = (
            ranged_ad_hole
            and cand_r.structural_tags is not None
            and cand_r.structural_tags.damage_profile in ("ad", "mixed")
            and cand_r.structural_tags.range in ("short", "medium", "long")
        )
        # Use ALL_FIELD_VALUES so range holes ("melee"/"long" values) are scored correctly.
        lvls = [ALL_FIELD_VALUES.get(get_structural_value(cand_r, f) or "none", 0.0) for f in normal_holes]
        if ad_source_hole:
            lvls.append(0.9 if ad_source_fill else 0.0)
        if ranged_ad_hole:
            lvls.append(0.95 if ranged_ad_fill else 0.0)
        coverage = sum(lvls) / len(lvls) if lvls else 0.0
        # Keep structural influential without making one "perfect" hole-filler
        # instantly dominate the whole recommendation. This is especially
        # important while structural data is still only partially populated.
        score = (
            0.40
            + 0.45 * coverage
            - penalty
            + ad_gap_bonus
            + bot_anchor_bonus
            - bot_anchor_penalty
            + support_anchor_bonus
            - support_anchor_penalty
            + mid_anchor_bonus
        )
        return max(0.0, min(1.0, score))

    return max(
        0.0,
        min(
            1.0,
            (
                0.55
                - penalty
                + ad_gap_bonus
                + bot_anchor_bonus
                - bot_anchor_penalty
                + support_anchor_bonus
                - support_anchor_penalty
                + mid_anchor_bonus
            ),
        ),
    )


def _meta_contribution(cand: Champion, meta_tiers: MetaTiers) -> float:
    best = 0.0
    for role in cand.roles:
        tier_list = meta_tiers.tiers.get(role, [])
        if cand.id in tier_list:
            pos = tier_list.index(cand.id)
            best = max(best, 0.5 * (1.0 - pos / max(1, len(tier_list))))
    return best


def score_survivability(
    cand: Champion, state: DraftState, meta_tiers: MetaTiers
) -> float:
    return min(1.0, 0.5 + 0.35 * _meta_contribution(cand, meta_tiers))


def _coherence_modifier(
    cand: Champion,
    team_picks: list[str],
    champions: dict[str, Champion],
    archetypes: list[Archetype],
) -> float:
    """Small total-score adjustment for explicit pairing fit.

    This intentionally sits outside the raw identity axis. Fivefold's thesis is
    that drafts are not pairwise-synergy optimization problems, so pair/archetype
    fit should shade close recommendations rather than redefine "identity".
    """
    if not team_picks:
        return 0.0

    if len(team_picks) == 1:
        context_scale = 0.30
    elif len(team_picks) == 2:
        context_scale = 0.55
    elif len(team_picks) == 3:
        context_scale = 0.80
    else:
        context_scale = 1.0

    synergy_allies = {
        pid for pid in team_picks
        if pid in cand.synergy_with
        or ((ch := champions.get(pid)) and cand.id in ch.synergy_with)
    }
    weak_allies = {
        pid for pid in team_picks
        if pid in cand.weak_with
        or ((ch := champions.get(pid)) and cand.id in ch.weak_with)
    }

    explicit = min(len(synergy_allies), 3) * 0.03 - min(len(weak_allies), 3) * 0.04
    archetype = _synergy_bonus(cand.id, team_picks, archetypes)
    return max(-0.08, min(0.06, context_scale * (explicit + archetype)))


# ---------------------------------------------------------------------------
# Rationale generation — deterministic bullets from score signals
# ---------------------------------------------------------------------------
def _build_rationale(
    cand: Champion,
    cand_r: Champion,
    draft_state: DraftState,
    champions: dict[str, Champion],
    meta_tiers: MetaTiers,
    archetypes: list[Archetype],
    identity: float,
    denial: float,
    structural: float,
    survivability: float,
    is_ban: bool,
) -> list[str]:
    lines: list[str] = []
    our_picks = draft_state.enemy_picks if is_ban else draft_state.our_picks
    enemy_picks = draft_state.our_picks if is_ban else draft_state.enemy_picks

    # --- Identity / color coherence ---
    if not is_ban:
        if identity >= 0.75:
            colors = " / ".join(cand_r.colors_main)
            lines.append(f"Strong color fit — {colors} reinforces your declared identity.")
        elif identity >= 0.5:
            colors = " / ".join(cand_r.colors_main)
            lines.append(f"Partial color fit ({colors}) — adds a secondary thread to the draft.")
        elif identity < 0.35 and our_picks:
            lines.append("Color identity is off-theme — consider whether this is the right pick for your win condition.")

    # Explicit synergy pairs
    synergy_allies = [
        pid for pid in our_picks
        if pid in cand.synergy_with
        or ((ch := champions.get(pid)) and cand.id in ch.synergy_with)
    ]
    if synergy_allies:
        names = ", ".join(champions[p].name for p in synergy_allies if p in champions)
        lines.append(f"Explicit synergy with {names}.")

    weak_allies = [
        pid for pid in our_picks
        if pid in cand.weak_with
        or ((ch := champions.get(pid)) and cand.id in ch.weak_with)
    ]
    if weak_allies:
        names = ", ".join(champions[p].name for p in weak_allies if p in champions)
        lines.append(f"Poor pairing with {names} — may work against your win condition.")

    # Archetype synergy
    for arch in archetypes:
        if arch.kind != "synergy" or cand.id not in arch.members:
            continue
        allies_in = [p for p in our_picks if p in arch.members]
        if allies_in:
            names = ", ".join(champions[p].name for p in allies_in if p in champions)
            lines.append(f"Completes {arch.name} archetype with {names}.")
            break

    # --- Denial ---
    if is_ban:
        if denial >= 0.70:
            lines.append("High threat to your comp — priority ban to prevent enemy access.")
        elif denial >= 0.50:
            lines.append("Moderate threat — banning removes a meaningful enemy option.")
    else:
        if denial >= 0.70:
            enemy_colors = []
            if enemy_picks:
                ec = composition.analyze(enemy_picks, champions, draft_state)
                enemy_colors = ec.primary_colors
            color_str = " / ".join(enemy_colors) if enemy_colors else "their identity"
            lines.append(f"Strong counter to enemy {color_str} — directly disrupts their win condition.")
        elif denial >= 0.50:
            lines.append("Good denial value — colors and capabilities match up well against enemy.")

    # Explicit counter pairs
    counter_enemies = [
        pid for pid in enemy_picks
        if (ch := champions.get(pid)) and cand.id in ch.countered_by
    ]
    if counter_enemies:
        names = ", ".join(champions[p].name for p in counter_enemies if p in champions)
        lines.append(f"Directly counters {names}.")

    # strong_against_tags hit
    if cand_r.strong_against_tags and enemy_picks:
        enemy_weaknesses: set[str] = set()
        for pid in enemy_picks:
            if ch := champions.get(pid):
                enemy_weaknesses.update(ch.counter_tags)
        hits = set(cand_r.strong_against_tags) & enemy_weaknesses
        if hits:
            lines.append(f"Specialist counter — exploits enemy vulnerability ({', '.join(sorted(hits)[:2])}).")

    # --- Structural ---
    comp = composition.analyze(our_picks if not is_ban else [], champions, draft_state)
    ambiguous_roles = _ambiguous_roles(our_picks, champions) if not is_ban else set()
    if comp.holes and not is_ban:
        filled = []
        for hole in comp.holes:
            if hole == "ad_source":
                if cand_r.structural_tags and cand_r.structural_tags.damage_profile in ("ad", "mixed"):
                    filled.append("AD damage source")
                continue
            if hole == "ranged_ad_source":
                if (
                    cand_r.structural_tags
                    and cand_r.structural_tags.damage_profile in ("ad", "mixed")
                    and cand_r.structural_tags.range in ("short", "medium", "long")
                ):
                    filled.append("ranged AD damage source")
                continue
            val = composition.get_structural_value(cand_r, hole)
            if val and composition.ALL_FIELD_VALUES.get(val, 0) >= 0.5:
                filled.append(hole.replace("_", " "))
        if "bot" in _unfilled_roles(our_picks, champions) and _is_real_bot_anchor(cand_r):
            filled.append("bot carry anchor")
        if "support" in _unfilled_roles(our_picks, champions) and _is_real_support_anchor(cand_r):
            filled.append("support anchor")
        if "mid" in _unfilled_roles(our_picks, champions) and _is_real_mid_anchor(cand_r):
            filled.append("mid anchor")
        if _preserves_flex_branch(cand_r, _unfilled_roles(our_picks, champions), ambiguous_roles):
            labels = sorted((set(cand_r.roles) - _unfilled_roles(our_picks, champions)) & ambiguous_roles)
            if labels:
                filled.append(f"preserves {' / '.join(labels)} flex")
        if filled:
            lines.append(f"Fills structural hole{'s' if len(filled) > 1 else ''}: {', '.join(filled)}.")
        elif structural < 0.45:
            lines.append("Doesn't address current structural gaps — comp may remain incomplete.")

    # Damage/range diversity warnings
    if not is_ban and cand_r.structural_tags:
        profile = cand_r.structural_tags.damage_profile
        if profile in ("ap", "ad"):
            same = sum(
                1 for pid in our_picks
                if (ch := champions.get(pid)) and
                   ch.structural_tags and ch.structural_tags.damage_profile == profile
            )
            if same >= 3:
                label = "AP" if profile == "ap" else "AD"
                lines.append(f"Warning: {same} {label} allies already — damage profile is dangerously narrow.")
            elif same == 2:
                label = "AP" if profile == "ap" else "AD"
                lines.append(f"Third {label} champion — watch damage profile diversity.")

        rng = cand_r.structural_tags.range
        if rng in ("melee", "short"):
            melee = sum(
                1 for pid in our_picks
                if (ch := champions.get(pid)) and
                   ch.structural_tags and ch.structural_tags.range in ("melee", "short")
            )
            if melee >= 3:
                lines.append(f"Warning: {melee} melee/short-range allies — comp lacks ranged presence.")

    # --- Meta / survivability ---
    mc = _meta_contribution(cand, meta_tiers)
    if mc >= 0.35:
        lines.append("Strong meta pick — high win rate and priority in current patch.")
    elif mc >= 0.15:
        lines.append("Solid meta standing this patch.")

    # --- Phase fit notes ---
    if not is_ban and cand_r.colors_main:
        phase = draft_state.phase if draft_state.phase in WEIGHTS_BY_PHASE else "pick2"
        pf = _phase_fit_modifier(cand_r.colors_main, phase, "pick")
        if pf <= -0.06:
            lines.append("Early R commitment telegraphs your gameplan — opponent can sideboard in real time.")
        elif pf >= 0.04:
            lines.append("Late R pick rewards patience — closes the game without revealing your identity early.")

    return lines


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def score_candidate(
    candidate_id: str,
    draft_state: DraftState,
    champions: dict[str, Champion],
    meta_tiers: MetaTiers,
    archetypes: list[Archetype] | None = None,
) -> CandidateScore:
    cand = champions[candidate_id]
    arch_list = archetypes or []

    # For bans, flip perspective: a ban's value is how much the ENEMY would
    # gain if they picked this champ. So "identity" becomes enemy-identity
    # reinforcement, "structural" becomes enemy-hole coverage, "denial"
    # becomes direct threat to our comp (enemy counter → us).
    if draft_state.action_to_take == "ban":
        identity_for = draft_state.enemy_picks  # enemy identity to reinforce
        denial_against = draft_state.our_picks  # champ's ability to hurt us
        structural_for = draft_state.enemy_picks
        synergy_side = draft_state.enemy_picks
        counter_target = draft_state.our_picks
    else:
        identity_for = draft_state.our_picks
        denial_against = draft_state.enemy_picks
        structural_for = draft_state.our_picks
        synergy_side = draft_state.our_picks
        counter_target = draft_state.enemy_picks

    identity = score_identity(cand, identity_for, champions, draft_state)
    denial = score_denial(cand, denial_against, champions, draft_state)
    structural = score_structural(cand, structural_for, champions, draft_state)
    # For bans, meta should still matter as a tiebreaker, but the pick-only
    # survivability axis ("can we execute this champ?") is semantically wrong.
    survivability = (
        0.5
        if draft_state.action_to_take == "ban"
        else score_survivability(cand, draft_state, meta_tiers)
    )

    denial = min(
        1.0,
        denial
        + _enemy_read_confidence(counter_target)
        * _counter_bonus(candidate_id, counter_target, champions, arch_list),
    )

    phase = draft_state.phase if draft_state.phase in WEIGHTS_BY_PHASE else "pick2"
    w = WEIGHTS_BY_PHASE[phase]
    total = (
        w["identity"] * identity
        + w["denial"] * denial
        + w["structural"] * structural
        + w["survivability"] * survivability
    )

    cand_r = contextual.resolve(cand, draft_state)
    coherence = _coherence_modifier(cand, synergy_side, champions, arch_list)
    total = max(0.0, min(1.0, total
        + coherence
        + _phase_fit_modifier(cand_r.colors_main, phase, draft_state.action_to_take)
        + _b_constraint_modifier(cand_r.colors_main, phase, draft_state.action_to_take)
        + _flex_bonus(cand, draft_state)
        + _opener_modifier(cand, draft_state)
        + _conditional_pick_modifier(cand, draft_state)
        + _support_unlock_modifier(cand, draft_state, champions)
        + _side_lane_branch_modifier(cand, draft_state, champions)
    ))

    is_ban = draft_state.action_to_take == "ban"
    rationale = _build_rationale(
        cand, cand_r, draft_state, champions, meta_tiers, arch_list,
        identity, denial, structural, survivability, is_ban,
    )

    return CandidateScore(
        champion_id=candidate_id,
        identity=round(identity, 4),
        denial=round(denial, 4),
        structural=round(structural, 4),
        survivability=round(survivability, 4),
        meta_contribution=round(_meta_contribution(cand, meta_tiers), 4),
        total=round(total, 4),
        rationale=rationale,
    )


def rank_candidates(
    candidate_ids: list[str],
    draft_state: DraftState,
    champions: dict[str, Champion],
    meta_tiers: MetaTiers,
    top_n: int | None = None,
    archetypes: list[Archetype] | None = None,
    diversify: bool = False,
) -> list[CandidateScore]:
    scores = [
        score_candidate(cid, draft_state, champions, meta_tiers, archetypes)
        for cid in candidate_ids
    ]

    scores.sort(key=lambda s: (-s.total, -s.meta_contribution))

    if top_n is None:
        return scores

    if not diversify:
        return scores[:top_n]

    # For pick actions with top_n >= 4, use categorized diversity slots so the
    # recommendations always cover different dimensions — not just five clones of
    # the same identity/role archetype.
    #
    # Slot layout (top_n == 5):
    #   [0-1]  Best overall  — highest total score
    #   [2]    Structural fill — highest structural score (fills comp holes)
    #   [3]    Best denial   — highest denial score (counters enemy hardest)
    #   [4]    Identity anchor — highest identity score (tightest color fit)
    #
    # For top_n < 4, just return top by total (existing behaviour).
    if top_n < 4 or draft_state.action_to_take == "ban":
        return scores[:top_n]

    seen: set[str] = set()
    result: list[CandidateScore] = []
    used_roles: set[str] = set()
    used_buckets: set[str] = set()

    def _add(s: CandidateScore, role: str) -> bool:
        if s.champion_id in seen:
            return False
        seen.add(s.champion_id)
        champ = champions[s.champion_id]
        used_roles.add(_primary_role(champ))
        used_buckets.add(_recommendation_bucket(champ))
        s.recommendation_role = role
        prefix = _ROLE_RATIONALE_PREFIX.get(role)
        if prefix and (not s.rationale or s.rationale[0] != prefix):
            s.rationale = [prefix, *s.rationale]
        result.append(s)
        return True

    our_picks = draft_state.our_picks
    enemy_confidence = _enemy_read_confidence(draft_state.enemy_picks)
    unfilled = _unfilled_roles(our_picks, champions)
    ambiguous = _ambiguous_roles(our_picks, champions)
    team_has_bot_anchor = any(
        _is_real_bot_anchor(champions[pid])
        for pid in our_picks
        if pid in champions
    )
    team_has_protect_carry_thread = any(
        "protect_the_carry" in (champions[pid].win_condition_tags or [])
        for pid in our_picks
        if pid in champions
    )

    # Slot 0: best overall
    if scores:
        _add(scores[0], "best_overall")

    # Slot 1: structural fill — highest structural score with light diversity pressure
    structural_best = _pick_distinct_candidate(
        scores,
        champions,
        seen,
        used_roles,
        used_buckets,
        key_fn=lambda s: s.structural,
        tolerance=0.05,
    )
    if structural_best:
        _add(structural_best, "structural_fill")

    # Dynamic branch slot: show either the support-enabler branch for
    # carry-centric shells, or a flex-preserving branch when the current
    # draft still has meaningful lane ambiguity.
    dynamic_branch = None
    dynamic_role = None
    if "support" in unfilled and (team_has_bot_anchor or team_has_protect_carry_thread):
        dynamic_branch = _pick_distinct_candidate(
            [
                s for s in scores
                if s.champion_id not in seen
                and _is_support_enabler(champions[s.champion_id])
            ],
            champions,
            seen,
            used_roles,
            used_buckets,
            key_fn=lambda s: s.total,
        )
        dynamic_role = "support_enabler"
    elif ambiguous and unfilled:
        dynamic_branch = _pick_distinct_candidate(
            [
                s for s in scores
                if s.champion_id not in seen
                and _preserves_flex_branch(champions[s.champion_id], unfilled, ambiguous)
            ],
            champions,
            seen,
            used_roles,
            used_buckets,
            key_fn=lambda s: s.total,
        )
        dynamic_role = "flex_branch"
    if dynamic_branch and dynamic_role:
        _add(dynamic_branch, dynamic_role)

    # Slot 3: best denial — highest denial with light diversity pressure
    denial_best = _pick_denial_candidate(
        scores,
        champions,
        seen,
        used_roles,
        used_buckets,
        enemy_confidence,
    )
    if denial_best:
        _add(denial_best, "best_denial")

    # Slot 4: identity anchor — highest identity with light diversity pressure
    identity_best = _pick_distinct_candidate(
        scores,
        champions,
        seen,
        used_roles,
        used_buckets,
        key_fn=lambda s: s.identity,
        tolerance=0.05,
    )
    if identity_best:
        _add(identity_best, "identity_anchor")

    # Pad with next-best if any category slot was empty. Label "alt" so the
    # UI doesn't mis-present a fallback as a true best_overall pick.
    for s in scores:
        if len(result) >= top_n:
            break
        _add(s, "alt")

    return result[:top_n]


def eligible_candidates(
    draft_state: DraftState, champions: dict[str, Champion]
) -> list[str]:
    """Champion IDs that are legal picks/bans for the side_to_act.

    Filters out taken champions. For picks, removes champs whose only roles
    are already claimed by our existing picks. For bans, removes champs whose
    only roles are already locked on the *enemy* side — a ban's value is
    denying the enemy a pick they could still make, so banning a bot-only
    champ when the enemy already has their ADC is wasted.
    """
    taken = draft_state.taken
    pool = [cid for cid in champions if cid not in taken]
    if draft_state.action_to_take == "pick":
        our_picks = draft_state.our_picks
        if len(our_picks) >= 5:
            return pool
        unfilled = _unfilled_roles(our_picks, champions)
        if not unfilled:
            return pool
        filtered = [cid for cid in pool if _role_fits(champions[cid], unfilled)]
        return filtered if filtered else pool

    # Ban: filter by the enemy's unfilled roles so we don't suggest banning
    # a single-role champ whose role the enemy has already locked.
    enemy_picks = draft_state.enemy_picks
    if len(enemy_picks) >= 5:
        return pool
    enemy_unfilled = _unfilled_roles(enemy_picks, champions)
    if not enemy_unfilled:
        return pool
    filtered = [cid for cid in pool if _role_fits(champions[cid], enemy_unfilled)]
    return filtered if filtered else pool
