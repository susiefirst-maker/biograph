"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

const STORAGE_KEY = "biograph.theme";

function readInitial(): Theme {
  if (typeof window === "undefined") return "light";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function apply(theme: Theme) {
  const root = document.documentElement;
  if (theme === "dark") root.classList.add("dark");
  else root.classList.remove("dark");
  root.style.colorScheme = theme;
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const initial = readInitial();
    setTheme(initial);
    apply(initial);
    setMounted(true);
  }, []);

  const setAndPersist = (next: Theme) => {
    setTheme(next);
    apply(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  };

  return (
    <div className="flex gap-1" role="group" aria-label="Theme">
      {(["light", "dark"] as const).map((code) => (
        <button
          key={code}
          type="button"
          onClick={() => setAndPersist(code)}
          className={`rounded px-2 py-1 text-xs ${
            mounted && theme === code
              ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
              : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
          }`}
          aria-pressed={mounted && theme === code}
        >
          {code === "light" ? "Light" : "Dark"}
        </button>
      ))}
    </div>
  );
}
