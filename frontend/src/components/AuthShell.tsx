"use client";

import React from "react";
import Navbar from "@/components/Navbar";
import { useAuth } from "@/lib/hooks";
import LoginPage from "@/app/login/LoginPage";

export default function AuthShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div
          role="status"
          aria-label="Loading"
          className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"
        />
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container py-8">{children}</main>
    </div>
  );
}
