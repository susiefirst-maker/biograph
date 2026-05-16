import { notFound } from "next/navigation";

import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { DealsList } from "@/components/entity/DealsList";
import { NarrativePanel } from "@/components/entity/NarrativePanel";
import { RelatedDrugsList } from "@/components/entity/RelatedDrugsList";
import { MiniGraph } from "@/components/graph/MiniGraph";
import {
  getCompany,
  getCompanyDeals,
  getCompanyPipeline,
  getNeighbors,
} from "@/lib/api";

export default async function CompanyPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ lang?: string }>;
}) {
  const { id } = await params;
  const { lang: langParam } = await searchParams;
  const initialLang = langParam === "zh" ? "zh" : "en";
  const envelope = await getCompany(id).catch(() => null);
  if (!envelope) notFound();

  const [pipelineRes, dealsRes, graphRes] = await Promise.all([
    getCompanyPipeline(id).catch(() => null),
    getCompanyDeals(id).catch(() => null),
    getNeighbors("company", id, 1).catch(() => null),
  ]);

  const { data: company } = envelope;
  const subtitle = [company.ticker, company.country, company.sec_cik && `CIK ${company.sec_cik}`]
    .filter(Boolean)
    .join(" · ");

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Companies" },
          { label: company.name },
        ]}
      />
      <header className="mb-8 border-b border-zinc-200 pb-6 dark:border-zinc-800">
        <h1 className="text-3xl font-semibold tracking-tight">{company.name}</h1>
        {subtitle && <p className="mt-2 text-sm text-zinc-500">{subtitle}</p>}
      </header>
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_280px]">
        <div className="space-y-8">
          <NarrativePanel
            initialLang={initialLang}
            tabs={[
              {
                key: "origin",
                label: "Origin",
                en: company.origin_narrative,
                zh: company.origin_narrative_zh,
              },
              {
                key: "strategy",
                label: "Strategy",
                en: company.strategic_summary,
                zh: company.strategic_summary_zh,
              },
            ]}
          />
          <RelatedDrugsList drugs={pipelineRes?.data ?? []} title="Pipeline" />
          <DealsList deals={dealsRes?.data ?? []} />
        </div>
        <aside className="space-y-6">{graphRes && <MiniGraph graph={graphRes.data} />}</aside>
      </div>
    </main>
  );
}
