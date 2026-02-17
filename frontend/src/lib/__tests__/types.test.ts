// src/lib/__tests__/types.test.ts
// Compile-time type-safety tests — these just verify the shapes don't drift
import { describe, it, expect } from "vitest";
import type {
  Prompt,
  PromptList,
  PromptVersion,
  VersionList,
  VersionDiff,
  ModelConfig,
  ExecutionResult,
  MultiExecutionResponse,
  Deployment,
  DeploymentList,
  ServeResponse,
} from "@/lib/types";

describe("TypeScript type shapes", () => {
  it("Prompt has all expected fields", () => {
    const p: Prompt = {
      id: "1",
      user_id: "u1",
      name: "Test",
      slug: "test",
      description: null,
      tags: ["a"],
      is_archived: false,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
      latest_version: 3,
    };
    expect(p.id).toBe("1");
    expect(p.latest_version).toBe(3);
  });

  it("PromptVersion allows null model_config", () => {
    const v: PromptVersion = {
      id: "v1",
      prompt_id: "p1",
      version_number: 1,
      version_hash: "abc123",
      template_text: "Hello {{name}}",
      system_prompt: null,
      variables: ["name"],
      model_config: null,
      commit_message: "init",
      author_id: "u1",
      created_at: "2025-01-01T00:00:00Z",
    };
    expect(v.model_config).toBeNull();
  });

  it("ModelConfig fields are all optional", () => {
    const empty: ModelConfig = {};
    const full: ModelConfig = {
      temperature: 0.7,
      max_tokens: 1024,
      top_p: 0.9,
      stop_sequences: ["END"],
    };
    expect(empty).toEqual({});
    expect(full.temperature).toBe(0.7);
  });

  it("VersionDiff has diff fields", () => {
    const d: VersionDiff = {
      from_version: 1,
      to_version: 2,
      unified_diff: "--- a\n+++ b",
      char_patches: "",
      from_text: "a",
      to_text: "b",
    };
    expect(d.from_version).toBe(1);
  });

  it("ExecutionResult captures LLM output", () => {
    const r: ExecutionResult = {
      id: "e1",
      model_provider: "openai",
      model_name: "gpt-4o-mini",
      response_text: "Hello!",
      tokens_in: 10,
      tokens_out: 5,
      latency_ms: 200,
      cost_estimate: 0.0001,
      status: "success",
      error_message: null,
      created_at: "2025-01-01T00:00:00Z",
    };
    expect(r.status).toBe("success");
  });

  it("Deployment tracks environment and active state", () => {
    const d: Deployment = {
      id: "d1",
      prompt_id: "p1",
      prompt_version_id: "v1",
      environment: "production",
      deployed_by: "user1",
      deployed_at: "2025-01-01T00:00:00Z",
      is_active: true,
      version_number: 3,
    };
    expect(d.is_active).toBe(true);
    expect(d.environment).toBe("production");
  });

  it("Lists wrap items with total", () => {
    const pl: PromptList = { items: [], total: 0 };
    const vl: VersionList = { items: [], total: 0 };
    const dl: DeploymentList = { items: [], total: 0 };
    expect(pl.total).toBe(0);
    expect(vl.items).toEqual([]);
    expect(dl.items).toEqual([]);
  });

  it("ServeResponse has expected shape", () => {
    const s: ServeResponse = {
      response: "Generated text",
      model: "gpt-4o",
      tokens_in: 100,
      tokens_out: 50,
      latency_ms: 500,
    };
    expect(s.model).toBe("gpt-4o");
  });

  it("MultiExecutionResponse groups results", () => {
    const r: MultiExecutionResponse = {
      prompt_version_id: "v1",
      rendered_prompt: "Hello World",
      results: [],
    };
    expect(r.results).toEqual([]);
  });
});
