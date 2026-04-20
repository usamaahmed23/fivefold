# Fivefold Project Memory

This file is a fast-ramp summary for future sessions. It is not the source of
truth over `AGENTS.md`, `TASKS.md`, or `docs/DESIGN.md`; it is the shortest
useful path back into the repo.

## What Fivefold Is

Fivefold is a League of Legends draft tool built around LS / MTG-style color
identity theory.

Core thesis:
- A draft is a coherent win condition built adversarially across alternating
  picks and bans.
- Deterministic scoring is the product.
- The LLM layer is narration, not decision-making.
- Meta should not drive identity or denial; it only belongs in survivability
  and close-call tiebreaking.

## Current Product State

As of 2026-04-20, Fivefold is already a usable deterministic draft product:

- Backend deterministic engine exists and is heavily tested.
- FastAPI wrapper exists.
- Next.js frontend exists and is being used as the primary UI.
- Recommendation flow is compact and interactive:
  - 10 icon-first recommendations
  - one expanded detail pane
  - explicit `Pick` / `Ban`
  - automatic refresh as the draft changes
- LLM pipeline is still not implemented yet.

Practical summary:
- The MVP is no longer just a scaffold; it is a working draft recommender.
- The largest missing product feature is still Phase 3 narrative generation.
- The highest-leverage improvements now are engine/data fidelity, not basic app scaffolding.

## Key Files

- [AGENTS.md](/Users/Usama/Desktop/LOOLLL/fivefold/AGENTS.md): repo-specific operating rules.
- [TASKS.md](/Users/Usama/Desktop/LOOLLL/fivefold/TASKS.md): project tracker.
- [docs/DESIGN.md](/Users/Usama/Desktop/LOOLLL/fivefold/docs/DESIGN.md): full product/design rationale.
- [data/champions.json](/Users/Usama/Desktop/LOOLLL/fivefold/data/champions.json): champion corpus.
- [data/meta_tiers.json](/Users/Usama/Desktop/LOOLLL/fivefold/data/meta_tiers.json): meta tier input for survivability.

## Backend Mental Model

Main package: [backend/fivefold](/Users/Usama/Desktop/LOOLLL/fivefold/backend/fivefold)

Important flow:
- [models.py](/Users/Usama/Desktop/LOOLLL/fivefold/backend/fivefold/models.py)
  defines `Champion`, `DraftState`, `CandidateScore`, `MetaTiers`.
- [loader.py](/Users/Usama/Desktop/LOOLLL/fivefold/backend/fivefold/loader.py)
  reads champion + meta JSON.
- [contextual.py](/Users/Usama/Desktop/LOOLLL/fivefold/backend/fivefold/contextual.py)
  re-resolves contextual champion colors based on ally/enemy picks.
- [composition.py](/Users/Usama/Desktop/LOOLLL/fivefold/backend/fivefold/composition.py)
  derives declared colors, primary colors, structural averages, and holes.
- [engine.py](/Users/Usama/Desktop/LOOLLL/fivefold/backend/fivefold/engine.py)
  computes identity, denial, structural, survivability, then totals/ranks.
- [api.py](/Users/Usama/Desktop/LOOLLL/fivefold/backend/fivefold/api.py)
  exposes `/api/champions`, `/api/draft/score`, `/api/draft/analyze`, `/api/health`.

Important scoring rules to remember:
- Identity is based on current allied color mass.
- Off-colors are weighted, not equal to main colors.
- Colorless is treated specially as a comp-definer.
- Denial combines a color-counter matrix with enemy `counter_tags`.
- Structural is mostly hole-coverage based on current `structural_tags`.
- Survivability is mostly neutral until `meta_tiers.json` is populated.

## Frontend Mental Model

Frontend root: [frontend](/Users/Usama/Desktop/LOOLLL/fivefold/frontend)

Important flow:
- [app/page.tsx](/Users/Usama/Desktop/LOOLLL/fivefold/frontend/app/page.tsx)
  is the orchestration layer.
- [lib/draftState.ts](/Users/Usama/Desktop/LOOLLL/fivefold/frontend/lib/draftState.ts)
  creates and advances local draft state.
- [lib/turnOrder.ts](/Users/Usama/Desktop/LOOLLL/fivefold/frontend/lib/turnOrder.ts)
  encodes the 2026 draft turn order.
- [lib/api.ts](/Users/Usama/Desktop/LOOLLL/fivefold/frontend/lib/api.ts)
  calls the backend.
- [components/ChampionGrid.tsx](/Users/Usama/Desktop/LOOLLL/fivefold/frontend/components/ChampionGrid.tsx)
  handles search/filter/pick entry.
- [components/RecommendationPanel.tsx](/Users/Usama/Desktop/LOOLLL/fivefold/frontend/components/RecommendationPanel.tsx)
  renders top recommendations from `/api/draft/analyze`.

Useful UX notes:
- Draft history is stored in localStorage.
- Recommendations refresh automatically as draft state changes.
- The UI now favors compact option browsing over tall card stacks.
- Champion portraits are fetched from Riot Data Dragon on the client.

## Data Reality

Current data shape is richer and messier than the original Phase 0 docs.

Observed facts:
- `data/champions.json` is a top-level object with metadata plus a
  `champions` array.
- The file currently contains 172 champions, not 167.
- Many champions have `roles`, `counter_tags`, partial `structural_tags`, and
  `kit_tags`.
- `data/archetypes.json` exists and appears intended for higher-level comp
  reasoning, but it is not wired into the engine yet.
- `data/meta_tiers.json` exists, but all role lists are currently empty.

Important implication:
- The scoring engine is operational, but some axes are still lower-signal than
  the design intends because the supporting data is incomplete.

## Drift / Gotchas

These are the main repo-shape issues worth remembering before editing:

- Some docs historically described the project as if backend/frontend were not built; README has now been updated, but older notes may still lag behind.
- `TASKS.md` is directionally useful, but not fully synced with actual repo state.
- [scripts/tag.py](/Users/Usama/Desktop/LOOLLL/fivefold/scripts/tag.py)
  points at `champions_complete.json`, which does not appear to be the current
  live data path.
- [scripts/add_roles.py](/Users/Usama/Desktop/LOOLLL/fivefold/scripts/add_roles.py)
  and [scripts/add_counter_tags.py](/Users/Usama/Desktop/LOOLLL/fivefold/scripts/add_counter_tags.py)
  assume an older `champions.json` structure.
- If doing data work, verify the real schema before trusting older scripts.

## Verification Notes

Recent verified state:
- Backend tests are active and were passing in the latest tuning pass.
- Frontend typecheck has been used as the main lightweight verification pass.
- Dev servers have been run locally with frontend on `:3000` and backend on `:8000`.

## Good Next Moves

If picking work back up, the highest-leverage next steps are:

1. Run the app end-to-end and verify draft flow against the backend.
2. Decide whether the next milestone is:
   - frontend polish,
   - Phase 3 LLM pipeline,
   - or data quality completion.
3. If focusing on scoring quality, prioritize:
   - filling `meta_tiers.json`,
   - auditing `structural_tags`,
   - and reconciling stale data scripts with the live schema.
