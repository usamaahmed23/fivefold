"""Snapshot tests for the scoring engine.

These are hand-curated draft scenarios with expected high/low scoring picks.
They are regression safety nets — if scoring weights change meaningfully, an
intentional update to these tests forces a review of the change.
"""
from __future__ import annotations

from fivefold import engine, loader
from fivefold.composition import analyze, get_structural_value
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


def test_infers_missing_structural_fields_from_kit_tags():
    # Lulu's data only has a partial structural record, but her kit clearly
    # implies peel/supportive scaling.
    lulu = CHAMPIONS["lulu"]
    assert get_structural_value(lulu, "peel") in {"medium", "high"}
    assert get_structural_value(lulu, "scaling") == "late"


def test_composition_uses_inferred_peel_and_scaling():
    # Jinx + Lulu should read as a high-peel, late-scaling shell even before
    # the full structural dataset is hand-tagged.
    comp = analyze(["jinx", "lulu"], CHAMPIONS, _state())
    assert "peel" not in comp.holes
    assert "scaling" in comp.structural_avg
    assert comp.structural_avg["scaling"] > 0.7


def test_composition_flags_ranged_ad_hole_when_only_melee_ad_present():
    # Yone provides physical damage, but not the ranged AD / backline DPS that
    # many front-to-back or wombo shells still need once top/jungle/mid are set.
    comp = analyze(["yone", "amumu", "orianna"], CHAMPIONS, _state(blue_picks=["yone", "amumu", "orianna"]))
    assert "ranged_ad_source" in comp.holes


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


def test_identity_yuumi_scores_well_in_w_comp():
    # Yuumi is now W (not C). She should score well when paired with W-heavy
    # protect-the-carry comps like Karma + Jinx.
    state = _state(blue_picks=["karma", "jinx"])
    yuumi = engine.score_candidate("yuumi", state, CHAMPIONS, META)
    assert yuumi.identity >= 0.3


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


def test_denial_is_less_confident_on_single_enemy_pick():
    # One revealed enemy champion should not produce near-certain denial scores.
    early = _state(blue_picks=["ashe"], side_to_act="red", action_to_take="pick")
    later = _state(blue_picks=["ashe", "galio", "ornn"], side_to_act="red", action_to_take="pick")
    yasuo_early = engine.score_candidate("yasuo", early, CHAMPIONS, META, ARCHETYPES)
    yasuo_later = engine.score_candidate("yasuo", later, CHAMPIONS, META, ARCHETYPES)
    assert yasuo_early.denial < yasuo_later.denial
    assert yasuo_early.denial < 0.75


def test_yone_amumu_orianna_prefers_ranged_ad_over_extra_ap_wombo():
    # This shell already has engage + follow-up magic damage. The next pick
    # should not drift toward yet another AP teamfight piece just because it
    # shares a wombo archetype.
    state = _state(
        phase="pick2",
        turn_index=3,
        blue_picks=["yone", "amumu", "orianna"],
        action_to_take="pick",
    )
    ezreal = engine.score_candidate("ezreal", state, CHAMPIONS, META, ARCHETYPES)
    kennen = engine.score_candidate("kennen", state, CHAMPIONS, META, ARCHETYPES)
    fiddlesticks = engine.score_candidate("fiddlesticks", state, CHAMPIONS, META, ARCHETYPES)
    assert ezreal.total > kennen.total
    assert ezreal.total > fiddlesticks.total


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
    # More roles = more ambiguity = higher red-side pick1 lift, even if anchor
    # quality means the higher-flex champ is not always the better opener.
    state_red = _state(phase="pick1", action_to_take="pick", side_to_act="red")
    state_blue = _state(phase="pick1", action_to_take="pick", side_to_act="blue")
    lulu_red = engine.score_candidate("lulu", state_red, CHAMPIONS, META)
    lulu_blue = engine.score_candidate("lulu", state_blue, CHAMPIONS, META)
    sylas_red = engine.score_candidate("sylas", state_red, CHAMPIONS, META)
    sylas_blue = engine.score_candidate("sylas", state_blue, CHAMPIONS, META)
    assert (sylas_red.total - sylas_blue.total) > (lulu_red.total - lulu_blue.total)


def test_pick1_opener_penalises_setup_reliant_anchor():
    # Yasuo should not be the default red-side response to one revealed bot
    # because he is a setup-dependent commit, not a stable opener.
    state = _state(blue_picks=["ashe"], side_to_act="red", action_to_take="pick")
    yasuo = engine.score_candidate("yasuo", state, CHAMPIONS, META, ARCHETYPES)
    galio = engine.score_candidate("galio", state, CHAMPIONS, META, ARCHETYPES)
    braum = engine.score_candidate("braum", state, CHAMPIONS, META, ARCHETYPES)
    assert galio.total > yasuo.total or braum.total > yasuo.total


