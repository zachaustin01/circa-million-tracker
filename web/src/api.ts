import type { Game, RootIndex, WeekPicks } from "./types";

const base = import.meta.env.BASE_URL + "data/";

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(base + path);
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}

const wk = (w: number) => String(w).padStart(2, "0");
export const fetchRoot = () => getJson<RootIndex>("index.json");
export const fetchEntries = () => getJson<string[]>("entries.json");
export const fetchGames = (w: number) => getJson<Game[]>(`week/${wk(w)}/games.json`);
export const fetchPicks = (w: number) => getJson<WeekPicks>(`week/${wk(w)}/picks.json`);
