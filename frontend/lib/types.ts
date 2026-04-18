export type Color = "R" | "G" | "U" | "W" | "B" | "C";
export type Role = "top" | "jungle" | "mid" | "bot" | "support";
export type Phase = "ban1" | "pick1" | "ban2" | "pick2" | "complete";
export type Side = "blue" | "red";
export type Action = "ban" | "pick";

export interface StructuralTags {
  damage_profile: string | null;
  range: string | null;
  engage: string | null;
  peel: string | null;
  frontline: string | null;
  waveclear: string | null;
  scaling: string | null;
}

export interface ContextRule {
  condition: string;
  value: string;
  effect: string;
  color: Color;
}

export interface Champion {
  id: string;
  name: string;
  colors_main: Color[];
  colors_off: Color[];
  contextual: boolean;
  ls_notes: string | null;
  source: string | null;
  roles: Role[];
  win_condition_tags: string[];
  structural_tags: StructuralTags | null;
  counter_tags: string[];
  context_rules: ContextRule[];
}

export interface DraftState {
  phase: Phase;
  turn_index: number;
  blue_bans: string[];
  red_bans: string[];
  blue_picks: string[];
  red_picks: string[];
  side_to_act: Side;
  action_to_take: Action;
  first_pick_side: Side;
}

export type RecommendationRole =
  | "best_overall"
  | "structural_fill"
  | "best_denial"
  | "identity_anchor"
  | null;

export interface CandidateScore {
  champion_id: string;
  identity: number;
  denial: number;
  structural: number;
  survivability: number;
  meta_contribution: number;
  total: number;
  rationale: string[];
  recommendation_role: RecommendationRole;
}

export interface ScoreResponse {
  scores: CandidateScore[];
}

export interface AnalyzeResponse {
  mode: "deterministic" | "llm";
  scores: CandidateScore[];
  enemy_reader: Record<string, unknown> | null;
  identity_critic: Record<string, unknown> | null;
  coach: string | null;
}

export interface ChampionsResponse {
  count: number;
  champions: Champion[];
}
