# Data Audit — Recommendation Engine Gaps

Date: 2026-04-19

This note ranks missing or sparse champion fields by how much they currently
hurt deterministic recommendation quality.

## Summary

Current coverage in `data/champions.json`:

- `counter_tags`: 172/172 champions populated
- `kit_tags`: 172/172 champions populated
- `roles`: 172/172 champions populated
- `win_condition_tags`: 0/172 champions populated
- `strong_against_tags`: 2/172 champions populated
- `countered_by`: 1/172 champions populated
- `synergy_with`: 33/172 champions populated
- `weak_with`: 18/172 champions populated

Structural coverage:

- Every champion has exactly 3 populated structural fields:
  - `damage_profile`
  - `range`
  - `frontline`
- Every champion is missing:
  - `engage`
  - `peel`
  - `waveclear`
  - `scaling`

## Highest-Leverage Missing Data

### 1. Structural subfields: `engage`, `peel`, `waveclear`, `scaling`

Impact: highest

Why it matters:

- These fields directly shape `CompositionAnalysis`.
- They determine whether the engine can correctly identify comp holes.
- They strongly affect whether a recommendation understands LS-style ideas
  like inevitability, ability to stall, ability to force, and whether a comp
  can actually play the fights it drafts.

Examples of what is currently hard without these fields:

- protect-the-carry vs dive
- low-engage blue shells
- whether a comp can actually waveclear into a lull state
- whether a pick adds inevitability or only a temporary power spike

### 2. `win_condition_tags`

Impact: high for design quality, currently low for live code

Why it matters:

- The field is entirely empty, so the repo has no explicit draft-level
  articulation of:
  - protect the carry
  - split push
  - wombo
  - poke/siege
  - global pressure
  - skirmish
- Right now `kit_tags` and archetypes carry much of this burden indirectly.
- If Fivefold is meant to speak in LS-style “what is this deck trying to do?”
  terms, this is the cleanest missing semantic layer.

### 3. `synergy_with` / `weak_with`

Impact: medium

Why it matters:

- These influence coherence and pairing fit.
- Sparse coverage means some famous pair logic is present while many other
  obvious same-theme relationships are absent.
- This can make the engine look sharp in a few spots and silent in others.

### 4. `strong_against_tags` / `countered_by`

Impact: medium-low right now

Why it matters:

- The framework is useful, but the data is too sparse to trust as a primary
  engine signal.
- These are best used after structural and win-condition coverage is stronger.

## LS-Aligned Interpretation

Using the stream discussion as a guide:

- `R` is about early forcing, tempo, and volatility.
- `U` is about control, inevitability, and winning by not losing.
- `G` is about harmony, item/power-spike timing, and ally amplification.
- `W` is about versatility and binary role commitment in a draft.
- `B` is about conditions, tradeoffs, and “power if the deck supports it”.

The missing fields that best express those ideas are:

1. structural `scaling`
2. structural `engage`
3. structural `peel`
4. structural `waveclear`
5. `win_condition_tags`

That order reflects how often those concepts matter in real draft states.

## Engine Mitigation Added

As of this audit, the engine now infers missing structural fields from
`kit_tags` and color identity as a fallback. This improves recommendation
quality immediately, but it is still a fallback, not a replacement for
hand-curated data.

Files involved:

- [backend/fivefold/composition.py](/Users/Usama/Desktop/LOOLLL/fivefold/backend/fivefold/composition.py)
- [backend/fivefold/engine.py](/Users/Usama/Desktop/LOOLLL/fivefold/backend/fivefold/engine.py)

## Best Next Tagging Work

If doing manual data improvement, the best order is:

1. Fill structural `scaling` for all champions
2. Fill structural `engage`
3. Fill structural `peel`
4. Fill structural `waveclear`
5. Fill `win_condition_tags`
6. Expand `synergy_with`
7. Expand `weak_with`
8. Expand `strong_against_tags`
9. Expand `countered_by`

This order maximizes recommendation-quality gains per hour of tagging work.
