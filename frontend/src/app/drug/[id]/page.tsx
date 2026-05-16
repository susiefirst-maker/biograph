import { notFound } from "next/navigation";

import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { ClaimsList } from "@/components/entity/ClaimsList";
import { EntityHeader } from "@/components/entity/EntityHeader";
import { LessonsPanel } from "@/components/entity/LessonsPanel";
import { MetricsCard } from "@/components/entity/MetricsCard";
import { NarrativePanel } from "@/components/entity/NarrativePanel";
import { TimelineStrip } from "@/components/entity/TimelineStrip";
import { MiniGraph } from "@/components/graph/MiniGraph";
import {
  getDrug,
  getDrugClaims,
  getDrugLessons,
  getDrugTimeline,
  getNeighbors,
} from "@/lib/api";

export default async function DrugPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ lang?: string }>;
}) {
  const { id } = await params;
  const { lang: langParam } = await searchParams;
  const initialLang = langParam === "zh" ? "zh" : "en";
  const envelope = await getDrug(id).catch(() => null);
  if (!envelope) notFound();

  // Additive fetches; failures degrade gracefully rather than 404ing.
  const [claimsRes, lessonsRes, timelineRes, graphRes] = await Promise.all([
    getDrugClaims(id).catch(() => null),
    getDrugLessons(id).catch(() => null),
    getDrugTimeline(id).catch(() => null),
    getNeighbors("drug", id, 1).catch(() => null),
  ]);

  const { data: drug, related } = envelope;
  const targets = (related.targets ?? []).map((t) => ({
    id: String(t.id),
    label: (t.gene_symbol as string | null) ?? (t.approved_name as string | null) ?? null,
    link: String(t.link),
  }));
  const indications = (related.indications ?? []).map((i) => ({
    id: String(i.id),
    label: (i.name as string | null) ?? null,
    link: String(i.link),
  }));
  const biosimilarCount = related.biosimilars?.length ?? 0;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Drugs" },
          { label: drug.generic_name },
        ]}
      />
      <EntityHeader drug={drug} targets={targets} indications={indications} />
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_280px]">
        <div className="space-y-8">
          <NarrativePanel
            initialLang={initialLang}
            tabs={[
              {
                key: "story",
                label: "Story",
                en: drug.discovery_narrative,
                zh: drug.discovery_narrative_zh,
              },
              {
                key: "science",
                label: "Science",
                en: drug.mechanism_of_action,
                zh: drug.mechanism_of_action_zh,
              },
            ]}
          />
          <TimelineStrip events={timelineRes?.data ?? []} />
          <LessonsPanel lessons={lessonsRes?.data ?? []} />
          <ClaimsList claims={claimsRes?.data ?? []} />
        </div>
        <aside className="space-y-6">
          <MetricsCard
            drug={drug}
            indicationCount={indications.length}
            biosimilarCount={biosimilarCount}
          />
          {graphRes && <MiniGraph graph={graphRes.data} />}
        </aside>
      </div>
    </main>
  );
}
