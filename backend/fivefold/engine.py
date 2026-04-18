"""Deterministic scoring engine.

Four axes: identity, denial, structural, survivability. Meta tiers only
influence survivability and the tiebreaker — they never drive identity or
denial scoring (see CLAUDE.md design principles).
"""
from __future__ import annotations

from . import composition, contextual
from .composition import ALL_FIELD_VALUES, COLORS, LEVEL_VALUES, OFF_COLOR_WEIGHT, RANGE_VALUES
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
    "pick1": {"identity": 0.40, "denial": 0.30, "structural": 0.20, "survivability": 0.10},
    "ban2":  {"identity": 0.30, "denial": 0.40, "structural": 0.20, "survivability": 0.10},
    "pick2": {"identity": 0.20, "denial": 0.20, "structural": 0.40, "survivability": 0.20},
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
            # One ally present = modest bonus; two+ = noticeable.
            bonus = min(0.20, 0.08 + 0.06 * allies_in)
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

    # Colorless is a draft-definer, not a filler — treat separately.
    if "C" in cand_r.colors_main:
        if comp.declared_colors.get("C", 0.0) > 0:
            score = min(1.0, score * 1.2)
        else:
            score = max(score, 0.45)

    # Explicit synergy pairs: each ally that lists this candidate as a
    # synergy_with partner adds a small identity bonus (+0.04, cap +0.12).
    synergy_count = sum(
        1 for pid in our_picks
        if (ch := champions.get(pid)) and cand.id in ch.synergy_with
    )
    # Also count from candidate's own synergy_with list matching allies
    synergy_count += sum(1 for pid in our_picks if pid in cand.synergy_with)
    # Deduplicate: a pair only counts once
    synergy_count = min(synergy_count, len(our_picks))
    score = min(1.0, score + synergy_count * 0.04)

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

    # strong_against_tags: explicit "I beat comps with these vulnerabilities"
    # bonus on top of the color-derived score. Counter-pick specialists (e.g.
    # Sona) use this to express that their value is conditional on enemy shape.
    strong_against_bonus = 0.0
    if cand_r.strong_against_tags and enemy_weaknesses:
        explicit_overlap = len(set(cand_r.strong_against_tags) & enemy_weaknesses)
        strong_against_bonus = min(0.15, explicit_overlap * 0.05)

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
    counter_bonus = min(0.15, counter_bonus)

    return min(1.0, 0.65 * color_score + 0.35 * tag_score + strong_against_bonus + counter_bonus)


def score_structural(
    cand: Champion, our_picks: list[str], champions: dict[str, Champion], state: DraftState
) -> float:
    cand_r = contextual.resolve(cand, state)
    comp = composition.analyze(our_picks, champions, state)

    # Without any tag data to reason about, stay neutral.
    if cand_r.structural_tags is None or not comp.structural_avg:
        return 0.5

    cand_st = cand_r.structural_tags

    # AP-saturation constraint: some champions (e.g. Karthus) need to be the
    # lone magic-damage source — picking them into an AP-heavy ally pool is a
    # structural anti-pattern.
    penalty = 0.0
    if "requires_solo_magic" in (cand_r.kit_tags or []):
        ap_allies = sum(
            1 for pid in our_picks
            if (ch := champions.get(pid)) and
               ch.structural_tags is not None and
               ch.structural_tags.damage_profile == "ap"
        )
        penalty = min(0.40, ap_allies * 0.20)

    # Damage profile diversity: a comp should never be mono-AP or mono-AD.
    cand_profile = cand_st.damage_profile if cand_st else None
    if cand_profile in ("ap", "ad"):
        same_profile_allies = sum(
            1 for pid in our_picks
            if (ch := champions.get(pid)) and
               ch.structural_tags is not None and
               ch.structural_tags.damage_profile == cand_profile
        )
        if same_profile_allies >= 4:
            penalty += 0.40
        elif same_profile_allies == 3:
            penalty += 0.25
        elif same_profile_allies == 2:
            penalty += 0.10

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
        # Use ALL_FIELD_VALUES so range holes ("melee"/"long" values) are scored correctly.
        lvls = [ALL_FIELD_VALUES.get(getattr(cand_st, f) or "none", 0.0) for f in comp.holes]
        coverage = sum(lvls) / len(lvls)
        return max(0.0, min(1.0, 0.25 + 0.75 * coverage - penalty))

    return max(0.0, 0.6 - penalty)


