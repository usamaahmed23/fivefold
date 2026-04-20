"use client";

import { useEffect, useMemo, useState } from "react";
import type { AnalyzeResponse, Champion, Side } from "@/lib/types";
import { ChampionPortrait } from "./ChampionPortrait";
import { RecommendationCard } from "./RecommendationCard";

interface Props {
  result: AnalyzeResponse | null;
  loading: boolean;
  error: string | null;
  champions: Map<string, Champion>;
  portraits: Map<string, string>;
  onSuggest?: () => void;
  onSelect?: (id: string) => void;
  actionLabel?: string;
  disabled: boolean;
  side?: Side;
}

export function RecommendationPanel({
  result,
  loading,
  error,
  champions,
  portraits,
  onSuggest,
  onSelect,
  actionLabel,
  disabled,
  side,
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const sideBadgeClass =
    side === "blue"
      ? "bg-blue-600 text-white"
      : side === "red"
        ? "bg-red-600 text-white"
        : "bg-surface-2 text-muted";

  useEffect(() => {
    setSelectedId(result?.scores[0]?.champion_id ?? null);
  }, [result]);

  const selectedScore = useMemo(
    () =>
      result?.scores.find((score) => score.champion_id === selectedId) ??
      result?.scores[0] ??
      null,
    [result, selectedId],
  );
  return (
    <div className="flex min-h-[600px] flex-col rounded-xl border border-border bg-surface/80 p-4 shadow-sm backdrop-blur-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-bold uppercase tracking-widest text-fg">
            Recommendation
          </h2>
          {side && actionLabel && (
            <span
              className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${sideBadgeClass}`}
            >
              {side} · {actionLabel}
            </span>
          )}
        </div>
        {onSuggest && (
          <button
            type="button"
            onClick={onSuggest}
            disabled={disabled || loading}
            className="rounded border border-border bg-surface px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted transition hover:border-muted/70 hover:text-fg disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        )}
      </div>
      {!loading && !result && !error && (
        <p className="mb-3 text-[11px] text-faint">
          Recommendations update automatically as the draft changes.
        </p>
      )}

      {error && (
        <p className="rounded border border-rose-300 bg-rose-50 p-2 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-200">
          {error}
        </p>
      )}

      {!result && !loading && !error && (
        <div className="rounded-lg border border-dashed border-border/60 bg-surface-2/30 p-4 text-sm text-faint">
          <p>
            Recommendations will populate here automatically with 10 distinct draft lines —{" "}
            <span className="text-amber-500">top picks</span>,{" "}
            <span className="text-teal-500">structural fill</span>,{" "}
            <span className="text-sky-500">support branch</span> /{" "}
            <span className="text-lime-500">flex branch</span>,{" "}
            <span className="text-rose-500">best denial</span>, and other{" "}
            <span className="text-violet-500">identity-fit</span> alternatives
            depending on the shell.
          </p>
        </div>
      )}

      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="animate-pulse rounded-lg border border-border/70 bg-surface-2/30 p-3"
            >
              <div className="mb-3 flex items-center gap-3">
                <div className="h-14 w-14 rounded bg-surface-2" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-20 rounded bg-surface-2" />
                  <div className="h-5 w-36 rounded bg-surface-2" />
                  <div className="h-3 w-28 rounded bg-surface-2" />
                </div>
                <div className="h-8 w-14 rounded bg-surface-2" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="h-8 rounded bg-surface-2" />
                <div className="h-8 rounded bg-surface-2" />
                <div className="h-8 rounded bg-surface-2" />
                <div className="h-8 rounded bg-surface-2" />
              </div>
            </div>
          ))}
        </div>
      )}

      {result && (
        <div className="flex-1 space-y-3 overflow-y-auto pr-1">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded border border-border/60 bg-surface-2/30 px-2.5 py-1.5 text-[11px] text-faint">
            <span>
              Showing <span className="font-semibold text-fg">{result.scores.length}</span> distinct draft lines.
            </span>
            {onSelect && (
              <span>
                Click any option to inspect it, then use the {actionLabel?.toLowerCase() ?? "action"} button below.
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
            {result.scores.map((s, i) => {
              const champion = champions.get(s.champion_id);
              const selected = s.champion_id === selectedScore?.champion_id;
              const role = s.recommendation_role ?? (i === 0 ? "best_overall" : null);
              const roleTone =
                role === "best_overall"
                  ? "text-amber-500"
                  : role === "structural_fill"
                    ? "text-teal-500"
                    : role === "support_enabler"
                      ? "text-sky-500"
                      : role === "flex_branch"
                        ? "text-lime-500"
                        : role === "best_denial"
                          ? "text-rose-500"
                          : role === "identity_anchor"
                            ? "text-violet-500"
                            : "text-faint";
              return (
                <button
                  key={s.champion_id}
                  type="button"
                  onClick={() => setSelectedId(s.champion_id)}
                  className={`rounded-lg border p-2 text-left transition ${
                    selected
                      ? "border-amber-400/70 bg-surface-2 ring-1 ring-amber-400/40"
                      : "border-border bg-surface hover:border-muted hover:bg-surface-2"
                  }`}
                >
                  <div className="flex items-start justify-between gap-1">
                    <div className="overflow-hidden rounded ring-1 ring-border">
                      <ChampionPortrait
                        url={portraits.get(s.champion_id) ?? null}
                        name={champion?.name ?? s.champion_id}
                        size={42}
                        className="h-[42px] w-[42px] object-cover"
                      />
                    </div>
                    <span className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-fg">
                      {s.total.toFixed(2)}
                    </span>
                  </div>
                  <div className="mt-2">
                    <p className="truncate text-[11px] font-semibold text-fg">
                      {champion?.name ?? s.champion_id}
                    </p>
                    <p className={`truncate text-[9px] font-semibold uppercase tracking-widest ${roleTone}`}>
                      {role ? role.replaceAll("_", " ") : `alt ${i}`}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
          {selectedScore && (
            <RecommendationCard
              score={selectedScore}
              champion={champions.get(selectedScore.champion_id)}
              portrait={portraits.get(selectedScore.champion_id) ?? null}
              rank={
                result.scores.findIndex((score) => score.champion_id === selectedScore.champion_id) + 1
              }
              onSelect={onSelect}
              actionLabel={actionLabel}
            />
          )}
          {result.mode === "deterministic" && (
            <p className="pt-1 text-[11px] text-faint">
              Mode: deterministic engine. LLM narration lands in Phase 3.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
