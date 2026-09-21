export type Budget = {
  minutes: number;
  queries: number;
  pages: number;
  rounds: number;
};
export type Brief = {
  name: string;
  aliases: string[];
  city: string;
  country: string;
  year_from: number | null;
  year_to: number | null;
  context: string;
  languages: string[];
  include_domains: string[];
  exclude_domains: string[];
  seed_urls: string[];
  freshness: string;
  budget: Budget;
};
export type Settings = {
  model_url: string;
  model: string;
  temperature: number;
  top_p: number;
  max_tokens: number;
  context_chars: number;
  model_timeout: number;
  structured_output: boolean;
  inference_mode: "chat" | "qwen_no_thinking";
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
export type Detail = Job & {
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
export type Models = { connected: boolean; models: string[]; error: string };
