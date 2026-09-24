import type { ReactNode } from "react";
import { type Domain, pct } from "@/lib/scale";

export type Series = { key: string; name: string; color: string; dashed?: boolean };
export type Estimate = { est: number; lo: number; hi: number };
export type IntervalRow = {
  id: string;
  label: ReactNode;
  aside?: ReactNode;
  detail?: ReactNode;
  /** Plain-text summary: SVG <title> tooltip and accessible name for the row. */
  summary: string;
  values: Record<string, Estimate>;
};

const LANE = 14;
const PAD = 9;

function Legend({ series }: { series: Series[] }) {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted" aria-label="Legend">
      {series.map((s) => (
        <li key={s.key} className="flex items-center gap-2">
          <svg width="22" height="8" aria-hidden>
            <line x1="1" x2="21" y1="4" y2="4" stroke={s.color} strokeWidth="2" strokeLinecap="round"
              strokeDasharray={s.dashed ? "4 3" : undefined} />
          </svg>
          {s.name}
        </li>
      ))}
    </ul>
  );
}

function Strip({ row, series, domain, ticks }: { row: IntervalRow; series: Series[]; domain: Domain; ticks: number[] }) {
  const height = PAD * 2 + LANE * (series.length - 1);
  return (
    <svg width="100%" height={height} className="block overflow-visible" role="img" aria-label={row.summary}>
      <title>{row.summary}</title>
      {ticks.map((t) => (
        <line key={t} x1={pct(t, domain)} x2={pct(t, domain)} y1="0" y2={height}
          stroke={t === 0 ? "var(--zero)" : "var(--grid)"} strokeWidth="1" />
      ))}
      {series.map((s, i) => {
        const v = row.values[s.key];
        if (!v) return null;
        const y = PAD + i * LANE;
        return (
          <g key={s.key}>
            <line x1={pct(v.lo, domain)} x2={pct(v.hi, domain)} y1={y} y2={y} stroke={s.color} strokeWidth="2"
              strokeLinecap="round" strokeDasharray={s.dashed ? "5 3" : undefined} />
            <circle cx={pct(v.est, domain)} cy={y} r="4.5" fill={s.color} stroke="var(--surface)" strokeWidth="2" />
          </g>
        );
      })}
    </svg>
  );
}

function Axis({ domain, ticks, format }: { domain: Domain; ticks: number[]; format: (x: number) => string }) {
  return (
    <svg width="100%" height="18" className="block overflow-visible" aria-hidden>
      {ticks.map((t, i) => (
        <text key={t} x={pct(t, domain)} y="13" fontSize="11" fill="var(--muted)" className="num"
          textAnchor={i === 0 ? "start" : i === ticks.length - 1 ? "end" : "middle"}>
          {format(t)}
        </text>
      ))}
    </svg>
  );
}

export function IntervalChart({
  series,
  rows,
  domain,
  ticks,
  format,
  axisLabel,
  legend = series.length > 1,
}: {
  series: Series[];
  rows: IntervalRow[];
  domain: Domain;
  ticks: number[];
  format: (x: number) => string;
  axisLabel: string;
  legend?: boolean;
}) {
  return (
    <figure className="space-y-3 rounded-lg border border-line bg-surface p-4">
      {legend && <Legend series={series} />}
      <div className="space-y-4">
        {rows.map((row) => (
          <div key={row.id} tabIndex={0} aria-label={row.summary}
            className="rounded-md outline-none focus-visible:ring-2 focus-visible:ring-accent">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
              <span className="font-medium">{row.label}</span>
              {row.aside && <span className="num text-muted">{row.aside}</span>}
            </div>
            {row.detail && <div className="num mt-0.5 text-xs text-muted">{row.detail}</div>}
            <div className="mt-1">
              <Strip row={row} series={series} domain={domain} ticks={ticks} />
            </div>
          </div>
        ))}
      </div>
      <div>
        <Axis domain={domain} ticks={ticks} format={format} />
        <figcaption className="mt-1 text-center text-xs text-muted">{axisLabel}</figcaption>
      </div>
    </figure>
  );
}
