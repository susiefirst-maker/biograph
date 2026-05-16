import { AlertTriangle, CheckCircle2, MessageSquare, Sparkles, TrendingUp } from "lucide-react";

import type { ClaimRead, ClaimType } from "@/lib/types";

const BADGE: Record<
  ClaimType,
  { label: string; icon: React.ComponentType<{ className?: string }>; className: string }
> = {
  verified_fact: {
    label: "Verified",
    icon: CheckCircle2,
    className: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  },
  attributed_analysis: {
    label: "Analysis",
    icon: TrendingUp,
    className: "bg-sky-50 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  },
  prediction: {
    label: "Prediction",
    icon: Sparkles,
    className: "bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  },
  opinion: {
    label: "Opinion",
    icon: MessageSquare,
    className: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  },
  disputed: {
    label: "Disputed",
    icon: AlertTriangle,
    className: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  },
};

export function ClaimsList({ claims }: { claims: ClaimRead[] }) {
  if (claims.length === 0) {
    return (
      <Section title="Claims">
        <p className="text-sm text-zinc-500">No claims curated yet.</p>
      </Section>
    );
  }

  return (
    <Section title={`Claims (${claims.length})`}>
      <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
        {claims.map((c) => {
          const badge = BADGE[c.claim_type] ?? BADGE.opinion;
          const Icon = badge.icon;
          return (
            <li key={c.id} className="py-4 first:pt-0 last:pb-0">
              <div className="flex items-start gap-3">
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${badge.className}`}
                >
                  <Icon className="h-3 w-3" />
                  {badge.label}
                </span>
                {c.confidence && (
                  <span className="text-xs uppercase text-zinc-400">
                    {c.confidence}
                  </span>
                )}
              </div>
              <p
                className="mt-2 text-[15px] leading-6 text-zinc-700 dark:text-zinc-300"
                lang={c.language}
              >
                {c.statement}
              </p>
              {c.evidence_basis && (
                <p className="mt-1 text-xs text-zinc-500">
                  Evidence: {c.evidence_basis}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </Section>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        {title}
      </h2>
      {children}
    </section>
  );
}
