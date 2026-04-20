import type { Champion } from "@/lib/types";
import { ChampionPortrait } from "./ChampionPortrait";
import { ColorBadges } from "./ColorBadges";

interface Props {
  champion: Champion;
  portrait: string | null;
  disabled?: boolean;
  onSelect: (id: string) => void;
  highlighted?: boolean;
}

export function ChampionCard({ champion, portrait, disabled, onSelect, highlighted }: Props) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onSelect(champion.id)}
      title={champion.name}
      className={`group relative flex flex-col items-center gap-1 rounded-sm p-1 transition ${
        disabled
          ? "cursor-not-allowed opacity-30"
          : highlighted
            ? "-translate-y-0.5 bg-amber-500/10"
            : "hover:-translate-y-0.5 hover:bg-surface-2"
      }`}
    >
      <div className={`relative overflow-hidden rounded-sm ring-1 transition ${
        highlighted ? "ring-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.5)]" : "ring-border group-hover:ring-muted"
      }`}>
        <ChampionPortrait
          url={portrait}
          name={champion.name}
          size={52}
          grayscale={disabled}
          className="h-[52px] w-[52px] object-cover sm:h-[60px] sm:w-[60px]"
        />
        <div className="absolute left-0.5 bottom-0.5 flex gap-0.5">
          <ColorBadges
            main={champion.colors_main}
            off={champion.colors_off}
            size="xs"
          />
        </div>
      </div>
      <span className="w-[52px] truncate text-center text-[10px] leading-tight text-fg sm:w-[60px] sm:text-[11px]">
        {champion.name}
      </span>
    </button>
  );
}
