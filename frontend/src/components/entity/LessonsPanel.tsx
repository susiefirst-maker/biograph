import { BadgeCheck, Key } from "lucide-react";

import type { LessonRead } from "@/lib/types";

export function LessonsPanel({ lessons }: { lessons: LessonRead[] }) {
  if (lessons.length === 0) {
    return (
      <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
          Lessons
        </h2>
        <p className="text-sm text-zinc-500">No lessons curated yet.</p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        Lessons ({lessons.length})
      </h2>
      <ul className="space-y-4">
        {lessons.map((l) => (
          <li
            key={l.id}
            className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800"
          >
            <div className="flex items-start gap-2">
              <Key className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" aria-hidden />
              <div className="flex-1">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-base font-semibold leading-tight">{l.title}</h3>
                  {l.human_reviewed && (
                    <span
                      className="inline-flex shrink-0 items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                      title="Human reviewed"
                    >
                      <BadgeCheck className="h-3 w-3" />
                      Reviewed
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs uppercase tracking-wide text-zinc-500">
                  {l.lesson_type.replace(/_/g, " ")}
                </p>
                {l.pattern && (
                  <p className="mt-3 whitespace-pre-wrap text-[15px] leading-6 text-zinc-700 dark:text-zinc-300">
                    {l.pattern}
                  </p>
                )}
                {l.limitations.length > 0 && (
                  <details className="mt-3">
                    <summary className="cursor-pointer text-xs font-medium text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300">
                      Limitations ({l.limitations.length})
                    </summary>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-zinc-600 dark:text-zinc-400">
                      {l.limitations.map((note, idx) => (
                        <li key={idx}>{note}</li>
                      ))}
                    </ul>
                  </details>
                )}
                {l.applicable_contexts.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {l.applicable_contexts.map((ctx) => (
                      <span
                        key={ctx}
                        className="rounded-full border border-zinc-200 px-2 py-0.5 text-[11px] text-zinc-600 dark:border-zinc-700 dark:text-zinc-400"
                      >
                        {ctx}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
