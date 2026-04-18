# Fivefold — Claude Code Context

This file is the source of truth for Claude Code working on this project.
Read it fully before writing any code.

**For current project state and next tasks, see `TASKS.md`.** That file tracks
what's done, what's next, and why. Update it as work progresses.

---

## What this project is

**Fivefold** is a League of Legends drafting tool grounded in LS's MTG-color
identity theory. The thesis: most drafting tools optimize for the wrong signal
(patch winrates, comfort picks, pairwise synergy). A draft is not a bag of
individually-optimized champions — it is a **coherent win condition built
adversarially across ten alternating decisions**.

The tool demonstrates this theory live: given any draft state, it scores
candidate picks on four axes derived from color-identity theory, and produces
a coaching-style rationale explaining *why* — in color-theory terms, not
winrate terms.

Full design doc: `docs/DESIGN.md`. Read it. This file summarizes the key
decisions; the design doc has the full rationale.

---

## Color framework (LS / MTG)

Six categories. All first-class:

| Code | Name | In League |
|------|------|-----------|
| R | Red | Aggression, early resource forcing, snowball. Volatile, linear. |
| G | Green | Harmony/synergy, curved power spikes, item timings. Bad solo. |
| U | Blue | Control, denial, deception. "Inaction is action." Generally scaling. |
| W | White | Versatile, supportive. Binary in game ("Choose One"). Resists Red. |
| B | Black | Power at a cost. Quests, conditions, sacrifice, tradeoffs. |
| C | Colorless | Dedicated theme. **Draft warps around them.** |

Each champion has:
- `colors_main` — the champion's core identity (X in the source sheet)
- `colors_off` — conditional/build-dependent colors (O in the source sheet)

**This distinction matters for scoring.** Main colors drive identity scoring.
Off colors are only activated when the DraftState confirms the condition.

---

## Data files

### `data/champions.json`

167 champions. Two sources:
- `"source": "ls_sheet"` — 148 champions tagged by LS / Rübezahl. Authoritative
  for color identity. Currently missing: `roles`, `win_condition_tags`,
  `structural_tags`, `counter_tags` (Phase 0 work).
- `"source": "owner"` — 19 recently-released champions tagged by the project
  owner. Have `counter_tags`; still missing `roles`, `win_condition_tags`,
  `structural_tags`.

Champion schema (full):
```json
{
  "id": "gangplank",
  "name": "Gangplank",
  "colors_main": ["G", "U"],
  "colors_off": ["W"],
  "contextual": false,
  "ls_notes": "controls everything, scales/ramps up...",
  "source": "ls_sheet",

  // --- Fivefold additions (Phase 0 — being filled via scripts/tag.py) ---
  "roles": ["top"],
  "win_condition_tags": ["scaling", "global_pressure", "teamfight_zone"],
  "structural_tags": {
    "damage_profile": "mixed",
    "range": "medium",
    "engage": "medium",
    "peel": "low",
    "frontline": "low",
    "waveclear": "high",
    "scaling": "late"
  },
  "counter_tags": ["early_all_in", "hard_cc_on_engage"],

  // --- Contextual champions only ---
  "context_rules": [
    {
      "condition": "ally_has_champion",
      "value": "xayah",
      "effect": "add_main_color",
      "color": "C"
    }
  ]
}
```

### `data/meta_tiers.json`

Does not exist yet — create it. Schema:
```json
{
  "patch": "2026.08",
  "updated_at": "2026-04-16",
  "tiers": {
    "top":     ["aatrox", "jax", "camille"],
    "jungle":  ["vi", "briar", "diana"],
    "mid":     ["ahri", "orianna", "hwei"],
    "bot":     ["kaisa", "jinx", "ezreal"],
    "support": ["nautilus", "thresh", "alistar"]
  }
}
```

Ordered arrays. Index 0 = strongest. Only champions considered genuinely
strong go here. Not every champion needs an entry.

**Critical design rule:** meta tiers are consumed ONLY by the Survivability
score axis and as a tiebreaker. Never by Identity or Denial scoring.
This enforces the thesis: meta strength modulates execution, it does not
drive strategy.

---

## Architecture

```
fivefold/
├── CLAUDE.md              ← you are here
├── docs/
│   └── DESIGN.md          ← full requirements and rationale
├── data/
│   ├── champions.json     ← 167 champions, color-tagged
│   └── meta_tiers.json    ← (to create) ordered S-tier lists per role
├── scripts/
│   └── tag.py             ← Phase 0 interactive tagging CLI
├── backend/               ← (to create) FastAPI app
│   ├── main.py
│   ├── models.py          ← Pydantic schemas
│   ├── engine.py          ← deterministic scoring engine
│   ├── pipeline.py        ← 3-stage LLM pipeline
│   └── prompts/           ← Handlebars-style prompt templates
│       ├── enemy_reader.txt
│       ├── identity_critic.txt
│       └── coach.txt
└── frontend/              ← (to create) Next.js app
    └── ...
```

---

## Build phases

### Phase 0 — Data (current)
- `scripts/tag.py` — interactive CLI to fill missing Fivefold fields
  on all 167 champions. Run with `python scripts/tag.py`.
  Commands: `--list`, `--stats`, `--champion <name>`
- Create `data/meta_tiers.json`

### Phase 1 — Scoring engine (next)
Python module. No web server yet. Pure functions over champion data + DraftState.

Core function signature:
```python
def score_candidate(
    candidate_id: str,
    draft_state: DraftState,
    champions: dict[str, Champion],
    meta_tiers: MetaTiers,
) -> CandidateScore:
    ...
```

