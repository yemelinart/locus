export type EvidenceClue = {
  kind: "education" | "organization" | "public_work";
  text: string;
};
export type Budget = {
  minutes: number;
  queries: number;
  pages: number;
  rounds: number;
};
export type Brief = {
  name: string;
  aliases: string[];
  expand_names: boolean;
  surname_change: "unknown" | "possible" | "known";
  previous_names: string[];
  output_language: "en" | "ru";
  city: string;
  country: string;
  year_from: number | null;
  year_to: number | null;
  context: string;
  evidence_clues: EvidenceClue[];
  languages: string[];
  include_domains: string[];
  exclude_domains: string[];
  seed_urls: string[];
  freshness: string;
  budget: Budget;
};
export type Settings = {
  model_provider: "lmstudio" | "ollama" | "openai_compatible";
  model_url: string;
  model: string;
  temperature: number;
  top_p: number;
  max_tokens: number;
  context_chars: number;
  model_timeout: number;
  structured_output: boolean;
  inference_mode: "chat" | "qwen_no_thinking" | "lmstudio";
  reasoning: string;
  response_language: "en" | "ru";
  top_k: number;
  min_p: number;
  repeat_penalty: number;
  safesearch: "on" | "moderate" | "off";
  search_region: string;
  search_provider: "direct" | "searxng";
  search_backends: string[];
  searxng_url: string;
  request_timeout: number;
  results_per_query: number;
  domain_delay: number;
};
export type Source = {
  id: string;
  url: string;
  title: string;
  status: string;
  error: string;
  fetched_at: string;
};
export type Fact = { category: string; statement: string; quote: string };
export type Candidate = {
  assessment?: {
    name_compatible?: boolean;
    identity_status?:
      "eligible" | "unresolved" | "conflicting" | "no_constraints";
    identity_checks?: {
      field: string;
      requested: string;
      relation: "supports" | "contradicts" | "unknown";
      quote: string;
      observed: string;
    }[];
    level:
      | "insufficient"
      | "limited"
      | "supported"
      | "strong"
      | "conflicting"
      | "excluded";
    model_reviewed: boolean;
    audit_outdated: boolean;
    checked_facts: (Fact & { index: number })[];
    withheld_count: number;
    note: string;
    note_facts: number[];
    name_quote: string;
    supported: (EvidenceClue & { quote: string })[];
    missing: EvidenceClue[];
    flags: string[];
    excluded: boolean;
    review_outdated: boolean;
    revision: number;
    method: string;
  };
  verification?: { at: string; model: string; revision: number };
  id: string;
  source_id: string;
  status: "unreviewed" | "confirmed" | "rejected";
  value: {
    name: string;
    description: string;
    matches: string[];
    contradictions: string[];
    facts: Fact[];
  };
};
export type Job = {
  activity?: { phase: string; target: string; url: string; at: string };
  revision: number;
  id: string;
  name: string;
  brief: Brief;
  status: string;
  reason: string;
  created_at: string;
  updated_at: string;
  active_seconds: number;
  rounds: number;
  stats: {
    queries: number;
    pages: number;
    sources: number;
    candidates: number;
  };
  settings_snapshot: Partial<Settings>;
};
export type LinkDecision = {
  left_id: string;
  right_id: string;
  status: "confirmed" | "rejected" | "unreviewed";
};
export type Detail = Job & {
  leads?: {
    id: string;
    url: string;
    title: string;
    snippet: string;
    query: string;
    state: string;
    source_id: string | null;
    error: string;
    rank: number;
  }[];
  retryable_model_steps?: number;
  queue?: { search: number; fetch: number; analyze: number; review: number };
  continuation?: {
    blocked_by: string[];
    exhausted: string[];
    pending_steps: number;
  };
  linkage?: {
    proposals: (LinkDecision & {
      from_source: string;
      to_source: string;
      context: string;
      kind: string;
      stale: boolean;
    })[];
    groups: {
      id: string;
      candidate_ids: string[];
      identity_status: string;
      source_count: number;
      source_families: number;
      identity_checks: {
        field: string;
        requested: string;
        relation: string;
        evidence: { source_id: string; quote: string }[];
      }[];
    }[];
  };
  conclusion?: {
    linked_matches?: number;
    unresolved_identity?: number;
    conflicting_identity?: number;
    state: string;
    provisional: boolean;
    promising_ids: string[];
    reviewed_claims: number;
    pending_cards: number;
    conflicting_cards: number;
    confirmed_cards: number;
    read_sources: number;
    unavailable_sources: number;
  };
  revisions: { number: number; at: string; brief: Brief }[];
  search_runs: SearchRun[];
  sources: Source[];
  candidates: Candidate[];
  events: { id: number; at: string; level: string; message: string }[];
  queries: {
    id: string;
    state: string;
    error: string;
    payload: { query: string; language: string; reason: string };
  }[];
};
export type ModelCapability = {
  key: string;
  name: string;
  instances: {
    id: string;
    config: { context_length?: number; parallel?: number };
  }[];
  max_context: number;
  reasoning_options: string[];
  reasoning_default: string | null;
  architecture: string;
};
export type Models = {
  connected: boolean;
  models: string[];
  error: string;
  capabilities?: ModelCapability[];
  capability_error?: string;
  excluded_models?: number;
};
export type SearchEngine = {
  id: string;
  name: string;
  available: boolean;
  kind: string;
};
export type SearchRun = {
  engine: string;
  status: string;
  result_count: number;
  seconds: number;
  at: string;
  error: string;
};
export type NameVariant = { name: string; origin: string; reason: string };
export type Analysis = {
  domains: {
    domain: string;
    read: number;
    unavailable: number;
    candidates: number;
    facts: number;
  }[];
  engines: {
    engine: string;
    attempts: number;
    ok: number;
    failed: number;
    results: number;
    seconds: number;
  }[];
  facts: number;
  confirmed: number;
  unreviewed: number;
  rejected: number;
  clues: string[];
  contradictions: string[];
  failed_sources: number;
  pending_queries: number;
  engine_coverage_known: boolean;
};
