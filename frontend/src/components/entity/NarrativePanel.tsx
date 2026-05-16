"use client";

import { useState } from "react";

export interface NarrativeTab {
  key: string;
  label: string;
  en: string | null;
  zh: string | null;
}

export function NarrativePanel({
  tabs,
  initialLang = "en",
}: {
  tabs: NarrativeTab[];
  initialLang?: "en" | "zh";
}) {
  const [activeKey, setActiveKey] = useState(tabs[0]?.key ?? "");
  const [lang, setLang] = useState<"en" | "zh">(initialLang);

  if (tabs.length === 0) return null;

  const active = tabs.find((t) => t.key === activeKey) ?? tabs[0];
  const body = lang === "zh" ? active.zh ?? active.en : active.en;

  return (
    <section className="rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800">
        <nav className="flex" aria-label="Narrative sections">
          {tabs.map((t) => {
            const isActive = t.key === active.key;
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => setActiveKey(t.key)}
                className={`px-4 py-3 text-sm font-medium ${
                  isActive
                    ? "border-b-2 border-blue-600 text-zinc-900 dark:text-zinc-100"
                    : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </nav>
        <div className="flex gap-1 px-3">
          {(["en", "zh"] as const).map((code) => (
            <button
              key={code}
              type="button"
              onClick={() => setLang(code)}
              className={`rounded px-2 py-1 text-xs ${
                code === lang
                  ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                  : "text-zinc-500"
              }`}
            >
              {code.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
      <article className="whitespace-pre-wrap px-6 py-5 text-[15px] leading-7 text-zinc-700 dark:text-zinc-300">
        {body ?? (
          <span className="italic text-zinc-400">
            No {lang.toUpperCase()} narrative available for this section yet.
          </span>
        )}
      </article>
    </section>
  );
}
