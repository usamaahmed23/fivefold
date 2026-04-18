import type { Champion, DraftState, Side } from "@/lib/types";
import { Slot } from "./Slot";

interface Props {
  side: Side;
  state: DraftState;
  champions: Map<string, Champion>;
  portraits: Map<string, string>;
  onSwapPicks?: (side: Side, from: number, to: number) => void;
}

export function SideColumn({ side, state, champions, portraits, onSwapPicks }: Props) {
  const canReorder = state.phase === "complete" && Boolean(onSwapPicks);
  const picks = side === "blue" ? state.blue_picks : state.red_picks;

  const isActive = (index: number) => {
    if (state.phase === "complete") return false;
    if (state.side_to_act !== side) return false;
    if (state.action_to_take !== "pick") return false;
    return index === picks.length;
  };

  return (
    <div className="flex w-28 flex-col gap-2">
      {Array.from({ length: 5 }, (_, i) => {
        const id = picks[i];
        const champ = id ? champions.get(id) ?? null : null;
        return (
          <Slot
            key={`${side}-pick-${i}`}
            variant="pick"
            side={side}
            index={i}
            champion={champ}
            portrait={id ? portraits.get(id) ?? null : null}
            active={isActive(i)}
            draggable={canReorder}
            onDropSwap={(from, to) => onSwapPicks?.(side, from, to)}
          />
        );
      })}
    </div>
  );
}
