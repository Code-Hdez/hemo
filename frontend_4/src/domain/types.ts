export type ThemePreference = "system" | "light" | "dark";
export type UserRole = "user" | "admin";
export type OnboardingTourStatus = "pending" | "completed" | "skipped";
export type Severity = "info" | "warn" | "danger";
export type LabStatus = "normal" | "low" | "high" | "critical" | "not_evaluable";
export type ResidenceSource = "address" | "pin" | "catalog";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  created_at: string;
  role: UserRole;
  onboarding_tour_status: OnboardingTourStatus;
  onboarding_tour_version: string | null;
  onboarding_tour_dismissed_at: string | null;
}

export interface Pet {
  id: string;
  owner_id: string;
  name: string;
  breed?: string | null;
  birth_year?: number | null;
  sex?: string | null;
  weight_kg?: number | null;
  notes?: string | null;
  residence_zone_code?: string | null;
  residence_label?: string | null;
  residence_lat?: number | null;
  residence_lng?: number | null;
  residence_precision?: string | null;
  residence_consent: boolean;
  created_at: string;
  /** URL consumible por la UI; se deriva de `photo_url` en el mapper de API. */
  image?: string;
  /** URL opaca entregada por el backend para una foto personalizada. */
  photo_url?: string | null;
}

export interface PetInput {
  name: string;
  breed?: string;
  birth_year?: number;
  sex?: "Hembra" | "Macho";
  weight_kg?: number;
  notes?: string;
  residence_zone_code?: string;
  residence_lat?: number;
  residence_lng?: number;
  residence_source?: ResidenceSource;
  residence_consent: boolean;
}

export interface PetProfileExtraction {
  source: "gemini";
  name?: string | null;
  breed?: string | null;
  birth_year?: number | null;
  sex?: "Hembra" | "Macho" | null;
  weight_kg?: number | null;
  notes?: string | null;
  detected_fields: string[];
  warnings: string[];
}

export interface ResidenceZone {
  code: string;
  label: string;
  province: string;
  municipality: string;
  lat: number;
  lng: number;
  precision: string;
}

export interface ResidenceCandidate {
  id: string;
  label: string;
  lat: number;
  lng: number;
  precision: string;
  source: string;
}

export interface NearbyVeterinaryCareRequest {
  pet_id: string;
  radius_meters: number;
}

export interface VeterinaryPlace {
  name: string;
  lat: number;
  lng: number;
  distance_meters: number;
  address: string | null;
  osm_url: string;
}

export interface NearbyVeterinaryCareResponse {
  items: VeterinaryPlace[];
  source: string;
  search_url: string;
  location_precision: string;
  message: string;
}

export interface LabValue {
  name: string;
  label?: string;
  value: string;
  unit: string;
  status: LabStatus;
  ref_min: number | null;
  ref_max: number | null;
  canonical_name?: string | null;
  reference_origin?: string | null;
  status_origin?: string | null;
  derived_status?: LabStatus | null;
  original_name?: string | null;
  original_value?: string | null;
  normalized_unit?: string | null;
  extraction_confidence?: number | null;
  notes?: string | null;
  data_origin?: string | null;
}

export interface Finding {
  label: string;
  detail: string;
  severity: Severity;
  glossary_slug?: string;
}

export interface AnalysisResult {
  id: string;
  prediction_id?: string | null;
  model_version?: string | null;
  policy_version?: string | null;
  schema_version?: string | null;
  status: "success" | "partial_imputation" | "no_prediction";
  imputed_fields: string[];
  extraction_provider?: "gemini" | "local" | "local_fallback" | null;
  extraction_mode?: "auto" | "gemini" | "local" | null;
  extraction_warnings: string[];
  filename: string;
  file_size: number;
  created_at: string;
  confidence: number;
  quality_score: number;
  species: string;
  summary: string;
  diagnoses: string[];
  findings: Finding[];
  qc_flags: string[];
  lab_values: LabValue[];
  pet_id?: string | null;
  pet_name?: string | null;
  residence_zone_code?: string | null;
  residence_label?: string | null;
  persisted: boolean;
}

export interface ExtractionResponse {
  cbc: Record<string, number>;
  fields?: ExtractedCbcField[];
  metadata: Record<string, string | null>;
  comments: string | null;
  extraction_provider: "gemini" | "local" | "local_fallback";
  extraction_mode: "auto" | "gemini" | "local";
  fallback_used: boolean;
  warnings: string[];
}

export interface ExtractedCbcField {
  key: string;
  label: string;
  unit: string;
  value: string;
  detected: boolean;
  required: boolean;
  group: string;
  order: number;
}

