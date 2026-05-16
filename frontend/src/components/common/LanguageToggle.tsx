"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

export function LanguageToggle() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const current = params.get("lang") === "zh" ? "zh" : "en";

  const setLang = (lang: "en" | "zh") => {
    const next = new URLSearchParams(params.toString());
    if (lang === "en") next.delete("lang");
    else next.set("lang", "zh");
    const qs = next.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  };

  return (
    <div className="flex gap-1" role="group" aria-label="Language">
      {(["en", "zh"] as const).map((code) => (
        <button
          key={code}
          type="button"
          onClick={() => setLang(code)}
          className={`rounded px-2 py-1 text-xs ${
            current === code
              ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
              : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
          }`}
          aria-pressed={current === code}
        >
          {code.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
