import Link from "next/link";

export interface Crumb {
  label: string;
  href?: string;
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  if (items.length === 0) return null;
  return (
    <nav aria-label="Breadcrumb" className="mb-4 text-sm text-zinc-500">
      <ol className="flex flex-wrap items-center gap-1.5">
        {items.map((crumb, i) => {
          const isLast = i === items.length - 1;
          return (
            <li key={i} className="flex items-center gap-1.5">
              {crumb.href && !isLast ? (
                <Link
                  href={crumb.href}
                  className="hover:text-zinc-700 dark:hover:text-zinc-200"
                >
                  {crumb.label}
                </Link>
              ) : (
                <span
                  className={isLast ? "font-medium text-zinc-700 dark:text-zinc-200" : ""}
                  aria-current={isLast ? "page" : undefined}
                >
                  {crumb.label}
                </span>
              )}
              {!isLast && <span aria-hidden className="text-zinc-300 dark:text-zinc-700">/</span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
