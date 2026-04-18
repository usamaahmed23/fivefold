import type {
  AnalyzeResponse,
  ChampionsResponse,
  DraftState,
  ScoreResponse,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_FIVEFOLD_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body || path}`);
  }
  return (await res.json()) as T;
}

export function fetchChampions() {
  return request<ChampionsResponse>("/api/champions");
}

export function scoreCandidates(
  state: DraftState,
  candidate_ids?: string[],
  top_n?: number,
) {
  return request<ScoreResponse>("/api/draft/score", {
    method: "POST",
    body: JSON.stringify({ state, candidate_ids, top_n }),
  });
}

export function analyzeDraft(state: DraftState, top_n = 3) {
  return request<AnalyzeResponse>("/api/draft/analyze", {
    method: "POST",
    body: JSON.stringify({ state, top_n }),
  });
}