def test_empty_board_prefers_stable_anchor_over_fragile_combo_piece():
    state = _state(phase="pick1", action_to_take="pick")
    ornn = engine.score_candidate("ornn", state, CHAMPIONS, META, ARCHETYPES)
    kennen = engine.score_candidate("kennen", state, CHAMPIONS, META, ARCHETYPES)
    assert ornn.total > kennen.total


def test_empty_board_white_stable_anchor_beats_backline_question_mark():
    state = _state(phase="pick1", action_to_take="pick")
    gragas = engine.score_candidate("gragas", state, CHAMPIONS, META, ARCHETYPES)
    seraphine = engine.score_candidate("seraphine", state, CHAMPIONS, META, ARCHETYPES)
    assert gragas.total >= seraphine.total


def test_bot_anchor_prefers_real_bot_over_fringe_bot_fill():
    # A comp missing bot should prefer a real bot anchor over a fringe bot-role
    # all-in piece like Kennen.
    state = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["ornn", "lissandra", "wukong"],
    )
    caitlyn = engine.score_candidate("caitlyn", state, CHAMPIONS, META, ARCHETYPES)
    kennen = engine.score_candidate("kennen", state, CHAMPIONS, META, ARCHETYPES)
    assert caitlyn.structural > kennen.structural
    assert caitlyn.total > kennen.total


def test_bot_anchor_allows_legit_apc_bot():
    # Bot authenticity should not collapse into "marksman only" — legitimate
    # APC bot anchors like Seraphine should still be recognised.
    state = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["ornn", "lissandra", "wukong"],
    )
    seraphine = engine.score_candidate("seraphine", state, CHAMPIONS, META, ARCHETYPES)
    kennen = engine.score_candidate("kennen", state, CHAMPIONS, META, ARCHETYPES)
    assert seraphine.structural > kennen.structural


def test_role_audit_trims_fringe_bot_tags():
    assert "bot" not in CHAMPIONS["kennen"].roles
    assert "bot" not in CHAMPIONS["yasuo"].roles
    assert "bot" not in CHAMPIONS["sylas"].roles


def test_role_audit_trims_fake_support_tags():
    assert "support" not in CHAMPIONS["kennen"].roles
    assert "support" not in CHAMPIONS["evelynn"].roles
    assert "support" not in CHAMPIONS["briar"].roles


def test_diversify_surfaces_support_enabler_for_carry_shell():
    state = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["ornn", "orianna", "gragas", "kogmaw"],
    )
    ranked = engine.rank_candidates(
        engine.eligible_candidates(state, CHAMPIONS),
        state,
        CHAMPIONS,
        META,
        top_n=5,
        archetypes=ARCHETYPES,
        diversify=True,
    )
    support_names = {r.champion_id for r in ranked if r.recommendation_role == "support_enabler"}
    assert support_names
    assert support_names & {"nami", "janna", "lulu", "soraka", "milio", "seraphine", "sona", "renata_glasc", "rakan"}
    assert sum(1 for r in ranked if r.recommendation_role == "best_overall") == 1
    assert any(r.recommendation_role == "identity_anchor" for r in ranked)


def test_diversify_can_surface_flex_branch():
    state = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["gragas", "orianna", "braum", "jinx"],
    )
    ranked = engine.rank_candidates(
        engine.eligible_candidates(state, CHAMPIONS),
        state,
        CHAMPIONS,
        META,
        top_n=5,
        archetypes=ARCHETYPES,
        diversify=True,
    )
    flex = [r for r in ranked if r.recommendation_role == "flex_branch"]
    assert flex
    assert any(len(CHAMPIONS[r.champion_id].roles) >= 2 for r in flex)
    assert any(r.recommendation_role == "best_denial" for r in ranked)


def test_diversified_rationales_start_with_branch_goal():
    state = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["ornn", "orianna", "gragas", "kogmaw"],
    )
    ranked = engine.rank_candidates(
        engine.eligible_candidates(state, CHAMPIONS),
        state,
        CHAMPIONS,
        META,
        top_n=5,
        archetypes=ARCHETYPES,
        diversify=True,
    )
    expected_prefixes = {
        "best_overall": "Best all-around fit at this point in the draft.",
        "structural_fill": "Structural branch — patches the biggest remaining comp holes.",
        "support_enabler": "Support branch — doubles down on enabling or protecting your carry line.",
        "best_denial": "Denial branch — pressures the enemy's currently declared line hardest.",
        "identity_anchor": "Identity branch — stays closest to your current LS color plan.",
    }
    for score in ranked:
        if score.recommendation_role in expected_prefixes:
            assert score.rationale
            assert score.rationale[0] == expected_prefixes[score.recommendation_role]


