import { useEffect, useRef, useState } from "react";

export interface Series { name: string; ranks: (number | null)[] }   // ranks[i] = rank after week i+1

const COLORS = ["#3b6fd8", "#e5702a", "#1f9d6b", "#c2398f", "#8a6d00", "#7a5cd6", "#d13b3b", "#0f8fa8", "#5f7a1f", "#a0522d"];
const M = { t: 16, r: 12, b: 40, l: 40 };
interface View { wa: number; wb: number; ra: number; rb: number }   // visible week and rank ranges

/** Line chart of rank by week (1st at the top). Pinch, double-tap, ctrl-scroll or +/− to zoom; drag to pan. */
export default function Trend({ series, weeks, moneyPlaces, hidden, onToggle }:
  { series: Series[]; weeks: number; moneyPlaces: number; hidden: string[]; onToggle: (name: string) => void }) {
  const box = useRef<HTMLDivElement>(null);
  const [W, setW] = useState(900);   // render at the container's real width so text stays readable and nothing scrolls
  const [zoom, setZoom] = useState<View | null>(null);
  useEffect(() => {
    const el = box.current; if (!el) return;
    const ro = new ResizeObserver(() => setW(Math.max(240, Math.floor(el.clientWidth))));
    ro.observe(el); setW(Math.max(240, Math.floor(el.clientWidth)));
    return () => ro.disconnect();
  }, []);
  const H = W < 520 ? 320 : 380;
  const shown = series.map((s, k) => ({ s, k })).filter(({ s }) => !hidden.includes(s.name));
  const all = shown.flatMap(({ s }) => s.ranks.filter((r): r is number => r != null));
  const full: View = { wa: 1, wb: Math.max(2, weeks), ra: 1, rb: last(niceTicks(1, Math.max(10, ...all))) };
  const v = zoom ?? full;
  const pw = W - M.l - M.r, ph = H - M.t - M.b;
  const x = (w: number) => M.l + ((w - v.wa) / (v.wb - v.wa)) * pw;
  const y = (r: number) => M.t + ((r - v.ra) / (v.rb - v.ra)) * ph;
  const wAt = (px: number) => v.wa + ((px - M.l) / pw) * (v.wb - v.wa);
  const rAt = (py: number) => v.ra + ((py - M.t) / ph) * (v.rb - v.ra);
  const clamp = (n: number, a: number, b: number) => Math.min(b, Math.max(a, n));

  const apply = (n: View) => {
    const wspan = Math.max(1, n.wb - n.wa), rspan = Math.max(5, n.rb - n.ra);
    let wa = clamp(n.wa, full.wa, full.wb - wspan), ra = clamp(n.ra, full.ra, full.rb - rspan);
    const out = { wa, wb: Math.min(full.wb, wa + wspan), ra, rb: Math.min(full.rb, ra + rspan) };
    setZoom(out.wa <= full.wa && out.wb >= full.wb && out.ra <= full.ra && out.rb >= full.rb ? null : out);
  };
  const scale = (f: number) => {
    const cw = (v.wa + v.wb) / 2, cr = (v.ra + v.rb) / 2, hw = ((v.wb - v.wa) * f) / 2, hr = ((v.rb - v.ra) * f) / 2;
    apply({ wa: cw - hw, wb: cw + hw, ra: cr - hr, rb: cr + hr });
  };

  // Map-style gestures: one pointer pans, two pointers pinch (zoom + pan), ctrl/⌘-wheel or trackpad pinch zooms
  // at the cursor, double-click/tap zooms in at the point. Each move is computed from a snapshot taken when the
  // set of pointers last changed, so it never drifts.
  const ptrs = useRef(new Map<number, { x: number; y: number }>());
  const snap = useRef<{ v: View; mx: number; my: number; dist: number } | null>(null);
  const lastTap = useRef({ t: 0, x: 0, y: 0 });
  const local = (e: { clientX: number; clientY: number }, el: Element) => { const r = el.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  const gesture = () => {
    const ps = [...ptrs.current.values()];
    if (!ps.length) { snap.current = null; return; }
    const mx = ps.reduce((t, p) => t + p.x, 0) / ps.length, my = ps.reduce((t, p) => t + p.y, 0) / ps.length;
    return { mx, my, dist: ps.length > 1 ? Math.hypot(ps[0].x - ps[1].x, ps[0].y - ps[1].y) : 0 };
  };
  // view after scaling the snapshot's span by f so the snapshot point under (sx, sy) lands at pixel (mx, my)
  const place = (sv: View, sx: number, sy: number, mx: number, my: number, f: number): View => {
    const fw = sv.wa + ((sx - M.l) / pw) * (sv.wb - sv.wa), fr = sv.ra + ((sy - M.t) / ph) * (sv.rb - sv.ra);
    const ws = (sv.wb - sv.wa) * f, rs = (sv.rb - sv.ra) * f;
    const wa = fw - ((mx - M.l) / pw) * ws, ra = fr - ((my - M.t) / ph) * rs;
    return { wa, wb: wa + ws, ra, rb: ra + rs };
  };
  const onDown = (e: React.PointerEvent<SVGSVGElement>) => {
    const p = local(e, e.currentTarget);
    if (zoom || e.pointerType === "mouse") e.currentTarget.setPointerCapture(e.pointerId);
    ptrs.current.set(e.pointerId, p);
    const g = gesture()!; snap.current = { v, ...g };
  };
  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    if (!ptrs.current.has(e.pointerId) || !snap.current) return;
    ptrs.current.set(e.pointerId, local(e, e.currentTarget));
    const g = gesture()!, s = snap.current;
    if (!zoom && ptrs.current.size === 1) return;      // nothing to pan at full view; a single finger scrolls the page
    const f = s.dist && g.dist ? s.dist / g.dist : 1;
    apply(place(s.v, s.mx, s.my, g.mx, g.my, f));
  };
  const onUp = (e: React.PointerEvent<SVGSVGElement>) => {
    const p = ptrs.current.get(e.pointerId); ptrs.current.delete(e.pointerId);
    const g = gesture(); snap.current = g ? { v, ...g } : null;
    if (p && e.type === "pointerup" && !ptrs.current.size && snap.current === null) {
      const now = Date.now(), lt = lastTap.current;
      if (now - lt.t < 320 && Math.hypot(p.x - lt.x, p.y - lt.y) < 24) { apply(place(v, p.x, p.y, p.x, p.y, 0.5)); lastTap.current = { t: 0, x: 0, y: 0 }; }
      else lastTap.current = { t: now, x: p.x, y: p.y };
    }
  };
  const svgRef = useRef<SVGSVGElement>(null);
  const vRef = useRef(v); vRef.current = v;
  const applyRef = useRef(apply); applyRef.current = apply;
  useEffect(() => {
    const el = svgRef.current; if (!el) return;
    const wheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;               // plain wheel keeps scrolling the page
      e.preventDefault();
      const p = local(e, el);
      applyRef.current(place(vRef.current, p.x, p.y, p.x, p.y, Math.exp(e.deltaY * 0.01)));
    };
    el.addEventListener("wheel", wheel, { passive: false });
    return () => el.removeEventListener("wheel", wheel);
  });

  const rTicks = niceTicks(v.ra, v.rb);
  const wTicks = Array.from({ length: Math.max(0, Math.floor(v.wb) - Math.ceil(v.wa) + 1) }, (_, i) => Math.ceil(v.wa) + i);
  const rep = (s: string) => s.replace(/[^a-z0-9]/gi, "");
  return <div>
    <div className="zoombar">
      <button onClick={() => scale(0.5)} aria-label="Zoom in" title="Zoom in">+</button>
      <button onClick={() => scale(2)} disabled={!zoom} aria-label="Zoom out" title="Zoom out">−</button>
      {zoom && <button className="reset" onClick={() => setZoom(null)}>Reset</button>}
      <span className="muted small">Pinch or double-tap the chart to zoom, drag to pan (ctrl/⌘ + scroll on desktop).</span>
    </div>
    <div className="scroll trend" ref={box}>
      <svg ref={svgRef} className={zoom ? "zoomed" : ""} width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Leaderboard rank by week"
        onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
        <defs><clipPath id="plot"><rect x={M.l} y={M.t - 6} width={pw} height={ph + 12} /></clipPath></defs>
        {rTicks.map(t => <g key={t}>
          <line x1={M.l} x2={W - M.r} y1={y(t)} y2={y(t)} className="grid" />
          <text x={M.l - 8} y={y(t) + 4} textAnchor="end" className="axis">{t}</text>
        </g>)}
        {moneyPlaces >= v.ra && moneyPlaces <= v.rb && <g>
          <line x1={M.l} x2={W - M.r} y1={y(moneyPlaces)} y2={y(moneyPlaces)} className="money" />
          <text x={W - M.r} y={y(moneyPlaces) - 4} textAnchor="end" className="axis">In the money (top {moneyPlaces})</text>
        </g>}
        {wTicks.map(w => <text key={w} x={x(w)} y={H - 22} textAnchor="middle" className="axis">{w}</text>)}
        <text x={(W + M.l) / 2} y={H - 4} textAnchor="middle" className="axis">Week</text>
        <g clipPath="url(#plot)">
          {shown.map(({ s, k }) => {
            const c = COLORS[k % COLORS.length];
            let d = "", pen = false;
            s.ranks.forEach((r, i) => { if (r == null) { pen = false; return; } d += `${pen ? "L" : "M"}${x(i + 1)},${y(r)}`; pen = true; });
            return <g key={rep(s.name) + k} style={{ color: c }}>
              <path d={d} fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinejoin="round" />
              {s.ranks.map((r, i) => r == null ? null :
                <circle key={i} cx={x(i + 1)} cy={y(r)} r={4} fill="currentColor"><title>{`${s.name} · week ${i + 1}: rank ${r}`}</title></circle>)}
            </g>;
          })}
        </g>
      </svg>
    </div>
    <div className="legend">{series.map((s, k) => {
      const last = [...s.ranks].reverse().find(r => r != null), off = hidden.includes(s.name);
      return <button key={s.name} className={off ? "off" : ""} aria-pressed={!off} onClick={() => onToggle(s.name)}>
        <i style={{ background: COLORS[k % COLORS.length] }} />{s.name}{last != null && <span className="muted"> · {last}</span>}</button>;
    })}</div>
    {shown.length === 0 && <p className="muted small">Tap a name above to add it to the chart.</p>}
  </div>;
}

function niceTicks(lo: number, hi: number): number[] {
  const raw = (hi - lo) / 5 || 1, pow = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map(m => m * pow).find(s => s >= raw) ?? raw;
  const out: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) out.push(t);
  if (lo === 1 && out[0] !== 1) out.unshift(1);
  // the full view tops out at a tick so the axis ends on a round number
  if (lo === 1 && last(out) < hi) out.push(Math.ceil(hi / step) * step);
  return out;
}

const last = (a: number[]) => a[a.length - 1];
