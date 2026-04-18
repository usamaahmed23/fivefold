"""CLI entry point.

Usage:
    python -m fivefold score --state state.json [--candidate aatrox] [--top 5]

If --candidate is omitted, ranks all eligible champions.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import engine, loader
from .models import DraftState


def _cmd_score(args: argparse.Namespace) -> int:
    state = DraftState.model_validate(json.loads(Path(args.state).read_text()))
    champs = loader.load_champions(args.champions)
    meta = loader.load_meta_tiers(args.meta)

    if args.candidate:
        score = engine.score_candidate(args.candidate, state, champs, meta)
        print(json.dumps(score.model_dump(), indent=2))
        return 0

    eligible = engine.eligible_candidates(state, champs)
    scores = engine.rank_candidates(eligible, state, champs, meta, top_n=args.top)
    print(json.dumps([s.model_dump() for s in scores], indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fivefold")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_score = sub.add_parser("score", help="Score candidates against a draft state.")
    p_score.add_argument("--state", required=True, help="Path to DraftState JSON.")
    p_score.add_argument("--candidate", help="Single champion id to score.")
    p_score.add_argument("--top", type=int, default=10, help="Top N when ranking all.")
    p_score.add_argument("--champions", default=None, help="Override champions.json path.")
    p_score.add_argument("--meta", default=None, help="Override meta_tiers.json path.")
    p_score.set_defaults(func=_cmd_score)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
