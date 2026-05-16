// Mirrors backend/app/schemas/*.py. Keep in sync when schemas change.

export type UUID = string;

// ── Envelopes ───────────────────────────────────────────────────────

export interface EntityMeta {
  entity_type: string;
  version: number;
  last_verified_at: string | null;
  sources: string[];
  narrative_generated_at: string | null;
  lang_fallback: boolean;
}

export interface EntityEnvelope<T> {
  data: T;
  meta: EntityMeta;
  related: Record<string, Array<Record<string, unknown>>>;
}

export interface ListMeta {
  count: number;
  entity_type: string;
}

export interface ListEnvelope<T> {
  data: T[];
  meta: ListMeta;
  related?: Record<string, Array<Record<string, unknown>>>;
}

export interface ErrorEnvelope {
  error: { code: string; message: string; details: Record<string, unknown> };
}

// ── Entity reads ────────────────────────────────────────────────────

export interface DrugRead {
  id: UUID;
  chembl_id: string | null;
  drugbank_id: string | null;
  generic_name: string;
  brand_names: string[];
  aliases: string[];
  inn: string | null;
  modality: string | null;
  status: string;
  max_phase: string | null;
  first_approval_date: string | null;
  mechanism_of_action: string | null;
  mechanism_of_action_zh: string | null;
  discovery_narrative: string | null;
  discovery_narrative_zh: string | null;
  revenue_peak_usd: number | null;
  revenue_peak_year: number | null;
  cumulative_revenue_usd: number | null;
}

export interface TargetRead {
  id: UUID;
  uniprot_id: string | null;
  ensembl_id: string | null;
  gene_symbol: string | null;
  approved_name: string | null;
  biotype: string | null;
  biology_summary: string | null;
  biology_summary_zh: string | null;
  validation_history: string | null;
  validation_history_zh: string | null;
  competitive_landscape_summary: string | null;
  competitive_landscape_summary_zh: string | null;
  pathway_ids: string[];
  go_molecular_function: string[];
  go_biological_process: string[];
  go_cellular_component: string[];
}

export interface CompanyRead {
  id: UUID;
  sec_cik: string | null;
  name: string;
  ticker: string | null;
  country: string | null;
  founded_date: string | null;
  origin_narrative: string | null;
  origin_narrative_zh: string | null;
  strategic_summary: string | null;
  strategic_summary_zh: string | null;
}

export interface IndicationRead {
  id: UUID;
  efo_id: string | null;
  mesh_id: string | null;
  name: string;
  name_zh: string | null;
  aliases: string[];
  treatment_landscape_summary: string | null;
  treatment_landscape_summary_zh: string | null;
}

// ── Sub-entities ────────────────────────────────────────────────────

export interface EventRead {
  id: UUID;
  event_type: string;
  event_date: string | null;
  headline: string | null;
  significance: string | null;
  description: string | null;
  description_zh: string | null;
  source_url: string | null;
  triggered_by: UUID | null;
}

export type ClaimType =
  | "verified_fact"
  | "attributed_analysis"
  | "prediction"
  | "opinion"
  | "disputed";

export interface ClaimRead {
  id: UUID;
  statement: string;
  language: string;
  claim_type: ClaimType;
  evidence_basis: string | null;
  confidence: string | null;
  article_id: UUID | null;
  entities_mentioned: string[];
}

export interface LessonRead {
  id: UUID;
  title: string;
  title_zh: string | null;
  lesson_type: string;
  pattern: string | null;
  pattern_zh: string | null;
  key_evidence: Record<string, unknown>[];
  limitations: string[];
  applicable_contexts: string[];
  applicable_to_landscapes: string[];
  human_reviewed: boolean;
}

export interface PatentRead {
  id: UUID;
  patent_number: string;
  title: string | null;
  filing_date: string | null;
  expiry_date: string | null;
  source_register: string;
  nda_number: string | null;
  bla_number: string | null;
  uspto_application_number: string | null;
  reference_product_exclusivity_end: string | null;
  litigation_history: string | null;
  litigation_history_zh: string | null;
}

