"""Sanity checks that picks and results line up. Errors fail CI; warnings are printed."""
from . import picks as pk
from . import results as rs
from . import weeks as wk


def check_week(week: int):
    """-> (errors, warnings) for one week."""
    w = wk.build(week)
    errors, warnings = list(w.problems), []
    if not w.entries:
        errors.append(f"week {week}: no picks stored")
        return errors, warnings
    if not w.games:
        warnings.append(f"week {week}: picks stored but no results yet")
        return errors, warnings

    names = [e for e, _ in w.entries]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        errors.append(f"week {week}: duplicate entry names {dupes[:5]}")
    for name, picks in w.entries:
        ns = [n for n, _, _ in picks]
        if len(set(ns)) != pk.PICKS_PER_ENTRY:
            errors.append(f"week {week}: {name} has duplicate selections {ns}")
        games = [w.game_for(n) for n in ns]
        if len({g.id for g in games if g}) < len([g for g in games if g]):
            warnings.append(f"week {week}: {name} picked both sides of one game")
    for g in w.games:
        if g.state == "post" and (g.away.score is None or g.home.score is None):
            errors.append(f"week {week}: {g.away.team}@{g.home.team} is final with no score")
        if g.away.n is None:
            warnings.append(f"week {week}: {g.away.team}@{g.home.team} has no selection number (nobody picked either side)")
    return errors, warnings


def check_all():
    errors, warnings = [], []
    for week in sorted(set(pk.stored_weeks()) | set(rs.stored_weeks())):
        e, w = check_week(week)
        errors += e
        warnings += w
    return errors, warnings
