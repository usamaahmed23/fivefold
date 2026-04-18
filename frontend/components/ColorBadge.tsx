import { COLOR_META } from "@/lib/colors";
import type { Color } from "@/lib/types";

interface Props {
  color: Color;
  size?: "xs" | "sm";
  dim?: boolean;
}

export function ColorBadge({ color, size = "sm", dim = false }: Props) {
  const meta = COLOR_META[color];
  const dims = size === "xs" ? "w-4 h-4 text-[10px]" : "w-5 h-5 text-xs";
  return (
    <span
      title={`${meta.name}${dim ? " (off)" : ""} — ${meta.hint}`}
      className={`inline-flex items-center justify-center rounded-sm font-bold leading-none ${dims} ${meta.bg} ${meta.text} ${meta.ring} ${
        dim ? "opacity-50" : ""
      }`}
    >
      {color}
    </span>
  );
}