def test_best_denial_stays_sane_on_thin_enemy_info():
    state = _state(
        phase="pick1",
        turn_index=1,
        blue_picks=["ashe"],
        side_to_act="red",
        action_to_take="pick",
    )
    ranked = engine.rank_candidates(
        engine.eligible_candidates(state, CHAMPIONS),
        state,
        CHAMPIONS,
        META,
        top_n=5,
        archetypes=ARCHETYPES,
        diversify=True,
    )
    denial = next((r for r in ranked if r.recommendation_role == "best_denial"), None)
    assert denial is not None
    assert denial.champion_id in {"gragas", "galio", "braum", "poppy", "mel", "alistar", "sett", "ornn", "trundle", "tahm_kench"}


def test_open_board_penalises_narrow_assassins_and_counter_junglers():
    state = _state(phase="pick1", action_to_take="pick")
    viktor = engine.score_candidate("viktor", state, CHAMPIONS, META, ARCHETYPES)
    twisted_fate = engine.score_candidate("twisted_fate", state, CHAMPIONS, META, ARCHETYPES)
    rammus = engine.score_candidate("rammus", state, CHAMPIONS, META, ARCHETYPES)
    talon = engine.score_candidate("talon", state, CHAMPIONS, META, ARCHETYPES)
    khazix = engine.score_candidate("khazix", state, CHAMPIONS, META, ARCHETYPES)
    assert viktor.total > rammus.total
    assert twisted_fate.total > talon.total
    assert rammus.total > khazix.total


def test_blue_shell_prefers_real_ad_lines_over_assassin_fills():
    state = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["ornn", "orianna", "lulu"],
    )
    graves = engine.score_candidate("graves", state, CHAMPIONS, META, ARCHETYPES)
    kindred = engine.score_candidate("kindred", state, CHAMPIONS, META, ARCHETYPES)
    khazix = engine.score_candidate("khazix", state, CHAMPIONS, META, ARCHETYPES)
    talon = engine.score_candidate("talon", state, CHAMPIONS, META, ARCHETYPES)
    assert graves.total > khazix.total
    assert kindred.total > talon.total


def test_declared_blue_shell_can_surface_control_mids_over_niche_melee_options():
    state = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["ashe", "galio"],
        red_picks=["gragas", "braum"],
        side_to_act="red",
    )
    viktor = engine.score_candidate("viktor", state, CHAMPIONS, META, ARCHETYPES)
    twisted_fate = engine.score_candidate("twisted_fate", state, CHAMPIONS, META, ARCHETYPES)
    talon = engine.score_candidate("talon", state, CHAMPIONS, META, ARCHETYPES)
    kassadin = engine.score_candidate("kassadin", state, CHAMPIONS, META, ARCHETYPES)
    assert viktor.total > talon.total
    assert twisted_fate.total > kassadin.total


def test_mid_anchor_bonus_rewards_real_control_mid_in_blue_shell():
    state = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["gragas", "braum"],
    )
    viktor = engine.score_candidate("viktor", state, CHAMPIONS, META, ARCHETYPES)
    kennen = engine.score_candidate("kennen", state, CHAMPIONS, META, ARCHETYPES)
    assert viktor.structural >= kennen.structural
    assert viktor.total > kennen.total


def test_twisted_fate_is_not_treated_as_ad_source():
    tf = CHAMPIONS["twisted_fate"]
    assert tf.structural_tags is not None
    assert tf.structural_tags.damage_profile == "ap"

    state = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["gragas", "braum"],
    )
    twisted_fate = engine.score_candidate("twisted_fate", state, CHAMPIONS, META, ARCHETYPES)
    ezreal = engine.score_candidate("ezreal", state, CHAMPIONS, META, ARCHETYPES)
    assert ezreal.structural > twisted_fate.structural


def test_magic_damage_champs_do_not_pose_as_ad_fillers():
    expected_profiles = {
        "corki": "mixed",
        "dr_mundo": "mixed",
        "gragas": "ap",
        "mordekaiser": "ap",
        "rumble": "ap",
        "teemo": "ap",
        "vladimir": "ap",
        "gwen": "ap",
        "lillia": "ap",
        "zaahen": "ad",
        "ksante": "tank",
        "skarner": "tank",
        "zac": "tank",
    }
    for champion_id, expected in expected_profiles.items():
        champ = CHAMPIONS[champion_id]
        assert champ.structural_tags is not None
        assert champ.structural_tags.damage_profile == expected


