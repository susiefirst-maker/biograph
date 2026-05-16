import type { MechanismGroup } from "@/lib/types";

const STATUS_MARK: Record<string, { symbol: string; className: string; label: string }> = {
  approved: {
    symbol: "✅",
    className: "text-emerald-700 dark:text-emerald-400",
    label: "approved",
  },
  conditional: {
    symbol: "▲",
    className: "text-amber-700 dark:text-amber-400",
    label: "conditional",
  },
  phase_3: {
    symbol: "○",
    className: "text-sky-700 dark:text-sky-400",
    label: "Phase 3",
  },
  phase_2: {
    symbol: "○",
    className: "text-sky-600 dark:text-sky-400",
    label: "Phase 2",
  },
  phase_1: {
    symbol: "○",
    className: "text-sky-500 dark:text-sky-400",
    label: "Phase 1",
  },
  discontinued: {
    symbol: "✗",
    className: "text-zinc-400 dark:text-zinc-500",
    label: "discontinued",
  },
  failed: {
    symbol: "✗",
    className: "text-rose-700 dark:text-rose-400",
    label: "failed",
  },
};

export function MechanismMap({ groups }: { groups: MechanismGroup[] }) {
  if (!groups?.length) return null;
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        Mechanism map
      </h2>
      <ul className="space-y-4">
        {groups.map((g) => (
          <li
            key={g.class}
            className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800"
          >
            <h3 className="mb-2 font-semibold">{g.class}</h3>
            <ul className="space-y-1.5 text-sm">
              {g.drugs.map((d, i) => {
                const mark = STATUS_MARK[d.status] ?? {
                  symbol: "·",
                  className: "text-zinc-500",
                  label: d.status,
                };
                return (
                  <li key={`${d.name}-${i}`} className="flex items-baseline gap-2">
                    <span className={mark.className} aria-hidden>
                      {mark.symbol}
                    </span>
                    <span className="font-medium">{d.name}</span>
                    <span className="text-xs text-zinc-500">
                      {mark.label}
                      {d.company ? ` · ${d.company}` : ""}
                      {d.approval_date ? ` · ${d.approval_date}` : ""}
                    </span>
                  </li>
                );
              })}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}
