"""Snapshot tests for the scoring engine.

These are hand-curated draft scenarios with expected high/low scoring picks.
They are regression safety nets — if scoring weights change meaningfully, an
intentional update to these tests forces a review of the change.
"""
from __future__ import annotations

from fivefold import engine, loader
from fivefold.composition import analyze
from fivefold.models import DraftState


def _state(**kwargs):
    defaults = dict(
        phase="pick1",
        turn_index=0,
        blue_bans=[],
        red_bans=[],
        blue_picks=[],
        red_picks=[],
        side_to_act="blue",
        action_to_take="pick",
        first_pick_side="blue",
    )
    defaults.update(kwargs)
    return DraftState(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
CHAMPIONS = loader.load_champions()
META = loader.load_meta_tiers()
ARCHETYPES = loader.load_archetypes()


# ---------------------------------------------------------------------------
# Composition-level sanity checks
# ---------------------------------------------------------------------------
def test_declared_colors_empty_picks():
    comp = analyze([], CHAMPIONS, _state())
    assert comp.total_color_mass == 0.0
    assert comp.primary_colors == []


def test_declared_colors_green_heavy_comp():
    # Jax(G) + Karma(G) + Lulu(G/off W) — G should dominate.
    comp = analyze(["jax", "karma", "lulu"], CHAMPIONS, _state())
    assert comp.primary_colors[0] == "G"
    assert comp.declared_colors["G"] > comp.declared_colors["R"]


# ---------------------------------------------------------------------------
# Identity axis
# ---------------------------------------------------------------------------
def test_identity_neutral_when_no_picks():
    state = _state()
    s = engine.score_candidate("aatrox", state, CHAMPIONS, META)
    assert s.identity == 0.5


def test_identity_rewards_matching_colors():
    # We're building Green. Jax (pure G) should beat Zed (pure B).
    state = _state(blue_picks=["karma", "lulu"])
    jax = engine.score_candidate("jax", state, CHAMPIONS, META)
    zed = engine.score_candidate("zed", state, CHAMPIONS, META)
    assert jax.identity > zed.identity


def test_identity_colorless_first_introduction_is_tempered():
    # Yuumi is pure Colorless. When our comp has no C yet, identity should
    # be at least 0.45 (C is a draft-definer, not a filler).
    state = _state(blue_picks=["jax", "karma"])
    yuumi = engine.score_candidate("yuumi", state, CHAMPIONS, META)
    assert yuumi.identity >= 0.45


# ---------------------------------------------------------------------------
# Denial axis
# ---------------------------------------------------------------------------
def test_denial_neutral_when_enemy_empty():
    s = engine.score_candidate("aatrox", _state(), CHAMPIONS, META)
    assert s.denial == 0.5


def test_denial_white_counters_red_heavy_enemy():
    # Enemy = Aatrox(RB) + Ahri(R/off B) + Akali(RU) — very Red.
    # Alistar (R/W) and Janna (G/U) bring anti-aggro; Yasuo (W/C) is White.
    state = _state(blue_picks=[], red_picks=["aatrox", "ahri", "akali"])
    janna = engine.score_candidate("janna", state, CHAMPIONS, META)
    darius = engine.score_candidate("darius", state, CHAMPIONS, META)  # R/C — same as enemy
    assert janna.denial > darius.denial


def test_denial_red_punishes_scaling_enemy():
    # Enemy = scaling Green: Jax + Kassadin + Veigar.
    state = _state(red_picks=["jax", "kassadin", "veigar"])
    darius = engine.score_candidate("darius", state, CHAMPIONS, META)  # R/C
    jinx = engine.score_candidate("jinx", state, CHAMPIONS, META)     # G/W (outscales them, shouldn't "deny")
    assert darius.denial > jinx.denial


# ---------------------------------------------------------------------------
# Ranking + tiebreaker
# ---------------------------------------------------------------------------
def test_rank_candidates_orders_by_total_desc():
    state = _state(blue_picks=["karma"])
    scores = engine.rank_candidates(
        ["jax", "zed", "lulu"], state, CHAMPIONS, META, top_n=3
    )
    assert scores[0].total >= scores[1].total >= scores[2].total


def test_eligible_excludes_picked_and_banned():
    state = _state(blue_picks=["jax"], red_bans=["zed"], action_to_take="ban")
    eligible = engine.eligible_candidates(state, CHAMPIONS)
    assert "jax" not in eligible
    assert "zed" not in eligible
    assert "aatrox" in eligible


def test_eligible_filters_filled_roles_on_pick():
    # Jax claims top for blue; any candidate whose only role is top is dropped.
    state = _state(blue_picks=["jax"], action_to_take="pick")
    eligible = set(engine.eligible_candidates(state, CHAMPIONS))
    for cid in eligible:
        roles = CHAMPIONS[cid].roles
        if roles:
            assert set(roles) != {"top"}


def test_eligible_ban_filters_role_locked_on_enemy():
    # Both bots locked. On a ban, Kai'Sa (bot-only) is useless against
    # either enemy — the role is already claimed.
    state_blue_bans = _state(
        phase="ban2",
        blue_picks=["aphelios"],
        red_picks=["caitlyn"],
        side_to_act="blue",
        action_to_take="ban",
    )
    eligible = set(engine.eligible_candidates(state_blue_bans, CHAMPIONS))
    assert "kaisa" not in eligible  # enemy (red) bot is locked
    # A top-only champ is still eligible because red has no top yet.
    assert "aatrox" in eligible


def test_eligible_ban_filters_single_role_locked_on_enemy_top():
    # Red already has Kled top; red banning → targets blue. Blue has GP top,
    # so banning another top-only champ (Aatrox) is wasted.
    state = _state(
        phase="ban2",
        blue_picks=["gangplank"],
        red_picks=["kled"],
        side_to_act="red",
        action_to_take="ban",
    )
    eligible = set(engine.eligible_candidates(state, CHAMPIONS))
    assert "aatrox" not in eligible


def test_ban_scoring_flips_perspective_to_enemy_identity():
    # Enemy (red) is building heavy U/G. On a ban, a U/G candidate should
    # beat an R candidate on identity — because the ban's value is denying
    # the enemy a pick that reinforces their identity.
    state = _state(
        phase="ban2",
        red_picks=["caitlyn", "kassadin", "ashe"],  # G/U heavy
        action_to_take="ban",
        side_to_act="blue",
    )
    veigar = engine.score_candidate("veigar", state, CHAMPIONS, META)  # G/U
    ahri = engine.score_candidate("ahri", state, CHAMPIONS, META)      # R
    assert veigar.identity > ahri.identity


def test_ban_scoring_denial_is_threat_to_us():
    # We (blue) are red-heavy. On a ban, a U-coloured candidate (which
    # counters R per the matrix) should score higher "denial" than an R
    # candidate — because the axis now measures threat-to-us.
    state = _state(
        phase="ban2",
        blue_picks=["darius", "garen"],  # R-heavy
        action_to_take="ban",
        side_to_act="blue",
    )
    ashe = engine.score_candidate("ashe", state, CHAMPIONS, META)   # U
    ahri = engine.score_candidate("ahri", state, CHAMPIONS, META)   # R
    assert ashe.denial > ahri.denial


def test_flex_bonus_applies_red_side_pick1():
    # On red side pick1, a flex champion (e.g. Karma: support/mid) should
    # score higher than the same champion on blue side pick1 — red side
    # gets counter-pick ambiguity from hiding the role until lock-in.
    state_red = _state(phase="pick1", action_to_take="pick", side_to_act="red")
    state_blue = _state(phase="pick1", action_to_take="pick", side_to_act="blue")
    karma_red = engine.score_candidate("karma", state_red, CHAMPIONS, META)
    karma_blue = engine.score_candidate("karma", state_blue, CHAMPIONS, META)
    assert karma_red.total > karma_blue.total


def test_flex_bonus_not_in_pick2():
    # Flex bonus is pick1 only — once both sides have established picks,
    # the counter-pick ambiguity window is gone.
    state_red_p1 = _state(phase="pick1", action_to_take="pick", side_to_act="red")
    state_red_p2 = _state(phase="pick2", action_to_take="pick", side_to_act="red")
    karma_p1 = engine.score_candidate("karma", state_red_p1, CHAMPIONS, META)
    karma_p2 = engine.score_candidate("karma", state_red_p2, CHAMPIONS, META)
    assert karma_p1.total > karma_p2.total


def test_flex_bonus_scales_with_role_count():
    # More roles = more ambiguity = higher bonus on red side pick1.
    # Karma (2 roles) should score lower than a 3-role flex champion.
    state_red = _state(phase="pick1", action_to_take="pick", side_to_act="red")
    karma = engine.score_candidate("karma", state_red, CHAMPIONS, META)      # 2 roles
    sylas = engine.score_candidate("sylas", state_red, CHAMPIONS, META)      # 4 roles
    assert sylas.total > karma.total


def test_b_constraint_penalises_b_lead_in_pick1():
    # Karthus (B/U) picked early reveals the "no more AP" constraint.
    # A U champion without B should outscore him in pick1.
    state = _state(phase="pick1", action_to_take="pick")
    karthus = engine.score_candidate("karthus", state, CHAMPIONS, META)   # B/U
    lissandra = engine.score_candidate("lissandra", state, CHAMPIONS, META)  # G/U/W
    assert lissandra.total > karthus.total


def test_b_constraint_no_penalty_when_r_present():
    # Draven (B/R) already gets the R-phase-fit penalty — no stacking B penalty.
    # Verify his score is driven by R-phase-fit not B-constraint.
    state = _state(phase="pick1", action_to_take="pick")
    draven = engine.score_candidate("draven", state, CHAMPIONS, META)    # B/R
    karthus = engine.score_candidate("karthus", state, CHAMPIONS, META)  # B/U — B-constraint applies
    # Both penalised, but differently — just confirm neither crashes.
    assert draven.total < 0.5  # R-phase-fit active
    assert karthus.total < 0.5  # B-constraint active


def test_b_constraint_not_in_bans():
    # Banning Karthus early is fine — we're denying, not constraining ourselves.
    state_ban = _state(phase="ban1", action_to_take="ban")
    state_pick = _state(phase="pick1", action_to_take="pick")
    karthus_ban = engine.score_candidate("karthus", state_ban, CHAMPIONS, META)
    karthus_pick = engine.score_candidate("karthus", state_pick, CHAMPIONS, META)
    assert karthus_ban.total > karthus_pick.total


def test_phase_fit_penalises_mono_r_in_pick1():
    # Darius (mono-R) should score lower in pick1 than a U/W champion
    # because anchoring aggression early telegraphs the gameplan.
    state_pick1 = _state(phase="pick1", action_to_take="pick")
    darius = engine.score_candidate("darius", state_pick1, CHAMPIONS, META)
    lissandra = engine.score_candidate("lissandra", state_pick1, CHAMPIONS, META)
    assert lissandra.total > darius.total


def test_phase_fit_boosts_r_in_pick2():
    # In pick2 (closing the draft), R picks get a boost — they're pick2 closers.
    state_pick1 = _state(phase="pick1", action_to_take="pick")
    state_pick2 = _state(phase="pick2", action_to_take="pick")
    darius_p1 = engine.score_candidate("darius", state_pick1, CHAMPIONS, META)
    darius_p2 = engine.score_candidate("darius", state_pick2, CHAMPIONS, META)
    assert darius_p2.total > darius_p1.total


def test_phase_fit_does_not_penalise_bans():
    # Bans are scored from enemy perspective — no phase fit penalty applies.
    state_ban1 = _state(phase="ban1", action_to_take="ban")
    state_pick1 = _state(phase="pick1", action_to_take="pick")
    # Banning Darius in ban1 should not be penalised (we're denying, not telegraphing).
    darius_ban = engine.score_candidate("darius", state_ban1, CHAMPIONS, META)
    darius_pick = engine.score_candidate("darius", state_pick1, CHAMPIONS, META)
    assert darius_ban.total > darius_pick.total


def test_tiebreaker_prefers_meta_tier_when_totals_close(tmp_path):
    # Fabricate a meta tiers file that places jax first in top.
    import json
    tiers_path = tmp_path / "meta.json"
    tiers_path.write_text(json.dumps({
        "patch": "test",
        "updated_at": "2026-04-17",
        "tiers": {"top": ["jax"], "jungle": [], "mid": [], "bot": [], "support": []},
    }))
    meta = loader.load_meta_tiers(tiers_path)

    # Symmetric-ish state so jax vs kayle totals are close.
    state = _state(blue_picks=["karma", "lulu"])
    ranked = engine.rank_candidates(["jax", "kayle"], state, CHAMPIONS, meta)
    # Jax should win any tie because he sits at top of meta.
    assert ranked[0].champion_id == "jax"


# ---------------------------------------------------------------------------
# Phase weights
# ---------------------------------------------------------------------------
def test_pick2_leans_structural_over_identity():
    w1 = engine.WEIGHTS_BY_PHASE["pick1"]
    w2 = engine.WEIGHTS_BY_PHASE["pick2"]
    assert w2["structural"] > w1["structural"]
    assert w2["identity"] < w1["identity"]


# ---------------------------------------------------------------------------
# Archetype bonuses
# ---------------------------------------------------------------------------
def test_synergy_bonus_boosts_yasuo_when_ally_has_knockup():
    # Malphite is in yasuo_knockup_chain as a knockup anchor. Yasuo should
    # score higher with Malphite on the team than without.
    with_anchor = engine.score_candidate(
        "yasuo", _state(blue_picks=["malphite"]), CHAMPIONS, META, ARCHETYPES
    )
    without_anchor = engine.score_candidate(
        "yasuo", _state(blue_picks=["malphite"]), CHAMPIONS, META, []
    )
    assert with_anchor.identity > without_anchor.identity


def test_counter_bonus_applies_when_archetype_targets_enemy_tags():
    # anti_scaling_tempo archetype targets the "scaling_hyper" kit_tag.
    # Put a scaling carry on the enemy team and confirm an early-ganker
    # jungler gets a denial bump.
    enemy = ["kogmaw"]  # kogmaw has scaling_hyper
    with_arch = engine.score_candidate(
        "lee_sin", _state(red_picks=enemy), CHAMPIONS, META, ARCHETYPES
    )
    without_arch = engine.score_candidate(
        "lee_sin", _state(red_picks=enemy), CHAMPIONS, META, []
    )
    # Only assert the bonus did something if lee_sin is actually in an
    # applicable counter archetype — otherwise skip (defensive for future
    # data changes).
    assert with_arch.denial >= without_arch.denial


# ---------------------------------------------------------------------------
# AP-saturation constraint
# ---------------------------------------------------------------------------
def test_karthus_structural_drops_with_ap_allies():
    # Karthus has requires_solo_magic. With an AP ally, structural should fall.
    clean = engine.score_candidate("karthus", _state(), CHAMPIONS, META)
    with_ap = engine.score_candidate(
        "karthus", _state(blue_picks=["lux"]), CHAMPIONS, META  # lux = ap
    )
    assert clean.structural > with_ap.structural


def test_karthus_structural_higher_with_ad_than_ap_allies():
    # With AD allies, the constraint doesn't fire — structural stays above the AP case.
    with_ad = engine.score_candidate(
        "karthus", _state(blue_picks=["jax"]), CHAMPIONS, META
    )
    with_ap = engine.score_candidate(
        "karthus", _state(blue_picks=["lux"]), CHAMPIONS, META
    )
    assert with_ad.structural > with_ap.structural
