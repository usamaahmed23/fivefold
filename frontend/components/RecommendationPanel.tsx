"use client";

import type { AnalyzeResponse, Champion, Side } from "@/lib/types";
import { RecommendationCard } from "./RecommendationCard";

interface Props {
  result: AnalyzeResponse | null;
  loading: boolean;
  error: string | null;
  champions: Map<string, Champion>;
  portraits: Map<string, string>;
  onSuggest: () => void;
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
  const sideBadgeClass =
    side === "blue"
      ? "bg-blue-600 text-white"
      : side === "red"
        ? "bg-red-600 text-white"
        : "bg-surface-2 text-muted";
  return (
    <div className="rounded-xl border border-border bg-surface/80 p-4 shadow-sm backdrop-blur-sm">
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
        <button
          type="button"
          onClick={onSuggest}
          disabled={disabled || loading}
          className="rounded bg-amber-500 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-slate-900 transition hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "Thinking…" : "Suggest"}
        </button>
      </div>

      {error && (
        <p className="rounded border border-rose-300 bg-rose-50 p-2 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-200">
          {error}
        </p>
      )}

      {!result && !loading && !error && (
        <div className="rounded-lg border border-dashed border-border/60 bg-surface-2/30 p-4 text-sm text-faint">
          <p>
            Press <kbd className="mx-0.5 rounded border-b border-border bg-surface-2 px-1 py-0.5 font-mono text-[10px] text-muted">S</kbd> or click <span className="text-fg">Suggest</span> for the top 3 candidates scored on
            four axes: <span className="text-fg">identity</span>,{" "}
            <span className="text-fg">denial</span>,{" "}
            <span className="text-fg">structural</span>, and{" "}
            <span className="text-fg">survivability</span>.
          </p>
        </div>
      )}

      {result && (
        <div className="space-y-3">
          {result.scores.map((s, i) => (
            <RecommendationCard
              key={s.champion_id}
              score={s}
              champion={champions.get(s.champion_id)}
              portrait={portraits.get(s.champion_id) ?? null}
              rank={i + 1}
              onSelect={onSelect}
              actionLabel={actionLabel}
            />
          ))}
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
