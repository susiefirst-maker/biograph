"use client";

import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type Simulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import type { GraphData } from "@/lib/types";

const TYPE_COLOR: Record<string, string> = {
  drug: "#2563eb",
  target: "#059669",
  company: "#f59e0b",
  indication: "#dc2626",
  clinical_trial: "#0ea5e9",
  regulatory_decision: "#10b981",
  patent: "#6366f1",
  event: "#a855f7",
  claim: "#14b8a6",
  lesson: "#eab308",
  deal: "#f43f5e",
};

const WIDTH = 280;
const HEIGHT = 280;
const MAX_NODES = 30;

interface SimNode extends SimulationNodeDatum {
  gid: string;
  entityId: string;
  type: string;
  label: string | null;
  link: string;
  distance: number;
}

interface SimLink extends SimulationLinkDatum<SimNode> {
  source: string | SimNode;
  target: string | SimNode;
}

export function MiniGraph({ graph }: { graph: GraphData }) {
  const router = useRouter();
  const simRef = useRef<Simulation<SimNode, SimLink> | null>(null);
  const [, setTick] = useState(0);
  const [hovered, setHovered] = useState<SimNode | null>(null);

  // Build a stable node set up-front. Cap total count so the sidebar stays
  // readable; prefer distance-0 (root) and distance-1 over distance-2.
  const { nodes, links } = useMemo(() => {
    const gidOf = (type: string, id: string) => `${type}:${id}`;
    const rootGid = gidOf(graph.source.type, graph.source.id);

    const sorted = [...graph.nodes].sort((a, b) => a.distance - b.distance);
    const capped = sorted.slice(0, MAX_NODES);
    const keep = new Set(capped.map((n) => gidOf(n.type, n.id)));

    const simNodes: SimNode[] = capped.map((n) => ({
      gid: gidOf(n.type, n.id),
      entityId: n.id,
      type: n.type,
      label: n.label,
      link: n.link,
      distance: n.distance,
      // Pin root at center so the graph doesn't drift.
      ...(gidOf(n.type, n.id) === rootGid
        ? { fx: WIDTH / 2, fy: HEIGHT / 2 }
        : {}),
    }));

    const simLinks: SimLink[] = graph.edges
      .map((e) => ({
        source: gidOf(e.source_type, e.source_id),
        target: gidOf(e.target_type, e.target_id),
      }))
      .filter(
        (e) =>
          keep.has(e.source as string) && keep.has(e.target as string),
      );

    return { nodes: simNodes, links: simLinks };
  }, [graph]);

  useEffect(() => {
    if (nodes.length === 0) return;

    const sim = forceSimulation<SimNode>(nodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(links)
          .id((d) => d.gid)
          .distance(34)
          .strength(0.6),
      )
      .force("charge", forceManyBody().strength(-110))
      .force("collide", forceCollide().radius(9))
      .force("center", forceCenter(WIDTH / 2, HEIGHT / 2))
      .on("tick", () => setTick((t) => t + 1));

    simRef.current = sim;
    return () => {
      sim.stop();
    };
  }, [nodes, links]);

  if (nodes.length === 0) {
    return (
      <aside className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
          Neighborhood
        </h2>
        <p className="text-sm text-zinc-500">No graph data.</p>
      </aside>
    );
  }

  return (
    <aside className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
          Neighborhood
        </h2>
        <span className="text-xs text-zinc-400">{graph.nodes.length}</span>
      </div>
      <svg
        role="img"
        aria-label="Immediate neighbors graph"
        width={WIDTH}
        height={HEIGHT}
        className="block"
      >
        <g>
          {links.map((l, i) => {
            const s = l.source as SimNode;
            const t = l.target as SimNode;
            if (s.x == null || t.x == null) return null;
            return (
              <line
                key={i}
                x1={s.x}
                y1={s.y}
                x2={t.x}
                y2={t.y}
                stroke="currentColor"
                className="text-zinc-300 dark:text-zinc-700"
                strokeWidth={0.8}
              />
            );
          })}
        </g>
        <g>
          {nodes.map((n) => {
            if (n.x == null || n.y == null) return null;
            const r = n.distance === 0 ? 8 : 5;
            const color = TYPE_COLOR[n.type] ?? "#71717a";
            return (
              <g
                key={n.gid}
                className="cursor-pointer"
                onClick={() => router.push(resolvePath(n))}
                onMouseEnter={() => setHovered(n)}
                onMouseLeave={() => setHovered(null)}
              >
                <circle
                  cx={n.x}
                  cy={n.y}
                  r={r}
                  fill={color}
                  stroke="white"
                  strokeWidth={1.5}
                  className="dark:stroke-zinc-950"
                />
                <title>
                  {n.type}: {n.label ?? n.gid}
                </title>
              </g>
            );
          })}
        </g>
      </svg>
      <div className="mt-2 text-xs text-zinc-500 truncate" aria-live="polite">
        {hovered
          ? `${hovered.type} · ${hovered.label ?? hovered.gid}`
          : "Hover for details · click to navigate"}
      </div>
    </aside>
  );
}

// Only certain types have pages today; others fall back to their source entity.
function resolvePath(n: SimNode): string {
  switch (n.type) {
    case "drug":
      return `/drug/${n.entityId}`;
    case "target":
      return `/target/${n.entityId}`;
    case "company":
      return `/company/${n.entityId}`;
    case "indication":
      return `/indication/${n.entityId}`;
    default:
      return n.link; // API URL — backend responds even if no frontend page exists yet
  }
}
