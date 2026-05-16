import Link from "next/link";

import { search } from "@/lib/api";
import type { SearchHit } from "@/lib/types";

const FACETS: { type: string; label: string }[] = [
  { type: "", label: "All" },
  { type: "landscape", label: "Landscapes" },
  { type: "drug", label: "Drugs" },
  { type: "target", label: "Targets" },
  { type: "company", label: "Companies" },
  { type: "indication", label: "Indications" },
];

const GROUP_ORDER = ["landscape", "drug", "target", "company", "indication"];
const GROUP_LABEL: Record<string, string> = {
  landscape: "Landscapes",
  drug: "Drugs",
  target: "Targets",
  company: "Companies",
  indication: "Indications",
};

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; type?: string }>;
}) {
  const { q = "", type = "" } = await searchParams;
  const hits = q.trim() ? await runSearch(q, type) : [];
  const grouped = groupHits(hits);

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">
          {q ? <>Results for “{q}”</> : "Search"}
        </h1>
        {q && (
          <p className="mt-1 text-sm text-zinc-500">
            {hits.length} {hits.length === 1 ? "match" : "matches"}
            {type && ` in ${type}s`}
          </p>
        )}
      </header>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[180px_1fr]">
        <aside>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
            Filter
          </h2>
          <ul className="space-y-1 text-sm">
            {FACETS.map((f) => {
              const href = buildHref(q, f.type);
              const isActive = (f.type || "") === (type || "");
              return (
                <li key={f.type || "all"}>
                  <Link
                    href={href}
                    className={`block rounded px-2 py-1 ${
                      isActive
                        ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                        : "hover:bg-zinc-100 dark:hover:bg-zinc-900"
                    }`}
                  >
                    {f.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </aside>

        <div>
          {q.trim() === "" ? (
            <p className="text-sm text-zinc-500">
              Type a query in the header search bar.
            </p>
          ) : hits.length === 0 ? (
            <p className="text-sm text-zinc-500">No matches for “{q}”.</p>
          ) : (
            <div className="space-y-6">
              {grouped.map(({ type: t, items }) => (
                <section key={t}>
                  <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    {GROUP_LABEL[t] ?? t} ({items.length})
                  </h2>
                  <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
                    {items.map((hit) => (
                      <li key={`${hit.entity_type}:${hit.entity_id}`}>
                        <Link
                          href={hitPath(hit)}
                          className="flex items-baseline justify-between gap-3 py-3 hover:bg-zinc-50 dark:hover:bg-zinc-900"
                        >
                          <span className="font-medium">{hit.display_name}</span>
                          {hit.aliases.length > 0 && (
                            <span className="truncate text-right text-xs text-zinc-500">
                              {hit.aliases.slice(0, 3).join(" · ")}
                            </span>
                          )}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

async function runSearch(q: string, type: string): Promise<SearchHit[]> {
  try {
    const res = await search(q, { type: type || undefined, limit: 50 });
    return res.data;
  } catch {
    return [];
  }
}

function groupHits(hits: SearchHit[]): { type: string; items: SearchHit[] }[] {
  const map = new Map<string, SearchHit[]>();
  for (const h of hits) {
    if (!map.has(h.entity_type)) map.set(h.entity_type, []);
    map.get(h.entity_type)!.push(h);
  }
  return GROUP_ORDER.filter((t) => map.has(t)).map((type) => ({
    type,
    items: map.get(type)!,
  }));
}

function buildHref(q: string, type: string): string {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (type) params.set("type", type);
  return `/search?${params}`;
}

function hitPath(hit: SearchHit): string {
  switch (hit.entity_type) {
    case "drug":
      return `/drug/${hit.entity_id}`;
    case "target":
      return `/target/${hit.entity_id}`;
    case "company":
      return `/company/${hit.entity_id}`;
    case "indication":
      return `/indication/${hit.entity_id}`;
    case "landscape":
      return `/landscape/${hit.entity_id}`;
    default:
      return hit.link;
  }
}
