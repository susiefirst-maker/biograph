import type { DrugRead } from "@/lib/types";

interface Props {
  drug: DrugRead;
  trialCount?: number;
  indicationCount?: number;
  biosimilarCount?: number;
}

export function MetricsCard({ drug, trialCount, indicationCount, biosimilarCount }: Props) {
  const rows: { label: string; value: string | null }[] = [
    {
      label: "Peak revenue",
      value: formatUsd(drug.revenue_peak_usd, drug.revenue_peak_year),
    },
    { label: "Cumulative revenue", value: formatUsd(drug.cumulative_revenue_usd) },
    { label: "Indications", value: indicationCount != null ? String(indicationCount) : null },
    { label: "Clinical trials", value: trialCount != null ? String(trialCount) : null },
    { label: "Biosimilars", value: biosimilarCount != null ? String(biosimilarCount) : null },
  ];

  return (
    <aside className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        Key metrics
      </h2>
      <dl className="space-y-3 text-sm">
        {rows.map((r) => (
          <div key={r.label} className="flex items-baseline justify-between gap-4">
            <dt className="text-zinc-500">{r.label}</dt>
            <dd className="text-right font-medium text-zinc-900 dark:text-zinc-100">
              {r.value ?? <span className="text-zinc-400">—</span>}
            </dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}

function formatUsd(amount: number | null, year?: number | null): string | null {
  if (!amount) return null;
  const b = amount / 1_000_000_000;
  const formatted = b >= 1 ? `$${b.toFixed(1)}B` : `$${(amount / 1_000_000).toFixed(0)}M`;
  return year ? `${formatted} (${year})` : formatted;
}
