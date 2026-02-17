// src/lib/api.ts
// ── Typed API client — all URLs from environment ────────────────────

// frontend/src/lib/api.ts
// API client — calls FastAPI backend with Supabase JWT
import type {
  Deployment,
  DeploymentList,
  MultiExecutionResponse,
  Prompt,
  PromptList,
  PromptVersion,
  VersionDiff,
  VersionList,
} from "./types";
import { createClient } from "./supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function getAuthHeaders(): Promise<HeadersInit> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const h: HeadersInit = { "Content-Type": "application/json" };
  if (session?.access_token) {
    h["Authorization"] = `Bearer ${session.access_token}`;
  }
  return h;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = await getAuthHeaders();
  const url = `${API_BASE}/api/v1${path}`;
  const res = await fetch(url, {
    ...init,
    headers: { ...headers, ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Prompts ──────────────────────────────────────────────────────────

export async function listPrompts(
  search?: string,
  includeArchived = false,
): Promise<PromptList> {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (includeArchived) params.set("include_archived", "true");
  return request<PromptList>(`/prompts?${params}`);
}

export async function getPrompt(promptId: string): Promise<Prompt> {
  return request<Prompt>(`/prompts/${promptId}`);
}

export async function createPrompt(data: {
  name: string;
  slug: string;
  description?: string;
  tags?: string[];
}): Promise<Prompt> {
  return request<Prompt>("/prompts", { method: "POST", body: JSON.stringify(data) });
}

export async function updatePrompt(
  promptId: string,
  data: { name?: string; description?: string; tags?: string[]; is_archived?: boolean },
): Promise<Prompt> {
  return request<Prompt>(`/prompts/${promptId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deletePrompt(promptId: string): Promise<void> {
  return request(`/prompts/${promptId}`, { method: "DELETE" });
}

// ── Versions ─────────────────────────────────────────────────────────

export async function listVersions(promptId: string): Promise<VersionList> {
  return request<VersionList>(`/prompts/${promptId}/versions`);
}

export async function createVersion(
  promptId: string,
  data: {
    template_text: string;
    system_prompt?: string;
    model_config_data?: { temperature?: number; max_tokens?: number; top_p?: number };
    commit_message: string;
  },
): Promise<PromptVersion> {
  return request<PromptVersion>(`/prompts/${promptId}/versions`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function diffVersions(
  promptId: string,
  fromVersion: number,
  toVersion: number,
): Promise<VersionDiff> {
  return request<VersionDiff>(
    `/prompts/${promptId}/versions/${fromVersion}/diff/${toVersion}`,
  );
}

// ── Execute ──────────────────────────────────────────────────────────

export async function executePrompt(data: {
  prompt_version_id: string;
  variables: Record<string, string>;
  providers: string[];
  model_config_override?: Record<string, unknown>;
}): Promise<MultiExecutionResponse> {
  return request<MultiExecutionResponse>("/execute", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ── Deployments ──────────────────────────────────────────────────────

export async function deploy(
  promptId: string,
  data: { prompt_version_id: string; environment?: string },
): Promise<Deployment> {
  return request<Deployment>(`/prompts/${promptId}/deployments`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listDeployments(promptId: string): Promise<DeploymentList> {
  return request<DeploymentList>(`/prompts/${promptId}/deployments`);
}

export async function undeploy(promptId: string, environment: string): Promise<void> {
  return request(`/prompts/${promptId}/deployments/${environment}`, {
    method: "DELETE",
  });
}