export interface EpidemiologyPoint {
  zone_code?: string | null;
  zone_label?: string | null;
  lat: number;
  lng: number;
  finding: string;
  count: number;
  report_count?: number | null;
  pet_count?: number | null;
  intensity_level?: "low" | "moderate" | "high" | null;
  intensity_score?: number | null;
  severity: Severity;
  location_name: string;
}

export interface ChatSource {
  citation_id?: string;
  display_title?: string;
  authors?: string[];
  edition?: string | null;
  chapter?: string | null;
  section?: string | null;
  page_start?: number | null;
  page_end?: number | null;
  source_type?: string;
  /** The source's own language, so a citation backing a Spanish answer can honestly flag it is not Spanish. */
  source_language?: string | null;
  /** Compatibility-only fields from the previous backend response. Never render directly. */
  id?: string;
  source_id?: string;
  title?: string;
  heading_path?: string;
  source_path?: string;
  score?: number;
  reference?: string;
}

export type ChatScope = "general" | "selected_hemogram" | "hemogram_history";
export type ChatResponseScope = ChatScope | "uploaded_analysis" | "historical_analysis";

export interface ChatRequestPayload {
  client_message_id: string;
  conversation_id?: string | null;
  message: string;
  context_scope: ChatScope;
  analysis_id?: string | null;
  pet_id?: string | null;
  expected_context_revision?: number | null;
  options: Record<string, never>;
}

export interface ChatCaseFact {
  parameter: string;
  value: string;
  fact_id?: string | null;
  code?: string | null;
  /** Additive longitudinal evidence fields returned by newer chat backends. */
  analysis_id?: string | null;
  study_key?: string | null;
  study_date?: string | null;
  unit?: string | null;
  status?: "low" | "normal" | "high" | "unknown" | string | null;
  reference_min?: string | number | null;
  reference_max?: string | number | null;
}

export interface ChatResponse {
  request_id?: string;
  conversation_id: string;
  turn_id?: string;
  client_message_id?: string;
  sequence?: number;
  message_id: string;
  answer: string;
  scope: ChatResponseScope;
  sources: ChatSource[];
  case_facts: ChatCaseFact[];
  warnings: string[];
  safety_action: string;
  model?: string | null;
  usage: { prompt_tokens: number; completion_tokens: number };
  duration_ms: number;
  finish_reason: string;
  llm_invoked: boolean;
  response_origin: "llm" | "legacy";
  attempt: number;
  generation_attempts: number;
  stream_mode: "live_validated" | "buffered_validated";
  validation_status: string;
  route_trace?: Record<string, unknown>;
  context?: Record<string, unknown>;
}

export interface ChatProviderAvailability {
  contract_version: "hemovet.availability/v1" | string;
  probe: "provider_availability";
  status: "ready" | "unavailable";
  provider: string;
  model?: string | null;
  ready: boolean;
  code?: string | null;
  retryable: boolean;
  identity_verified?: boolean | null;
}

export interface ChatRagAvailability {
  contract_version: "hemovet.availability/v1" | string;
  probe: "rag_availability";
  status: "ready" | "unavailable";
  required: boolean;
  ready: boolean;
  chroma_ready: boolean;
  collection_ready: boolean;
  index_ready: boolean;
  codes: string[];
}

export interface ChatRuntimeStatus {
  provider: string;
  model?: string | null;
  installed: boolean;
  loaded: boolean;
  digest?: string | null;
  quantization?: string | null;
  gpu_active: boolean | null;
  gpu_memory_bytes: number | null;
  inference_device: string;
  residency_observed: boolean;
  identity_verified: boolean | null;
  identity_error_code: string | null;
}

export interface ChatAvailability {
  contract_version: "hemovet.availability/v1" | string;
  probe: "chat_availability";
  status: "ok" | "degraded" | "fail";
  chat_ready: boolean;
  degraded: boolean;
  module_ready: boolean;
  provider_ready: boolean;
  /** Compatibility alias while older operational clients migrate. */
  llm_ready: boolean;
  rag_required: boolean;
  rag_ready: boolean;
  chroma_ready: boolean;
  collection_ready: boolean;
  codes: string[];
  provider: ChatProviderAvailability;
  rag: ChatRagAvailability;
  rag_enabled: boolean;
  rag_issue: string | null;
  chunk_count: number;
  embedding_model: string;
  index_fingerprint: string;
  runtime: ChatRuntimeStatus;
  runtime_identity_error: string | null;
  gpu_active: boolean | null;
  gpu_memory_bytes: number | null;
  inference_device: string;
  /** Sanitized remote-provider contract (timeouts, retry policy). Never the host, URL or credentials. */
  provider_contract: Record<string, unknown> | null;
}

