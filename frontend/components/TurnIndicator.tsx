import type { DraftState } from "@/lib/types";
import { phaseLabel } from "@/lib/draftState";

export function TurnIndicator({ state }: { state: DraftState }) {
  const complete = state.phase === "complete";
  const sideColor =
    state.side_to_act === "blue"
      ? "text-blue-600 dark:text-blue-300"
      : "text-red-600 dark:text-red-300";

  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-md border border-border bg-surface px-2 py-1 text-xs shadow-sm sm:gap-2.5 sm:px-2.5 sm:text-sm">
      <span className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] font-medium text-fg">
        {Math.min(state.turn_index + 1, 20)}/20
      </span>
      <span className="text-xs font-medium text-muted">{phaseLabel(state.phase)}</span>
      {!complete && (
        <>
          <span className="h-3 w-px bg-border" />
          <span className="text-xs">
            <span className={`font-semibold ${sideColor}`}>
              {state.side_to_act.toUpperCase()}
            </span>
            <span className="text-muted"> to {state.action_to_take}</span>
          </span>
        </>
      )}
    </div>
  );
}
