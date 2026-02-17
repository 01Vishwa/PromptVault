// src/components/__tests__/LoginPage.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginPage from "@/app/login/LoginPage";

// Mock useAuth
const mockSignIn = vi.fn();
const mockSignUp = vi.fn();

vi.mock("@/lib/hooks", () => ({
  useAuth: () => ({
    signIn: mockSignIn,
    signUp: mockSignUp,
  }),
}));

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSignIn.mockResolvedValue({ error: null });
    mockSignUp.mockResolvedValue({ error: null });
  });

  it("renders sign-in form by default", () => {
    render(<LoginPage />);
    expect(screen.getByText("Sign in to your account")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
  });

  it("toggles to sign-up mode", async () => {
    render(<LoginPage />);
    const toggle = screen.getByText(/Don't have an account/);
    await userEvent.click(toggle);
    expect(screen.getByText("Create a new account")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign Up" })).toBeInTheDocument();
  });

  it("calls signIn with email and password", async () => {
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "test@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "password123");
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith("test@example.com", "password123");
    });
  });

  it("shows error on failed sign-in", async () => {
    mockSignIn.mockResolvedValue({ error: { message: "Invalid credentials" } });
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "bad@email.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    });
  });

  it("shows success message on sign-up", async () => {
    render(<LoginPage />);
    await userEvent.click(screen.getByText(/Don't have an account/));
    await userEvent.type(screen.getByLabelText("Email"), "new@email.com");
    await userEvent.type(screen.getByLabelText("Password"), "password123");
    await userEvent.click(screen.getByRole("button", { name: "Sign Up" }));

    await waitFor(() => {
      expect(screen.getByText(/Check your email/)).toBeInTheDocument();
    });
  });
});
