const TOOLTIPS: Record<string, string> = {
  Identity: "Reinforces your team's color identity and win condition",
  Denial: "Disrupts the enemy's declared win condition",
  Structural: "Fills a structural hole in your comp (engage, peel, waveclear…)",
  Survivability: "Meta tier strength across this champion's roles",
};

interface Props {
  label: string;
  value: number;
  tone: string;
}

export function AxisBar({ label, value, tone }: Props) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="space-y-0.5" title={TOOLTIPS[label]}>
      <div className="flex items-center justify-between text-[10px] uppercase tracking-widest text-muted">
        <span className="cursor-help">{label}</span>
        <span className="font-mono text-faint">{pct}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded bg-surface-2">
        <div
          className={`h-full transition-[width] duration-300 ${tone}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
