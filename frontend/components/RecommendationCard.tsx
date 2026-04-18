import type { CandidateScore, Champion, RecommendationRole } from "@/lib/types";
import { AxisBar } from "./AxisBar";
import { ChampionPortrait } from "./ChampionPortrait";
import { ColorBadges } from "./ColorBadges";

const ROLE_LABELS: Record<NonNullable<RecommendationRole>, string> = {
  best_overall: "TOP PICK",
  structural_fill: "FILLS GAPS",
  best_denial: "BEST DENIAL",
  identity_anchor: "IDENTITY FIT",
};

const ROLE_COLORS: Record<NonNullable<RecommendationRole>, string> = {
  best_overall: "text-amber-500 dark:text-amber-400/80",
  structural_fill: "text-teal-500 dark:text-teal-400/80",
  best_denial: "text-rose-500 dark:text-rose-400/80",
  identity_anchor: "text-violet-500 dark:text-violet-400/80",
};

const ROLE_ACCENTS: Record<NonNullable<RecommendationRole>, string> = {
  best_overall: "border-amber-500/60 bg-amber-500/5 hover:border-amber-400 hover:bg-amber-500/10",
  structural_fill: "border-teal-500/40 bg-teal-500/5 hover:border-teal-400 hover:bg-teal-500/10",
  best_denial: "border-rose-500/40 bg-rose-500/5 hover:border-rose-400 hover:bg-rose-500/10",
  identity_anchor: "border-violet-500/40 bg-violet-500/5 hover:border-violet-400 hover:bg-violet-500/10",
};

interface Props {
  score: CandidateScore;
  champion: Champion | undefined;
  portrait: string | null;
  rank: number;
  onSelect?: (id: string) => void;
  actionLabel?: string;
}

export function RecommendationCard({
  score,
  champion,
  portrait,
  rank,
  onSelect,
  actionLabel,
}: Props) {
  const role = score.recommendation_role ?? (rank === 1 ? "best_overall" : null);
  const isTop = role === "best_overall";
  const accent = role
    ? ROLE_ACCENTS[role]
    : "border-border bg-surface hover:border-muted hover:bg-surface-2";
  const rankLabel = role ? ROLE_LABELS[role] : `ALT #${rank - 1}`;
  const clickable = Boolean(onSelect);

  const content = (
    <>
      <div className="mb-3 flex items-center gap-3">
        <div className="shrink-0 overflow-hidden rounded ring-1 ring-border">
          <ChampionPortrait
            url={portrait}
            name={champion?.name ?? score.champion_id}
            size={56}
            className="h-14 w-14 object-cover"
          />
        </div>
        <div className="min-w-0 flex-1">
          <p
            className={`mb-0.5 text-[10px] font-semibold uppercase tracking-widest ${
              role ? ROLE_COLORS[role] : "text-faint"
            }`}
          >
            {rankLabel}
          </p>
          <h3 className="truncate text-lg font-semibold text-fg">
            {champion?.name ?? score.champion_id}
          </h3>
          {champion && (
            <div className="mt-1 flex items-center gap-2">
              <ColorBadges
                main={champion.colors_main}
                off={champion.colors_off}
                size="xs"
              />
              <span className="text-[10px] uppercase tracking-wider text-faint">
                {champion.roles.join(" · ")}
              </span>
            </div>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="rounded bg-surface-2 px-2 py-1 font-mono text-lg font-semibold text-fg">
            {score.total.toFixed(2)}
          </span>
          {clickable && actionLabel && (
            <span
              className={`text-[10px] font-semibold uppercase tracking-widest ${
                role ? ROLE_COLORS[role] : "text-faint"
              }`}
            >
              {actionLabel} →
            </span>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-2">
        <AxisBar label="Identity" value={score.identity} tone="bg-violet-500" />
        <AxisBar label="Denial" value={score.denial} tone="bg-rose-500" />
        <AxisBar label="Structural" value={score.structural} tone="bg-amber-500" />
        <AxisBar
          label="Survivability"
          value={score.survivability}
          tone="bg-teal-500"
        />
      </div>
      {score.rationale.length > 0 && (
        <ul className="mt-2.5 space-y-0.5 border-t border-border pt-2.5">
          {score.rationale.map((r, i) => (
            <li key={i} className="flex gap-1.5 text-[11px] leading-snug text-muted">
              <span className="mt-0.5 shrink-0 text-faint">·</span>
              {r}
            </li>
          ))}
        </ul>
      )}
    </>
  );

  if (clickable) {
    return (
      <button
        type="button"
        onClick={() => onSelect!(score.champion_id)}
        className={`w-full rounded border ${accent} p-3 text-left transition`}
      >
        {content}
      </button>
    );
  }

  return <div className={`rounded border ${accent} p-3`}>{content}</div>;
}
