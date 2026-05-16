import Link from "next/link";

import { listLandscapes, search } from "@/lib/api";
import type { LandscapeIndexEntry } from "@/lib/api";

export default async function Home() {
  const [featured, landscapes] = await Promise.all([
    fetchFeatured(),
    fetchLandscapes(),
  ]);

  return (
    <main className="mx-auto flex max-w-3xl flex-1 flex-col gap-10 px-6 py-16">
      <div>
        <h1 className="text-4xl font-semibold tracking-tight">BioGraph</h1>
        <p className="mt-3 text-lg text-zinc-600 dark:text-zinc-400">
          Biopharma knowledge compilation. Drugs, targets, companies, and the causal
          stories behind them — in English and 中文.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href="/explore"
            className="inline-block rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium hover:border-blue-500 dark:border-zinc-700 dark:hover:border-blue-400"
          >
            Explore the knowledge graph →
          </Link>
        </div>
      </div>

      {landscapes.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
            Curated landscapes
          </h2>
          <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {landscapes.map((l) => (
              <li key={l.slug}>
                <Link
                  className="block rounded-md border border-zinc-200 px-4 py-3 hover:border-blue-500 dark:border-zinc-800 dark:hover:border-blue-400"
                  href={`/landscape/${l.slug}`}
                >
                  <span className="font-medium">{l.display_name}</span>
                  {l.last_curated_at && (
                    <span className="ml-2 text-xs text-zinc-500">
                      · curated {l.last_curated_at}
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
          Featured drugs
        </h2>
        {featured.length === 0 ? (
          <p className="text-zinc-500">
            Backend unreachable. Run <code className="rounded bg-zinc-100 px-1 py-0.5 text-sm dark:bg-zinc-900">uvicorn app.main:app</code>{" "}
            in the backend directory.
          </p>
        ) : (
          <ul className="space-y-2">
            {featured.map((hit) => (
              <li key={hit.entity_id}>
                <Link
                  className="block rounded-md border border-zinc-200 px-4 py-3 hover:border-blue-500 dark:border-zinc-800 dark:hover:border-blue-400"
                  href={`/drug/${hit.entity_id}`}
                >
                  <span className="font-medium">{hit.display_name}</span>
                  {hit.aliases.length > 0 && (
                    <span className="ml-2 text-sm text-zinc-500">
                      {hit.aliases.slice(0, 3).join(" · ")}
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

async function fetchFeatured() {
  try {
    const res = await search("humira", { type: "drug", limit: 3 });
    return res.data;
  } catch {
    return [];
  }
}

async function fetchLandscapes(): Promise<LandscapeIndexEntry[]> {
  try {
    const res = await listLandscapes();
    return res.data;
  } catch {
    return [];
  }
}
