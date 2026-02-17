"use client";

import AuthShell from "@/components/AuthShell";
import PlaygroundView from "@/components/PlaygroundView";

export default function PlaygroundPage() {
  return (
    <AuthShell>
      <PlaygroundView />
    </AuthShell>
  );
}