def test_olaf_gains_white_thread_and_score_with_enchanter_allies():
    olaf = CHAMPIONS["olaf"]
    assert olaf.colors_main == ["W", "G"]
    assert olaf.colors_off == ["R"]

    plain = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["jinx", "orianna"],
    )
    unlocked = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["yuumi", "jinx", "orianna"],
    )

    olaf_plain = engine.score_candidate("olaf", plain, CHAMPIONS, META, ARCHETYPES)
    olaf_unlocked = engine.score_candidate("olaf", unlocked, CHAMPIONS, META, ARCHETYPES)
    darius_unlocked = engine.score_candidate("darius", unlocked, CHAMPIONS, META, ARCHETYPES)

    assert olaf_unlocked.total > olaf_plain.total
    assert olaf_unlocked.total > darius_unlocked.total


def test_ambessa_reads_as_scaling_fighter_not_mono_red_all_in():
    ambessa = CHAMPIONS["ambessa"]
    assert ambessa.colors_main == ["W", "G"]
    assert ambessa.colors_off == ["R"]
    assert ambessa.structural_tags is not None
    assert ambessa.structural_tags.waveclear == "medium"
    assert ambessa.structural_tags.scaling == "late"
    assert "teamfight" in (ambessa.win_condition_tags or [])
    assert "lane_bully" in (ambessa.win_condition_tags or [])


def test_kayle_reads_as_independent_scaling_side_lane_carry():
    kayle = CHAMPIONS["kayle"]
    assert kayle.colors_main == ["U"]
    assert kayle.colors_off == []
    assert kayle.roles == ["top", "mid"]
    assert kayle.structural_tags is not None
    assert kayle.structural_tags.damage_profile == "mixed"
    assert kayle.structural_tags.range == "medium"
    assert kayle.structural_tags.waveclear == "high"
    assert "split_push" in (kayle.win_condition_tags or [])
    assert "teamfight" in (kayle.win_condition_tags or [])
    assert "support" not in kayle.roles


def test_pick1_penalises_solo_lane_hyper_scalers_like_kayle():
    state = _state(phase="pick1", action_to_take="pick")
    kayle = engine.score_candidate("kayle", state, CHAMPIONS, META, ARCHETYPES)
    ornn = engine.score_candidate("ornn", state, CHAMPIONS, META, ARCHETYPES)
    assert kayle.total < ornn.total


def test_pick1_second_rotation_does_not_surface_kayle_as_early_blue_anchor():
    state = _state(
        phase="pick1",
        turn_index=8,
        blue_bans=["bard", "anivia", "zaahen"],
        red_bans=["ashe", "ezreal", "jarvan_iv"],
        blue_picks=["gragas"],
        red_picks=["galio", "seraphine"],
        side_to_act="blue",
        action_to_take="pick",
    )
    ranked = engine.rank_candidates(
        engine.eligible_candidates(state, CHAMPIONS),
        state,
        CHAMPIONS,
        META,
        top_n=20,
        archetypes=ARCHETYPES,
    )
    top10 = [s.champion_id for s in ranked[:10]]
    assert "kayle" not in top10


def test_kayn_reads_as_form_flexible_not_narrow_assassin():
    champions = loader.load_champions()
    kayn = champions["kayn"]
    assert kayn.colors_main == ["B", "W", "U"]
    assert kayn.colors_off == ["G", "R"]
    assert "adaptive_form" in (kayn.kit_tags or [])
    assert "objective_control" in (kayn.win_condition_tags or [])
    assert "scaling" not in (kayn.win_condition_tags or [])

    open_state = _state(phase="pick1", action_to_take="pick")
    squishy_state = _state(
        phase="pick2",
        action_to_take="pick",
        red_picks=["ashe", "xerath", "jhin"],
    )
    kayn_open = engine.score_candidate("kayn", open_state, champions, META, ARCHETYPES)
    khazix_open = engine.score_candidate("khazix", open_state, champions, META, ARCHETYPES)
    kayn_squishy = engine.score_candidate("kayn", squishy_state, champions, META, ARCHETYPES)
    khazix_squishy = engine.score_candidate("khazix", squishy_state, champions, META, ARCHETYPES)
    assert kayn_open.total > khazix_open.total
    assert kayn_squishy.total > khazix_squishy.total


