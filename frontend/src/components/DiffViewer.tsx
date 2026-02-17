"use client";

import React, { useCallback } from "react";
import * as api from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  promptId: string;
  fromVersion: number;
  toVersion: number;
}

export default function DiffViewer({ promptId, fromVersion, toVersion }: Props) {
  const fetcher = useCallback(
    () => api.diffVersions(promptId, fromVersion, toVersion),
    [promptId, fromVersion, toVersion],
  );
  const { data: diff, loading, error } = useAsync(fetcher, [promptId, fromVersion, toVersion]);

  if (loading) return <p className="text-muted-foreground text-sm">Computing diff...</p>;
  if (error) return <p className="text-destructive text-sm">{error.message}</p>;
  if (!diff) return null;

  const lines = diff.unified_diff.split("\n");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">
          v{diff.from_version} &rarr; v{diff.to_version}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {lines.length === 0 || diff.unified_diff.length === 0 ? (
          <p className="text-muted-foreground text-sm">No text changes.</p>
        ) : (
          <pre className="text-xs leading-6 overflow-x-auto rounded-md bg-muted p-4 font-mono">
            {lines.map((line, i) => {
              let cls = "text-foreground";
              if (line.startsWith("+++") || line.startsWith("---")) {
                cls = "text-muted-foreground font-semibold";
              } else if (line.startsWith("+")) {
                cls = "text-green-700 bg-green-50 dark:text-green-400 dark:bg-green-950";
              } else if (line.startsWith("-")) {
                cls = "text-red-700 bg-red-50 dark:text-red-400 dark:bg-red-950";
              } else if (line.startsWith("@@")) {
                cls = "text-blue-600 dark:text-blue-400";
              }

              return (
                <div key={i} className={cls}>
                  {line}
                </div>
              );
            })}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}
