# Fivefold — Task Tracker

Living document. Update as work progresses. Top of file = current state. Each phase has a concrete "next action" so resuming work never requires re-reading the whole design doc.

> **Update rules:** When finishing a task, change `[ ]` to `[x]` and add a one-line note under it if non-obvious. When starting a new phase, update the **Current state** block at the top.

---

## Current state

**Phase:** 4 — Frontend (MVP shipped + QoL polish pass; LLM pipeline deferred)
**Last updated:** 2026-04-18
**Next action:** Run end-to-end: `cd backend && .venv/bin/uvicorn fivefold.api:app --port 8000` and `cd frontend && npm run dev`. Click through a draft, verify Suggest returns top 3. Then decide: (a) polish frontend (champion images, Enemy/Identity cards shell), (b) Phase 3 LLM pipeline to fill `analyze` narrative, or (c) circle back to Phase 0 to populate `win_condition_tags` / `structural_tags` / `meta_tiers.json` so the scores gain signal.

**What's done:**
- Design doc written (`docs/DESIGN.md`)
- Champion color data imported from LS / Rübezahl sheet (148 champions)
- Recent champions color-tagged by owner (19 champions)
- Counter tags added for owner-tagged champions
- Tagging CLI built (`scripts/tag.py`)
- Project structured for Claude Code

**What's next:**
Fill out `roles`, `win_condition_tags`, `structural_tags` for all 167 champions, and `counter_tags` for the 148 LS-sheet champions. Use the tagging CLI.

**Blockers:** None.

---

## Phase 0 — Data

Goal: every champion in `data/champions.json` has complete Fivefold-schema data.

- [x] Import LS / Rübezahl color data (148 champions)
- [x] Tag recent champions with colors (19 champions)
- [x] Add counter_tags to owner-tagged champions
- [x] Build tagging CLI (`scripts/tag.py`)
- [ ] Add Briar to `champions.json` with owner-provided colors
- [ ] Fill `roles` for all 167 champions
- [ ] Fill `win_condition_tags` for all 167 champions
- [ ] Fill `structural_tags` for all 167 champions (7 sub-fields each)
- [ ] Fill `counter_tags` for 148 LS-sheet champions
- [ ] Populate `data/meta_tiers.json` with current patch S-tiers per role
- [ ] Add a validation script (`scripts/validate.py`) that checks every champion has all required fields and all tag values are in the known vocabulary

**How to do it:** `cd scripts && python tag.py`. It picks up where you left off, saves after every champion, shows similar already-tagged champions as anchors.

**Definition of done:** `python scripts/tag.py --list` shows 167/167 complete, and validation script passes.

---

## Phase 1 — Scoring engine

Goal: pure-Python module that scores a candidate pick given a DraftState.

- [x] Create `backend/` directory and Python project setup (pyproject.toml)
- [x] Define Pydantic models: `Champion`, `DraftState`, `CandidateScore`, `MetaTiers` (`backend/fivefold/models.py`)
- [x] Implement data loaders for `champions.json` and `meta_tiers.json`
- [x] Implement `ContextualColorResolver` — re-resolves contextual champion identity based on DraftState
- [x] Implement `CompositionAnalysis` — derives declared_colors, structural_holes, coherence from a side's picks
- [x] Implement `score_identity()` — color overlap with colorless-definer handling
- [x] Implement `score_denial()` — color-counter matrix + tag capability match
- [x] Implement `score_structural()` — hole coverage (neutral until structural_tags are populated)
- [x] Implement `score_survivability()` — meta tier bonus (neutral until `data/meta_tiers.json` populated)
- [x] Implement `score_candidate()` — main entry point, applies phase-adjusted weights
- [x] Implement tiebreaker logic (meta tier position when totals within 0.03)
- [x] Write snapshot tests with expected high/low picks (12 tests passing)
- [x] CLI entry point: `python -m fivefold score --state state.json`

**Key signature (from CLAUDE.md):**
```python
def score_candidate(
    candidate_id: str,
    draft_state: DraftState,
    champions: dict[str, Champion],
    meta_tiers: MetaTiers,
) -> CandidateScore
```

**Hardest sub-task:** the structural_holes detection. Mediocre version: rule-based ("no frontline if frontline_level of all picks is 'none' or 'low'"). Good version: learned from testing against real draft examples. Start with rule-based.

**Definition of done:** all snapshot tests pass, CLI can score any candidate against any valid DraftState.

---

## Phase 2 — API

Goal: FastAPI wrapping the engine, no LLM yet.

- [x] FastAPI project skeleton (`backend/fivefold/api.py` with app factory + lifespan data load)
- [x] `GET /api/champions` — returns all champion data
- [x] `POST /api/draft/score` — takes DraftState + candidate_ids or top_n, returns scores only (no LLM, fast)
- [x] `POST /api/draft/analyze` — deterministic placeholder shape that Phase 3 will fill with LLM output
- [x] CORS config for local Next.js dev server (env-overridable via `FIVEFOLD_CORS_ORIGINS`)
- [x] Dockerfile (`backend/Dockerfile`, build from repo root)
- [x] Basic CI (GitHub Actions: `pytest`)
- [x] `GET /api/health` (bonus: useful for Railway/Fly healthchecks)

