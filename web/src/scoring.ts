import type { Game, WeekPicks } from "./types";

export type Res = "W" | "L" | "P";
export interface Sel { n: number; team: string; opp: string; line: number; game: Game; res: Res | null; final: boolean }

/** Result of a selection: W/L/P against its line; null until the game starts. `final` once the game is over. */
export function selection(games: Map<number, { game: Game; me: Game["away"]; opp: Game["away"] }>, n: number): Sel | null {
  const s = games.get(n);
  if (!s || s.me.line == null) return null;
  const line: number = s.me.line;
  const { game, me, opp } = s;
  let res: Res | null = null;
  if (game.state !== "pre" && me.score != null && opp.score != null) {
    const m = me.score + line - opp.score;
    res = m > 0 ? "W" : m < 0 ? "L" : "P";
  }
  return { n, team: me.team, opp: opp.team, line, game, res, final: game.state === "post" };
}

export function indexGames(games: Game[]) {
  const m = new Map<number, { game: Game; me: Game["away"]; opp: Game["away"] }>();
  for (const g of games) {
    if (g.away.n != null) m.set(g.away.n, { game: g, me: g.away, opp: g.home });
    if (g.home.n != null) m.set(g.home.n, { game: g, me: g.home, opp: g.away });
  }
  return m;
}

/** Per entry: [w, l, p, liveW, liveL, liveP, pending] for one week. Flat Int8Array, 7 per entry id. */
export const TALLY = 7;
export function tallyWeek(games: Game[], picks: WeekPicks, nEntries: number): Int8Array {
  const idx = indexGames(games);
  const out = new Int8Array(nEntries * TALLY);
  const cache = new Map<number, number>();  // selection number -> slot in tally (0..6)
  const slot = (n: number) => {
    let v = cache.get(n);
    if (v === undefined) {
      const s = selection(idx, n);
      v = !s || !s.res ? 6 : (s.final ? 0 : 3) + (s.res === "W" ? 0 : s.res === "L" ? 1 : 2);
      cache.set(n, v);
    }
    return v;
  };
  for (let i = 0; i < picks.e.length; i++) {
    const base = picks.e[i] * TALLY;
    for (let k = 0; k < 5; k++) out[base + slot(picks.p[i * 5 + k])]++;
  }
  return out;
}

export const points = (t: Int8Array, o: number, live: boolean) =>
  t[o] + 0.5 * t[o + 2] + (live ? t[o + 3] + 0.5 * t[o + 5] : 0);
