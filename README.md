# circa-million-tracker

Live standings for the Circa Sports Million football contest (unofficial). Same shape as
[ballpark-projections](https://github.com/zachaustin01/ballpark-projections): a Python batch job in GitHub
Actions writes static JSON, a Vite/React site renders it, Firebase Hosting serves it.

```bash
uv sync
uv run circa sync          # fetch new selection PDFs + game results into data/
uv run circa reconcile     # check every pick maps to a real game (non-zero exit on errors)
uv run circa export        # write static JSON -> web/public/data/
uv run circa top -n 10 --live    # standings from Python, handy to cross-check the site
cd web && npm install && npm run dev
uv run --group dev pytest
```

## Data
- **Picks**: `Circa-Sports-Million-VIII-Week-N-Selections.pdf` from circasports.com (the upload month folder varies,
  so the job probes for it). Parsed to `data/picks/week-NN.parquet` + `.meta.json` (URL, ETag, sha256). The newest two
  weeks are re-checked each run in case Circa posts a corrected PDF; older weeks are frozen.
- **Results**: ESPN's public scoreboard -> `data/results/week-NN.parquet`, refetched every run until a week is
  final, then frozen. Same one-file-per-week layout as picks so they can be reconciled.
- **Reconciliation**: Circa numbers selections 2k-1 / 2k per game. Picks give `number -> team + line`; results give
  the games; `weeks.py` joins them by team and `reconcile.py` fails on anything that does not line up.
- Grading is done in the browser from `games.json` + `picks.json` (win 1, push ½), so a results-only refresh never
  rewrites the large pick files. "Count games in progress" toggles provisional scoring of live games.
- Season knobs (year, contest numeral, quarters) live in `src/circa/config.py`.

Storage, CI/CD and hosting: see `docs/DEPLOY.md`.
