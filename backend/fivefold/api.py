"""FastAPI wrapper around the scoring engine.

Three routes:
    GET  /api/champions          — all champion data
    POST /api/draft/score        — deterministic scores, LLM-free (hover-fast)
    POST /api/draft/analyze      — scores + LLM narrative (placeholder in Phase 2)

Data is loaded once at startup and held in app.state.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import engine, loader
from .models import CandidateScore, Champion, DraftState, MetaTiers

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class ScoreRequest(BaseModel):
    state: DraftState
    candidate_ids: Optional[list[str]] = Field(
        default=None,
        description="If omitted, every non-banned / non-picked champion is scored.",
    )
    top_n: Optional[int] = Field(
        default=None,
        description="When ranking all eligible candidates, trim to this many. Ignored if candidate_ids is set.",
    )


class ScoreResponse(BaseModel):
    scores: list[CandidateScore]


class AnalyzeRequest(BaseModel):
    state: DraftState
    top_n: int = 5


class AnalyzeResponse(BaseModel):
    mode: Literal["deterministic", "llm"] = "deterministic"
    scores: list[CandidateScore]
    # Phase 3 will populate these; for now they're nullable placeholders so
    # the frontend can depend on a stable shape across phases.
    enemy_reader: Optional[dict] = None
    identity_critic: Optional[dict] = None
    coach: Optional[str] = None


class ChampionsResponse(BaseModel):
    count: int
    champions: list[Champion]


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def _default_origins() -> list[str]:
    raw = os.environ.get("FIVEFOLD_CORS_ORIGINS")
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    # Next.js dev defaults.
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


@asynccontextmanager
async def _lifespan(app: FastAPI):
    app.state.champions = loader.load_champions()
    app.state.meta_tiers = loader.load_meta_tiers()
    app.state.archetypes = loader.load_archetypes()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fivefold API",
        version="0.1.0",
        description="LoL draft scoring engine over LS color-identity theory.",
        lifespan=_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_default_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    @app.get("/api/health")
    def health():
        return {"status": "ok", "champions_loaded": len(app.state.champions)}

    @app.get("/api/champions", response_model=ChampionsResponse)
    def list_champions(request: Request):
        champs: dict[str, Champion] = request.app.state.champions
        return ChampionsResponse(count=len(champs), champions=list(champs.values()))

    @app.post("/api/draft/score", response_model=ScoreResponse)
    def score(req: ScoreRequest, request: Request):
        champs: dict[str, Champion] = request.app.state.champions
        meta: MetaTiers = request.app.state.meta_tiers
        archs = request.app.state.archetypes

        if req.candidate_ids is not None:
            unknown = [cid for cid in req.candidate_ids if cid not in champs]
            if unknown:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown champion ids: {unknown}",
                )
            scores = [
                engine.score_candidate(cid, req.state, champs, meta, archs)
                for cid in req.candidate_ids
            ]
            return ScoreResponse(scores=scores)

        eligible = engine.eligible_candidates(req.state, champs)
        ranked = engine.rank_candidates(
            eligible, req.state, champs, meta, top_n=req.top_n, archetypes=archs
        )
        return ScoreResponse(scores=ranked)

    @app.post("/api/draft/analyze", response_model=AnalyzeResponse)
    def analyze(req: AnalyzeRequest, request: Request):
        champs: dict[str, Champion] = request.app.state.champions
        meta: MetaTiers = request.app.state.meta_tiers
        archs = request.app.state.archetypes

        eligible = engine.eligible_candidates(req.state, champs)
        ranked = engine.rank_candidates(
            eligible, req.state, champs, meta, top_n=req.top_n, archetypes=archs
        )
        # Phase 3 will fill in enemy_reader / identity_critic / coach by
        # calling the LLM pipeline. For now: deterministic mode only.
        return AnalyzeResponse(mode="deterministic", scores=ranked)

    return app


app = create_app()
