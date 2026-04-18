# Fivefold — Design & Requirements

> *A League of Legends drafting tool grounded in color-identity theory and
> game-theoretic adaptation, not patch winrates or comfort picks.*

> Working name: **Fivefold**. Alternates considered: Coherence, Bant, Drafted.
> Final name TBD.

---

## 1. Thesis

Most existing draft tools (Blitz, Mobalytics, OP.GG) optimize for the wrong signal.
They recommend picks based on:

1. Patch-level champion winrate.
2. Player comfort / one-trick history.
3. Pairwise "synergy" heuristics (X pairs well with Y).
4. Isolated counter-picks (Z shuts down A in lane).

This collapses a draft into a bag of individually-optimized champions. But a draft
is not a bag — it is a **coherent win condition built adversarially across ten
alternating decisions**. Each team is simultaneously trying to:

1. Build a composition that has one clear way to win (the *win condition*).
2. Disrupt, delay, or invalidate the opponent's emerging win condition.
3. Cover its own structural holes (frontline, engage, waveclear, peel, scaling).

The tool operationalizes this by treating champions as **color-identity primitives**
(per LS's MTG-colors framing) rather than as winrate rows. Color tags encode what
a champion *wants to do* on a fundamental level, independent of patch. A draft
is then a sequence of decisions that builds and defends a color identity while
denying the opponent theirs.

The product demonstrates this theory live: given any draft state, it scores
candidate picks on four axes derived from the theory, and produces a
coaching-style rationale that explains *why* — in color-theory terms, not
winrate terms.

---

## 2. Scope

### v1 (this document)

- Standard 5v5 Summoner's Rift draft.
- 10 bans (5 per side) + 10 picks (alternating, Blue picks first).
- Pure theory: no patch data, no meta winrates, no Riot API.
- Single-draft mode (no series / Fearless).
- Web app, publicly accessible.

### v1.5

- Fearless Draft mode (BO3/BO5), with series-level champion pool tracking.
- First Selection pre-draft advisor (side vs pick-order tradeoff).

### Out of scope (explicitly)

- Live patch data integration.
- Player comfort / account history.
- ARAM, Arena, or non-Rift modes.
- Draft replay import from pro games (nice-to-have for v2+).

---

## 3. User & Use Case

**Primary user: me.** This is a portfolio / theory-demonstration project, not
a commercial tool. Implications:

- Explanation quality > recommendation optimality. A mediocre pick with a brilliant
  rationale is more valuable than a perfect pick with a generic one-liner.
- The repo itself is part of the product. README, design doc, and code clarity
  matter as much as the running app.
- No user accounts, no persistence across sessions, no analytics in v1.

**Secondary audience:** anyone (coach, analyst, curious player) who lands on
the repo or app and wants to see the theory applied live.

---

## 4. Architecture Overview

Two layers with a clean contract between them.

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND (Next.js)                                          │
│   Draft board · Pick/ban UI · Score display · Rationale     │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST/JSON
┌──────────────────────────▼──────────────────────────────────┐
│ BACKEND (FastAPI)                                           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ DETERMINISTIC CORE                                  │    │
│  │   • Champion data (JSON)                            │    │
│  │   • DraftState model                                │    │
│  │   • Scoring engine (4-axis)                         │    │
│  │   • Legal-candidate enumeration                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐    │
│  │ LLM PIPELINE (3 stages)                             │    │
│  │   1. Enemy Reader  → what are they building?        │    │
│  │   2. Identity Critic → are WE coherent?             │    │
│  │   3. Coach → final recommendation + rationale       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Design principle:** the deterministic core is the product. The LLM layer is
narration over a decision that's already been made by code. If the LLM
disappears tomorrow, the tool still works — it just gets less eloquent.

---

## 5. Color Framework (LS / MTG)

All six categories (W, U, B, R, G, and Colorless) are first-class in this tool.
Definitions below are from LS / Rübezahl's master spreadsheet, which is the
canonical source.

| Code | Name | Definition (per LS) |
|------|------|---------------------|
| **R** | Red | Aggression. Relies on aggressive play for early resources to force early wins. Runs out of fuel fast; often extremely weak if behind or even; needs to keep accelerating. Snowball-based. Volatile, straight-forward, linear, speed. *Not every Red champion is a "sinner."* |
| **G** | Green | Harmony / synergy. Curved power spikes and item timings. Bad solo. Very good in wars of attrition, building with allies and helping them. Also covers champions with heavy item timings. |
| **U** | Blue | Control, knowledge, manipulation, deception. Denial. Superior resource management. Evasion. Terraforming. Often weak or decent early, massive later. Tries to account for everything before it happens. Wins by depleting the opponent of options. *"Inaction is action."* |
| **W** | White | Versatile, fills many roles, often supporting — can blend with other colors easily. Versatile in draft, binary in game ("Choose One"). Good at resisting early Red. |
| **B** | Black | Power at a cost. Quests, demands, conditions. Sacrifice, tradeoffs. Accelerates what another color is already trying to do. |
| **C** | Colorless | Dedicated themes. Strong inside them. **Draft warps around them.** |

### Main vs off colors

This is a core distinction in LS's system and the scoring engine must respect it:

- **Main color** (X in the sheet): the theme best expressed by the champion's
  kit, core items, team interaction, and scaling numbers. This is the identity.
- **Off color** (O in the sheet): a theme that is *conditional* — influenced
  by item build, playstyle choice, or matchup. Not core identity, but available
  as a flex direction.

Implication for scoring: main colors drive the Identity score. Off colors are
used only when the DraftState confirms the condition that activates them
(e.g. Braum's Green off-color activates if our comp is clearly Green-heavy
and we're drafting him as a scaling peel support rather than early engage).

### Contextual champions

A handful of champions have colors that **only resolve once other picks land**.
Examples from the source data:

- **Rakan** — colorless when paired with Xayah.
- **Aphelios** — "dependent on team composition."
- **Lux** — Green if mid full AP.
- **Braum** — off-colors depend on usage pattern.

The scoring engine re-evaluates these champions' effective identity on every
turn based on current ally picks. This is not a special case to hack around —
it's a real feature of the theory and worth a named primitive in the code
(`ContextualColorResolver`).

---

## 6. Data Model

### 6.1 Champion schema

Based on the actual LS spreadsheet (148 champions parsed), plus room for the
structural and matchup data Fivefold adds on top.

Gangplank as a worked example:

```json
{
  "id": "gangplank",
  "name": "Gangplank",
  "roles": ["top"],
  "colors_main": ["G", "U"],
  "colors_off": ["W"],
  "contextual": false,
  "ls_notes": "controls everything, scales/ramps up, still supportive. critplank, tankplank, can accelerate, can be a menace to kill. lots of synergy with botlane, item timings [IE, sterak, trinity, lvl 9/13]",
  "win_condition_tags": ["scaling", "global_pressure", "teamfight_zone"],
  "structural_tags": {
    "damage_profile": "mixed",
    "range": "medium",
    "engage": "medium",
    "peel": "low",
    "frontline": "low",
    "waveclear": "high",
    "scaling": "high"
  },
  "synergy_tags": ["global_ult", "scaling_carry"],
  "counter_tags": ["early_all_in", "mobility_dodge_barrels"]
}
```

A contextual champion (Rakan) for contrast:

```json
{
  "id": "rakan",
  "name": "Rakan",
  "roles": ["support"],
  "colors_main": ["R", "W"],
  "colors_off": ["U", "C"],
  "contextual": true,
  "context_rules": [
    {
      "condition": "ally_has_champion",
      "value": "xayah",
      "effect": "add_main_color",
      "color": "C"
    }
  ],
  "ls_notes": "colorless when paired with Xayah",
  ...
}
```

### 6.2 Data provenance

Champion color data is imported from LS / Rübezahl's public spreadsheet. The
project credits this source in the README and in `champions.json` itself. The
~22 champions missing from the sheet (recent releases: K'Sante, Naafiri,
Briar, Smolder, Hwei, Milio, Nilah, Bel'Veth, Akshan, Viego, Samira, Rell,
Seraphine, Gwen, Vex, Zeri, Renata, Aurora, Ambessa, etc.) are tagged manually
using the Phase 0 tagging-assist CLI, with the owner's own judgment flagged
as such in the data.

### 6.3 DraftState schema

```python
class DraftState:
    phase: Literal["ban1", "pick1", "ban2", "pick2", "complete"]
    turn_index: int  # 0..19
    blue_bans: list[ChampionId]   # up to 5
    red_bans: list[ChampionId]    # up to 5
    blue_picks: list[ChampionId]  # up to 5
    red_picks: list[ChampionId]   # up to 5
    side_to_act: Literal["blue", "red"]
    action_to_take: Literal["ban", "pick"]
```

Standard pro draft turn order (Blue has First Pick):

```
Phase 1 bans: B R B R B R
Phase 1 picks: B | RR | BB | R
Phase 2 bans: R B R B
Phase 2 picks: R | BB | R
```

### 6.4 Composition analysis (derived from DraftState)

For each side, at any point in the draft:

```python
class CompositionAnalysis:
    declared_colors: dict[Color, float]        # weighted color presence
    inferred_win_condition: str | None         # null until enough picks
    archetype_distribution: dict[Archetype, float]
    structural_holes: list[StructuralHole]     # e.g. "no frontline"
    coherence_score: float                     # 0..1
```

### 6.5 Meta tiers (manually maintained, per patch)

A separate file, `meta_tiers.json`, maintained by hand per patch. Five ordered
arrays (one per role), champions ordered from strongest to weakest *within*
the tier. Anything not listed is treated as "playable but not meta-prioritized."

```json
{
  "patch": "2026.14",
  "updated_at": "2026-04-12",
  "tiers": {
    "top": ["aatrox", "jax", "renekton", "ksante", "gragas"],
    "jungle": ["vi", "briar", "diana", "wukong"],
    "mid": ["ahri", "hwei", "orianna", "viktor"],
    "bot": ["kaisa", "jinx", "ezreal", "varus"],
    "support": ["nautilus", "alistar", "karma", "thresh"]
  }
}
```

**Design rules for this data:**

- Order within the array matters. Index 0 is strongest.
- Separate from champion data — meta is patch-dependent, identity is not.
- Consumed only by the Survivability score (§7.4) and as a tiebreaker.
  **Never** consumed by identity or denial scoring. This enforces the thesis:
  meta strength modulates execution, it does not drive strategy.

---

## 7. Scoring Engine

For any candidate pick given a DraftState, compute four scores in `[0, 1]`:

### 7.1 Identity score

Does this pick reinforce our team's emerging color identity and win condition?

- High when the candidate's colors overlap our declared colors.
- High when the candidate's win-condition tags align with what the first 1–2
  picks suggested.
- Low when it contradicts (e.g. adding a scaling scaler to a lane-dominant
  early-game comp).
- **Meta-agnostic.** Does not consult `meta_tiers.json`.

### 7.2 Denial score

Does this pick disrupt the opponent's win condition?

- High when candidate's counter_tags match the enemy's dominant color/archetype.
- Weighted by how committed the enemy already is (a fifth-pick denial is more
  valuable than a first-pick denial because they can't adapt).
- **Meta-agnostic.** Does not consult `meta_tiers.json`.

### 7.3 Structural score

Does this pick fill our structural holes?

- Penalizes redundancy (two engage tanks, three scaling carries).
- Rewards covering holes flagged in the current CompositionAnalysis.
- **Meta-agnostic.** Does not consult `meta_tiers.json`.

### 7.4 Survivability score

Basic lane-matchup sanity check *plus* meta-tier modulation. Low-resolution by
design — this is the axis that prevents "theoretically perfect, practically
unplayable" picks.

- Does the candidate's lane have a reasonable matchup against the opponent's
  likely lane opponent? (Uses counter_tags, not matchup tables.)
- **Meta tier bonus:** if the candidate is in `meta_tiers[role]`, apply a
  bonus that scales with position in the array (index 0 → largest bonus,
  tapering off). Cap the bonus so a meta pick never wins on meta alone.
- **Meta tier penalty:** if the enemy's lane counterpart is a high-tier meta
  pick and our candidate is not, apply a small penalty — you're walking into
  a buzzsaw.

### 7.5 Final score

```
score = w_i * identity + w_d * denial + w_s * structural + w_v * survivability
```

Weights adjust with draft phase — early picks weight identity and denial heavily,
late picks weight structural (gap-filling) and survivability (counter-picking).

**Tiebreaker rule:** when two candidates' final scores are within a small
epsilon (say 0.03), break the tie by meta-tier position. This is where "these
two picks are theoretically equivalent, pick the one that's S-tier right now"
gets encoded without letting meta dominate the recommendation.

**Critical:** each axis is returned alongside the final score *and* the meta
contribution is returned as its own field. The LLM layer consumes axes
separately and can say "this pick is great on identity and denial but it's
currently weak in the meta, consider it anyway" — surfacing the meta input
to the user instead of hiding it in a black-box score.

---

## 8. LLM Pipeline

Three stages, each a single structured call. No agent loops, no autonomous
orchestration.

### 8.1 Stage 1 — Enemy Reader

**Input:** enemy side's current picks + bans + (on their first pick) the champion
data for what they just picked.

**Output:** structured JSON.

```json
{
  "declared_colors": ["U", "W"],
  "likely_win_condition": "protect the hyper-carry, scale to 3 items",
  "likely_archetype": "protect_the_carry",
  "power_spike": "mid-to-late",
  "structural_holes_so_far": ["no early pressure"],
  "confidence": 0.6
}
```

Prompt lives in `backend/prompts/enemy_reader.hbs` (Handlebars templated,
matching the pattern you already use at Educative).

### 8.2 Stage 2 — Identity Critic

**Input:** our side's current picks + the scoring engine's raw output for the
top N candidates.

**Output:** critique of our emerging comp.

```json
{
  "our_declared_identity": "mid-range teamfight with skirmish pivots",
  "coherence_assessment": "mostly coherent, but our 3rd pick added a split-push threat that doesn't match",
  "risks": ["win condition is not clearly defined yet", "no reliable engage"],
  "what_we_need_next": ["engage tool", "reinforce primary color"]
}
```

### 8.3 Stage 3 — Coach

**Input:** everything — DraftState, top 3 candidates with 4-axis scores, Enemy
Reader output, Identity Critic output.

**Output:** the recommendation shown to the user.

- A top pick with one-paragraph rationale that references enemy's win condition
  and our identity coherence.
- 2 alternate picks with one-line tradeoffs.
- Optional "what to watch for" note about the next enemy pick.

### 8.4 Model choice & fallback

- Default: Claude Sonnet via API (fast, good at structured output).
- Fallback: scoring-engine-only mode returns top-3 picks by score with
  templated rationale. Useful for dev, rate-limit handling, and "this app
  still works if the LLM service is down."

---

## 9. Frontend

Single-page app. Minimal routing.

### 9.1 Main draft view

- Two 5-slot columns (Blue left, Red right), 5 ban slots above each.
- Champion grid (roleable, searchable, filterable by color).
- Current-turn indicator with countdown (cosmetic only in v1 — no real timer
  enforcement).
- "Suggest for me" button — triggers backend call for current side.
- "Simulate opponent" toggle — if on, backend also auto-picks for the opposing side.

### 9.2 Recommendation panel

- Top pick with rationale (from Coach stage).
- 2 alternates with axis-score bars visible (identity/denial/structural/survivability).
- Collapsible "Enemy Reader" card showing what we think they're building.
- Collapsible "Identity Critic" card showing how coherent we are.

### 9.3 Out of scope for v1 UI

- Drag-to-reorder roles in lane assignments (assume role = primary role in data).
- Draft-history / save-and-resume.
- Mobile-optimized layout (desktop-first; just don't break on mobile).

---

## 10. API Contract

```
POST /api/draft/analyze
  body: DraftState
  returns: {
    top_candidates: [{ champion, scores, rationale_short }],
    enemy_reader: EnemyReaderOutput,
    identity_critic: IdentityCriticOutput,
    coach_recommendation: CoachOutput
  }

POST /api/draft/score
  body: { draft_state, candidate_champion_ids: [string] }
  returns: [{ champion, scores }]   # scoring only, no LLM

GET /api/champions
  returns: [ChampionData]
```

Keep `/api/draft/score` public and LLM-free so the frontend can show live
axis-score bars as the user hovers champions in the grid, without rate-limiting
concerns.

---

## 11. Build Plan

Phased so each phase is a usable artifact.

### Phase 0 — Data & tagging tooling (1–2 weekends)

- Finalize champion schema (needs your sample).
- Import your existing ~170 tagged champions into a single `champions.json`.
- Write a validation script: every champion has all required fields, referenced
  tags exist in a tag vocabulary file.
- **Build a tagging-assist CLI.** Walks through untagged or newly-released
  champions one at a time. For each, shows:
  - The candidate champion's kit summary (pulled from a static blurb file).
  - The 3–5 already-tagged champions with the most similar structural_tags,
    as calibration anchors.
  - Prompts for colors, color_weights, win_condition_tags, counter_tags.
  - Writes back to `champions.json`, with a git-friendly diff.
- Create the first `meta_tiers.json` for the current patch.

### Phase 1 — Scoring engine (1 week)

- Python module, no web server yet.
- `score_candidate(candidate, draft_state) -> Scores` function.
- CLI entry point: `python -m drafter score --state state.json`.
- Snapshot tests on a handful of hand-curated draft states with expected
  top-3 candidates. This is your regression safety net.

### Phase 2 — API (3–4 days)

- Wrap engine in FastAPI.
- Add `/score` and `/champions` endpoints first (no LLM).
- Dockerfile, basic CI.

### Phase 3 — LLM pipeline (1 week)

- Implement three prompts in Handlebars templates.
- Pydantic response models for each stage (so responses are validated).
- `/analyze` endpoint.
- Fallback path (LLM disabled → templated rationale).

### Phase 4 — Frontend (1–2 weeks)

- Next.js app, Tailwind.
- Draft board state machine.
- Calls to `/analyze` and `/score`.
- Deploy: Vercel (frontend), Railway/Fly (backend).

### Phase 5 — Polish & README (3–4 days)

- Landing page that opens with the thesis, not the UI.
- README with the theory section as the first thing a reader sees.
- Short screen-recording demo in the README.

### Phase 6+ (v1.5)

- Fearless Draft mode — adds a series state wrapping DraftState with a pool of
  unavailable champions.
- First Selection advisor.

---

## 12. Open Questions for You

Data-level questions (mostly resolved by LS sheet import):

1. ~~Champion schema shape~~ — resolved. Main + off colors, no weights,
   plus `contextual` flag for conditional identity.
2. ~~Pure vs weighted colors~~ — resolved. Main/off binary.
3. ~~Archetypes~~ — deferred. LS system doesn't require explicit archetypes;
   composition identity emerges from color distribution. Revisit if the
   Identity Critic's output feels too diffuse in testing.
4. **Counter granularity** — still open. Tags vs champion-to-champion edges
   vs both. Recommend tags for v1 to keep the data tractable.

Product-level questions:

5. **Missing champions** — the LS sheet stops at Zyra and misses recent
   releases (~22 champions). Plan: tag manually via Phase 0 CLI, mark
   `source: "owner"` vs `source: "ls_sheet"` so provenance is honest.
6. **Attribution** — what does the README say about LS / Rübezahl?
   Suggested: direct credit at the top of the color-framework section,
   link to the Pick-Ban.gg drafting sandbox they host, and a note that
   missing champions were tagged by you.
7. **Naming** — Fivefold is the working name. Other candidates: Coherence,
   Bant, Drafted, or something LS-ecosystem-native.

---

## 13. What This Project Signals

For a portfolio reviewer, this repo demonstrates:

- A non-trivial domain model (drafting as game theory, not winrate lookup).
- Clean separation between deterministic reasoning and LLM narration — the
  exact pattern that matters in serious GenAI engineering.
- Multi-stage prompt pipelines with typed contracts between stages.
- Product thinking: the LLM is not the product, the theory is; the LLM is
  a presentation layer.
- Shipped full-stack project with a clear thesis and a working demo.

Intentionally *not* demonstrated:
- Fine-tuning, vector search, or RAG. None of them fit this problem, and
  pretending they do would be worse than not using them.
