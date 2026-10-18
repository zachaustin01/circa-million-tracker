"""Circa Sports Million selection PDFs -> data/picks/week-NN.parquet (+ .meta.json).

One PDF per week lists every entry's 5 picks as "<n>. <TEAM> <line>", where n is Circa's
selection number (games are pairs 2k-1 / 2k). Like the Statcast store in ballpark-projections,
the store is a plain folder that CI keeps in the Actions cache; if it is evicted the next run
re-downloads and re-parses every published week.
"""
import hashlib
import json
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import requests

from . import config
from .paths import PICKS
from .teams import abbr

PICK_RE = re.compile(r"(\d{1,2})\. ([A-Za-z0-9]+) ([+-](?:\d+(?:½|\.5)?|½)|PK|pk)(?=\s|$)")
ENTRY_RE = re.compile(r"-\d+$")
SKIP_RE = re.compile(r"^(Circa Sports Million.*|Week \d+ Selections|ENTRY NAME\s+SELECTIONS|\d{1,2}/\d{1,2}/\d{2,4})$")
PICKS_PER_ENTRY = 5


def parse_line_value(s: str) -> float:
    if s.upper() == "PK":
        return 0.0
    sign = -1.0 if s[0] == "-" else 1.0
    body = s[1:]
    if body.endswith("½"):
        return sign * (float(body[:-1] or 0) + 0.5)
    return sign * float(body)


def parse_row(text: str):
    """'NAME-1 6. COLTS +2½ ...' -> (entry, [(n, team_abbr, line)] * 5), or None if not a full row."""
    ms = list(PICK_RE.finditer(text))
    if len(ms) < PICKS_PER_ENTRY:
        return None
    ms = ms[-PICKS_PER_ENTRY:]
    name = text[:ms[0].start()].strip()
    if not ENTRY_RE.search(name):
        return None
    picks = [(int(m.group(1)), abbr(m.group(2)), parse_line_value(m.group(3))) for m in ms]
    return name, picks


def parse_lines(lines):
    """Rows can wrap across lines in the PDF; glue unparseable fragments together until a row parses."""
    rows, buf = [], ""
    for raw in lines:
        line = raw.strip()
        if not line or SKIP_RE.match(line):
            continue
        row = parse_row(line) if not buf else None
        if row is None:
            buf = f"{buf} {line}".strip()
            row = parse_row(buf)
            if row is None:
                if buf.count(" ") > 60:
                    raise ValueError(f"cannot parse row near: {buf[:120]!r}")
                continue
        rows.append(row)
        buf = ""
    if buf:
        raise ValueError(f"trailing unparsed text: {buf[:120]!r}")
    return rows


def parse_pdf(path: Path):
    import pdfplumber  # imported lazily: slow to load, only needed when a PDF actually changed
    lines = []
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) > config.MAX_PDF_PAGES:
            raise ValueError(f"{path.name}: {len(pdf.pages)} pages (limit {config.MAX_PDF_PAGES})")
        for page in pdf.pages:
            lines.extend((page.extract_text() or "").split("\n"))
    return parse_lines(lines)


# ---- store -------------------------------------------------------------------------------------

def _file(week: int) -> Path:
    return PICKS / f"week-{week:02d}.parquet"


def _meta_file(week: int) -> Path:
    return PICKS / f"week-{week:02d}.meta.json"


def read_meta(week: int):
    f = _meta_file(week)
    return json.loads(f.read_text()) if f.exists() else None


def write_week(week: int, rows, meta: dict) -> None:
    cols = {"entry": [], "slot": [], "n": [], "team": [], "line": []}
    for name, picks in rows:
        for slot, (n, team, line) in enumerate(picks):
            cols["entry"].append(name); cols["slot"].append(slot); cols["n"].append(n)
            cols["team"].append(team); cols["line"].append(line)
    table = pa.table({"entry": pa.array(cols["entry"]).dictionary_encode(), "slot": pa.array(cols["slot"], pa.int8()),
                      "n": pa.array(cols["n"], pa.int8()), "team": pa.array(cols["team"]).dictionary_encode(),
                      "line": pa.array(cols["line"], pa.float32())})
    pq.write_table(table, _file(week), compression="zstd")
    _meta_file(week).write_text(json.dumps(meta, indent=1, sort_keys=True))


def stored_weeks() -> list[int]:
    return sorted(int(p.stem.split("-")[1]) for p in PICKS.glob("week-*.parquet"))


