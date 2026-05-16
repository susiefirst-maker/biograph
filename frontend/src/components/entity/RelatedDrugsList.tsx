import Link from "next/link";

import type { DrugRead } from "@/lib/types";

interface Props {
  drugs: DrugRead[];
  title?: string;
}

export function RelatedDrugsList({ drugs, title = "Drugs" }: Props) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        {title} ({drugs.length})
      </h2>
      {drugs.length === 0 ? (
        <p className="text-sm text-zinc-500">None linked yet.</p>
      ) : (
        <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {drugs.map((d) => (
            <li key={d.id}>
              <Link
                href={`/drug/${d.id}`}
                className="flex items-baseline justify-between gap-3 py-2 hover:bg-zinc-50 dark:hover:bg-zinc-900"
              >
                <span className="font-medium">{d.generic_name}</span>
                <span className="text-xs text-zinc-500">
                  {[d.modality, d.status, d.max_phase].filter(Boolean).join(" · ")}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
