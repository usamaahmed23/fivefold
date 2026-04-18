import type { Action, Phase, Side } from "./types";

export interface TurnSpec {
  side: Side;
  action: Action;
  phase: Phase;
}

export const TOTAL_TURNS = 20;

// Standard 2026 LoL draft: 10 bans + 10 picks = 20 turns.
// The side with first pick starts phase-1 bans; phase-2 reverses.
export function buildTurnOrder(firstPickSide: Side): TurnSpec[] {
  const first = firstPickSide;
  const second: Side = firstPickSide === "blue" ? "red" : "blue";
  const ban1 = (side: Side): TurnSpec => ({ side, action: "ban", phase: "ban1" });
  const pick1 = (side: Side): TurnSpec => ({ side, action: "pick", phase: "pick1" });
  const ban2 = (side: Side): TurnSpec => ({ side, action: "ban", phase: "ban2" });
  const pick2 = (side: Side): TurnSpec => ({ side, action: "pick", phase: "pick2" });

  return [
    // Phase 1 bans — 3 per side, alternating.
    ban1(first), ban1(second), ban1(first), ban1(second), ban1(first), ban1(second),
    // Phase 1 picks — snake: first, second, second, first, first, second.
    pick1(first), pick1(second), pick1(second), pick1(first), pick1(first), pick1(second),
    // Phase 2 bans — 2 per side, alternating, second side starts.
    ban2(second), ban2(first), ban2(second), ban2(first),
    // Phase 2 picks — second, first, first, second.
    pick2(second), pick2(first), pick2(first), pick2(second),
  ];
}
