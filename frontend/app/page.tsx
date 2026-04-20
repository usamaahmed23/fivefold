"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { analyzeDraft, API_BASE, fetchChampions } from "@/lib/api";
import { advance, initialDraftState, swapPicks, swapSides } from "@/lib/draftState";
import {
  buildPortraitMap,
  fetchDDragonChampionIndex,
  fetchDDragonVersion,
} from "@/lib/ddragon";
import type {
  AnalyzeResponse,
  Champion,
  DraftState,
  Side,
} from "@/lib/types";
import { BanRow } from "@/components/BanRow";
import { ChampionGrid } from "@/components/ChampionGrid";
import { PhaseProgress } from "@/components/PhaseProgress";
import { RecommendationPanel } from "@/components/RecommendationPanel";
import { SideBanner } from "@/components/SideBanner";
import { SideColumn } from "@/components/SideColumn";
import { ThemeToggle } from "@/components/ThemeToggle";
import { TurnIndicator } from "@/components/TurnIndicator";

const DRAFT_STORAGE_KEY = "fivefold-draft-history";

export default function HomePage() {
  const [champions, setChampions] = useState<Champion[]>([]);
  const [portraits, setPortraits] = useState<Map<string, string>>(new Map());
  const [loadError, setLoadError] = useState<string | null>(null);

  const [history, setHistory] = useState<DraftState[]>([
    initialDraftState("blue"),
  ]);
  const state = history[history.length - 1];
  const hydrated = useRef(false);

  const [suggestion, setSuggestion] = useState<AnalyzeResponse | null>(null);
  const [suggesting, setSuggesting] = useState(false);
  const [suggestError, setSuggestError] = useState<string | null>(null);

  useEffect(() => {
    fetchChampions()
      .then((data) => setChampions(data.champions))
      .catch((e) => setLoadError(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(() => {
    if (champions.length === 0) return;
    let cancelled = false;
    (async () => {
      try {
        const version = await fetchDDragonVersion();
        const index = await fetchDDragonChampionIndex(version);
        if (cancelled) return;
        setPortraits(buildPortraitMap(version, index, champions));
      } catch {
        // portraits optional
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [champions]);

  // Hydrate draft from localStorage once on mount.
  useEffect(() => {
    try {
      const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as DraftState[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          setHistory(parsed);
        }
      }
    } catch {}
    hydrated.current = true;
  }, []);

  // Persist draft history whenever it changes (after hydration).
  useEffect(() => {
    if (!hydrated.current) return;
    try {
      localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(history));
    } catch {}
  }, [history]);

  const championMap = useMemo(
    () => new Map(champions.map((c) => [c.id, c])),
    [champions],
  );

  const taken = useMemo(
    () =>
      new Set([
        ...state.blue_bans,
        ...state.red_bans,
        ...state.blue_picks,
        ...state.red_picks,
      ]),
    [state],
  );

  const requestSeq = useRef(0);

  const onSelect = useCallback(
    (id: string) => {
      if (taken.has(id) || state.phase === "complete") return;
      setHistory((h) => [...h, advance(state, id)]);
      setSuggestion(null);
    },
    [state, taken],
  );

  const onUndo = useCallback(() => {
    setHistory((h) => (h.length > 1 ? h.slice(0, -1) : h));
  }, []);

  const onReset = useCallback(() => {
    setHistory([initialDraftState(state.first_pick_side)]);
    setSuggestion(null);
    setSuggestError(null);
  }, [state.first_pick_side]);

  const onFirstPickToggle = (side: Side) => {
    if (side === state.first_pick_side && history.length === 1) return;
    setHistory([initialDraftState(side)]);
    setSuggestion(null);
    setSuggestError(null);
  };

  const onSwap = useCallback(() => {
    setHistory((h) => [...h, swapSides(h[h.length - 1])]);
    setSuggestion(null);
  }, []);

  const onSwapPicks = useCallback((side: Side, from: number, to: number) => {
    setHistory((h) => [...h, swapPicks(h[h.length - 1], side, from, to)]);
  }, []);

  const onSuggest = useCallback(async () => {
    if (state.phase === "complete") return;
    const seq = ++requestSeq.current;
    setSuggesting(true);
    setSuggestError(null);
    try {
      const result = await analyzeDraft(state, 10);
      if (seq === requestSeq.current) {
        setSuggestion(result);
      }
    } catch (e) {
      if (seq === requestSeq.current) {
        setSuggestError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      if (seq === requestSeq.current) {
        setSuggesting(false);
      }
    }
  }, [state]);

  useEffect(() => {
    if (champions.length === 0 || state.phase === "complete") return;
    setSuggestion(null);
    const handle = window.setTimeout(() => {
      void onSuggest();
    }, 120);
    return () => window.clearTimeout(handle);
  }, [champions.length, onSuggest, state]);

  // Keyboard shortcuts (ignored while typing in an input).
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "u" || e.key === "U") {
        e.preventDefault();
        onUndo();
      } else if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        onReset();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onUndo, onReset]);

  const btnBase =
    "rounded-md border border-border bg-surface px-2.5 py-1 text-xs font-medium text-muted transition hover:border-muted/60 hover:bg-surface-2 hover:text-fg disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <main className="mx-auto max-w-[1500px] px-3 py-4 sm:px-4 sm:py-5 lg:px-6 lg:py-6">
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3 sm:mb-5 sm:items-center sm:gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-fg sm:text-xl">
            Fivefold{" "}
            <span className="font-light text-faint">— Draft Coach</span>
          </h1>
          <p className="mt-0.5 text-xs leading-relaxed text-faint">
            Color-identity theory. A draft is a coherent win condition, not a
            bag of champions.
          </p>
          <p className="mt-1 text-[11px] text-faint/70">
            <span className="inline-flex items-center gap-1 rounded border border-border/60 bg-surface-2 px-1.5 py-0.5 font-mono font-medium">
              Patch 26.8
            </span>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <TurnIndicator state={state} />
          <div className="flex items-center gap-0.5 rounded-md bg-surface-2 p-0.5 text-xs ring-1 ring-border">
            <button
              type="button"
              className={`rounded px-2 py-1 font-medium transition ${
                state.first_pick_side === "blue"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-muted hover:text-fg"
              }`}
              onClick={() => onFirstPickToggle("blue")}
            >
              Blue 1st
            </button>
            <button
              type="button"
              className={`rounded px-2 py-1 font-medium transition ${
                state.first_pick_side === "red"
                  ? "bg-red-600 text-white shadow-sm"
                  : "text-muted hover:text-fg"
              }`}
              onClick={() => onFirstPickToggle("red")}
            >
              Red 1st
            </button>
          </div>
          <button type="button" onClick={onSwap} title="Mirror blue ↔ red" className={btnBase}>
            ⇄ Swap
          </button>
          <button type="button" onClick={onUndo} disabled={history.length <= 1} title="Undo (U)" className={btnBase}>
            Undo
          </button>
          <button type="button" onClick={onReset} title="Reset (R)" className={btnBase}>
            Reset
          </button>
          <ThemeToggle />
        </div>
      </header>

      {loadError && (
        <div className="mb-4 rounded border border-rose-300 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-200">
          Couldn&apos;t load champions: {loadError}. Make sure the backend is
          running on <code className="font-mono">{API_BASE}</code>.
        </div>
      )}

      <div className="mb-3 flex justify-center overflow-x-auto pb-1">
        <PhaseProgress phase={state.phase} turnIndex={state.turn_index} />
      </div>

      <SideBanner />

      <div className="mt-3 grid gap-3 md:grid-cols-2 md:gap-4">
        <div className="min-w-0">
          <BanRow
            side="blue"
            state={state}
            champions={championMap}
            portraits={portraits}
          />
        </div>
        <div className="min-w-0 md:flex md:justify-end">
          <BanRow
            side="red"
            state={state}
            champions={championMap}
            portraits={portraits}
          />
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 xl:grid-cols-[7rem_minmax(0,1fr)_7rem] xl:gap-4">
        <SideColumn
          className="order-1 col-span-1 xl:order-1 xl:col-start-1"
          side="blue"
          state={state}
          champions={championMap}
          portraits={portraits}
          onSwapPicks={onSwapPicks}
        />
        <SideColumn
          className="order-2 col-span-1 xl:order-3 xl:col-start-3"
          side="red"
          state={state}
          champions={championMap}
          portraits={portraits}
          onSwapPicks={onSwapPicks}
        />
        <div className="order-3 col-span-2 flex min-w-0 flex-col gap-4 xl:order-2 xl:col-span-1 xl:col-start-2 xl:row-start-1">
          <div className="h-[52svh] min-h-[340px] rounded-xl border border-border bg-surface/80 p-2.5 shadow-sm backdrop-blur-sm sm:h-[500px] sm:p-3">
            <ChampionGrid
              champions={champions}
              taken={taken}
              portraits={portraits}
              onSelect={onSelect}
              highlighted={suggestion?.scores.map((s) => s.champion_id)}
            />
          </div>
          <div>
            <RecommendationPanel
              result={suggestion}
              loading={suggesting}
              error={suggestError}
              champions={championMap}
              portraits={portraits}
              onSuggest={onSuggest}
              onSelect={onSelect}
              actionLabel={
                state.action_to_take === "ban" ? "Ban" : "Pick"
              }
              side={state.side_to_act}
              disabled={state.phase === "complete"}
            />
          </div>
        </div>
      </div>

      <div className="mx-auto mt-6 flex max-w-3xl flex-wrap items-center justify-center gap-x-3 gap-y-2 rounded-lg border border-border/60 bg-surface/40 px-3 py-2 text-[10px] text-faint backdrop-blur-sm sm:mt-8 sm:gap-x-4 sm:px-4 sm:text-[11px]">
        {[
          ["/", "focus search"],
          ["Enter", "pick first"],
          ["Esc", "clear search"],
          ["U", "undo"],
          ["R", "reset"],
        ].map(([key, label]) => (
          <span key={key} className="flex items-center gap-1.5">
            <kbd className="rounded border-b border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] font-medium text-muted shadow-sm">
              {key}
            </kbd>
            <span>{label}</span>
          </span>
        ))}
      </div>
    </main>
  );
}