**Definition of done:** can hit `/api/draft/score` from curl/httpie and get valid JSON back.

---

## Phase 3 — LLM pipeline

Goal: 3-stage pipeline that produces the final recommendation narrative.

- [ ] Anthropic SDK setup with env var for API key
- [ ] Prompt template loader (simple f-string or Handlebars)
- [ ] Stage 1: Enemy Reader prompt + Pydantic response model
- [ ] Stage 2: Identity Critic prompt + Pydantic response model
- [ ] Stage 3: Coach prompt + Pydantic response model
- [ ] Pipeline orchestrator function (takes DraftState, calls three stages in order)
- [ ] Wire into `/api/draft/analyze`
- [ ] Fallback path: if ANTHROPIC_API_KEY missing or call fails, return templated rationale from scores only
- [ ] Rate limit handling (exponential backoff, cached results by DraftState hash)

**Model:** `claude-sonnet-4-20250514`.

**Definition of done:** `/api/draft/analyze` returns coherent recommendation narrative, and degrades gracefully with LLM disabled.

---

## Phase 4 — Frontend

Goal: Next.js draft board app that talks to the backend.

- [x] Next.js 14 + Tailwind + TypeScript scaffolding (`frontend/`)
- [x] Champion grid component (search, filter by role)
- [x] Draft board layout: 5-slot columns per side, 5 ban slots per side, phase indicator
- [x] DraftState state machine (client-side, turn order enforced via `lib/turnOrder.ts`)
- [x] Recommendation panel: top pick + 2 alternates with 4-axis bars (via `/api/draft/analyze`)
- [x] Axis score visualization (4 bars: identity, denial, structural, survivability)
- [x] Undo + Reset + First-pick side toggle in header
- [x] Filter champion grid by color (R/G/U/W/B/C with per-color available counts)
- [x] Role filter shows live available-count per role
- [x] Drag-to-swap pick slots after draft completes (reorder top→support)
- [x] Distinct role-icon glyphs (top/jungle/mid/bot/support all unique)
- [x] Visual polish pass: radial-gradient surfaces, rounded-xl panels, backdrop blur, warmer palette, refined PhaseProgress + TurnIndicator pills, amber focus rings
- [ ] Collapsible Enemy Reader card (shell only until Phase 3 fills data)
- [ ] Collapsible Identity Critic card (shell only until Phase 3 fills data)
- [ ] "Simulate opponent" toggle (backend auto-picks for opposing side)
- [ ] Responsive on tablet at minimum (don't need to optimize mobile, just don't break)
- [ ] Deploy to Vercel

**Definition of done:** someone can do a full 20-turn draft in the UI and see recommendations that match what the CLI would output.

---

## Phase 5 — Polish & ship

- [ ] README landing content: lead with theory, not UI
- [ ] Screen recording demo embedded in README
- [ ] Credits & attribution for LS / Rübezahl in color framework section
- [ ] Public backend deploy (Railway or Fly.io)
- [ ] Rate-limiting on the LLM endpoint (to prevent API bill surprises)
- [ ] Basic analytics (just counts: drafts started, recommendations served)
- [ ] Share on LS Community Discord for feedback
- [ ] Write launch LinkedIn post in your established voice

---

## Phase 6+ — Fearless Draft & First Selection (v1.5)

Not starting until v1 is shipped and has been used for at least a week.

- [ ] Series-level state model wrapping DraftState with `unavailable_pool`
- [ ] Fearless Draft mode toggle in UI (BO3 / BO5 selector, game-N indicator)
- [ ] Score adjustments for Fearless: Identity Critic prompt gets series context
- [ ] First Selection pre-draft advisor: side vs pick-order tradeoff given enemy scouting

---

## Known debt / decisions deferred

Things to revisit but not block on:

- **Archetype classification** — currently derived implicitly from colors + tags. Revisit if Identity Critic output feels too diffuse in practice.
- **Champion-to-champion counter edges** — currently tag-only (cleaner, scales). Revisit if tag-matching produces obviously wrong rankings.
- **Smolder color reconsideration** — B/U tagged by owner; could reconsider as G/U given stacking fantasy. Non-blocking.
- **Patch data overlay (opt-in)** — deliberately out of scope for v1. If someone asks "but champion X is gutted," the answer is "your pick is theoretically sound; meta tiers flag this via Survivability." Revisit only if this feels insufficient after real use.

---

## Scratchpad / notes

Use this section for in-flight thoughts that don't yet have a home. Clear out periodically.

