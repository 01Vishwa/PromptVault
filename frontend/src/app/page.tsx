"use client";

import AuthShell from "@/components/AuthShell";
import PromptListView from "@/components/PromptListView";

export default function HomePage() {
  return (
    <AuthShell>
      <PromptListView />
    </AuthShell>
  );
}
