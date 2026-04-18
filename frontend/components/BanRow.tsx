import type { Champion, DraftState, Side } from "@/lib/types";
import { Slot } from "./Slot";

interface Props {
  side: Side;
  state: DraftState;
  champions: Map<string, Champion>;
  portraits: Map<string, string>;
}

export function BanRow({ side, state, champions, portraits }: Props) {
  const bans = side === "blue" ? state.blue_bans : state.red_bans;

  const isActive = (index: number) => {
    if (state.phase === "complete") return false;
    if (state.side_to_act !== side) return false;
    if (state.action_to_take !== "ban") return false;
    return index === bans.length;
  };

  return (
    <div className="flex gap-1.5">
      {Array.from({ length: 5 }, (_, i) => {
        const id = bans[i];
        const champ = id ? champions.get(id) ?? null : null;
        return (
          <Slot
            key={`${side}-ban-${i}`}
            variant="ban"
            side={side}
            index={i}
            champion={champ}
            portrait={id ? portraits.get(id) ?? null : null}
            active={isActive(i)}
          />
        );
      })}
    </div>
  );
}
