# Changelog

All notable changes to Fivefold. Most recent on top.

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
