"""Batch job: write static JSON for the web front end.

web/public/data/
  index.json                {"updated", "season", "contest", "quarters", "current_week", "weeks": [...]}
  entries.json              ["ENTRY-1", ...]   (index = entry id used by the per-week pick files)
  week/NN/games.json        games with scores, status, and Circa selection number + line per side
  week/NN/picks.json        {"e": [entry ids], "p": [5 selection numbers per entry, flattened]}

Grading happens in the browser from games + picks, so a results-only refresh never touches the picks.
"""
import json
from datetime import datetime, timezone

from . import config
from . import picks as pk
from . import results as rs
from . import weeks as wk
from .paths import WEB_DATA


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":"), allow_nan=False, ensure_ascii=False))


def _side(s: wk.Side) -> dict:
    return {"team": s.team, "score": s.score, "n": s.n, "line": s.line}


def export() -> None:
    weeks = [wk.build(w) for w in pk.stored_weeks()]
    names = sorted({e for w in weeks for e, _ in w.entries})
    ids = {n: i for i, n in enumerate(names)}

    summaries = []
    for w in weeks:
        wd = WEB_DATA / "week" / f"{w.week:02d}"
        _write(wd / "games.json", [{"id": g.id, "kickoff": g.kickoff, "state": g.state, "detail": g.detail,
                                     "away": _side(g.away), "home": _side(g.home)} for g in w.games])
        _write(wd / "picks.json", {"e": [ids[e] for e, _ in w.entries],
                                   "p": [n for _, picks in w.entries for n, _, _ in picks]})
        count = lambda s: sum(g.state == s for g in w.games)
        summaries.append({"week": w.week, "entries": len(w.entries), "games": len(w.games),
                          "pre": count("pre"), "live": count("in"), "final": count("post")})

    # When the *sources* were last fetched (not when we exported), so the site can flag stale data.
    cur = max((w.week for w in weeks), default=None)
    res = rs.load_week(cur) if cur else []
    meta = pk.read_meta(cur) if cur else None
    results_as_of = max((g["fetched_at"] for g in res), default=None)
    picks_as_of = meta.get("fetched_at") if meta else None

    _write(WEB_DATA / "entries.json", names)
    _write(WEB_DATA / "index.json", {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "season": config.SEASON, "contest": config.CONTEST, "quarters": config.QUARTERS,
        "current_week": cur, "results_as_of": results_as_of, "picks_as_of": picks_as_of, "weeks": summaries,
    })
    print(f"exported {len(weeks)} week(s), {len(names)} entries -> {WEB_DATA}")
