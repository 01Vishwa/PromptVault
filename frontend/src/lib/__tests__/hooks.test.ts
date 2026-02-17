// src/lib/__tests__/hooks.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useDebounce, useAsync } from "@/lib/hooks";

describe("useDebounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns initial value immediately", () => {
    const { result } = renderHook(() => useDebounce("hello", 300));
    expect(result.current).toBe("hello");
  });

  it("debounces value changes", () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 300),
      { initialProps: { value: "a" } },
    );

    rerender({ value: "ab" });
    expect(result.current).toBe("a"); // not yet updated

    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current).toBe("ab"); // now updated
  });

  it("resets timer on rapid changes", () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 300),
      { initialProps: { value: "a" } },
    );

    rerender({ value: "ab" });
    act(() => vi.advanceTimersByTime(200));

    rerender({ value: "abc" }); // resets timer
    act(() => vi.advanceTimersByTime(200));
    expect(result.current).toBe("a"); // still old — 200ms since last change

    act(() => vi.advanceTimersByTime(100));
    expect(result.current).toBe("abc");
  });
});

describe("useAsync", () => {
  it("fetches data on mount", async () => {
    const fetcher = vi.fn().mockResolvedValue({ items: [1, 2, 3] });
    const { result } = renderHook(() => useAsync(fetcher));

    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual({ items: [1, 2, 3] });
    expect(result.current.error).toBeUndefined();
  });

  it("handles errors", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useAsync(fetcher));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toBeUndefined();
    expect(result.current.error?.message).toBe("boom");
  });

  it("does nothing when fetcher is null", async () => {
    const { result } = renderHook(() => useAsync(null));

    // Should never enter loading state
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it("refetch works", async () => {
    let count = 0;
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(++count));
    const { result } = renderHook(() => useAsync(fetcher));

    await waitFor(() => expect(result.current.data).toBe(1));

    await act(async () => {
      await result.current.refetch();
    });
    expect(result.current.data).toBe(2);
  });
});
