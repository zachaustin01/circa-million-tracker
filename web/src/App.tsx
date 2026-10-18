import { Fragment, useEffect, useMemo, useState } from "react";
import { fetchEntries, fetchGames, fetchPicks, fetchRoot } from "./api";
import { TALLY, indexGames, points, selection, tallyWeek } from "./scoring";
import type { Game, RootIndex, WeekPicks } from "./types";

type Tab = "leaderboard" | "games";
const PAGE = 100;
const fmtLine = (l: number) => (l > 0 ? "+" : l < 0 ? "−" : "") + (l === 0 ? "PK" : String(Math.abs(l)).replace(".5", "½").replace(/^0½$/, "½"));
const fmtPts = (p: number) => (Number.isInteger(p) ? String(p) : p.toFixed(1));
const fmtTime = (iso: string) => new Date(iso).toLocaleString([], { weekday: "short", hour: "numeric", minute: "2-digit" });

function useStored<T>(key: string, init: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(() => {
    try { const s = localStorage.getItem(key); return s ? (JSON.parse(s) as T) : init; } catch { return init; }
  });
  return [v, (n: T) => { setV(n); try { localStorage.setItem(key, JSON.stringify(n)); } catch { /* private mode */ } }];
}

export default function App() {
  const [root, setRoot] = useState<RootIndex | null>(null);
  const [names, setNames] = useState<string[]>([]);
  const [games, setGames] = useState<Record<number, Game[]>>({});
  const [picks, setPicks] = useState<Record<number, WeekPicks>>({});
  const [err, setErr] = useState("");
  const [tab, setTab] = useState<Tab>("leaderboard");
  const [week, setWeek] = useState<number | null>(null);
  const [quarter, setQuarter] = useState(0);            // 0 = full season, 1..4
  const [search, setSearch] = useState("");
  const [favs, setFavs] = useStored<string[]>("circa-favs", []);
  const [favOnly, setFavOnly] = useState(false);
  const [live, setLive] = useStored("circa-live", true);
  const [page, setPage] = useState(0);
  const [open, setOpen] = useState<Set<number>>(new Set());

  useEffect(() => {
    Promise.all([fetchRoot(), fetchEntries()]).then(([r, n]) => { setRoot(r); setNames(n); setWeek(r.current_week); }, e => setErr(String(e)));
  }, []);

  // load every week up to the selected one (standings are cumulative)
  useEffect(() => {
    if (!root || week == null) return;
    for (let w = 1; w <= week; w++) {
      if (picks[w]) continue;
      Promise.all([fetchGames(w), fetchPicks(w)]).then(([g, p]) => {
        setGames(s => ({ ...s, [w]: g })); setPicks(s => ({ ...s, [w]: p }));
      }, e => setErr(String(e)));
    }
  }, [root, week]);  // eslint-disable-line react-hooks/exhaustive-deps

  // refresh the current week's scores while games are in progress
  const inProgress = week != null && games[week]?.some(g => g.state === "in");
  useEffect(() => {
    if (!inProgress || week == null) return;
    const t = setInterval(() => fetchGames(week).then(g => setGames(s => ({ ...s, [week]: g })), () => {}), 60_000);
    return () => clearInterval(t);
  }, [inProgress, week]);

  const loaded = week != null && Array.from({ length: week }, (_, i) => i + 1).every(w => games[w] && picks[w]);

  const tallies = useMemo(() => {
    const m: Record<number, Int8Array> = {};
    for (const w in picks) m[w] = tallyWeek(games[+w], picks[+w], names.length);
    return m;
  }, [games, picks, names.length]);

  const rows = useMemo(() => {
    if (!root || week == null || !loaded) return null;
    const [qa, qb] = quarter ? root.quarters[quarter - 1] : [1, week];
    const weeksIn = (through: number) => { const out = []; for (let w = qa; w <= Math.min(qb, through); w++) out.push(w); return out; };
    const cur = weeksIn(week), prev = weeksIn(week - 1);
    const rank = (ws: number[]) => {
      const pts = new Float32Array(names.length);
      for (const w of ws) { const t = tallies[w]; for (let e = 0; e < names.length; e++) pts[e] += points(t, e * TALLY, live); }
      const order = Array.from(pts.keys()).sort((a, b) => pts[b] - pts[a] || (names[a] < names[b] ? -1 : 1));
      const rk = new Int32Array(names.length), size = new Map<number, number>();
      order.forEach((e, i) => { rk[e] = i && pts[e] === pts[order[i - 1]] ? rk[order[i - 1]] : i + 1; size.set(rk[e], (size.get(rk[e]) ?? 0) + 1); });
      return { pts, order, rk, size };
    };
    const c = rank(cur), p = prev.length ? rank(prev) : null;
    const wk = tallies[week];
    const inWeek = new Set(picks[week].e);
    const out = c.order.filter(e => inWeek.has(e) || cur.some(w => tallies[w][e * TALLY] + tallies[w][e * TALLY + 1] + tallies[w][e * TALLY + 2] > 0)).map(e => {
      let w = 0, l = 0, ps = 0, pend = 0;
      for (const x of cur) { const t = tallies[x], o = e * TALLY; w += t[o] + (live ? t[o + 3] : 0); l += t[o + 1] + (live ? t[o + 4] : 0); ps += t[o + 2] + (live ? t[o + 5] : 0); pend += t[o + 6] + (live ? 0 : t[o + 3] + t[o + 4] + t[o + 5]); }
      return { e, rank: c.rk[e], tie: (c.size.get(c.rk[e]) ?? 1) > 1, prev: p ? p.rk[e] : null, pts: c.pts[e],
        wkPts: points(wk, e * TALLY, live), w, l, p: ps, pend };
    });
    return { rows: out, weeks: cur };
  }, [root, week, quarter, live, loaded, tallies, names, picks]);

  const filtered = useMemo(() => {
    if (!rows) return [];
    const q = search.trim().toLowerCase();
    const fs = new Set(favs);
    return rows.rows.filter(r => (!q || names[r.e].toLowerCase().includes(q)) && (!favOnly || fs.has(names[r.e])));
  }, [rows, search, favOnly, favs, names]);

  useEffect(() => setPage(0), [search, favOnly, week, quarter, live]);

  if (err) return <div className="wrap"><p className="err">Couldn't load data: {err}</p></div>;
  if (!root || week == null) return <div className="wrap"><p className="muted">Loading…</p></div>;

  const pageRows = filtered.slice(page * PAGE, (page + 1) * PAGE);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const wkGames = games[week] ?? [];
  const wkIdx = indexGames(wkGames);
  const wkPicks = picks[week];
  const pickedBy = new Map<string, number>();
  if (wkPicks) for (let i = 0; i < wkPicks.p.length; i++) pickedBy.set(String(wkPicks.p[i]), (pickedBy.get(String(wkPicks.p[i])) ?? 0) + 1);
  const picksOf = (e: number) => { const i = wkPicks?.e.indexOf(e) ?? -1; return i < 0 ? [] : wkPicks.p.slice(i * 5, i * 5 + 5); };
  const toggleFav = (n: string) => setFavs(favs.includes(n) ? favs.filter(x => x !== n) : [...favs, n]);
  const toggleOpen = (e: number) => setOpen(s => { const n = new Set(s); n.has(e) ? n.delete(e) : n.add(e); return n; });

  const chip = (n: number) => {
    const s = selection(wkIdx, n);
    if (!s) return <span className="pick pending">#{n}</span>;
    const cls = s.res ? (s.final ? "" : "live ") + s.res : "pending";
    const score = s.game.state === "pre" ? fmtTime(s.game.kickoff) : `${s.game.away.team} ${s.game.away.score}–${s.game.home.score} ${s.game.home.team}`;
    return <span className={`pick ${cls}`} title={`${score} · ${s.game.detail}`}><b>{s.team}</b> {fmtLine(s.line)}</span>;
  };

  return (
    <div className="wrap">
      <header>
        <h1>Circa Million <span className="muted">{root.contest} · {root.season}</span></h1>
        <p className="muted small">Unofficial fan tracker. Updated {new Date(root.updated).toLocaleString()}{inProgress ? " · games in progress, scores refresh every minute" : ""}.</p>
        <nav>
          <button className={tab === "leaderboard" ? "on" : ""} onClick={() => setTab("leaderboard")}>Leaderboard</button>
          <button className={tab === "games" ? "on" : ""} onClick={() => setTab("games")}>Games</button>
        </nav>
        <div className="controls">
          <label>Week <select value={week} onChange={e => setWeek(+e.target.value)}>
            {root.weeks.map(w => <option key={w.week} value={w.week}>Week {w.week}</option>)}</select></label>
          {tab === "leaderboard" && <>
            <label>Contest <select value={quarter} onChange={e => setQuarter(+e.target.value)}>
              <option value={0}>Full season</option>
              {root.quarters.map(([a, b], i) => <option key={i} value={i + 1}>Q{i + 1} (wks {a}–{b})</option>)}</select></label>
            <input type="search" placeholder="Search entries" value={search} onChange={e => setSearch(e.target.value)} />
            <label className="chk"><input type="checkbox" checked={favOnly} onChange={e => setFavOnly(e.target.checked)} /> ★ only</label>
          </>}
          <label className="chk"><input type="checkbox" checked={live} onChange={e => setLive(e.target.checked)} /> Count games in progress</label>
        </div>
      </header>

      {tab === "leaderboard" && (!rows ? <p className="muted">Loading week data…</p> : rows.weeks.length === 0 ?
        <p className="muted">This quarter hasn't started as of week {week}.</p> : <>
        <p className="muted small">{filtered.length.toLocaleString()} entries · {quarter ? `Q${quarter}` : "season"} points through week {week}</p>
        <div className="scroll"><table>
          <thead><tr><th></th><th>Rank</th><th className="hm">Prev</th><th className="l">Entry</th>
            <th className="hm l" colSpan={5}>Week {week} selections</th><th>Pts</th><th className="hm">Wk</th><th>W-L-P</th><th className="hm">Pending</th></tr></thead>
          <tbody>{pageRows.map(r => {
            const name = names[r.e], isOpen = open.has(r.e), mine = picksOf(r.e);
            const mv = r.prev == null ? 0 : r.prev - r.rank;
            return <Fragment key={r.e}>
              <tr onClick={() => toggleOpen(r.e)} className="row">
                <td><button className={"star" + (favs.includes(name) ? " on" : "")} aria-label="favorite"
                  onClick={ev => { ev.stopPropagation(); toggleFav(name); }}>{favs.includes(name) ? "★" : "☆"}</button></td>
                <td><b>{r.tie ? "T" : ""}{r.rank}</b></td>
                <td className="hm muted">{r.prev == null ? "–" : <>{r.tie ? "" : ""}{r.prev}{mv > 0 && <span className="up"> ▲{mv}</span>}{mv < 0 && <span className="dn"> ▼{-mv}</span>}</>}</td>
                <td className="l name">{name}</td>
                {[0, 1, 2, 3, 4].map(k => <td key={k} className="hm">{mine[k] != null ? chip(mine[k]) : ""}</td>)}
                <td><b>{fmtPts(r.pts)}</b></td><td className="hm">{fmtPts(r.wkPts)}</td>
                <td>{r.w}-{r.l}-{r.p}</td><td className="hm">{r.pend}</td>
              </tr>
              {isOpen && <tr className="picks-row"><td colSpan={13}>{mine.length ? mine.map(n => <span key={n}>{chip(n)} </span>) : <span className="muted">No selections for week {week}</span>}</td></tr>}
            </Fragment>;
          })}</tbody>
        </table></div>
        <div className="pager">
          <button disabled={page === 0} onClick={() => setPage(page - 1)}>‹ Prev</button>
          <span>Page {page + 1} / {pages}</span>
          <button disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>Next ›</button>
        </div></>)}

      {tab === "games" && (!wkPicks ? <p className="muted">Loading…</p> : <div className="games">
        {wkGames.map(g => <div key={g.id} className="game">
          <div className="gh"><span>{g.state === "pre" ? fmtTime(g.kickoff) : g.detail}</span>{g.state === "in" && <span className="livebadge">LIVE</span>}</div>
          {[g.away, g.home].map(s => {
            const sel = s.n != null ? selection(wkIdx, s.n) : null;
            const cnt = s.n != null ? pickedBy.get(String(s.n)) ?? 0 : 0;
            return <div key={s.team} className="side">
              <b>{s.team}</b><span className="muted">{s.line != null ? fmtLine(s.line) : ""}</span>
              <span className="score">{g.state === "pre" ? "" : s.score}</span>
              <span className={"pick " + (sel?.res ? (sel.final ? "" : "live ") + sel.res : "pending")}>{sel?.res ? (g.state === "post" ? { W: "Covers", L: "Doesn't cover", P: "Push" }[sel.res] : { W: "Covering", L: "Not covering", P: "Push" }[sel.res]) : "—"}</span>
              <span className="muted small">{cnt.toLocaleString()} picks ({((cnt / (wkPicks.e.length || 1)) * 100).toFixed(1)}%)</span>
            </div>;
          })}
        </div>)}
        {wkGames.length === 0 && <p className="muted">No games stored for this week yet.</p>}
      </div>)}

      <footer className="muted small">
        Picks are parsed from Circa's published selection PDFs; scores come from ESPN. Win = 1 point, push = ½.
        Not affiliated with Circa Sports. Always check official results.
      </footer>
    </div>
  );
}
