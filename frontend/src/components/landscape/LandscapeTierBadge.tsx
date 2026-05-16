import type { QualityTier } from "@/lib/types";

const STYLE: Record<QualityTier, { symbol: string; color: string }> = {
  T1_CURATED: {
    symbol: "★",
    color:
      "bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800",
  },
  T2_STRUCTURED: {
    symbol: "◆",
    color:
      "bg-sky-50 text-sky-800 border-sky-200 dark:bg-sky-950 dark:text-sky-300 dark:border-sky-800",
  },
  T3_EXPLORATORY: {
    symbol: "○",
    color:
      "bg-zinc-100 text-zinc-700 border-zinc-300 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-600",
  },
};

export function LandscapeTierBadge({
  tier,
  label,
  lastCuratedAt,
}: {
  tier: QualityTier;
  label: string;
  lastCuratedAt?: string | null;
}) {
  const style = STYLE[tier];
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-md border px-3 py-1 text-xs ${style.color}`}
      title={lastCuratedAt ? `Last curated ${lastCuratedAt}` : undefined}
    >
      <span aria-hidden>{style.symbol}</span>
      <span className="font-medium">{label}</span>
      {lastCuratedAt && (
        <span className="opacity-70">· {lastCuratedAt}</span>
      )}
    </span>
  );
}
