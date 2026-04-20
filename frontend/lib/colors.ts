import type { Color } from "./types";

export const COLOR_META: Record<
  Color,
  { bg: string; text: string; ring: string; name: string; hint: string }
> = {
  R: {
    bg: "bg-red-600",
    text: "text-white",
    ring: "",
    name: "Red",
    hint: "Aggression · tempo · snowball",
  },
  G: {
    bg: "bg-emerald-600",
    text: "text-white",
    ring: "",
    name: "Green",
    hint: "Synergy · curved spikes · item timings",
  },
  U: {
    bg: "bg-blue-600",
    text: "text-white",
    ring: "",
    name: "Blue",
    hint: "Control · scaling · denial",
  },
  W: {
    bg: "bg-stone-200 dark:bg-slate-100",
    text: "text-stone-900",
    ring: "ring-1 ring-stone-400 dark:ring-slate-400",
    name: "White",
    hint: "Structure · utility · anti-aggro",
  },
  B: {
    bg: "bg-slate-950",
    text: "text-slate-100",
    ring: "ring-1 ring-slate-600",
    name: "Black",
    hint: "Power at a cost · sacrifice · conditions",
  },
};
