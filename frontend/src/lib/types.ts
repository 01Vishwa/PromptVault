// src/lib/types.ts
// ── Canonical TypeScript types matching backend Pydantic schemas ─────

// ── Types matching backend Pydantic schemas ─────────────────────────

export interface Prompt {
  id: string;
  user_id: string;
  name: string;
  slug: string;
  description: string | null;
  tags: string[];
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  latest_version: number | null;
}

export interface PromptList {
  items: Prompt[];
  total: number;
}

export interface ModelConfig {
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  stop_sequences?: string[];
}

export interface PromptVersion {
  id: string;
  prompt_id: string;
  version_number: number;
  version_hash: string;
  template_text: string;
  system_prompt: string | null;
  variables: string[];
  model_config: ModelConfig | null;
  commit_message: string;
  author_id: string;
  created_at: string;
}

export interface VersionList {
  items: PromptVersion[];
  total: number;
}

export interface VersionDiff {
  from_version: number;
  to_version: number;
  unified_diff: string;
  char_patches: string;
  from_text: string;
  to_text: string;
}

export interface ExecutionResult {
  id: string;
  model_provider: string;
  model_name: string;
  response_text: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  latency_ms: number | null;
  cost_estimate: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface MultiExecutionResponse {
  prompt_version_id: string;
  rendered_prompt: string;
  results: ExecutionResult[];
}

export interface Deployment {
  id: string;
  prompt_id: string;
  prompt_version_id: string;
  environment: string;
  deployed_by: string;
  deployed_at: string;
  is_active: boolean;
  version_number: number | null;
}

export interface DeploymentList {
  items: Deployment[];
  total: number;
}

export interface ServeResponse {
  response: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  latency_ms: number;
}

