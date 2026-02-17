// src/lib/__tests__/api.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock supabase before importing api
vi.mock("@/lib/supabase", () => ({
  createClient: () => ({
    auth: {
      getSession: () =>
        Promise.resolve({
          data: { session: { access_token: "test-jwt" } },
        }),
    },
  }),
}));

// Dynamic import after mock
const api = await import("@/lib/api");

describe("API client", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  function mockFetchOk(body: unknown, status = 200) {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status,
      json: () => Promise.resolve(body),
    });
  }

  function mockFetchError(detail: string, status = 400) {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status,
      statusText: "Bad Request",
      json: () => Promise.resolve({ detail }),
    });
  }

  it("listPrompts sends GET with auth header", async () => {
    mockFetchOk({ items: [], total: 0 });
    const res = await api.listPrompts();

    expect(res).toEqual({ items: [], total: 0 });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/prompts"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-jwt",
        }),
      }),
    );
  });

  it("listPrompts passes search param", async () => {
    mockFetchOk({ items: [], total: 0 });
    await api.listPrompts("hello");

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]![0] as string;
    expect(url).toContain("search=hello");
  });

  it("createPrompt sends POST with body", async () => {
    const prompt = { id: "1", name: "Test", slug: "test" };
    mockFetchOk(prompt);

    const res = await api.createPrompt({ name: "Test", slug: "test" });
    expect(res).toEqual(prompt);

    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]!;
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ name: "Test", slug: "test" });
  });

  it("throws on HTTP error with detail", async () => {
    mockFetchError("Not found", 404);
    await expect(api.getPrompt("missing")).rejects.toThrow("Not found");
  });

  it("deletePrompt sends DELETE", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 204,
      json: () => Promise.reject(new Error("no body")),
    });

    await api.deletePrompt("abc");
    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]!;
    expect(init.method).toBe("DELETE");
  });

  it("createVersion sends POST to correct path", async () => {
    const version = { id: "v1", version_number: 1 };
    mockFetchOk(version);

    await api.createVersion("p1", {
      template_text: "Hello {{name}}",
      commit_message: "init",
    });

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]![0] as string;
    expect(url).toContain("/api/v1/prompts/p1/versions");
  });

  it("diffVersions hits correct endpoint", async () => {
    mockFetchOk({ from_version: 1, to_version: 2, unified_diff: "" });
    await api.diffVersions("p1", 1, 2);

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]![0] as string;
    expect(url).toContain("/prompts/p1/versions/1/diff/2");
  });

  it("deploy sends POST with environment", async () => {
    mockFetchOk({ id: "d1", environment: "staging" });
    await api.deploy("p1", {
      prompt_version_id: "v1",
      environment: "staging",
    });

    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]!;
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body).environment).toBe("staging");
  });

  it("undeploy sends DELETE to environment path", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 204,
      json: () => Promise.reject(new Error("no body")),
    });

    await api.undeploy("p1", "production");
    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]![0] as string;
    expect(url).toContain("/prompts/p1/deployments/production");
  });
});
