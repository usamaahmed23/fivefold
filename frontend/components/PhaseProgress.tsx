import type { Phase } from "@/lib/types";

const PHASES: { id: Phase; label: string; bans: number; picks: number }[] = [
  { id: "ban1", label: "Bans I", bans: 6, picks: 0 },
  { id: "pick1", label: "Picks I", bans: 0, picks: 4 },
  { id: "ban2", label: "Bans II", bans: 4, picks: 0 },
  { id: "pick2", label: "Picks II", bans: 0, picks: 6 },
];

const PHASE_ORDER = ["ban1", "pick1", "ban2", "pick2", "complete"];

interface Props {
  phase: Phase;
  turnIndex: number;
}

export function PhaseProgress({ phase, turnIndex }: Props) {
  const currentIdx = PHASE_ORDER.indexOf(phase);

  return (
    <div className="flex min-w-max items-center gap-1 rounded-full border border-border/60 bg-surface/60 px-2 py-1.5 shadow-sm backdrop-blur-sm sm:gap-1.5 sm:px-3">
      {PHASES.map((p, i) => {
        const state =
          phase === "complete"
            ? "done"
            : i < currentIdx
              ? "done"
              : i === currentIdx
                ? "active"
                : "pending";

        return (
          <div key={p.id} className="flex items-center gap-1.5">
            {i > 0 && (
              <div
                className={`h-px w-5 transition-colors ${
                  state === "done" || (state === "active" && i <= currentIdx)
                    ? "bg-border"
                    : "bg-surface-2"
                }`}
              />
            )}
            <div
              className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider transition-all sm:gap-1.5 sm:px-2.5 sm:text-[10px] ${
                state === "active"
                  ? p.id.startsWith("ban")
                    ? "bg-rose-500/15 text-rose-600 ring-1 ring-rose-500/30 dark:bg-rose-500/20 dark:text-rose-300"
                    : "bg-emerald-500/15 text-emerald-700 ring-1 ring-emerald-500/30 dark:bg-emerald-500/20 dark:text-emerald-300"
                  : state === "done"
                    ? "text-faint/70"
                    : "text-faint/40"
              }`}
            >
              {p.label}
              {state === "active" && (
                <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
