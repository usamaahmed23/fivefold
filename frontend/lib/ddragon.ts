// Thin Data Dragon helpers. We fetch the latest version + champion index
// on mount, then build a map from our champion.id → portrait URL.
// No Next/image optimization — plain <img> keeps this dependency-free.

import type { Champion } from "./types";

const VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json";
const FALLBACK_VERSION = "14.24.1";

export async function fetchDDragonVersion(): Promise<string> {
  try {
    const r = await fetch(VERSIONS_URL, { cache: "force-cache" });
    const vs = (await r.json()) as string[];
    return vs[0] ?? FALLBACK_VERSION;
  } catch {
    return FALLBACK_VERSION;
  }
}

interface DDragonChampionEntry {
  id: string;
  name: string;
}

export async function fetchDDragonChampionIndex(
  version: string,
): Promise<Map<string, string>> {
  const url = `https://ddragon.leagueoflegends.com/cdn/${version}/data/en_US/champion.json`;
  const r = await fetch(url, { cache: "force-cache" });
  const data = (await r.json()) as {
    data: Record<string, DDragonChampionEntry>;
  };
  const map = new Map<string, string>();
  for (const key of Object.keys(data.data)) {
    const entry = data.data[key];
    map.set(normalize(entry.name), entry.id);
  }
  return map;
}

export function normalize(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]/g, "");
}

export function buildPortraitMap(
  version: string,
  nameToDDragonId: Map<string, string>,
  champions: Champion[],
): Map<string, string> {
  const out = new Map<string, string>();
  for (const c of champions) {
    const key = normalize(c.name);
    const ddragonId = nameToDDragonId.get(key);
    if (!ddragonId) continue;
    out.set(
      c.id,
      `https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/${ddragonId}.png`,
    );
  }
  return out;
}