export type ChatRecoveryAction =
  | "retry_same_turn"
  | "poll_turn"
  | "start_new_conversation"
  | "choose_context"
  | "none";

export interface ChatErrorEnvelope {
  code: string;
  message: string;
  detail: string;
  category:
    | "provider"
    | "timeout"
    | "capacity"
    | "conflict"
    | "validation"
    | "persistence"
    | "transport"
    | "cancellation"
    | "authorization"
    | "unexpected";
  retryable: boolean;
  recovery_action: ChatRecoveryAction;
  request_id: string;
  client_message_id: string;
  conversation_id?: string | null;
  turn_id?: string | null;
  attempt?: number | null;
  retry_after_ms?: number | null;
  http_status: number;
}

export type ChatLegacyTurnStatus =
  | "pending"
  | "processing"
  | "completed"
  | "refused"
  | "failed"
  | "interrupted"
  | "incomplete";

export type ChatTurnState =
  | "pending"
  | "generating"
  | "validating"
  | "repairing"
  | "completed"
  | "failed_retryable"
  | "failed_terminal"
  | "cancelled"
  | "expired";

export interface ChatTurnStatus {
  conversation_id: string;
  turn_id?: string | null;
  client_message_id: string;
  /** Durable legacy status kept for compatibility with persisted turns. */
  status: ChatLegacyTurnStatus;
  /** Canonical public state returned by the current backend. */
  state?: ChatTurnState;
  processing_stage?: string | null;
  /** Compatibility with servers that exposed `stage` before `processing_stage`. */
  stage?: string | null;
  attempt: number;
  retryable: boolean;
  error_code?: string | null;
  response?: ChatResponse | null;
}

export interface ChatConversation {
  id: string;
  mode: string;
  pet_id?: string | null;
  analysis_id?: string | null;
  context_revision: number;
  context_key?: string | null;
  context_token?: string | null;
  study_count?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
  expires_at?: string | null;
}

export interface ChatConversationTurn {
  conversation_id: string;
  turn_id?: string | null;
  client_message_id: string;
  context_revision: number;
  turn_index: number;
  status: ChatLegacyTurnStatus;
  state?: ChatTurnState;
  processing_stage?: string | null;
  stage?: string | null;
  attempt: number;
  retryable: boolean;
  error_code?: string | null;
  user_message: {
    id: string;
    content: string;
    status: string;
    created_at?: string | null;
  };
  response?: ChatResponse | null;
  updated_at?: string | null;
}

export interface ChatConversationTurnPage {
  items: ChatConversationTurn[];
  limit: number;
  offset: number;
}

export interface GlossaryTerm {
  slug: string;
  term: string;
  aliases: string[];
  category: "Serie roja" | "Serie blanca" | "Plaquetas" | "Patrones" | "Calidad";
  short: string;
  explanation: string;
  high?: string;
  low?: string;
  ask_vet: string;
  related: string[];
}

export interface ModelQuality {
  version: string;
  prauc_macro: number;
  labels: Array<{
    name: string;
    pr_auc: number;
    roc_auc: number;
    f1: number;
    ece: number;
    threshold?: number | null;
    status: string;
  }>;
  external_validation: {
    dataset: string;
    n: number;
    coherence_check: string;
    domain_shifts: Array<{ feature: string; d: number; severity: string }>;
  };
  gates: Record<string, string>;
}

export interface LabelActivation {
  labels: Array<{
    name: string;
    rate_idexx: number;
    rate_dap: number;
    threshold?: number | null;
    diagnosis?: string | null;
  }>;
}

export interface TemporalAnalytics {
  timeline: Array<{
    period: string;
    n_analyses: number;
    mean_confidence: number;
    qc_flag_pct: number;
    top_finding: string;
  }>;
  granularity: "week" | "month";
  period_days: number;
}

export interface BreedDistribution {
  breeds: Array<{ name: string; count: number; pct: number }>;
  period_days: number;
  total: number;
}

export interface SurveillanceReport {
  generated_at: string;
  period_days: number;
  cohort_size: number;
  status: "pass" | "warn" | "fail";
  status_counts: Record<string, number>;
  temporal_signals: Array<{
    metric: string;
    value: number;
    baseline?: number | null;
    status: "pass" | "warn" | "fail";
    action: string;
  }>;
  geographic_hotspots: Array<{ location: string; count: number; pct: number }>;
  gate_status: Record<string, string>;
}