def load_week(week: int):
    """-> [(entry, [(n, team, line) x5])] in the order printed in the PDF."""
    t = pq.read_table(_file(week)).to_pydict()
    out, cur, picks = [], None, []
    for e, n, team, line in zip(t["entry"], t["n"], t["team"], t["line"]):
        if e != cur:
            if cur is not None:
                out.append((cur, picks))
            cur, picks = e, []
        picks.append((n, team, float(line)))
    if cur is not None:
        out.append((cur, picks))
    return out


# ---- fetching ----------------------------------------------------------------------------------

def _url(week: int, year: int, month: int) -> str:
    return config.PDF_URL.format(year=year, month=month, contest=config.CONTEST, week=week)


def _months_from(start):
    y, m = start
    while (y, m) <= config.PDF_LAST_MONTH:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def check_url(url: str) -> str:
    """Only ever fetch Circa's own upload folder (the URL comes from a cache file, so don't trust it blindly)."""
    if not url.startswith(config.PDF_URL_PREFIX) or ".." in url or not url.endswith(".pdf"):
        raise ValueError(f"refusing to fetch unexpected URL {url!r}")
    return url


def _head(url: str):
    check_url(url)
    for attempt in range(3):
        try:
            r = requests.head(url, headers=config.HEADERS, allow_redirects=False, timeout=30)  # a redirect = not our file
            return r
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def discover(week: int, start_month=None):
    """URL of the week's PDF (probing the month folders), with its HEAD response, or None if unpublished."""
    for y, m in _months_from(start_month or config.PDF_FIRST_MONTH):
        url = _url(week, y, m)
        r = _head(url)
        if r.status_code == 200:
            return url, r
    return None


def _fingerprint(r) -> dict:
    return {"etag": r.headers.get("ETag"), "last_modified": r.headers.get("Last-Modified"),
            "size": int(r.headers.get("Content-Length", 0)) or None}


def _unchanged(meta, fp) -> bool:
    return bool(meta) and meta.get("size") == fp["size"] and meta.get("etag") == fp["etag"] \
        and meta.get("last_modified") == fp["last_modified"]


def _download(url: str, dest: Path) -> str:
    check_url(url)
    h, size = hashlib.sha256(), 0
    with requests.get(url, headers=config.HEADERS, stream=True, allow_redirects=False, timeout=120) as r:
        r.raise_for_status()
        if r.status_code != 200 or int(r.headers.get("Content-Length", 0)) > config.MAX_PDF_BYTES:
            raise ValueError(f"unexpected response for {url}: {r.status_code}, {r.headers.get('Content-Length')} bytes")
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                size += len(chunk)
                if size > config.MAX_PDF_BYTES:
                    raise ValueError(f"{url} exceeds {config.MAX_PDF_BYTES} bytes")
                f.write(chunk); h.update(chunk)
    return h.hexdigest()


def fetch_week(week: int, url: str, head) -> int:
    fp = _fingerprint(head)
    with tempfile.TemporaryDirectory() as d:
        pdf = Path(d) / "selections.pdf"
        digest = _download(url, pdf)
        rows = parse_pdf(pdf)
    if not rows:
        raise ValueError(f"week {week}: parsed 0 entries from {url}")
    write_week(week, rows, {**fp, "url": url, "sha256": digest, "entries": len(rows), "week": week,
                            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return len(rows)


def sync(verbose: bool = True) -> list[int]:
    """Fetch every published week not yet stored (and re-check the newest few for corrected PDFs).
    Weeks are published in order, so stop at the first one that is not out yet."""
    have = stored_weeks()
    newest = max(have, default=0)
    changed, month = [], config.PDF_FIRST_MONTH
    for week in range(1, config.WEEKS + 1):
        meta = read_meta(week) if week in have else None
        try:
            if meta and week <= newest - config.REVALIDATE_LAST:
                continue  # frozen
            if meta:
                url = meta["url"]
                head = _head(url)
                if head.status_code != 200:
                    continue  # PDF moved/removed: keep what we have
            else:
                found = discover(week, month)
                if not found:
                    break
                url, head = found
            month = tuple(int(x) for x in url.split("/uploads/")[1].split("/")[:2])
            if _unchanged(meta, _fingerprint(head)):
                continue
            n = fetch_week(week, url, head)
            changed.append(week)
            if verbose:
                print(f"picks: week {week}: {n} entries from {url}")
        except Exception as e:  # a flaky Circa site must not take down the deploy of cached data
            print(f"picks: week {week}: {type(e).__name__}: {e}")
            if not meta:
                break
    return changed
