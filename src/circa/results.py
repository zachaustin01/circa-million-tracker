"""Actual NFL results (ESPN's public scoreboard) -> data/results/week-NN.parquet.

Stored the same way as the picks (one parquet per week) so a pick can always be reconciled with
the game it refers to. A week is refetched on every sync until all its games are final, then frozen.
"""
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import requests

from . import config
from .paths import RESULTS

SCHEMA = pa.schema([
    ("game_id", pa.string()), ("week", pa.int8()), ("kickoff", pa.string()),
    ("state", pa.string()),      # pre | in | post
    ("detail", pa.string()),     # "Final", "10:51 - 3rd", "10/18 - 8:20 PM EDT"
    ("home", pa.string()), ("away", pa.string()),
    ("home_score", pa.int16()), ("away_score", pa.int16()),
    ("fetched_at", pa.string()),
])


def _file(week: int) -> Path:
    return RESULTS / f"week-{week:02d}.parquet"


def stored_weeks() -> list[int]:
    return sorted(int(p.stem.split("-")[1]) for p in RESULTS.glob("week-*.parquet"))


def normalize(event: dict, week: int, fetched_at: str) -> dict:
    comp = event["competitions"][0]
    side = {c["homeAway"]: c for c in comp["competitors"]}
    st = event["status"]["type"]

    def score(c):
        s = c.get("score")
        return int(float(s)) if s not in (None, "") else None

    return {"game_id": str(event["id"]), "week": week, "kickoff": event["date"], "state": st["state"],
            "detail": st.get("shortDetail") or st.get("description", ""),
            "home": side["home"]["team"]["abbreviation"], "away": side["away"]["team"]["abbreviation"],
            "home_score": score(side["home"]), "away_score": score(side["away"]), "fetched_at": fetched_at}


def fetch_week(week: int) -> list[dict]:
    params = {"seasontype": 2, "week": week, "dates": config.SEASON, "limit": 100}
    for attempt in range(4):
        try:
            r = requests.get(config.ESPN_SCOREBOARD, params=params, headers=config.HEADERS, timeout=30)
            r.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))
    data = r.json()
    got = data.get("week", {}).get("number")
    if got != week:
        raise ValueError(f"ESPN returned week {got}, expected {week}")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return sorted((normalize(e, week, now) for e in data["events"]), key=lambda g: (g["kickoff"], g["game_id"]))


def write_week(week: int, games: list[dict]) -> None:
    cols = {f.name: [g[f.name] for g in games] for f in SCHEMA}
    pq.write_table(pa.table(cols, schema=SCHEMA), _file(week), compression="zstd")


def load_week(week: int) -> list[dict]:
    f = _file(week)
    if not f.exists():
        return []
    t = pq.read_table(f).to_pylist()
    return t


def is_final(week: int) -> bool:
    """All games over, and fetched at least a day after the last kickoff (stat corrections land late)."""
    games = load_week(week)
    if not games or any(g["state"] != "post" for g in games):
        return False
    last = max(g["kickoff"] for g in games)
    fetched = max(g["fetched_at"] for g in games)
    return (date.fromisoformat(fetched[:10]) - date.fromisoformat(last[:10])).days >= 1


def sync(weeks: list[int], verbose: bool = True) -> list[int]:
    """Fetch results for these weeks unless already final. Returns weeks fetched."""
    done = []
    for w in weeks:
        if is_final(w):
            continue
        try:
            games = fetch_week(w)
        except Exception as e:
            print(f"results: week {w}: {type(e).__name__}: {e}")
            continue
        if games:
            write_week(w, games)
            done.append(w)
            if verbose:
                states = {s: sum(g["state"] == s for g in games) for s in ("pre", "in", "post")}
                print(f"results: week {w}: {len(games)} games {states}")
    return done
