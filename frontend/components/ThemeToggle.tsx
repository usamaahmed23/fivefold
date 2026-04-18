"use client";

import { useTheme } from "@/lib/useTheme";

export function ThemeToggle() {
  const [theme, toggle] = useTheme();
  const isDark = theme === "dark";
  return (
    <button
      type="button"
      onClick={toggle}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="rounded border border-border bg-surface px-2 py-1 text-xs text-muted transition hover:text-fg"
    >
      {isDark ? "☀︎ Light" : "☾ Dark"}
    </button>
  );
}
