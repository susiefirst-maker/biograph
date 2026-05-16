"use client";

import { Search as SearchIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import { search } from "@/lib/api";
import type { SearchHit } from "@/lib/types";

const DEBOUNCE_MS = 200;

const TYPE_LABEL: Record<string, string> = {
  landscape: "Landscapes",
  drug: "Drugs",
  target: "Targets",
  company: "Companies",
  indication: "Indications",
};

const ENTITY_TYPE_ORDER = ["landscape", "drug", "target", "company", "indication"];

export function SearchBar() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Debounced search. Abort in-flight request on new keystroke.
  useEffect(() => {
    if (q.trim().length === 0) {
      setHits([]);
      setLoading(false);
      return;
    }
    const timer = setTimeout(async () => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setLoading(true);
      try {
        const res = await search(q, { limit: 8 });
        if (!ctrl.signal.aborted) {
          setHits(res.data);
          setActiveIndex(0);
        }
      } catch {
        if (!ctrl.signal.aborted) setHits([]);
      } finally {
        if (!ctrl.signal.aborted) setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [q]);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const grouped = useMemo(() => groupHits(hits), [hits]);

  const navigate = useCallback(
    (hit: SearchHit) => {
      setOpen(false);
      setQ("");
      router.push(hitPath(hit));
    },
    [router],
  );

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      setOpen(false);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, Math.max(hits.length - 1, 0)));
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
      return;
    }
    if (e.key === "Enter" && hits[activeIndex]) {
      e.preventDefault();
      navigate(hits[activeIndex]);
    }
  };

  return (
    <div
      ref={containerRef}
      className="relative w-full max-w-md"
      role="search"
    >
      <SearchIcon
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400"
        aria-hidden
      />
      <input
        type="search"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder="Search drugs, targets, companies… (try 'humira' or '修美乐')"
        className="w-full rounded-md border border-zinc-200 bg-white py-2 pl-9 pr-3 text-sm placeholder-zinc-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-zinc-700 dark:bg-zinc-900 dark:placeholder-zinc-500"
        aria-autocomplete="list"
        aria-expanded={open && hits.length > 0}
      />
      {open && q.trim().length > 0 && (
        <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-96 overflow-auto rounded-md border border-zinc-200 bg-white shadow-lg dark:border-zinc-700 dark:bg-zinc-900">
          {loading && hits.length === 0 && (
            <p className="px-3 py-2 text-xs text-zinc-400">Searching…</p>
          )}
          {!loading && hits.length === 0 && (
            <p className="px-3 py-2 text-xs text-zinc-400">No matches.</p>
          )}
          {grouped.map(({ type, items }) => (
            <div key={type}>
              <h3 className="bg-zinc-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:bg-zinc-950">
                {TYPE_LABEL[type] ?? type}
              </h3>
              <ul>
                {items.map((hit) => {
                  const flatIdx = hits.indexOf(hit);
                  const isActive = flatIdx === activeIndex;
                  return (
                    <li key={`${hit.entity_type}:${hit.entity_id}`}>
                      <button
                        type="button"
                        onMouseEnter={() => setActiveIndex(flatIdx)}
                        onClick={() => navigate(hit)}
                        className={`block w-full px-3 py-2 text-left text-sm ${
                          isActive
                            ? "bg-blue-50 dark:bg-blue-950"
                            : "hover:bg-zinc-100 dark:hover:bg-zinc-800"
                        }`}
                      >
                        <span className="font-medium">{hit.display_name}</span>
                        {hit.aliases.length > 0 && (
                          <span className="ml-2 text-xs text-zinc-500">
                            {hit.aliases.slice(0, 2).join(" · ")}
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
          {hits.length > 0 && (
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                router.push(`/search?q=${encodeURIComponent(q)}`);
              }}
              className="block w-full border-t border-zinc-200 bg-zinc-50 px-3 py-2 text-center text-xs font-medium text-blue-600 hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-950 dark:text-blue-400 dark:hover:bg-zinc-800"
            >
              See all results →
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function groupHits(hits: SearchHit[]): { type: string; items: SearchHit[] }[] {
  const map = new Map<string, SearchHit[]>();
  for (const h of hits) {
    if (!map.has(h.entity_type)) map.set(h.entity_type, []);
    map.get(h.entity_type)!.push(h);
  }
  return ENTITY_TYPE_ORDER.filter((t) => map.has(t)).map((type) => ({
    type,
    items: map.get(type)!,
  }));
}

function hitPath(hit: SearchHit): string {
  switch (hit.entity_type) {
    case "drug":
      return `/drug/${hit.entity_id}`;
    case "target":
      return `/target/${hit.entity_id}`;
    case "company":
      return `/company/${hit.entity_id}`;
    case "indication":
      return `/indication/${hit.entity_id}`;
    case "landscape":
      return `/landscape/${hit.entity_id}`;
    default:
      return hit.link;
  }
}
