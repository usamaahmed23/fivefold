"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Champion, Color, Role } from "@/lib/types";
import { ChampionCard } from "./ChampionCard";
import { ColorBadge } from "./ColorBadge";
import { RoleIcon } from "./RoleIcon";

const ROLES: Role[] = ["top", "jungle", "mid", "bot", "support"];
const COLORS: Color[] = ["R", "G", "U", "W", "B", "C"];

interface Props {
  champions: Champion[];
  taken: Set<string>;
  portraits: Map<string, string>;
  onSelect: (id: string) => void;
  highlighted?: string[];
}

export function ChampionGrid({ champions, taken, portraits, onSelect, highlighted = [] }: Props) {
  const highlightSet = new Set(highlighted);
  const [query, setQuery] = useState("");
  const [role, setRole] = useState<Role | null>(null);
  const [color, setColor] = useState<Color | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey) return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      e.preventDefault();
      inputRef.current?.focus();
      inputRef.current?.select();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return champions
      .filter((c) => !role || c.roles.includes(role))
      .filter(
        (c) =>
          !color ||
          c.colors_main.includes(color) ||
          c.colors_off.includes(color),
      )
      .filter(
        (c) =>
          !q ||
          c.name.toLowerCase().includes(q) ||
          c.id.includes(q.replace(/\s+/g, "")),
      )
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [champions, query, role, color]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      setQuery("");
      return;
    }
    if (e.key === "Enter") {
      const first = filtered.find((c) => !taken.has(c.id));
      if (first) {
        onSelect(first.id);
        setQuery("");
      }
    }
  };

  const available = filtered.filter((c) => !taken.has(c.id)).length;
  const showCount = query || role || color;

  const roleCounts = useMemo(() => {
    const m = new Map<Role, number>();
    for (const r of ROLES) {
      m.set(r, champions.filter((c) => c.roles.includes(r) && !taken.has(c.id)).length);
    }
    return m;
  }, [champions, taken]);

  const colorCounts = useMemo(() => {
    const m = new Map<Color, number>();
    for (const k of COLORS) {
      m.set(
        k,
        champions.filter(
          (c) =>
            !taken.has(c.id) &&
            (c.colors_main.includes(k) || c.colors_off.includes(k)),
        ).length,
      );
    }
    return m;
  }, [champions, taken]);

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Search champions…"
            className="w-full rounded bg-surface-2 px-3 py-2 pr-8 text-sm text-fg placeholder:text-faint outline-none ring-1 ring-border transition focus:ring-2 focus:ring-amber-400/50"
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                inputRef.current?.focus();
              }}
              title="Clear (Esc)"
              className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-1 text-faint hover:text-fg"
            >
              ✕
            </button>
          )}
        </div>
        {showCount && (
          <span className="shrink-0 text-[11px] text-faint">
            {available} available
          </span>
        )}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          {ROLES.map((r) => {
            const active = role === r;
            const count = roleCounts.get(r) ?? 0;
            return (
              <button
                key={r}
                type="button"
                title={`${r} · ${count} available`}
                onClick={() => setRole(active ? null : r)}
                className={`flex items-center gap-1 rounded px-1.5 py-1 transition ${
                  active
                    ? "bg-amber-500/20 text-amber-600 dark:text-amber-300"
                    : "text-faint hover:bg-surface-2 hover:text-fg"
                }`}
              >
                <RoleIcon role={r} className="h-4 w-4" />
                <span className="text-[10px] font-semibold tabular-nums">{count}</span>
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-1">
          {COLORS.map((k) => {
            const active = color === k;
            const count = colorCounts.get(k) ?? 0;
            return (
              <button
                key={k}
                type="button"
                title={`${k} · ${count} available`}
                onClick={() => setColor(active ? null : k)}
                className={`flex items-center gap-1 rounded px-1 py-1 transition ${
                  active ? "bg-amber-500/20 ring-1 ring-amber-400/60" : "hover:bg-surface-2"
                }`}
              >
                <ColorBadge color={k} size="xs" />
                <span className="text-[10px] font-semibold tabular-nums text-faint">{count}</span>
              </button>
            );
          })}
        </div>
      </div>
      <div className="grid flex-1 grid-cols-6 gap-0.5 overflow-y-auto pr-1 sm:grid-cols-7 md:grid-cols-8 lg:grid-cols-9 xl:grid-cols-10">
        {filtered.map((c) => (
          <ChampionCard
            key={c.id}
            champion={c}
            portrait={portraits.get(c.id) ?? null}
            disabled={taken.has(c.id)}
            onSelect={onSelect}
            highlighted={highlightSet.has(c.id)}
          />
        ))}
        {filtered.length === 0 && (
          <p className="col-span-full py-8 text-center text-sm text-faint">
            No champions match.
          </p>
        )}
      </div>
    </div>
  );
}
