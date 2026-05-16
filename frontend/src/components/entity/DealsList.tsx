import type { DealRead } from "@/lib/types";

export function DealsList({ deals }: { deals: DealRead[] }) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        Deals ({deals.length})
      </h2>
      {deals.length === 0 ? (
        <p className="text-sm text-zinc-500">No deals on file.</p>
      ) : (
        <ul className="space-y-3">
          {deals.map((d) => (
            <li
              key={d.id}
              className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800"
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-sm font-semibold">{d.headline}</h3>
                {d.value_usd != null && (
                  <span className="shrink-0 text-xs text-zinc-500">
                    {formatBillion(d.value_usd)}
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs uppercase tracking-wide text-zinc-500">
                {d.deal_type}
                {d.announcement_date ? ` · ${d.announcement_date}` : ""}
              </p>
              {d.strategic_rationale && (
                <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-700 dark:text-zinc-300">
                  {d.strategic_rationale}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function formatBillion(amount: number): string {
  const b = amount / 1_000_000_000;
  if (b >= 1) return `$${b.toFixed(1)}B`;
  return `$${(amount / 1_000_000).toFixed(0)}M`;
}