def score_survivability(
    cand: Champion, state: DraftState, meta_tiers: MetaTiers
) -> float:
    base = 0.5
    for role in cand.roles:
        tier_list = meta_tiers.tiers.get(role, [])
        if cand.id in tier_list:
            pos = tier_list.index(cand.id)
            bonus = 0.5 * (1.0 - pos / max(1, len(tier_list)))
            base = max(base, 0.5 + bonus)
    return min(1.0, base)


def _meta_contribution(cand: Champion, meta_tiers: MetaTiers) -> float:
    best = 0.0
    for role in cand.roles:
        tier_list = meta_tiers.tiers.get(role, [])
        if cand.id in tier_list:
            pos = tier_list.index(cand.id)
            best = max(best, 0.5 * (1.0 - pos / max(1, len(tier_list))))
    return best


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
    survivability = score_survivability(cand, draft_state, meta_tiers)

    identity = min(1.0, identity + _synergy_bonus(candidate_id, synergy_side, arch_list))
    denial = min(1.0, denial + _counter_bonus(candidate_id, counter_target, champions, arch_list))

    phase = draft_state.phase if draft_state.phase in WEIGHTS_BY_PHASE else "pick2"
    w = WEIGHTS_BY_PHASE[phase]
    total = (
        w["identity"] * identity
        + w["denial"] * denial
        + w["structural"] * structural
        + w["survivability"] * survivability
    )

    cand_r = contextual.resolve(cand, draft_state)
    total = max(0.0, min(1.0, total
        + _phase_fit_modifier(cand_r.colors_main, phase, draft_state.action_to_take)
        + _b_constraint_modifier(cand_r.colors_main, phase, draft_state.action_to_take)
        + _flex_bonus(cand, draft_state)
    ))

    return CandidateScore(
        champion_id=candidate_id,
        identity=round(identity, 4),
        denial=round(denial, 4),
        structural=round(structural, 4),
        survivability=round(survivability, 4),
        meta_contribution=round(_meta_contribution(cand, meta_tiers), 4),
        total=round(total, 4),
    )


def rank_candidates(
    candidate_ids: list[str],
    draft_state: DraftState,
    champions: dict[str, Champion],
    meta_tiers: MetaTiers,
    top_n: int | None = None,
    archetypes: list[Archetype] | None = None,
) -> list[CandidateScore]:
    scores = [
        score_candidate(cid, draft_state, champions, meta_tiers, archetypes)
        for cid in candidate_ids
    ]

    def sort_key(s: CandidateScore) -> tuple:
        bucket = round(s.total / TIEBREAKER_TOLERANCE)
        return (-bucket, -s.meta_contribution, -s.total)

    scores.sort(key=sort_key)

    if top_n is None:
        return scores

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

    def _add(s: CandidateScore, role: str) -> bool:
        if s.champion_id in seen:
            return False
        seen.add(s.champion_id)
        s.recommendation_role = role
        result.append(s)
        return True

    # Slots 0-1: best overall
    for s in scores:
        if len(result) >= 2:
            break
        _add(s, "best_overall")

    # Slot 2: structural fill — highest structural, not already picked
    structural_best = max(
        (s for s in scores if s.champion_id not in seen),
        key=lambda s: s.structural,
        default=None,
    )
    if structural_best:
        _add(structural_best, "structural_fill")

    # Slot 3: best denial — highest denial
    denial_best = max(
        (s for s in scores if s.champion_id not in seen),
        key=lambda s: s.denial,
        default=None,
    )
    if denial_best:
        _add(denial_best, "best_denial")

    # Slot 4: identity anchor — highest identity
    identity_best = max(
        (s for s in scores if s.champion_id not in seen),
        key=lambda s: s.identity,
        default=None,
    )
    if identity_best:
        _add(identity_best, "identity_anchor")

    # Pad with next-best overall if we somehow have fewer than top_n
    for s in scores:
        if len(result) >= top_n:
            break
        _add(s, "best_overall")

    return result


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
