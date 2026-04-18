import type { Champion, Role, Side } from "@/lib/types";
import { ChampionPortrait } from "./ChampionPortrait";
import { ColorBadges } from "./ColorBadges";
import { RoleIcon } from "./RoleIcon";

const SLOT_ROLES: Role[] = ["top", "jungle", "mid", "bot", "support"];

interface Props {
  variant: "ban" | "pick";
  side: Side;
  index: number;
  champion: Champion | null;
  portrait: string | null;
  active: boolean;
  draggable?: boolean;
  onDragStart?: (index: number) => void;
  onDropSwap?: (fromIndex: number, toIndex: number) => void;
}

export function Slot({
  variant,
  side,
  index,
  champion,
  portrait,
  active,
  draggable,
  onDragStart,
  onDropSwap,
}: Props) {
  const sideText = side === "blue"
    ? "text-blue-600 dark:text-blue-300"
    : "text-red-600 dark:text-red-300";
  const sideBorder = side === "blue"
    ? "border-blue-300/60 dark:border-blue-900/50"
    : "border-red-300/60 dark:border-red-900/50";

  const activeRing = active
    ? "border-amber-400 shadow-[0_0_0_2px_rgba(251,191,36,0.4)] animate-pulse"
    : sideBorder;

  if (variant === "ban") {
    const label = `${side === "blue" ? "B" : "R"}${index + 1}`;
    return (
      <div
        className={`relative aspect-square w-11 overflow-hidden rounded-sm border bg-surface-2 ${activeRing}`}
      >
        {champion ? (
          <>
            <ChampionPortrait
              url={portrait}
              name={champion.name}
              size={44}
              grayscale
              className="h-full w-full object-cover opacity-60"
            />
            <div className="absolute inset-0 flex items-center justify-center bg-black/40">
              <svg
                viewBox="0 0 24 24"
                className="h-6 w-6 text-red-500 drop-shadow"
                fill="currentColor"
              >
                <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm0 18a8 8 0 0 1-6.32-12.906l11.226 11.226A7.957 7.957 0 0 1 12 20Zm6.32-3.094L7.094 5.68A8 8 0 0 1 18.32 16.906Z" />
              </svg>
            </div>
          </>
        ) : (
          <span
            className={`absolute inset-0 flex items-center justify-center text-[10px] font-bold tracking-wider ${sideText} opacity-40`}
          >
            {label}
          </span>
        )}
      </div>
    );
  }

  // pick variant — large square
  const label = `${side === "blue" ? "B" : "R"}${index + 1}`;
  const canDrag = Boolean(draggable && champion);
  return (
    <div
      draggable={canDrag}
      onDragStart={(e) => {
        if (!canDrag) return;
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", String(index));
        onDragStart?.(index);
      }}
      onDragOver={(e) => {
        if (!draggable) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
      }}
      onDrop={(e) => {
        if (!draggable) return;
        e.preventDefault();
        const from = Number(e.dataTransfer.getData("text/plain"));
        if (!Number.isNaN(from) && from !== index) {
          onDropSwap?.(from, index);
        }
      }}
      className={`relative aspect-square w-full overflow-hidden rounded-md border-2 bg-surface ${activeRing} ${
        canDrag ? "cursor-grab active:cursor-grabbing" : ""
      }`}
    >
      {champion ? (
        <ChampionPortrait
          url={portrait}
          name={champion.name}
          size={128}
          className="h-full w-full object-cover"
        />
      ) : (
        <div className="flex h-full w-full flex-col items-center justify-center gap-1 opacity-25">
          <RoleIcon role={SLOT_ROLES[index]} className={`h-7 w-7 ${sideText}`} />
          <span className={`text-[9px] font-bold uppercase tracking-widest ${sideText}`}>
            {SLOT_ROLES[index]}
          </span>
        </div>
      )}

      <span
        className={`absolute left-1 top-1 rounded bg-black/70 px-1.5 py-0.5 text-[10px] font-bold tracking-wider ${sideText}`}
      >
        {label}
      </span>

      {champion && (
        <>
          <div className="absolute left-1 bottom-1 flex gap-0.5">
            <ColorBadges
              main={champion.colors_main}
              off={champion.colors_off}
              size="xs"
            />
          </div>
          <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/95 via-black/60 to-transparent px-1 pb-0.5 pt-4">
            <p className="truncate text-center text-[11px] font-semibold text-white">
              {champion.name}
            </p>
          </div>
        </>
      )}
    </div>
  );
}
