# Changelog

All notable changes to Fivefold. Most recent on top.

## 2026-04-20 — Productization pass + major scoring cleanup

### Engine
- Added early-anchor quality checks so thin-information states stop surfacing fake-genius setup picks as openers.
- Added real role-authenticity logic for `bot`, `support`, and `mid` anchors.
- Added `ranged_ad_source` and related damage-shape logic so melee AD no longer masquerades as enough physical coverage.
- Added support-enabler logic for explicit unlocked melee carry branches like Olaf + enchanters.
- Added side-lane branch logic so true 1-4 pressure champions can appear once a stable shell exists, without becoming blind first-rotation spam.
- Tightened denial branch selection so `best_denial` stays a real draft option instead of a raw counter-score trap.

### Data
- Audited and corrected many structural damage profiles and role assignments that were distorting scoring.
- Reworked several champion identities to better match LS-style draft function, including Olaf, Ambessa, Kayle, Kayn, Quinn, Bel'Veth, K'Sante, Volibear, Zac, Skarner, Renekton, and Dr. Mundo.
- Filled missing `win_condition_tags` using a conservative inference pipeline, then manually corrected outliers.

### Frontend
- Reworked recommendations from 5 tall cards into a compact 10-option selector with one expanded detail panel.
- Recommendations now refresh automatically as the draft changes.
- Added explicit `Pick` / `Ban` buttons to the selected recommendation.
- Removed unnecessary scroll-jump behavior and improved empty/loading states.

### Docs / Repo hygiene
- README rewritten to reflect the real product instead of the old scaffold phases.
- Added `docs/DATA_AUDIT.md`.
- Ignored stale frontend build artifacts and tsbuildinfo noise in git.

## 2026-04-19 — Structural data complete + engine correctness pass

### Data
- **All 172 champions hand-tagged** for `engage`, `peel`, `waveclear`, `scaling` in `structural_tags`. Engine inference fallback (`composition.infer_structural_level`) now acts as safety net only, not primary source.
- **`win_condition_tags` fully populated** across all 172 champions — final batch of 19 corrections including Trundle (was empty), Vladimir (+teamfight), Mordekaiser (+teamfight), Xayah (lane_bully→scaling/teamfight), Rumble (+wombo), Varus (→pick/teamfight), Tristana (+split_push), Reksai/Sylas (+pick), Lillia (+roam/wombo), and more.

### Engine (Codex pass, then Claude follow-up)
- **Identity axis cleaned up** — synergy/pair bonuses removed from `score_identity`. Identity is now purely color-coherence. Pair/archetype fit lives in new `_coherence_modifier()` (±0.12 shading on final total).
- **`diversify` flag on `rank_candidates`** — `/api/draft/score` uses `diversify=False` (strict total-descending). `/api/draft/analyze` uses `diversify=True` (categorized slots). Restores endpoint contract that had been broken.
- **Bans: survivability fixed to 0.5** — meta execution axis is meaningless for bans. Meta still contributes via `meta_contribution` tiebreaker.
- **Structural curve softened** — `0.40 + 0.45 * coverage` (was `0.25 + 0.75 * coverage`). Less spiky while data is still partially populated.
- **Scaling added to hole detection** — `scaling` now tracked in `composition.structural_avg` and included in `comp.holes`. Early-scaling-heavy comps flag it as a hole, rewarding late-scalers.
- **AP saturation + damage diversity penalties share a cap** — `max(solo_magic_penalty, diversity_penalty)` instead of additive stack. Both penalise AP overlap; taking the max avoids redundant stacking.
- **Synergy/weak pair deduplication** — set-based dedup so mutual listings (Xayah↔Rakan both listing each other) count as one pair, not two.
- **`rank_candidates` pad label fixed** — fallback padding now labelled `"alt"` instead of re-using `"best_overall"`.
- **`score_survivability` deduplication** — now delegates to `_meta_contribution()` (no logic duplication).
- **Structural fallback inference added** (Codex) — `composition.infer_structural_level` provides kit_tag + color-based fallbacks for sparse fields.
- 53 passing tests (up from 35).

### Frontend
- `RecommendationRole` union type extended with `"alt"` for padded recommendation slots.

## 2026-04-18 — Scoring engine modifiers

