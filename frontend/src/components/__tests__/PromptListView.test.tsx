// src/components/__tests__/PromptListView.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PromptListView from "@/components/PromptListView";

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

// Mock API
const mockListPrompts = vi.fn();
vi.mock("@/lib/api", () => ({
  listPrompts: (...args: unknown[]) => mockListPrompts(...args),
}));

// Mock hooks
vi.mock("@/lib/hooks", async () => {
  const actual = await vi.importActual("@/lib/hooks");
  return { ...actual };
});

describe("PromptListView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state", () => {
    mockListPrompts.mockReturnValue(new Promise(() => {})); // never resolves
    render(<PromptListView />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows empty state when no prompts", async () => {
    mockListPrompts.mockResolvedValue({ items: [], total: 0 });
    render(<PromptListView />);

    await waitFor(() => {
      expect(screen.getByText(/No prompts yet/)).toBeInTheDocument();
    });
  });

  it("renders prompt cards", async () => {
    mockListPrompts.mockResolvedValue({
      items: [
        {
          id: "1",
          user_id: "u1",
          name: "Summarizer",
          slug: "summarizer",
          description: "Summarize documents",
          tags: ["prod"],
          is_archived: false,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
          latest_version: 3,
        },
      ],
      total: 1,
    });
    render(<PromptListView />);

    await waitFor(() => {
      expect(screen.getByText("Summarizer")).toBeInTheDocument();
    });
    expect(screen.getByText("summarizer")).toBeInTheDocument();
    expect(screen.getByText("prod")).toBeInTheDocument();
    expect(screen.getByText("v3")).toBeInTheDocument();
  });

  it("has a search input", () => {
    mockListPrompts.mockResolvedValue({ items: [], total: 0 });
    render(<PromptListView />);
    expect(screen.getByPlaceholderText("Search prompts...")).toBeInTheDocument();
  });

  it("has a New Prompt button", () => {
    mockListPrompts.mockResolvedValue({ items: [], total: 0 });
    render(<PromptListView />);
    expect(screen.getByText("New Prompt")).toBeInTheDocument();
  });
});