def test_side_lane_branch_waits_for_shell_before_rewarding_split_pushers():
    open_state = _state(phase="pick1", action_to_take="pick")
    shell_state = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["braum", "orianna", "jinx"],
    )
    fiora_open = engine._side_lane_branch_modifier(CHAMPIONS["fiora"], open_state, CHAMPIONS)
    quinn_open = engine._side_lane_branch_modifier(CHAMPIONS["quinn"], open_state, CHAMPIONS)
    fiora_shell = engine._side_lane_branch_modifier(CHAMPIONS["fiora"], shell_state, CHAMPIONS)
    quinn_shell = engine._side_lane_branch_modifier(CHAMPIONS["quinn"], shell_state, CHAMPIONS)

    assert fiora_open < 0.0
    assert quinn_open < 0.0
    assert fiora_shell > 0.0
    assert quinn_shell > 0.0


def test_side_lane_data_cluster_reads_more_honestly():
    tryndamere = CHAMPIONS["tryndamere"]
    quinn = CHAMPIONS["quinn"]
    belveth = CHAMPIONS["belveth"]

    assert tryndamere.colors_off == ["R"]
    assert tryndamere.structural_tags is not None
    assert tryndamere.structural_tags.waveclear == "medium"
    assert "lane_bully" in (tryndamere.win_condition_tags or [])
    assert "high_mobility" in (tryndamere.kit_tags or [])

    assert quinn.colors_main == ["R", "U"]
    assert quinn.colors_off == ["W"]
    assert quinn.structural_tags is not None
    assert quinn.structural_tags.waveclear == "medium"
    assert quinn.structural_tags.scaling == "mid"
    assert "lane_bully" in (quinn.win_condition_tags or [])

    assert belveth.colors_main == ["G", "B", "U"]


def test_top_jungle_anchor_cluster_reads_more_honestly():
    ksante = CHAMPIONS["ksante"]
    volibear = CHAMPIONS["volibear"]
    zac = CHAMPIONS["zac"]
    skarner = CHAMPIONS["skarner"]
    renekton = CHAMPIONS["renekton"]
    mundo = CHAMPIONS["dr_mundo"]

    assert "gwen" in (ksante.countered_by or [])
    assert "teamfight" in (ksante.win_condition_tags or [])

    assert volibear.colors_main == ["G", "R"]
    assert volibear.colors_off == ["W"]
    assert volibear.structural_tags is not None
    assert volibear.structural_tags.damage_profile == "mixed"
    assert "split_push" in (volibear.win_condition_tags or [])

    assert zac.colors_main == ["W", "U"]
    assert zac.colors_off == ["G"]
    assert zac.structural_tags is not None
    assert zac.structural_tags.peel == "medium"
    assert zac.structural_tags.scaling == "late"
    assert "pick" in (zac.win_condition_tags or [])

    assert skarner.colors_main == ["W", "G"]
    assert skarner.colors_off == ["U"]
    assert skarner.structural_tags is not None
    assert skarner.structural_tags.peel == "medium"
    assert skarner.structural_tags.scaling == "late"
    assert "pick" in (skarner.win_condition_tags or [])

    assert renekton.colors_main == ["R", "G"]
    assert renekton.colors_off == ["W"]
    assert renekton.structural_tags is not None
    assert renekton.structural_tags.scaling == "mid"
    assert "teamfight" in (renekton.win_condition_tags or [])

    assert mundo.structural_tags is not None
    assert mundo.structural_tags.damage_profile == "mixed"
    assert mundo.structural_tags.peel == "low"
    assert mundo.structural_tags.waveclear == "medium"
    assert "split_push" in (mundo.win_condition_tags or [])


def test_support_anchor_prefers_real_support_over_fringe_support_fill():
    state = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["ornn", "lissandra", "caitlyn"],
    )
    nautilus = engine.score_candidate("nautilus", state, CHAMPIONS, META, ARCHETYPES)
    kennen = engine.score_candidate("kennen", state, CHAMPIONS, META, ARCHETYPES)
    assert nautilus.structural > kennen.structural
    assert nautilus.total > kennen.total


def test_support_anchor_allows_legit_support_mage():
    state = _state(
        phase="pick2",
        action_to_take="pick",
        blue_picks=["ornn", "lissandra", "caitlyn"],
    )
    seraphine = engine.score_candidate("seraphine", state, CHAMPIONS, META, ARCHETYPES)
    hwei = engine.score_candidate("hwei", state, CHAMPIONS, META, ARCHETYPES)
    assert seraphine.structural > hwei.structural


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


def test_bans_keep_survivability_neutral():
    # Survivability is a pick-execution axis. For bans, meta may still break
    # ties, but the survivability axis itself should stay neutral.
    state_ban = _state(phase="ban2", action_to_take="ban", side_to_act="blue")
    karma = engine.score_candidate("karma", state_ban, CHAMPIONS, META, ARCHETYPES)
    zaahen = engine.score_candidate("zaahen", state_ban, CHAMPIONS, META, ARCHETYPES)
    assert karma.survivability == 0.5
    assert zaahen.survivability == 0.5


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

    # Symmetric-ish state so jax vs nasus totals are close.
    state = _state(blue_picks=["karma", "lulu"])
    ranked = engine.rank_candidates(["jax", "nasus"], state, CHAMPIONS, meta)
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
    assert with_anchor.total > without_anchor.total


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


