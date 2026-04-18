import type { DraftState, Phase, Side } from "./types";
import { buildTurnOrder, TOTAL_TURNS } from "./turnOrder";

export function initialDraftState(firstPickSide: Side = "blue"): DraftState {
  const order = buildTurnOrder(firstPickSide);
  const first = order[0];
  return {
    phase: first.phase,
    turn_index: 0,
    blue_bans: [],
    red_bans: [],
    blue_picks: [],
    red_picks: [],
    side_to_act: first.side,
    action_to_take: first.action,
    first_pick_side: firstPickSide,
  };
}

export function advance(state: DraftState, championId: string): DraftState {
  if (state.turn_index >= TOTAL_TURNS) return state;

  const order = buildTurnOrder(state.first_pick_side);
  const current = order[state.turn_index];
  const nextIndex = state.turn_index + 1;
  const next = nextIndex < TOTAL_TURNS ? order[nextIndex] : null;

  const blue_bans = [...state.blue_bans];
  const red_bans = [...state.red_bans];
  const blue_picks = [...state.blue_picks];
  const red_picks = [...state.red_picks];

  if (current.action === "ban") {
    (current.side === "blue" ? blue_bans : red_bans).push(championId);
  } else {
    (current.side === "blue" ? blue_picks : red_picks).push(championId);
  }

  const phase: Phase = next ? next.phase : "complete";

  return {
    ...state,
    turn_index: nextIndex,
    blue_bans,
    red_bans,
    blue_picks,
    red_picks,
    phase,
    side_to_act: next ? next.side : state.side_to_act,
    action_to_take: next ? next.action : state.action_to_take,
  };
}

export function allTaken(state: DraftState): Set<string> {
  return new Set([
    ...state.blue_bans,
    ...state.red_bans,
    ...state.blue_picks,
    ...state.red_picks,
  ]);
}

export function swapSides(state: DraftState): DraftState {
  return {
    ...state,
    blue_bans: state.red_bans,
    red_bans: state.blue_bans,
    blue_picks: state.red_picks,
    red_picks: state.blue_picks,
    side_to_act: state.side_to_act === "blue" ? "red" : "blue",
    first_pick_side: state.first_pick_side === "blue" ? "red" : "blue",
  };
}

export function swapPicks(state: DraftState, side: Side, i: number, j: number): DraftState {
  if (i === j) return state;
  const key = side === "blue" ? "blue_picks" : "red_picks";
  const picks = [...state[key]];
  if (i < 0 || j < 0 || i >= picks.length || j >= picks.length) return state;
  [picks[i], picks[j]] = [picks[j], picks[i]];
  return { ...state, [key]: picks };
}

export function phaseLabel(phase: Phase): string {
  switch (phase) {
    case "ban1":
      return "Phase 1 Bans";
    case "pick1":
      return "Phase 1 Picks";
    case "ban2":
      return "Phase 2 Bans";
    case "pick2":
      return "Phase 2 Picks";
    case "complete":
      return "Draft Complete";
  }
}
