"""Join picks with results: attach Circa's selection numbers (and lines) to the real games.

A pick says "<n>. <TEAM> <line>". The result store knows the games. The join is by team within the
week; games' two sides are Circa numbers 2k-1 / 2k, so a side nobody picked still gets its number and
(negated) line from its partner. Anything that does not line up is returned as a problem.
"""
from dataclasses import dataclass, field

from . import picks as pk
from . import results as rs
from .config import PUSH_POINTS, WIN_POINTS


def partner(n: int) -> int:
    return n + 1 if n % 2 else n - 1


def cover(score: int, opp: int, line: float) -> str:
    """W / L / P for a side that has `score` against `opp` and was picked at `line`."""
    m = score + line - opp
    return "W" if m > 0 else "L" if m < 0 else "P"


@dataclass
class Side:
    team: str
    score: int | None
    n: int | None = None
    line: float | None = None


@dataclass
class Game:
    id: str
    kickoff: str
    state: str
    detail: str
    away: Side
    home: Side

    def side_for(self, n: int) -> tuple[Side, Side] | None:
        for me, other in ((self.away, self.home), (self.home, self.away)):
            if me.n == n:
                return me, other
        return None

    def status_of(self, n: int) -> str | None:
        """Cover status of selection n right now: W/L/P (provisional unless state == 'post'), None if not started."""
        s = self.side_for(n)
        if not s or self.state == "pre" or s[0].line is None or s[0].score is None or s[1].score is None:
            return None
        return cover(s[0].score, s[1].score, s[0].line)


@dataclass
class Week:
    week: int
    entries: list  # [(entry, [(n, team, line)] * 5)]
    games: list[Game]
    problems: list[str] = field(default_factory=list)

    def game_for(self, n: int) -> Game | None:
        return next((g for g in self.games if g.side_for(n)), None)


def build(week: int) -> Week:
    entries = pk.load_week(week) if week in pk.stored_weeks() else []
    sides: dict[int, tuple[str, float]] = {}
    problems: list[str] = []
    for _, picks in entries:
        for n, team, line in picks:
            if n in sides and sides[n] != (team, line):
                problems.append(f"week {week}: selection {n} appears as both {sides[n]} and {(team, line)}")
            sides.setdefault(n, (team, line))
    by_team = {team: (n, line) for n, (team, line) in sides.items()}

    games = []
    for r in rs.load_week(week):
        away = Side(r["away"], r["away_score"])
        home = Side(r["home"], r["home_score"])
        for s in (away, home):
            if s.team in by_team:
                s.n, s.line = by_team[s.team]
        if away.n is not None and home.n is not None:
            if partner(away.n) != home.n or away.line != -home.line:
                problems.append(f"week {week}: {away.team}@{home.team} sides {away.n}/{home.n} lines "
                                f"{away.line}/{home.line} are not a pair")
        elif away.n is not None or home.n is not None:
            known, other = (away, home) if away.n is not None else (home, away)
            other.n, other.line = partner(known.n), -known.line
        games.append(Game(r["game_id"], r["kickoff"], r["state"], r["detail"], away, home))

    matched = {s.team for g in games for s in (g.away, g.home) if s.n in sides and sides[s.n][0] == s.team}
    for n, (team, line) in sorted(sides.items()):
        if team not in matched and (entries and games):
            problems.append(f"week {week}: selection {n} ({team} {line:+g}) matches no game in the results store")
    return Week(week, entries, games, problems)


def score_entry(week: Week, picks) -> dict:
    """Final-only points plus a provisional count for in-progress games."""
    out = {"w": 0, "l": 0, "p": 0, "live_w": 0, "live_l": 0, "live_p": 0, "pending": 0}
    for n, _, _ in picks:
        g = week.game_for(n)
        res = g.status_of(n) if g else None
        if res is None:
            out["pending"] += 1
        elif g.state == "post":
            out[res.lower()] += 1
        else:
            out["live_" + res.lower()] += 1
    out["points"] = out["w"] * WIN_POINTS + out["p"] * PUSH_POINTS
    return out
