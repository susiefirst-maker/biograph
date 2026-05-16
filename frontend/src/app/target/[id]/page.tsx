import { notFound } from "next/navigation";

import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { NarrativePanel } from "@/components/entity/NarrativePanel";
import { RelatedDrugsList } from "@/components/entity/RelatedDrugsList";
import { MiniGraph } from "@/components/graph/MiniGraph";
import { getNeighbors, getTarget, getTargetDrugs } from "@/lib/api";

export default async function TargetPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ lang?: string }>;
}) {
  const { id } = await params;
  const { lang: langParam } = await searchParams;
  const initialLang = langParam === "zh" ? "zh" : "en";
  const envelope = await getTarget(id).catch(() => null);
  if (!envelope) notFound();

  const [drugsRes, graphRes] = await Promise.all([
    getTargetDrugs(id).catch(() => null),
    getNeighbors("target", id, 1).catch(() => null),
  ]);

  const { data: target } = envelope;
  const subtitle = [target.biotype, target.uniprot_id, target.ensembl_id]
    .filter(Boolean)
    .join(" · ");

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Targets" },
          { label: target.gene_symbol ?? "(unknown)" },
        ]}
      />
      <header className="mb-8 border-b border-zinc-200 pb-6 dark:border-zinc-800">
        <h1 className="text-3xl font-semibold tracking-tight">
          {target.gene_symbol ?? "(unknown)"}
        </h1>
        {target.approved_name && (
          <p className="mt-1 text-lg text-zinc-600 dark:text-zinc-400">
            {target.approved_name}
          </p>
        )}
        {subtitle && (
          <p className="mt-2 text-sm text-zinc-500">{subtitle}</p>
        )}
      </header>
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_280px]">
        <div className="space-y-8">
          <NarrativePanel
            initialLang={initialLang}
            tabs={[
              {
                key: "biology",
                label: "Biology",
                en: target.biology_summary,
                zh: target.biology_summary_zh,
              },
              {
                key: "validation",
                label: "Validation",
                en: target.validation_history,
                zh: target.validation_history_zh,
              },
              {
                key: "landscape",
                label: "Competitive landscape",
                en: target.competitive_landscape_summary,
                zh: target.competitive_landscape_summary_zh,
              },
            ]}
          />
          <RelatedDrugsList drugs={drugsRes?.data ?? []} title="Drugs hitting this target" />
        </div>
        <aside className="space-y-6">{graphRes && <MiniGraph graph={graphRes.data} />}</aside>
      </div>
    </main>
  );
}
