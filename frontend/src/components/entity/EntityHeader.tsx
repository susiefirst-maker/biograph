import Link from "next/link";

import type { DrugRead } from "@/lib/types";

interface EntityChip {
  id: string;
  label: string | null;
  link: string;
}

interface Props {
  drug: DrugRead;
  targets: EntityChip[];
  indications: EntityChip[];
}

export function EntityHeader({ drug, targets, indications }: Props) {
  const brand = drug.brand_names?.[0];
  const zh = drug.brand_names?.find((b) => /[\u4e00-\u9fff]/.test(b));
  const display = [drug.generic_name, brand && `(${brand}${zh ? ` / ${zh}` : ""})`]
    .filter(Boolean)
    .join(" ");

  return (
    <header className="border-b border-zinc-200 pb-6 mb-8 dark:border-zinc-800">
      <h1 className="text-3xl font-semibold tracking-tight">{display}</h1>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-zinc-600 dark:text-zinc-400">
        {drug.modality && <span>{drug.modality}</span>}
        {drug.max_phase && (
          <>
            <span aria-hidden>·</span>
            <span>{drug.max_phase}</span>
          </>
        )}
        {drug.status && (
          <>
            <span aria-hidden>·</span>
            <span className="capitalize">{drug.status}</span>
          </>
        )}
        {drug.first_approval_date && (
          <>
            <span aria-hidden>·</span>
            <span>First approval {drug.first_approval_date}</span>
          </>
        )}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {targets.map((t) => (
          <Chip key={t.id} href={`/target/${t.id}`} prefix="Target">
            {t.label ?? t.id.slice(0, 8)}
          </Chip>
        ))}
        {indications.slice(0, 4).map((i) => (
          <Chip key={i.id} href={`/indication/${i.id}`} prefix="Indication">
            {i.label ?? i.id.slice(0, 8)}
          </Chip>
        ))}
        {indications.length > 4 && (
          <span className="text-xs text-zinc-500">+{indications.length - 4} more</span>
        )}
      </div>
    </header>
  );
}

function Chip({
  href,
  prefix,
  children,
}: {
  href: string;
  prefix: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="rounded-full border border-zinc-200 px-3 py-1 text-xs hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900"
    >
      <span className="text-zinc-500">{prefix}:</span>{" "}
      <span className="font-medium">{children}</span>
    </Link>
  );
}