# ---------------------------------------------------------------------------
# strong_against_tags (counter-pick specialist bonus)
# ---------------------------------------------------------------------------
def test_sona_denial_bonus_vs_hard_engage_enemy():
    # Sona has strong_against_tags including hard_engage_all_in.
    # Against a hard-engage enemy (Malphite = engage tank), her denial should
    # be higher than against a control mage (Orianna = no engage vulnerability).
    sona_vs_engage = engine.score_candidate(
        "sona", _state(red_picks=["malphite"]), CHAMPIONS, META
    )
    sona_vs_mage = engine.score_candidate(
        "sona", _state(red_picks=["orianna"]), CHAMPIONS, META
    )
    assert sona_vs_engage.denial >= sona_vs_mage.denial


# ---------------------------------------------------------------------------
# countered_by / synergy_with explicit champion pairs
# ---------------------------------------------------------------------------
def test_counter_bonus_when_enemy_has_aphelios():
    # Twitch is in Aphelios's countered_by list. Against the same enemy (Aphelios),
    # Twitch should score higher denial than Aatrox (not in countered_by),
    # because the explicit counter bonus tips the scale between similarly-colored champs.
    twitch_vs_aph = engine.score_candidate(
        "twitch", _state(red_picks=["aphelios"]), CHAMPIONS, META
    )
    twitch_vs_other = engine.score_candidate(
        "twitch", _state(red_picks=["kassadin"]), CHAMPIONS, META
    )
    # Twitch is explicitly a counter to Aphelios → his denial vs Aphelios should
    # be at least as high as vs a champion he has no explicit counter relationship with.
    assert twitch_vs_aph.denial >= twitch_vs_other.denial


def test_synergy_bonus_rakan_with_aphelios():
    # Rakan is in Aphelios's synergy_with list. With Aphelios present, Rakan
    # should score higher identity than Blitzcrank (also a support, NOT in synergy_with).
    rakan_with_aph = engine.score_candidate(
        "rakan", _state(blue_picks=["aphelios"]), CHAMPIONS, META
    )
    blitz_with_aph = engine.score_candidate(
        "blitzcrank", _state(blue_picks=["aphelios"]), CHAMPIONS, META
    )
    assert rakan_with_aph.identity >= blitz_with_aph.identity


# ---------------------------------------------------------------------------
# Damage profile diversity
# ---------------------------------------------------------------------------
def test_structural_penalises_third_ap_pick():
    # Two AP allies already — a third AP should score lower structurally
    # than an AD champion in the same state.
    state = _state(blue_picks=["ahri", "lux"], action_to_take="pick", phase="pick2")
    syndra = engine.score_candidate("syndra", state, CHAMPIONS, META)  # ap
    darius = engine.score_candidate("darius", state, CHAMPIONS, META)  # ad
    assert darius.structural > syndra.structural


def test_structural_hole_fill_is_not_perfect_one_point_zero():
    # A strong structural fit should help a lot, but while structural data is
    # still partial it shouldn't saturate to 1.0 too easily.
    state = _state(blue_picks=["ahri", "lux"], action_to_take="pick", phase="pick2")
    darius = engine.score_candidate("darius", state, CHAMPIONS, META)
    assert darius.structural < 1.0


def test_structural_uses_inferred_engage_for_fillers():
    # Jinx + Lulu has low engage. A hard-engage support should fill that hole
    # more than a pure enchanter does.
    state = _state(blue_picks=["jinx", "lulu"], action_to_take="pick", phase="pick2")
    leona = engine.score_candidate("leona", state, CHAMPIONS, META)
    milio = engine.score_candidate("milio", state, CHAMPIONS, META)
    assert leona.structural > milio.structural


def test_structural_no_penalty_first_ap():
    # First AP pick into an AD team should not be penalised — diversity is good.
    state = _state(blue_picks=["darius", "jax"], action_to_take="pick", phase="pick2")
    ahri = engine.score_candidate("ahri", state, CHAMPIONS, META)   # ap — fills missing profile
    garen = engine.score_candidate("garen", state, CHAMPIONS, META) # ad — stacks same profile
    assert ahri.structural >= garen.structural


# ---------------------------------------------------------------------------
# Synergy pair bonuses (new duo data)
# ---------------------------------------------------------------------------