- Added a synthetic `ranged_ad_source` structural hole so comps with only melee physical damage (e.g. Yone + AP/wombo shell) stop over-prioritizing extra AP engage/teamfight picks.
- Added early-draft confidence scaling for denial/counter logic plus a small opener-suitability modifier so thin enemy information no longer over-promotes setup-reliant anchors like Yasuo.
- Audited fringe role tags and removed clearly polluting bot assignments from `kennen`, `yasuo`, and `sylas` so role logic reflects real draft shapes more closely.
- Added light `bot` / `support` anchor authenticity checks so the engine prefers real structural anchors over fringe slotting while still allowing legitimate APC/support mage patterns.
- Trimmed clearly fake support assignments from `kennen`, `evelynn`, and `briar` to reduce role-pool noise at the data layer instead of stacking more scoring heuristics.
- Diversified recommendations now behave more like five distinct draft branches: one true top pick plus structural, support/flex, denial, and identity lines, each with explicit rationale prefixes so the UI reads like coaching rather than five near-duplicates.
- Best-denial selection now uses enemy-read confidence and a total-score sanity gate, so thin-information states stop surfacing fake-genius denial picks that LS would reject as premature commitments.
- Added a narrow/conditional-pick modifier so assassins, hard counter-junglers, and other exploit picks need actual draft justification before surfacing as generic recommendations; this also lets real blue/control mids win more of the fair tie-breaks in declared control shells.
- Added mid-anchor authenticity for declared blue/control shells and corrected Twisted Fate's structural damage profile from `ad` to `ap`, reducing fake AD-hole fills while surfacing real control/global mids more naturally when the shell wants them.
- Audited structural damage profiles and corrected several clear magic-damage misclassifications (`gragas`, `mordekaiser`, `rumble`, `teemo`, `vladimir`, `gwen`, `lillia`) plus `corki` to `mixed`; reverted `zaahen` back to `ad` to match the owner's intended design. These tags matter because wrong `ad`/`mixed` values pollute structural AD-source logic rather than just display.
- Reclassified `ksante`, `skarner`, and `zac` from `ad` to `tank` at the structural layer so they stop masquerading as real physical-damage source solutions. This is a draft-logic fix, not a commentary-on-builds fix.
- Added an enchanter-unlock path for Olaf: his data now explicitly links to `yuumi`, `lulu`, and `soraka`, and his color identity was re-centered from mono-red toward `W/G` core with `R` as the conditional aggression thread. The engine also applies a small data-driven bonus for explicit enchanter-unlocked melee AD carry lines so Olaf can surface as a real later carry branch instead of reading like generic mono-red lane bully forever.
- Reframed Ambessa from narrow mono-red diver into a `W/G` core fighter with `R` off-thread, plus more honest `waveclear`, `scaling`, and `win_condition_tags`. This made her behave like a real standard top/fighter branch instead of vanishing in generic drafts.
- Reframed Kayle away from fake `W/R` support-adjacent tagging into a true independent scaling carry: `U` core, `top/mid` only, `mixed` damage, stronger waveclear, and added split-push/teamfight threads plus explicit enchanter synergy. Narrowing her back to blue also stopped her from over-inheriting every white/green scaling shell.
- Reframed Kayn away from `R/B` assassin-bruiser soup into a binary form-flex identity: `B/W/U` core with `G/R` as the form-dependent payoff threads, plus explicit `adaptive_form` handling in the engine so he is taxed less like a narrow assassin and more like a versatile conditional jungler.
- Added a small independent-side-lane branch modifier so true 1-4 / side-pressure picks are rewarded once a real four-man shell exists, but slightly taxed as blind/openers. This keeps Quinn/Fiora/Trynd/Bel'Veth from being dead all the time without turning them into generic first-rotation anchors.
- Began a side-lane cluster data pass: Fiora got a clearer G/W duelist note, Tryndamere gained `R` as an off-thread plus more honest mobility/waveclear/lane-bully modeling, Nasus got a quest-style G/B note, Quinn was reframed toward `R/U` map-pressure identity, Tristana picked up a light `R` off-thread, and Bel'Veth was reframed as `G/B/U` rather than just `B/U`.
- Added a top/jungle anchor cleanup pass: K'Sante now explicitly carries the Gwen counter edge and a truer W/G anchor note; Volibear was reframed toward G/R with mixed damage and real dive/split-push/objective tags; Zac and Skarner were moved toward W/U/G and W/G/U-style control-tank identities with better peel/pick/scaling signals; Renekton was softened from pure early mono-R into a more honest R/G bruiser profile; Dr. Mundo's structural profile was corrected away from fake `ad`/high-peel into mixed damage, low peel, stronger waveclear, and real split-push/objective value.
- Consider adding a "why was this picked" detail view that shows the 4 axis contributions broken down, with a natural-language explanation for each. Would help debug the scoring logic.
- The Enemy Reader might benefit from seeing recent meta trends as side context ("in the current patch, protect-the-carry comps are common"), but that breaks the pure-theory thesis. Leave it out for v1.
