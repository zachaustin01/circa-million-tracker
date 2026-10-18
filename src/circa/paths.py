from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
PICKS = DATA / "picks"
RESULTS = DATA / "results"
for p in (PICKS, RESULTS):
    p.mkdir(parents=True, exist_ok=True)

WEB_DATA = ROOT / "web" / "public" / "data"
