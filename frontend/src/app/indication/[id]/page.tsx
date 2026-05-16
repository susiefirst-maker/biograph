import { notFound } from "next/navigation";

import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { NarrativePanel } from "@/components/entity/NarrativePanel";
import { MiniGraph } from "@/components/graph/MiniGraph";
import { getIndication, getNeighbors } from "@/lib/api";

// Drugs treating this indication aren't on a dedicated sub-endpoint yet —
// we derive them from the graph neighborhood (entity_relationships view).
export default async function IndicationPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ lang?: string }>;
}) {
  const { id } = await params;
  const { lang: langParam } = await searchParams;
  const initialLang = langParam === "zh" ? "zh" : "en";
  const envelope = await getIndication(id).catch(() => null);
  if (!envelope) notFound();

  const graphRes = await getNeighbors("indication", id, 1).catch(() => null);
  const { data: indication } = envelope;

  const subtitle = [indication.efo_id, indication.mesh_id && `MeSH ${indication.mesh_id}`]
    .filter(Boolean)
    .join(" · ");

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Indications" },
          { label: indication.name },
        ]}
      />
      <header className="mb-8 border-b border-zinc-200 pb-6 dark:border-zinc-800">
        <h1 className="text-3xl font-semibold tracking-tight">{indication.name}</h1>
        {indication.name_zh && (
          <p className="mt-1 text-lg text-zinc-600 dark:text-zinc-400">
            {indication.name_zh}
          </p>
        )}
        {subtitle && <p className="mt-2 text-sm text-zinc-500">{subtitle}</p>}
      </header>
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_280px]">
        <div className="space-y-8">
          <NarrativePanel
            initialLang={initialLang}
            tabs={[
              {
                key: "landscape",
                label: "Treatment landscape",
                en: indication.treatment_landscape_summary,
                zh: indication.treatment_landscape_summary_zh,
              },
            ]}
          />
        </div>
        <aside className="space-y-6">{graphRes && <MiniGraph graph={graphRes.data} />}</aside>
      </div>
    </main>
  );
}
