// Backend API client. BIOGRAPH_API_URL points at FastAPI; defaults to
// localhost:8000 for `next dev` against `uvicorn app.main:app`.

import type {
  ClaimRead,
  CompanyRead,
  DealRead,
  DrugRead,
  EntityEnvelope,
  EventRead,
  GraphEnvelope,
  IndicationRead,
  LandscapeEnvelope,
  LessonRead,
  ListEnvelope,
  PatentRead,
  RegulatoryDecisionRead,
  SearchHit,
  TargetRead,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_BIOGRAPH_API_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${path}`);
  }
  return (await res.json()) as T;
}

// Entities
export const getDrug = (id: string) =>
  fetchJson<EntityEnvelope<DrugRead>>(`/api/drugs/${id}`);

export const getTarget = (id: string) =>
  fetchJson<EntityEnvelope<TargetRead>>(`/api/targets/${id}`);

export const getCompany = (id: string) =>
  fetchJson<EntityEnvelope<CompanyRead>>(`/api/companies/${id}`);

export const getIndication = (id: string) =>
  fetchJson<EntityEnvelope<IndicationRead>>(`/api/indications/${id}`);

// Drug sub-resources
export const getDrugTimeline = (id: string) =>
  fetchJson<ListEnvelope<EventRead>>(`/api/drugs/${id}/timeline`);

export const getDrugClaims = (id: string) =>
  fetchJson<ListEnvelope<ClaimRead>>(`/api/drugs/${id}/claims`);

export const getDrugLessons = (id: string) =>
  fetchJson<ListEnvelope<LessonRead>>(`/api/drugs/${id}/lessons`);

export const getDrugPatents = (id: string, register?: string) => {
  const query = register ? `?register=${encodeURIComponent(register)}` : "";
  return fetchJson<ListEnvelope<PatentRead>>(`/api/drugs/${id}/patents${query}`);
};

export const getDrugRegulatoryDecisions = (id: string, jurisdiction?: string) => {
  const query = jurisdiction ? `?jurisdiction=${encodeURIComponent(jurisdiction)}` : "";
  return fetchJson<ListEnvelope<RegulatoryDecisionRead>>(
    `/api/drugs/${id}/regulatory-decisions${query}`,
  );
};

// Peer sub-resources
export const getCompanyPipeline = (id: string) =>
  fetchJson<ListEnvelope<DrugRead>>(`/api/companies/${id}/pipeline`);

export const getCompanyDeals = (id: string) =>
  fetchJson<ListEnvelope<DealRead>>(`/api/companies/${id}/deals`);

export const getTargetDrugs = (id: string) =>
  fetchJson<ListEnvelope<DrugRead>>(`/api/targets/${id}/drugs`);

// Graph
export const getNeighbors = (entityType: string, id: string, depth: 1 | 2 = 1) =>
  fetchJson<GraphEnvelope>(`/api/graph/neighbors/${entityType}/${id}?depth=${depth}`);

// Landscape
export const getLandscape = (slug: string, lang: "en" | "zh" = "en") =>
  fetchJson<LandscapeEnvelope>(`/api/landscape/${encodeURIComponent(slug)}?lang=${lang}`);

export interface LandscapeIndexEntry {
  slug: string;
  display_name: string;
  quality_tier: string;
  last_curated_at: string;
}

export const listLandscapes = () =>
  fetchJson<{ data: LandscapeIndexEntry[]; meta: { count: number } }>(
    "/api/landscape",
  );

// Search
export const search = (q: string, opts?: { type?: string; limit?: number }) => {
  const params = new URLSearchParams({ q });
  if (opts?.type) params.set("type", opts.type);
  if (opts?.limit) params.set("limit", String(opts.limit));
  return fetchJson<ListEnvelope<SearchHit>>(`/api/search?${params}`);
};
