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
import { select } from "d3-selection";
import { zoom, zoomIdentity, type ZoomBehavior } from "d3-zoom";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type { GraphData } from "@/lib/types";

// Native SVG coordinate space. Scales to container via `viewBox`, so the
// graph looks consistent regardless of viewport width.
const VB_W = 1200;
const VB_H = 800;

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
  relationship: string;
}

export function KnowledgeGraph({ graph }: { graph: GraphData }) {
  const router = useRouter();
  const svgRef = useRef<SVGSVGElement>(null);
  const viewportRef = useRef<SVGGElement>(null);
  const simRef = useRef<Simulation<SimNode, SimLink> | null>(null);
  const [, setTick] = useState(0);
  const [selected, setSelected] = useState<SimNode | null>(null);
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const { nodes, links, presentTypes } = useMemo(() => {
    const gidOf = (type: string, id: string) => `${type}:${id}`;
    const rootGid = gidOf(graph.source.type, graph.source.id);

    const simNodes: SimNode[] = graph.nodes.map((n) => ({
      gid: gidOf(n.type, n.id),
      entityId: n.id,
      type: n.type,
      label: n.label,
      link: n.link,
      distance: n.distance,
      ...(gidOf(n.type, n.id) === rootGid
        ? { fx: VB_W / 2, fy: VB_H / 2 }
        : {}),
    }));

    const simLinks: SimLink[] = graph.edges.map((e) => ({
      source: gidOf(e.source_type, e.source_id),
      target: gidOf(e.target_type, e.target_id),
      relationship: e.relationship_type,
    }));

    const types = new Set(simNodes.map((n) => n.type));
    return { nodes: simNodes, links: simLinks, presentTypes: types };
  }, [graph]);

  // Visible set after filter.
  const visibleNodes = useMemo(
    () => nodes.filter((n) => !hidden.has(n.type)),
    [nodes, hidden],
  );
  const visibleIds = useMemo(
    () => new Set(visibleNodes.map((n) => n.gid)),
    [visibleNodes],
  );
  const visibleLinks = useMemo(
    () =>
      links.filter((l) => {
        const s = typeof l.source === "string" ? l.source : l.source.gid;
        const t = typeof l.target === "string" ? l.target : l.target.gid;
        return visibleIds.has(s) && visibleIds.has(t);
      }),
    [links, visibleIds],
  );

  // Force simulation — runs over the full node set so positions stay stable
  // when filters toggle.
  useEffect(() => {
    if (nodes.length === 0) return;
    const sim = forceSimulation<SimNode>(nodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(links)
          .id((d) => d.gid)
          .distance((l) => {
            const s = l.source as SimNode;
            const t = l.target as SimNode;
            return 40 + Math.max(s.distance ?? 0, t.distance ?? 0) * 20;
          })
          .strength(0.5),
      )
      .force("charge", forceManyBody().strength(-220))
      .force("collide", forceCollide().radius(16))
      .force("center", forceCenter(VB_W / 2, VB_H / 2))
      .on("tick", () => setTick((t) => t + 1));
    simRef.current = sim;
    return () => {
      sim.stop();
    };
  }, [nodes, links]);

  // d3-zoom pan/zoom — attach once on mount.
  useEffect(() => {
    if (!svgRef.current || !viewportRef.current) return;
    const svgSel = select(svgRef.current);
    const vp = select(viewportRef.current);
    const behavior: ZoomBehavior<SVGSVGElement, unknown> = zoom<
      SVGSVGElement,
      unknown
    >()
      .scaleExtent([0.25, 4])
      .on("zoom", (e) => {
        vp.attr("transform", e.transform.toString());
      });
    svgSel.call(behavior);
    svgSel.call(behavior.transform, zoomIdentity);
    return () => {
      svgSel.on(".zoom", null);
    };
  }, []);

  const toggleType = useCallback((t: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  }, []);

  const onNodeClick = useCallback(
    (n: SimNode) => {
      if (selected?.gid === n.gid && hasPage(n.type)) {
        router.push(resolvePath(n));
        return;
      }
      setSelected(n);
    },
    [router, selected],
  );

  const recenter = useCallback(
    (n: SimNode) => {
      router.push(`/explore?type=${n.type}&id=${n.entityId}`);
    },
    [router],
  );

  return (
    <div className="relative h-[calc(100vh-64px)] w-full overflow-hidden bg-zinc-50 dark:bg-zinc-950">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        preserveAspectRatio="xMidYMid meet"
        className="h-full w-full cursor-grab active:cursor-grabbing"
        role="img"
        aria-label="Knowledge graph"
      >
        <g ref={viewportRef}>
          <g aria-label="links">
            {visibleLinks.map((l, i) => {
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
                  strokeWidth={1}
                />
              );
            })}
          </g>
          <g aria-label="nodes">
            {visibleNodes.map((n) => {
              if (n.x == null || n.y == null) return null;
              const r = n.distance === 0 ? 14 : n.distance === 1 ? 9 : 6;
              const color = TYPE_COLOR[n.type] ?? "#71717a";
              const isSelected = selected?.gid === n.gid;
              return (
                <g
                  key={n.gid}
                  className="cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    onNodeClick(n);
                  }}
                >
                  <circle
                    cx={n.x}
                    cy={n.y}
                    r={r + (isSelected ? 3 : 0)}
                    fill={color}
                    stroke={isSelected ? "#0f172a" : "white"}
                    strokeWidth={isSelected ? 3 : 1.5}
                    className="dark:stroke-zinc-950"
                  />
                  {n.label && n.distance <= 1 && (
                    <text
                      x={n.x}
                      y={n.y + r + 14}
                      textAnchor="middle"
                      className="pointer-events-none fill-zinc-700 text-[11px] dark:fill-zinc-200"
                    >
                      {truncate(n.label, 20)}
                    </text>
                  )}
                  <title>
                    {n.type}: {n.label ?? n.gid}
                  </title>
                </g>
              );
            })}
          </g>
        </g>
      </svg>

      {/* Filter legend */}
      <div className="absolute right-4 top-4 rounded-md border border-zinc-200 bg-white/95 p-3 text-xs shadow-sm backdrop-blur dark:border-zinc-700 dark:bg-zinc-900/95">
        <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
          Filter
        </h3>
        <ul className="space-y-1">
          {[...presentTypes].sort().map((t) => {
            const isHidden = hidden.has(t);
            return (
              <li key={t}>
                <button
                  type="button"
                  onClick={() => toggleType(t)}
                  className={`flex items-center gap-2 ${
                    isHidden ? "opacity-40" : ""
                  }`}
                >
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: TYPE_COLOR[t] ?? "#71717a" }}
                    aria-hidden
                  />
                  <span>{t.replace(/_/g, " ")}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Selected node panel */}
      {selected && (
        <div className="absolute bottom-4 left-4 max-w-sm rounded-md border border-zinc-200 bg-white/95 p-4 text-sm shadow-sm backdrop-blur dark:border-zinc-700 dark:bg-zinc-900/95">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-zinc-500">
                {selected.type.replace(/_/g, " ")} · distance {selected.distance}
              </p>
              <h3 className="font-semibold">
                {selected.label ?? selected.entityId}
              </h3>
            </div>
            <button
              type="button"
              aria-label="Close"
              onClick={() => setSelected(null)}
              className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
            >
              ×
            </button>
          </div>
          <div className="mt-3 flex gap-2">
            {hasPage(selected.type) ? (
              <button
                type="button"
                onClick={() => router.push(resolvePath(selected))}
                className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-500"
              >
                Open page →
              </button>
            ) : (
              <span className="rounded border border-dashed border-zinc-300 px-3 py-1 text-xs text-zinc-500 dark:border-zinc-700">
                No detail page for this entity type
              </span>
            )}
            <button
              type="button"
              onClick={() => recenter(selected)}
              className="rounded border border-zinc-300 px-3 py-1 text-xs font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
            >
              Re-center
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function truncate(s: string, n: number): string {
  return s.length <= n ? s : s.slice(0, n - 1).trimEnd() + "…";
}

function hasPage(type: string): boolean {
  return ["drug", "target", "company", "indication"].includes(type);
}

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
      return n.link;
  }
}