Returns:
```python
@dataclass
class CandidateScore:
    champion_id: str
    identity: float      # 0..1 — reinforces our color identity?
    denial: float        # 0..1 — disrupts enemy win condition?
    structural: float    # 0..1 — fills our comp's holes?
    survivability: float # 0..1 — lane matchup + meta tier
    meta_contribution: float  # isolated meta component (for display)
    total: float         # weighted sum, phase-adjusted weights
```

Phase-adjusted weights (approximate starting point, tune via testing):
```python
WEIGHTS_BY_PHASE = {
    "ban1":  {"identity": 0.4, "denial": 0.4, "structural": 0.1, "survivability": 0.1},
    "pick1": {"identity": 0.4, "denial": 0.3, "structural": 0.2, "survivability": 0.1},
    "ban2":  {"identity": 0.3, "denial": 0.4, "structural": 0.2, "survivability": 0.1},
    "pick2": {"identity": 0.2, "denial": 0.2, "structural": 0.4, "survivability": 0.2},
}
```

Tiebreaker: when two candidates' totals are within 0.03 of each other,
break by meta tier position.

**Add snapshot tests in Phase 1.** Hand-craft 3–5 draft states with expected
top-3 candidates and assert against them. These are your regression safety net.

### Phase 2 — API
FastAPI wrapping the engine.

Endpoints:
```
GET  /api/champions           → list of all champion data
POST /api/draft/score         → scoring only, no LLM (for hover previews)
POST /api/draft/analyze       → full analysis including LLM pipeline
```

`/api/draft/score` must be fast and LLM-free — the frontend calls it on
every champion hover in the grid.

### Phase 3 — LLM pipeline
Three sequential calls, each with a Pydantic response model.

**Stage 1 — Enemy Reader**
Input: enemy picks + bans so far
Output:
```json
{
  "declared_colors": ["U", "W"],
  "likely_win_condition": "protect the carry, scale to 3 items",
  "likely_archetype": "protect_the_carry",
  "power_spike": "mid-to-late",
  "structural_holes": ["no early pressure"],
  "confidence": 0.6
}
```

**Stage 2 — Identity Critic**
Input: our picks + top N candidate scores
Output:
```json
{
  "our_declared_identity": "mid-range teamfight",
  "coherence_assessment": "mostly coherent, 3rd pick added split-push threat that doesn't fit",
  "risks": ["win condition unclear", "no reliable engage"],
  "what_we_need_next": ["engage tool", "reinforce primary color"]
}
```

**Stage 3 — Coach**
Input: DraftState + top 3 scored candidates + Enemy Reader + Identity Critic
Output: the human-readable recommendation shown in the UI.

Model: `claude-sonnet-4-20250514`. Use the Anthropic Python SDK.
Fallback: if LLM unavailable, return templated rationale from scores only.

### Phase 4 — Frontend
Next.js + Tailwind. Desktop-first.

Key views:
- Draft board: 5-slot columns per side, 5 ban slots per side, champion grid
- "Suggest for me" → calls `/api/draft/analyze`
- Recommendation panel: top pick with rationale + 2 alternates with axis bars
- Collapsible Enemy Reader card + Identity Critic card

### Phase 5 — Polish
- README leads with the theory, not the UI
- Short screen-recording demo in README
- Attribution to LS / Rübezahl in color framework section

### Phase 6 — Fearless Draft (v1.5)
Series-level state wrapping DraftState. Tracks champion pool across games.
First Selection pre-draft advisor (side vs pick-order tradeoff).

---

## Draft format (Standard 2026)

5 bans per side, 5 picks per side. 10 total bans, 10 total picks.
Blue side picks first when they have first pick (decoupled from side in 2026
via First Selection rule).

Turn order:
```
Phase 1 bans  (6 turns): B R B R B R
Phase 1 picks (4 turns): B | RR | BB | R      (snake)
Phase 2 bans  (4 turns): R B R B
Phase 2 picks (6 turns): R | BB | RR | B      (snake)
```

DraftState model:
```python
class DraftState(BaseModel):
    phase: Literal["ban1", "pick1", "ban2", "pick2", "complete"]
    turn_index: int           # 0..19 absolute turn counter
    blue_bans: list[str]      # champion ids, up to 5
    red_bans: list[str]       # champion ids, up to 5
    blue_picks: list[str]     # champion ids, up to 5
    red_picks: list[str]      # champion ids, up to 5
    side_to_act: Literal["blue", "red"]
    action_to_take: Literal["ban", "pick"]
    first_pick_side: Literal["blue", "red"]  # set before draft starts
```

---

## Key design principles (do not violate)

1. **Deterministic core is the product.** The LLM is narration. The scoring
   engine must produce meaningful output with the LLM completely disabled.

2. **Meta tiers never drive Identity or Denial scores.** Only Survivability
   and tiebreaking. This enforces the thesis.

3. **Main colors drive identity; off colors are conditional.** Don't flatten
   them into a single list.

4. **Colorless champions are comp-definers, not color-fillers.** The Identity
   Critic must reason about them differently.

5. **Contextual champions re-resolve identity each turn.** Rakan with Xayah
   gets Colorless. Rakan without Xayah doesn't. Check `context_rules`.

6. **Each LLM stage has a Pydantic response model.** Validate all LLM output.
   Never trust raw JSON strings from the model.

7. **`/api/draft/score` is LLM-free.** Always. It's called on hover.

---

## Stack

- Backend: Python 3.11+, FastAPI, Pydantic v2, Anthropic Python SDK
- Frontend: Next.js 14+, Tailwind CSS, TypeScript
- Deploy: Vercel (frontend), Railway or Fly.io (backend)
- Data: static JSON files (no database in v1)

---

## Attribution

Champion color data sourced from the LS / Rübezahl MTG Color Spreadsheet
(LS Community Discord). Credit this in the README and in `champions.json`.
Champions not in the original sheet are tagged by the project owner and
marked `"source": "owner"` in the data.
