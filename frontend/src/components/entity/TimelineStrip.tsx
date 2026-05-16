"use client";

import { scaleTime } from "d3-scale";
import { useMemo, useState } from "react";

import type { EventRead } from "@/lib/types";

const EVENT_TYPE_COLOR: Record<string, string> = {
  discovery: "#8b5cf6",
  research: "#8b5cf6",
  clinical_trial: "#0ea5e9",
  clinical: "#0ea5e9",
  regulatory: "#10b981",
  approval: "#10b981",
  commercial: "#f59e0b",
  revenue: "#f59e0b",
  corporate: "#f43f5e",
  m_and_a: "#f43f5e",
  spinoff: "#f43f5e",
  patent: "#6366f1",
  ip: "#6366f1",
};

const SIGNIFICANCE_RADIUS: Record<string, number> = {
  landmark: 11,
  major: 8,
  moderate: 6,
  minor: 4,
};

const HEIGHT = 180;
const MARGIN = { top: 20, right: 40, bottom: 50, left: 40 };
const AXIS_Y = HEIGHT - MARGIN.bottom;
const MIN_WIDTH = 960;

export function TimelineStrip({ events }: { events: EventRead[] }) {
  const [selected, setSelected] = useState<EventRead | null>(null);

  const dated = useMemo(
    () =>
      events
        .filter((e): e is EventRead & { event_date: string } => Boolean(e.event_date))
        .sort(
          (a, b) => new Date(a.event_date).getTime() - new Date(b.event_date).getTime(),
        ),
    [events],
  );

  if (dated.length === 0) {
    return (
      <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
          Timeline
        </h2>
        <p className="text-sm text-zinc-500">No dated events yet.</p>
      </section>
    );
  }

  const minDate = new Date(dated[0].event_date);
  const maxDate = new Date(dated[dated.length - 1].event_date);
  // Pad domain by ~2% each side so terminal nodes don't sit on the margin.
  const span = maxDate.getTime() - minDate.getTime() || 31_536_000_000;
  const pad = span * 0.02;
  const paddedMin = new Date(minDate.getTime() - pad);
  const paddedMax = new Date(maxDate.getTime() + pad);

  // Width scales by count to keep labels readable; enforce MIN_WIDTH.
  const width = Math.max(MIN_WIDTH, dated.length * 90);
  const x = scaleTime()
    .domain([paddedMin, paddedMax])
    .range([MARGIN.left, width - MARGIN.right]);

  const byId = new Map(dated.map((e) => [e.id, e]));

  // Year ticks: every 2-3 years depending on span length in years.
  const yearSpan =
    paddedMax.getUTCFullYear() - paddedMin.getUTCFullYear() || 1;
  const yearStep = yearSpan > 30 ? 5 : yearSpan > 15 ? 3 : yearSpan > 6 ? 2 : 1;
  const startYear = Math.ceil(paddedMin.getUTCFullYear() / yearStep) * yearStep;
  const ticks: number[] = [];
  for (let y = startYear; y <= paddedMax.getUTCFullYear(); y += yearStep) {
    ticks.push(y);
  }

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
          Timeline ({dated.length})
        </h2>
        <span className="text-xs text-zinc-400">Click a node for details</span>
      </div>

      <div className="overflow-x-auto">
        <svg
          role="img"
          aria-label="Event timeline"
          width={width}
          height={HEIGHT}
          className="block"
        >
          <defs>
            <marker
              id="arrowhead"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#a1a1aa" />
            </marker>
          </defs>

          {/* Axis */}
          <line
            x1={MARGIN.left}
            x2={width - MARGIN.right}
            y1={AXIS_Y}
            y2={AXIS_Y}
            stroke="currentColor"
            className="text-zinc-300 dark:text-zinc-700"
          />

          {/* Year ticks */}
          {ticks.map((year) => {
            const tx = x(new Date(Date.UTC(year, 0, 1)));
            return (
              <g key={year}>
                <line
                  x1={tx}
                  x2={tx}
                  y1={AXIS_Y}
                  y2={AXIS_Y + 5}
                  stroke="currentColor"
                  className="text-zinc-300 dark:text-zinc-700"
                />
                <text
                  x={tx}
                  y={AXIS_Y + 18}
                  textAnchor="middle"
                  className="fill-zinc-500 text-[11px]"
                >
                  {year}
                </text>
              </g>
            );
          })}

          {/* Causal arrows — render before nodes so nodes sit on top. */}
          {dated.map((event) => {
            if (!event.triggered_by) return null;
            const trigger = byId.get(event.triggered_by);
            if (!trigger) return null;
            const sx = x(new Date(trigger.event_date));
            const tx = x(new Date(event.event_date));
            if (Math.abs(tx - sx) < 4) return null;
            const midX = (sx + tx) / 2;
            const lift = Math.min(40, Math.abs(tx - sx) * 0.35);
            const cy = AXIS_Y - 40 - lift;
            return (
              <path
                key={`arrow-${event.id}`}
                d={`M ${sx} ${AXIS_Y - 14} Q ${midX} ${cy} ${tx} ${AXIS_Y - 14}`}
                stroke="#a1a1aa"
                strokeWidth={1.5}
                strokeDasharray="4 3"
                fill="none"
                markerEnd="url(#arrowhead)"
              />
            );
          })}

          {/* Event nodes */}
          {dated.map((event) => {
            const cx = x(new Date(event.event_date));
            const r = SIGNIFICANCE_RADIUS[event.significance ?? ""] ?? 5;
            const fill = EVENT_TYPE_COLOR[event.event_type] ?? "#71717a";
            const isSelected = selected?.id === event.id;
            return (
              <g
                key={event.id}
                className="cursor-pointer"
                onClick={() => setSelected(isSelected ? null : event)}
              >
                <circle
                  cx={cx}
                  cy={AXIS_Y}
                  r={r + 2}
                  fill="white"
                  className="dark:fill-zinc-950"
                />
                <circle
                  cx={cx}
                  cy={AXIS_Y}
                  r={r}
                  fill={fill}
                  stroke={isSelected ? "#0f172a" : "transparent"}
                  strokeWidth={2}
                  className="dark:stroke-white"
                />
                <title>
                  {event.headline ?? event.event_type} ({event.event_date})
                </title>
                {event.headline && (
                  <text
                    x={cx}
                    y={AXIS_Y - r - 6}
                    textAnchor="middle"
                    className="pointer-events-none fill-zinc-700 text-[11px] dark:fill-zinc-300"
                  >
                    {truncate(event.headline, 24)}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {selected && (
        <article className="mt-4 rounded-md border border-zinc-200 bg-zinc-50 p-4 text-sm dark:border-zinc-800 dark:bg-zinc-900">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold">
                {selected.headline ?? selected.event_type}
              </h3>
              <p className="mt-0.5 text-xs text-zinc-500">
                {selected.event_date} · {selected.event_type}
                {selected.significance ? ` · ${selected.significance}` : ""}
              </p>
            </div>
            <button
              type="button"
              aria-label="Close details"
              onClick={() => setSelected(null)}
              className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
            >
              ×
            </button>
          </div>
          {selected.description && (
            <p className="mt-3 whitespace-pre-wrap leading-6 text-zinc-700 dark:text-zinc-300">
              {selected.description}
            </p>
          )}
          {selected.source_url && (
            <a
              href={selected.source_url}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-block text-xs text-blue-600 underline dark:text-blue-400"
            >
              Source →
            </a>
          )}
        </article>
      )}
    </section>
  );
}

function truncate(s: string, n: number): string {
  return s.length <= n ? s : s.slice(0, n - 1).trimEnd() + "…";
}
