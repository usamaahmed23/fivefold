# Fivefold

Fivefold is a League of Legends draft tool built around **LS's MTG color philosophy** instead of patch winrates or comfort-pick heuristics.

Most draft tools collapse the problem into champion strength lists. Fivefold treats a draft as a **coherent win condition built adversarially across alternating picks and bans**. A recommendation is judged on:

- `Identity`: does this reinforce our color identity?
- `Denial`: does this disrupt what the enemy is building?
- `Structural`: does this fill real composition holes?
- `Survivability`: can this actually execute in the current meta/lane context?

The deterministic engine is the product. Any LLM layer is narration, not decision-making.

## What It Does Now

The current app is already a usable deterministic drafting product:

- live draft board for 2026 draft order
- blue/red picks and bans with enforced turn flow
- 10 compact recommendations instead of 5 oversized cards
- click a recommendation to inspect the rationale, then `Pick` / `Ban`
- automatic recommendation refresh as the draft changes
- diversified recommendation branches like:
  - best overall
  - structural fill
  - support branch
  - flex branch
  - denial line
- role authenticity guards so fake bot/support picks pollute recommendations less
- LS-style structural logic for:
  - early anchor quality
  - ranged AD coverage
  - flex value
  - side-lane branches
  - support-enabler unlocks

## Core Idea

Champions are modeled as **color-identity primitives**, not stat rows.

| Code | Meaning in League |
|---|---|
| `R` | aggression, snowball, forced early concessions |
| `G` | harmony, item spikes, curved power growth |
| `U` | control, denial, deception, inaction as action |
| `W` | versatility, supportiveness, binary "Choose One" play |
| `B` | power at a cost, quests, conditions, warped incentives |
| `C` | dedicated theme that warps the entire draft |

Each champion has:

- `colors_main`: core identity
- `colors_off`: conditional or build-dependent threads
- `roles`
- `win_condition_tags`
- `structural_tags`
- `counter_tags`
- optional contextual rules and champion-specific synergy/counter edges

## Current Product State

What is already real in this repo:

- backend deterministic scoring engine
- FastAPI API
- Next.js frontend
- recommendation UI with compact selector + detail pane
- champion dataset with extensive hand-tuned fields
- automated backend test coverage

What is not shipped yet:

- 3-stage LLM narrative pipeline
- fully populated meta tiers
- deploy/docs polish

## Repo Layout

```text
fivefold/
├── backend/
│   ├── fivefold/
│   │   ├── api.py
│   │   ├── composition.py
│   │   ├── contextual.py
│   │   ├── engine.py
│   │   ├── loader.py
│   │   ├── models.py
│   │   └── win_conditions.py
│   └── tests/
├── data/
│   ├── champions.json
│   ├── archetypes.json
│   └── meta_tiers.json
├── docs/
│   ├── DESIGN.md
│   └── DATA_AUDIT.md
├── frontend/
└── scripts/
```

## Running Locally

### Backend

```bash
cd backend
.venv/bin/pytest -q
.venv/bin/uvicorn fivefold.api:app --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).

## API

Main endpoints:

- `GET /api/health`
- `GET /api/champions`
- `POST /api/draft/score`
- `POST /api/draft/analyze`

`/api/draft/score` is LLM-free and fast.

## Data Notes

Champion color identity is based on the **LS / Rübezahl MTG color spreadsheet** plus owner-authored additions for newer champions and follow-up tuning passes.

This repo intentionally prefers:

- theory-consistent structure over patch-winrate shortcuts
- deterministic rules over opaque recommendation mush
- explicit champion modeling over hidden learned weights

## Philosophy Constraints

Some rules Fivefold tries hard not to violate:

- meta tiers must not drive `identity` or `denial`
- main colors matter more than off-colors
- contextual/colorless champs should warp the draft, not act like normal fillers
- narrow exploit picks should not appear as generic blind recommendations
- stable early anchors matter more than fake-genius thin-info counters

## Attribution

Color-identity theory and the underlying framework are inspired by **LS** and the LS community spreadsheet work around MTG colors in League.

Fivefold is an independent fan project and is not endorsed by Riot Games.
