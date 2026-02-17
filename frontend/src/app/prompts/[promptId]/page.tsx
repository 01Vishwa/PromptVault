"use client";

import AuthShell from "@/components/AuthShell";
import PromptDetailView from "@/components/PromptDetailView";

export default function PromptPage() {
  return (
    <AuthShell>
      <PromptDetailView />
    </AuthShell>
  );
}
