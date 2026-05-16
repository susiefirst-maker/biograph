import type { PipelineByPhase } from "@/lib/types";

const PHASES: {
  key: keyof PipelineByPhase;
  label: string;
  barClass: string;
}[] = [
  { key: "approved", label: "Approved", barClass: "bg-emerald-500" },
  { key: "phase_3", label: "Phase 3", barClass: "bg-sky-500" },
  { key: "phase_2", label: "Phase 2", barClass: "bg-sky-400" },
  { key: "phase_1", label: "Phase 1", barClass: "bg-sky-300" },
  { key: "failed", label: "Failed", barClass: "bg-rose-500" },
];

export function PipelineWaterfall({ pipeline }: { pipeline: PipelineByPhase }) {
  const counts = PHASES.map((p) => (pipeline[p.key] || []).length);
  const max = Math.max(1, ...counts);
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        Pipeline waterfall
      </h2>
      <ul className="space-y-2">
        {PHASES.map((p, i) => {
          const items = pipeline[p.key] || [];
          const widthPct = Math.round((counts[i] / max) * 100);
          return (
            <li key={p.key}>
              <div className="flex items-center gap-3">
                <span className="w-20 text-xs font-medium text-zinc-600 dark:text-zinc-400">
                  {p.label}
                </span>
                <div className="flex-1">
                  <div
                    className={`h-5 rounded ${p.barClass}`}
                    style={{ width: `${widthPct}%` }}
                    aria-hidden
                  />
                </div>
                <span className="w-6 text-right text-xs font-medium">
                  {counts[i]}
                </span>
              </div>
              {items.length > 0 && (
                <ul className="ml-24 mt-1 text-xs text-zinc-600 dark:text-zinc-400">
                  {items.slice(0, 6).map((item) => (
                    <li key={item} className="truncate">
                      {item}
                    </li>
                  ))}
                  {items.length > 6 && <li>+{items.length - 6} more</li>}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
