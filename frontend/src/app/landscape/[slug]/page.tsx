import { notFound } from "next/navigation";

import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { BottleneckPanel } from "@/components/landscape/BottleneckPanel";
import { LandscapeTierBadge } from "@/components/landscape/LandscapeTierBadge";
import { MechanismMap } from "@/components/landscape/MechanismMap";
import { PipelineWaterfall } from "@/components/landscape/PipelineWaterfall";
import { RelatedLandscapes } from "@/components/landscape/RelatedLandscapes";
import { TrialTable } from "@/components/landscape/TrialTable";
import { getLandscape } from "@/lib/api";

interface RelatedLandscapeChip {
  slug: string;
  display_name: string;
  shared_drugs: string[];
  shared_targets: string[];
}

export default async function LandscapePage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ lang?: string }>;
}) {
  const { slug } = await params;
  const { lang: langParam } = await searchParams;
  const lang = langParam === "zh" ? "zh" : "en";
  const envelope = await getLandscape(slug, lang).catch(() => null);
  if (!envelope) notFound();

  const { data, meta } = envelope;
  const totalCompanies = data.companies?.length ?? 0;
  const approvedCount = data.pipeline?.approved?.length ?? 0;
  const activeCount =
    (data.pipeline?.phase_3?.length ?? 0) +
    (data.pipeline?.phase_2?.length ?? 0) +
    (data.pipeline?.phase_1?.length ?? 0);

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Landscapes" },
          { label: data.display_name },
        ]}
      />
      <header className="mb-8 border-b border-zinc-200 pb-6 dark:border-zinc-800">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">
            {data.display_name}
          </h1>
          <LandscapeTierBadge
            tier={meta.quality_tier}
            label={meta.tier_label_en}
            lastCuratedAt={meta.last_curated_at}
          />
        </div>
        <p className="mt-2 text-sm text-zinc-500">
          {activeCount} active · {approvedCount} approved · {totalCompanies} companies
          {meta.data_completeness_score > 0 && (
            <> · completeness {(meta.data_completeness_score * 100).toFixed(0)}%</>
          )}
        </p>
      </header>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_320px]">
        <div className="space-y-8">
          <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
              Disease overview
            </h2>
            <p className="whitespace-pre-wrap text-[15px] leading-7 text-zinc-700 dark:text-zinc-300">
              {data.disease_overview}
            </p>
          </section>

          <PipelineWaterfall pipeline={data.pipeline} />

          <MechanismMap groups={data.mechanism_map} />

          <TrialTable trials={data.key_trials} />

          <BottleneckPanel items={data.scientific_bottlenecks} />

          {data.regulatory_context && (
            <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
                Regulatory context
              </h2>
              <p className="whitespace-pre-wrap text-[15px] leading-7 text-zinc-700 dark:text-zinc-300">
                {data.regulatory_context}
              </p>
            </section>
          )}

          {data.market_dynamics && (
            <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
                Market dynamics
              </h2>
              <p className="whitespace-pre-wrap text-[15px] leading-7 text-zinc-700 dark:text-zinc-300">
                {data.market_dynamics}
              </p>
            </section>
          )}

          {data.lessons?.length > 0 && (
            <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
                Lessons
              </h2>
              <ul className="space-y-4">
                {data.lessons.map((l, i) => (
                  <li
                    key={`${l.title ?? "lesson"}-${i}`}
                    className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800"
                  >
                    <h3 className="font-semibold">{l.title}</h3>
                    {l.lesson_type && (
                      <p className="mt-0.5 text-xs uppercase tracking-wide text-zinc-500">
                        {l.lesson_type.replace(/_/g, " ")}
                      </p>
                    )}
                    {l.pattern && (
                      <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-700 dark:text-zinc-300">
                        {l.pattern}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <RelatedLandscapes
            items={
              (envelope.related?.landscapes as unknown as RelatedLandscapeChip[]) ?? []
            }
          />
        </div>

        <aside className="space-y-6">
          {data.hot_targets?.length > 0 && (
            <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
                Hot targets
              </h2>
              <ul className="space-y-2 text-sm">
                {data.hot_targets.map((t, i) => (
                  <li key={`${t.gene_symbol ?? "target"}-${i}`}>
                    <span className="font-medium">{t.gene_symbol}</span>
                    {t.name && (
                      <span className="text-zinc-500"> · {t.name}</span>
                    )}
                    {t.rationale && (
                      <p className="mt-0.5 text-xs text-zinc-500">
                        {t.rationale}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {data.companies?.length > 0 && (
            <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
                Companies ({data.companies.length})
              </h2>
              <ul className="space-y-2 text-sm">
                {data.companies.map((c, i) => (
                  <li key={`${c.name ?? "company"}-${i}`}>
                    <span className="font-medium">{c.name}</span>
                    {c.ticker && (
                      <span className="text-xs text-zinc-500"> ({c.ticker})</span>
                    )}
                    {c.role && (
                      <p className="mt-0.5 text-xs text-zinc-500">{c.role}</p>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {data.literature?.length > 0 && (
            <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
                Literature
              </h2>
              <ul className="space-y-2 text-sm">
                {data.literature.map((lit, i) => (
                  <li key={`${lit.pmid ?? lit.title ?? "lit"}-${i}`}>
                    <span className="font-medium">{lit.title}</span>
                    <p className="text-xs text-zinc-500">
                      {[lit.authors, lit.journal, lit.year]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </aside>
      </div>
    </main>
  );
}
