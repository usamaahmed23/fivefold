"""FastAPI smoke tests.

Covers the three public endpoints with a fresh TestClient per test so lifespan
hooks re-run and app.state is populated.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from fivefold.api import create_app


@pytest.fixture
def client():
    # TestClient as a context manager triggers the lifespan hook so
    # app.state.champions / meta_tiers get populated.
    with TestClient(create_app()) as c:
        yield c


def _base_state(**overrides):
    state = {
        "phase": "pick1",
        "turn_index": 0,
        "blue_bans": [],
        "red_bans": [],
        "blue_picks": [],
        "red_picks": [],
        "side_to_act": "blue",
        "action_to_take": "pick",
        "first_pick_side": "blue",
    }
    state.update(overrides)
    return state


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["champions_loaded"] > 150


def test_list_champions(client):
    r = client.get("/api/champions")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == len(body["champions"])
    assert body["count"] > 150
    sample = body["champions"][0]
    # Sanity: full champion shape is serialized.
    for key in ("id", "name", "colors_main", "colors_off", "roles"):
        assert key in sample


def test_score_with_explicit_candidates(client):
    r = client.post(
        "/api/draft/score",
        json={
            "state": _base_state(blue_picks=["jax", "karma"]),
            "candidate_ids": ["lulu", "zed"],
        },
    )
    assert r.status_code == 200
    scores = r.json()["scores"]
    assert len(scores) == 2
    ids = [s["champion_id"] for s in scores]
    assert ids == ["lulu", "zed"]  # explicit order preserved


def test_score_unknown_candidate_is_400(client):
    r = client.post(
        "/api/draft/score",
        json={
            "state": _base_state(),
            "candidate_ids": ["not_a_real_champion"],
        },
    )
    assert r.status_code == 400


def test_score_without_candidate_ids_ranks_all_eligible(client):
    r = client.post(
        "/api/draft/score",
        json={
            "state": _base_state(
                blue_picks=["jax"],
                red_picks=["aatrox"],
                red_bans=["zed"],
            ),
            "top_n": 5,
        },
    )
    assert r.status_code == 200
    scores = r.json()["scores"]
    assert len(scores) == 5
    ids = [s["champion_id"] for s in scores]
    # Already-placed or banned champions must be filtered out.
    assert "jax" not in ids
    assert "aatrox" not in ids
    assert "zed" not in ids
    # Descending total.
    totals = [s["total"] for s in scores]
    assert totals == sorted(totals, reverse=True)


def test_analyze_returns_deterministic_placeholder(client):
    r = client.post(
        "/api/draft/analyze",
        json={"state": _base_state(blue_picks=["karma"]), "top_n": 3},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "deterministic"
    assert len(body["scores"]) == 3
    # LLM fields are null placeholders until Phase 3.
    assert body["enemy_reader"] is None
    assert body["identity_critic"] is None
    assert body["coach"] is None


def test_cors_preflight(client):
    r = client.options(
        "/api/champions",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
