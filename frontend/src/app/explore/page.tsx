import { KnowledgeGraph } from "@/components/graph/KnowledgeGraph";
import { getNeighbors, search } from "@/lib/api";

const VALID_TYPES = new Set(["drug", "target", "company", "indication"]);

export default async function ExplorePage({
  searchParams,
}: {
  searchParams: Promise<{ type?: string; id?: string }>;
}) {
  const { type, id } = await searchParams;
  const resolved = await resolveRoot(type, id);

  if (!resolved) {
    return (
      <main className="mx-auto max-w-xl px-6 py-16 text-center text-zinc-500">
        <h1 className="text-xl font-semibold">Explore</h1>
        <p className="mt-2">
          No root entity selected and no default available. Use the search bar
          above, then click a result to start exploring.
        </p>
      </main>
    );
  }

  const graphRes = await getNeighbors(resolved.type, resolved.id, 2).catch(
    () => null,
  );
  if (!graphRes) {
    return (
      <main className="mx-auto max-w-xl px-6 py-16 text-center text-zinc-500">
        <p>Failed to load graph. Is the backend reachable?</p>
      </main>
    );
  }

  return <KnowledgeGraph graph={graphRes.data} />;
}

async function resolveRoot(
  type?: string,
  id?: string,
): Promise<{ type: string; id: string } | null> {
  if (type && id && VALID_TYPES.has(type)) {
    return { type, id };
  }
  // Default: Humira (adalimumab) demo entity.
  try {
    const res = await search("adalimumab", { type: "drug", limit: 1 });
    const first = res.data[0];
    if (first) return { type: "drug", id: first.entity_id };
  } catch {
    /* fall through */
  }
  return null;
}
