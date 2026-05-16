import type { LandscapeKeyTrial } from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  met_primary: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  ongoing: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
  conditional_failure: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  failed: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300",
};

export function TrialTable({ trials }: { trials: LandscapeKeyTrial[] }) {
  if (!trials?.length) return null;
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        Key clinical trials
      </h2>
      <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
        {trials.map((t) => {
          const style = t.status ? STATUS_STYLE[t.status] : undefined;
          return (
            <li key={t.name} className="py-3">
              <div className="flex items-start justify-between gap-3">
                <h3 className="font-semibold">{t.name}</h3>
                {t.status && (
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${
                      style ?? "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                    }`}
                  >
                    {t.status.replace(/_/g, " ")}
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-xs text-zinc-500">
                {[t.phase?.replace(/_/g, " "), t.sponsor, t.drug]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              {t.significance && (
                <p className="mt-1.5 text-sm text-zinc-700 dark:text-zinc-300">
                  {t.significance}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
