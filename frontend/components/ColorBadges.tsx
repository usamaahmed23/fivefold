import type { Color } from "@/lib/types";
import { ColorBadge } from "./ColorBadge";

interface Props {
  main: Color[];
  off?: Color[];
  size?: "xs" | "sm";
}

export function ColorBadges({ main, off = [], size = "sm" }: Props) {
  return (
    <span className="inline-flex gap-0.5">
      {main.map((c, i) => (
        <ColorBadge key={`m-${c}-${i}`} color={c} size={size} />
      ))}
      {off.map((c, i) => (
        <ColorBadge key={`o-${c}-${i}`} color={c} size={size} dim />
      ))}
    </span>
  );
}
