export interface WeekSummary { week: number; entries: number; games: number; pre: number; live: number; final: number }
export interface RootIndex {
  updated: string; season: number; contest: string; quarters: [number, number][];
  current_week: number | null; weeks: WeekSummary[];
}
export interface GameSide { team: string; score: number | null; n: number | null; line: number | null }
export interface Game {
  id: string; kickoff: string; state: "pre" | "in" | "post"; detail: string; away: GameSide; home: GameSide;
}
export interface WeekPicks { e: number[]; p: number[] }   // p: 5 selection numbers per entry id in e
export interface WeekData { games: Game[]; picks: WeekPicks }
