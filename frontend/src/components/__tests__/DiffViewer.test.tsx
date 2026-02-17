// src/components/__tests__/DiffViewer.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import DiffViewer from "@/components/DiffViewer";

// Mock API
const mockDiffVersions = vi.fn();
vi.mock("@/lib/api", () => ({
  diffVersions: (...args: unknown[]) => mockDiffVersions(...args),
}));

describe("DiffViewer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state", () => {
    mockDiffVersions.mockReturnValue(new Promise(() => {}));
    render(<DiffViewer promptId="p1" fromVersion={1} toVersion={2} />);
    expect(screen.getByText("Computing diff...")).toBeInTheDocument();
  });

  it("renders diff output", async () => {
    mockDiffVersions.mockResolvedValue({
      from_version: 1,
      to_version: 2,
      unified_diff: "--- v1\n+++ v2\n-old line\n+new line",
      char_patches: "",
      from_text: "old line",
      to_text: "new line",
    });
    render(<DiffViewer promptId="p1" fromVersion={1} toVersion={2} />);

    await waitFor(() => {
      expect(screen.getByText(/v1 → v2/)).toBeInTheDocument();
    });
  });

  it("shows error on failure", async () => {
    mockDiffVersions.mockRejectedValue(new Error("Diff failed"));
    render(<DiffViewer promptId="p1" fromVersion={1} toVersion={2} />);

    await waitFor(() => {
      expect(screen.getByText("Diff failed")).toBeInTheDocument();
    });
  });
});