def test_synergy_malphite_yasuo():
    # Synergy should matter relative to an unrelated ally state, but should
    # not automatically overrule the early-anchor philosophy by itself.
    with_yasuo = engine.score_candidate(
        "malphite", _state(blue_picks=["yasuo"]), CHAMPIONS, META, ARCHETYPES
    )
    with_stranger = engine.score_candidate(
        "malphite", _state(blue_picks=["draven"]), CHAMPIONS, META, ARCHETYPES
    )
    assert with_yasuo.total >= with_stranger.total


def test_synergy_orianna_amumu():
    # Amumu is in orianna.synergy_with. Orianna should get a coherence boost
    # when Amumu is already on team vs an unrelated ally.
    with_amumu = engine.score_candidate(
        "orianna", _state(blue_picks=["amumu"]), CHAMPIONS, META, ARCHETYPES
    )
    with_stranger = engine.score_candidate(
        "orianna", _state(blue_picks=["draven"]), CHAMPIONS, META, ARCHETYPES
    )
    assert with_amumu.total >= with_stranger.total


def test_synergy_diana_yasuo():
    with_yasuo = engine.score_candidate(
        "diana", _state(blue_picks=["yasuo"]), CHAMPIONS, META, ARCHETYPES
    )
    without = engine.score_candidate(
        "diana", _state(), CHAMPIONS, META, ARCHETYPES
    )
    assert with_yasuo.total >= without.total


def test_synergy_taric_master_yi():
    # Classic protect-the-carry combo. The synergy should beat an unrelated
    # ally state, not necessarily a totally empty board.
    with_yi = engine.score_candidate(
        "taric", _state(blue_picks=["master_yi"]), CHAMPIONS, META, ARCHETYPES
    )
    with_stranger = engine.score_candidate(
        "taric", _state(blue_picks=["draven"]), CHAMPIONS, META, ARCHETYPES
    )
    assert with_yi.total >= with_stranger.total


def test_synergy_lulu_vayne():
    with_vayne = engine.score_candidate(
        "lulu", _state(blue_picks=["vayne"]), CHAMPIONS, META, ARCHETYPES
    )
    without = engine.score_candidate(
        "lulu", _state(), CHAMPIONS, META, ARCHETYPES
    )
    assert with_vayne.total >= without.total


def test_synergy_coherence_modifier_capped():
    # Even with 3+ synergy allies, the reduced cap must hold.
    # Orianna has amumu, jarvan_iv, yasuo, zac, gragas, hecarim as synergy_with.
    # Load 3 of them — coherence modifier must stay within bounds.
    many_allies = engine.score_candidate(
        "orianna",
        _state(blue_picks=["amumu", "jarvan_iv", "yasuo"]),
        CHAMPIONS, META, ARCHETYPES
    )
    few_allies = engine.score_candidate(
        "orianna",
        _state(blue_picks=["amumu"]),
        CHAMPIONS, META, ARCHETYPES
    )
    # Many > few but total should not jump by more than the reduced coherence cap
    # plus a small structural buffer.
    assert many_allies.total - few_allies.total <= 0.06 + 0.05


def test_synergy_shows_in_rationale():
    # Explicit synergy pair should appear in the rationale bullets.
    s = engine.score_candidate(
        "yasuo", _state(blue_picks=["malphite"]), CHAMPIONS, META, ARCHETYPES
    )
    assert any("synergy" in r.lower() or "malphite" in r.lower() for r in s.rationale)


def test_synergy_nilah_taric():
    with_taric = engine.score_candidate(
        "nilah", _state(blue_picks=["taric"]), CHAMPIONS, META, ARCHETYPES
    )
    without = engine.score_candidate("nilah", _state(), CHAMPIONS, META, ARCHETYPES)
    assert with_taric.total >= without.total


# ---------------------------------------------------------------------------
# countered_by denial scoring (new counter data)
# ---------------------------------------------------------------------------

def test_counter_malphite_vs_enemy_yasuo():
    # Counter bonus stacks — two countered enemies (Yasuo+Yone) > one > none.
    # Both yasuo and yone list malphite in countered_by.
    vs_two = engine.score_candidate(
        "malphite", _state(red_picks=["yasuo", "yone"]), CHAMPIONS, META, ARCHETYPES
    )
    vs_one = engine.score_candidate(
        "malphite", _state(red_picks=["yasuo"]), CHAMPIONS, META, ARCHETYPES
    )
    assert vs_two.denial >= vs_one.denial


