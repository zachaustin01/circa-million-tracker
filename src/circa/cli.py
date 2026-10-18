import argparse
import sys

from . import picks as pk
from . import results as rs


def _sync(verbose=True):
    pk.sync(verbose)
    rs.sync(pk.stored_weeks(), verbose)


def cmd_sync(args):
    _sync()


def cmd_picks(args):
    pk.sync()


def cmd_results(args):
    rs.sync(args.week and [args.week] or pk.stored_weeks())


def cmd_reconcile(args):
    from .reconcile import check_all
    _sync(verbose=False)
    errors, warnings = check_all()
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    print(f"reconcile: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def cmd_export(args):
    from .export import export
    _sync()
    export()


def cmd_top(args):
    """Print the top of the standings from Python (independent of the web client's scoring)."""
    from . import weeks as wk
    _sync(verbose=False)
    through = args.week or max(pk.stored_weeks())
    total: dict[str, float] = {}
    live: dict[str, float] = {}
    for w in range(1, through + 1):
        week = wk.build(w)
        for entry, picks in week.entries:
            s = wk.score_entry(week, picks)
            total[entry] = total.get(entry, 0) + s["points"]
            live[entry] = live.get(entry, 0) + s["points"] + 0.0 + s["live_w"] + 0.5 * s["live_p"]
    key = live if args.live else total
    print(f"top {args.n} through week {through} ({'incl. live' if args.live else 'final games only'})")
    for i, (e, p) in enumerate(sorted(key.items(), key=lambda kv: (-kv[1], kv[0]))[:args.n], 1):
        print(f"{i:>3}  {p:>5.1f}  {e}")


def main():
    ap = argparse.ArgumentParser(prog="circa")
    sub = ap.add_subparsers(required=True)
    sub.add_parser("sync", help="fetch new selection PDFs and results").set_defaults(fn=cmd_sync)
    sub.add_parser("picks", help="fetch new selection PDFs only").set_defaults(fn=cmd_picks)
    p = sub.add_parser("results", help="fetch game results only")
    p.add_argument("--week", type=int)
    p.set_defaults(fn=cmd_results)
    sub.add_parser("reconcile", help="check picks line up with results").set_defaults(fn=cmd_reconcile)
    sub.add_parser("export", help="write static JSON for the site -> web/public/data/").set_defaults(fn=cmd_export)
    p = sub.add_parser("top", help="print standings")
    p.add_argument("-n", type=int, default=10)
    p.add_argument("--week", type=int, help="through this week")
    p.add_argument("--live", action="store_true", help="count in-progress games")
    p.set_defaults(fn=cmd_top)
    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)
