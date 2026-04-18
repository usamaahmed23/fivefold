# Fivefold

> A League of Legends drafting tool grounded in color-identity theory, not patch winrates.

Most drafting tools optimize for the wrong signal. They recommend picks based on patch winrate, player comfort, and pairwise synergy heuristics. This collapses a draft into a bag of individually-optimized champions.

A draft is not a bag. It is a **coherent win condition built adversarially across ten alternating decisions**. Each team is simultaneously building a composition with a clear win condition, disrupting the opponent's emerging win condition, and covering its own structural holes.

Fivefold operationalizes this by treating champions as **color-identity primitives** — based on LS's MTG-colors framing — rather than as winrate rows. A pick is scored on four axes: does it reinforce our identity, disrupt theirs, fill our structural gaps, and survive the lane? The resulting recommendation comes with a coaching-style rationale in color-theory terms, not stat terms.

---

## Color framework

Based on LS / Rübezahl's MTG Color Spreadsheet (LS Community Discord). Color identity reflects what a champion fundamentally *wants to do*, independent of patch.

| | Red | Green | Blue | White | Black | Colorless |
|--|-----|-------|------|-------|-------|-----------|
| **Theme** | Aggression | Synergy | Control | Versatility | Power at a cost | Warps draft |
| **Feel** | Snowball, tempo | Item timings, attrition | Denial, scaling | "Choose One" | Conditions, sacrifice | Dedicated theme |

Champions can be multi-color. Gangplank is Green/Blue (off White). Aatrox is Red/Black. Some champions have **contextual** identity that only resolves once allies are picked (Rakan gains Colorless when paired with Xayah).

---

## Architecture

```
Deterministic scoring engine (Python)
    → color identity math + structural analysis over champion data
    → produces 4-axis scores (identity, denial, structural, survivability)

LLM pipeline (3 stages, Claude Sonnet)
    → Enemy Reader: what is the opponent building?
    → Identity Critic: how coherent are we?
    → Coach: final recommendation with rationale

Frontend (Next.js)
    → live draft board
    → recommendation panel with axis visualisation
```

The engine is the product. The LLM is narration. The tool works — with less eloquence — if the LLM is unavailable.

---

## Project status

- [x] Champion color data — 167 champions tagged
- [x] Phase 0 tagging CLI (`scripts/tag.py`)
- [ ] Phase 0 complete — all structural/counter tags filled
- [ ] Phase 1 — Scoring engine
- [ ] Phase 2 — FastAPI backend
- [ ] Phase 3 — LLM pipeline
- [ ] Phase 4 — Next.js frontend
- [ ] Phase 5 — Deploy

---

## Data

Champion color data is sourced from the **LS / Rübezahl MTG Color Spreadsheet** (LS Community Discord). Attribution in `data/champions.json`. Champions released after the spreadsheet was last updated are tagged by the project owner and marked accordingly in the data.

---

## Running the tagging CLI (Phase 0)

```bash
cd scripts

# See what's left to tag
python tag.py --list

# Tag the next untagged champion
python tag.py

# Jump to a specific champion
python tag.py --champion gangplank

# See tag distribution
python tag.py --stats
```

The CLI saves after every champion and auto-backs up before each write.

---

## Dev setup (Phase 1+)

```bash
# Backend
cd backend
pip install fastapi uvicorn anthropic pydantic
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

*This project is not endorsed by Riot Games. League of Legends is a trademark of Riot Games, Inc.*
