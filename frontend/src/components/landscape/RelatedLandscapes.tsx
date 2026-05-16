import Link from "next/link";

interface Related {
  slug: string;
  display_name: string;
  shared_drugs: string[];
  shared_targets: string[];
}

export function RelatedLandscapes({ items }: { items: Related[] }) {
  if (!items?.length) return null;
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        Related landscapes
      </h2>
      <ul className="space-y-3">
        {items.map((r) => (
          <li key={r.slug}>
            <Link
              href={`/landscape/${r.slug}`}
              className="block rounded-md border border-zinc-200 px-4 py-3 hover:border-blue-500 dark:border-zinc-700 dark:hover:border-blue-400"
            >
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-medium">{r.display_name}</span>
                <span className="text-xs text-zinc-500">
                  {r.shared_drugs.length + r.shared_targets.length} overlaps
                </span>
              </div>
              {(r.shared_drugs.length > 0 || r.shared_targets.length > 0) && (
                <p className="mt-1 text-xs text-zinc-500">
                  {r.shared_drugs.length > 0 && (
                    <>
                      <span className="font-medium">drugs:</span>{" "}
                      {r.shared_drugs.slice(0, 4).join(", ")}
                      {r.shared_drugs.length > 4 && `, +${r.shared_drugs.length - 4}`}
                    </>
                  )}
                  {r.shared_drugs.length > 0 && r.shared_targets.length > 0 && " · "}
                  {r.shared_targets.length > 0 && (
                    <>
                      <span className="font-medium">targets:</span>{" "}
                      {r.shared_targets.slice(0, 4).join(", ")}
                      {r.shared_targets.length > 4 && `, +${r.shared_targets.length - 4}`}
                    </>
                  )}
                </p>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