### Added
- **Phase-fit modifier** — R-heavy picks penalized in pick1/ban1 (telegraphing aggression face-up), boosted in pick2. Mono-R gets -0.10 in pick1; pick2 closers get +0.04.
- **Red side flex bonus** — Flex champions (2+ roles) get a pick1 bonus on red side for counter-pick ambiguity (2 roles → +0.03, 3 → +0.05, 4+ → +0.08). Pick2 only; not in bans.
- **B-constraint modifier** — B-primary picks in pick1 get a structural penalty when no R is present: -0.05 if B leads, -0.02 if B is secondary. Banning Karthus is still fine; picking him early is costly.
- **AP-saturation constraint** (`requires_solo_magic` kit_tag) — Karthus's structural score drops -0.20 per AP ally (capped -0.40). Karthus tagged with `requires_solo_magic`.
- **9 new regression tests** (35 total) covering all four new modifiers.

## 2026-04-18 — Ban scoring overhaul + GitHub

### Added
- **Ban perspective flip** — `score_candidate` now evaluates bans from the enemy's point of view: `identity` measures how much the candidate reinforces *enemy* colors, `structural` measures how much it fills *enemy* holes, `denial` measures the candidate's threat to *us*, and archetype synergy/counter bonuses flip sides accordingly. Previously bans were scored as if we were picking for ourselves, producing nonsensical suggestions.
- **Ban role-saturation filter** — `eligible_candidates` now filters bans by the *enemy's* unfilled roles. A single-role champion whose role is already locked on the enemy side (e.g. Kai'Sa when both bots are picked, Aatrox when both tops are locked) is no longer eligible as a ban suggestion.
- **4 new regression tests** for ban eligibility and ban perspective scoring (26 total).
- **Public GitHub repo** at https://github.com/usamaahmed23/fivefold.

## 2026-04-18 — Frontend QoL polish

### Added
- **Color filter** in champion grid (R/G/U/W/B/C) with per-color available counts. Matches either `colors_main` or `colors_off`.
- **Role filter counts** — each role button shows a live count of still-available champions for that role.
- **Drag-to-swap pick slots** after the draft completes, so teams can be reordered top→support for visual clarity (`lib/draftState.ts::swapPicks`).
- **Suggested-pick highlight** — top-3 candidates from `/analyze` now glow amber in the champion grid.
- **Side/action badge** on the Recommendation panel (`BLUE · Pick` / `RED · Ban`) to make intent unambiguous.
- **Rationale bullets** under axis bars on each `RecommendationCard`.
- **Role-icon placeholders** in empty pick slots (icon + lane label).

### Changed
- Role icons rewritten — five distinct stroke glyphs (crossed swords / tree / wand / crosshair / eye). Previously top and bot shared the same shape.
- Filter row split into two rows (search on top; role + color filters below) so counts are legible and nothing overlaps.
- Champion grid panel height bumped 460 → 500 px to accommodate the second filter row.
- Recommendation panel empty state redesigned as a dashed-border card with keyboard hint and inline axis callouts.
- Visual polish across surfaces: radial-gradient backgrounds (`globals.css`), rounded-xl panels with backdrop blur, softer SideBanner gradients, refined PhaseProgress pills with active-ring + pulse dot, TurnIndicator as a self-contained pill card, amber focus ring on search.
- Inter font wired in via `next/font/google`.
- Buttons in the header unified via a shared `btnBase` utility class.

### Removed
- `components/DraftSummary.tsx` — color-identity breakdown on draft completion (removed on user request).
- `components/TeamColorSummary.tsx` — color pills beneath support tiles; broke column alignment as soon as the first pick was made.
- "Draft complete · drag champion portraits to reorder within a team" banner — appeared abruptly and disrupted layout.

### Fixed
- Role-filtering in candidate eligibility: greedy, flexibility-ordered pass in `_unfilled_roles`. Single-role champs claim their lane first, flex champs fill remaining lanes. Prevents support-only champs (Rakan) being suggested after a support was already picked (Braum).
- Archetype enrichment: ID normalization with underscore/no-underscore fallback; unresolved archetype members now resolved via `id_by_norm` mapping before writing `archetypes.json`.
- Stray `"true"` tag on Fiora removed from kit_tags vocabulary.

## Earlier

See git history and `docs/DESIGN.md` for pre-2026-04-18 development (Phases 0–4 initial build: color data import, tagging CLI, scoring engine, FastAPI, Next.js MVP).