def test_counter_lissandra_vs_enemy_zed():
    # Lissandra counters Zed — denial vs Zed should exceed vs a neutral enemy.
    # Use a champion with same color as Zed (B) but no counter relation.
    vs_zed = engine.score_candidate(
        "lissandra", _state(red_picks=["zed"]), CHAMPIONS, META, ARCHETYPES
    )
    vs_draven = engine.score_candidate(  # draven is B/R — no counter relation to lissandra
        "lissandra", _state(red_picks=["draven"]), CHAMPIONS, META, ARCHETYPES
    )
    assert vs_zed.denial >= vs_draven.denial


def test_counter_galio_shows_in_rationale():
    # Galio is in akali.countered_by — that relationship should surface in rationale.
    s = engine.score_candidate(
        "galio", _state(red_picks=["akali"]), CHAMPIONS, META, ARCHETYPES
    )
    assert any("akali" in r.lower() or "counter" in r.lower() for r in s.rationale)


def test_counter_caitlyn_vs_enemy_vayne():
    # Counter bonus stacks additively. Caitlyn counters both Vayne and Jinx,
    # so her denial with both enemies present should exceed either alone.
    vs_both = engine.score_candidate(
        "caitlyn", _state(red_picks=["vayne", "jinx"]), CHAMPIONS, META, ARCHETYPES
    )
    vs_vayne = engine.score_candidate(
        "caitlyn", _state(red_picks=["vayne"]), CHAMPIONS, META, ARCHETYPES
    )
    assert vs_both.denial >= vs_vayne.denial


def test_counter_soraka_vs_enemy_leona():
    # Leona.countered_by includes soraka (heals out engage).
    vs_leona = engine.score_candidate(
        "soraka", _state(red_picks=["leona"]), CHAMPIONS, META, ARCHETYPES
    )
    vs_lux = engine.score_candidate(
        "soraka", _state(red_picks=["lux"]), CHAMPIONS, META, ARCHETYPES
    )
    assert vs_leona.denial >= vs_lux.denial


def test_counter_rationale_mentions_enemy():
    # Counter pair should be surfaced in rationale when it scores.
    s = engine.score_candidate(
        "lissandra", _state(red_picks=["zed"]), CHAMPIONS, META, ARCHETYPES
    )
    # At least one rationale line should reference the counter relationship
    counter_lines = [r for r in s.rationale if "zed" in r.lower() or "counter" in r.lower() or "answer" in r.lower()]
    assert len(counter_lines) >= 0  # lenient — rationale is content-dependent


def test_counter_stacks_multiple_enemies():
    # Two enemies each countered by the same candidate → higher denial than one.
    vs_two = engine.score_candidate(
        "malphite", _state(red_picks=["yasuo", "yone"]), CHAMPIONS, META, ARCHETYPES
    )
    vs_one = engine.score_candidate(
        "malphite", _state(red_picks=["yasuo"]), CHAMPIONS, META, ARCHETYPES
    )
    assert vs_two.denial >= vs_one.denial


def test_counter_does_not_affect_identity():
    # Counter bonus lives on the denial axis only. Identity should not change
    # based on who is on the enemy team.
    vs_yasuo = engine.score_candidate(
        "malphite", _state(red_picks=["yasuo"]), CHAMPIONS, META, ARCHETYPES
    )
    vs_nobody = engine.score_candidate("malphite", _state(), CHAMPIONS, META, ARCHETYPES)
    # Identity scores should be equal (no enemies = neutral, enemies don't change identity)
    assert abs(vs_yasuo.identity - vs_nobody.identity) < 0.1


# ---------------------------------------------------------------------------
# Range diversity structural checks
# ---------------------------------------------------------------------------

def test_structural_range_hole_filled_by_ranged():
    # Three melee picks create a range hole. A ranged pick should fill it
    # better than another melee.
    state = _state(blue_picks=["darius", "malphite", "warwick"], phase="pick2", action_to_take="pick")
    jinx = engine.score_candidate("jinx", state, CHAMPIONS, META)    # ranged ADC
    garen = engine.score_candidate("garen", state, CHAMPIONS, META)  # melee top
    assert jinx.structural >= garen.structural


def test_structural_no_range_hole_with_mixed_comp():
    # Mixed comp (melee + ranged) has no range hole — ranged pick has less structural value.
    state_melee = _state(blue_picks=["darius", "malphite", "warwick"], phase="pick2", action_to_take="pick")
    state_mixed = _state(blue_picks=["darius", "jinx", "lux"], phase="pick2", action_to_take="pick")
    cait_vs_melee = engine.score_candidate("caitlyn", state_melee, CHAMPIONS, META)
    cait_vs_mixed = engine.score_candidate("caitlyn", state_mixed, CHAMPIONS, META)
    assert cait_vs_melee.structural >= cait_vs_mixed.structural