export interface RegulatoryDecisionRead {
  id: UUID;
  jurisdiction: string;
  action_type: string;
  decision_date: string | null;
  application_number: string | null;
  bla_number: string | null;
  nda_number: string | null;
  submission_number: string | null;
  submission_type: string | null;
  review_priority: string | null;
  indication_text: string | null;
  notes: string | null;
  review_documents: string[];
}

export interface DealRead {
  id: UUID;
  deal_type: string;
  headline: string;
  announcement_date: string | null;
  value_usd: number | null;
  acquirer_id: UUID | null;
  target_id: UUID | null;
  description: string | null;
  description_zh: string | null;
  strategic_rationale: string | null;
  strategic_rationale_zh: string | null;
}

// ── Graph ───────────────────────────────────────────────────────────

export interface GraphNode {
  type: string;
  id: UUID;
  label: string | null;
  link: string;
  distance: number;
}

export interface GraphEdge {
  source_type: string;
  source_id: UUID;
  target_type: string;
  target_id: UUID;
  relationship_type: string;
}

export interface GraphData {
  source: GraphNode;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphMeta {
  entity_type: "graph";
  root_type: string;
  depth: number;
  node_count: number;
  edge_count: number;
}

export interface GraphEnvelope {
  data: GraphData;
  meta: GraphMeta;
}

// ── Search ──────────────────────────────────────────────────────────

export interface SearchHit {
  entity_type: string;
  entity_id: UUID;
  display_name: string | null;
  aliases: string[];
  modality: string | null;
  link: string;
}

// ── Landscape ───────────────────────────────────────────────────────

export type QualityTier = "T1_CURATED" | "T2_STRUCTURED" | "T3_EXPLORATORY";

export interface LandscapeMeta {
  entity_type: "landscape";
  slug: string;
  quality_tier: QualityTier;
  tier_label_en: string;
  tier_label_zh: string;
  data_completeness_score: number;
  human_reviewed: boolean;
  last_curated_at: string | null;
  sources: string[];
  lang_fallback: boolean;
}

export type DrugStatus =
  | "approved"
  | "conditional"
  | "phase_3"
  | "phase_2"
  | "phase_1"
  | "discontinued"
  | "failed";

export interface MechanismDrug {
  name: string;
  status: DrugStatus | string;
  company?: string;
  approval_date?: string;
}

export interface MechanismGroup {
  class: string;
  drugs: MechanismDrug[];
}

export interface PipelineByPhase {
  approved?: string[];
  phase_3?: string[];
  phase_2?: string[];
  phase_1?: string[];
  failed?: string[];
}

export interface LandscapeCompany {
  name: string;
  ticker?: string;
  role?: string;
}

export interface LandscapeKeyTrial {
  name: string;
  drug?: string;
  sponsor?: string;
  phase?: string;
  status?: string;
  significance?: string;
}

export interface LandscapeHotTarget {
  gene_symbol: string;
  name?: string;
  rationale?: string;
}

export interface LandscapeLiterature {
  pmid?: string;
  title: string;
  authors?: string;
  journal?: string;
  year?: number;
}

export interface LandscapeArticle {
  title: string;
  source_name: string;
  source_type?: string;
  language: string;
  publish_date?: string;
  url?: string;
}

export interface LandscapeLesson {
  title: string;
  title_zh?: string;
  lesson_type?: string;
  pattern?: string;
  key_evidence?: string[];
  limitations?: string[];
  applicable_contexts?: string[];
  applicable_to_landscapes?: string[];
  human_reviewed?: boolean;
}

export interface LandscapeData {
  slug: string;
  display_name: string;
  efo_id?: string;
  mesh_id?: string;
  disease_overview: string;
  mechanism_map: MechanismGroup[];
  pipeline: PipelineByPhase;
  failed_trials?: string[];
  companies: LandscapeCompany[];
  key_trials: LandscapeKeyTrial[];
  scientific_bottlenecks: string[];
  market_dynamics: string;
  regulatory_context: string;
  hot_targets: LandscapeHotTarget[];
  literature: LandscapeLiterature[];
  articles?: LandscapeArticle[];
  lessons: LandscapeLesson[];
}

export interface LandscapeEnvelope {
  data: LandscapeData;
  meta: LandscapeMeta;
  related: Record<string, Array<Record<string, unknown>>>;
}
