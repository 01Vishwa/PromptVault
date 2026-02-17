"use client";

import React, { useState, useMemo, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { ArrowLeft, Plus, GitCompare } from "lucide-react";
import * as api from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import CreateVersionDialog from "@/components/CreateVersionDialog";
import DiffViewer from "@/components/DiffViewer";
import DeployPanel from "@/components/DeployPanel";
import type { PromptVersion } from "@/lib/types";

export default function PromptDetailView() {
  const params = useParams();
  const promptId = params?.promptId as string;

  const promptFetcher = useCallback(() => api.getPrompt(promptId), [promptId]);
  const versionFetcher = useCallback(() => api.listVersions(promptId), [promptId]);

  const { data: prompt, loading: promptLoading, error: promptError } = useAsync(promptFetcher, [promptId]);
  const { data: versions, loading: versionsLoading, error: versionsError, refetch: refetchVersions } = useAsync(versionFetcher, [promptId]);

  const [selectedVersion, setSelectedVersion] = useState<PromptVersion | null>(null);
  const [compareVersion, setCompareVersion] = useState<PromptVersion | null>(null);
  const [versionDialogOpen, setVersionDialogOpen] = useState(false);

  const sortedVersions = useMemo(() => {
    if (!versions) return [];
    return [...versions.items].sort((a, b) => b.version_number - a.version_number);
  }, [versions]);

  // Auto-select latest version
  const activeVersion = selectedVersion ?? sortedVersions[0] ?? null;
  const activeCompare = compareVersion ?? sortedVersions[1] ?? null;

  if (!promptId) return null;

  if (promptLoading || versionsLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div role="status" aria-label="Loading" className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (promptError || versionsError) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-destructive">
          {(promptError ?? versionsError)?.message ?? "Failed to load prompt"}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{prompt?.name ?? "..."}</h1>
            {prompt && (
              <p className="text-sm text-muted-foreground font-mono">{prompt.slug}</p>
            )}
          </div>
        </div>
        <Button onClick={() => setVersionDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New Version
        </Button>
      </div>

      {prompt?.tags && prompt.tags.length > 0 && (
        <div className="flex gap-1">
          {prompt.tags.map((t) => (
            <Badge key={t} variant="secondary">{t}</Badge>
          ))}
        </div>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Version list sidebar */}
        <div className="col-span-3 space-y-2">
          <h2 className="text-sm font-semibold text-muted-foreground mb-3">
            Versions ({sortedVersions.length})
          </h2>
          {sortedVersions.map((v) => (
            <button
              key={v.id}
              type="button"
              aria-current={activeVersion?.id === v.id ? "true" : undefined}
              onClick={() => {
                if (activeVersion && activeVersion.id !== v.id) {
                  setCompareVersion(activeVersion);
                }
                setSelectedVersion(v);
              }}
              className={`w-full text-left rounded-lg border p-3 transition-colors ${
                activeVersion?.id === v.id
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/30"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">v{v.version_number}</span>
                <time className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(v.created_at), { addSuffix: true })}
                </time>
              </div>
              <p className="text-xs text-muted-foreground font-mono mt-1 truncate">
                {v.version_hash.slice(0, 12)}
              </p>
              {v.commit_message && (
                <p className="text-xs mt-1 line-clamp-1">{v.commit_message}</p>
              )}
              {v.variables.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {v.variables.map((vr) => (
                    <Badge key={vr} variant="outline" className="text-[10px]">
                      {`{{${vr}}}`}
                    </Badge>
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>

        {/* Center content */}
        <div className="col-span-6">
          <Tabs defaultValue="template">
            <TabsList>
              <TabsTrigger value="template">
                Template
              </TabsTrigger>
              <TabsTrigger value="diff">
                <GitCompare className="mr-1 h-3 w-3" />
                Diff
              </TabsTrigger>
            </TabsList>

            <TabsContent value="template">
              {activeVersion && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">
                      Template (v{activeVersion.version_number})
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <pre className="rounded-md bg-muted p-4 text-sm overflow-x-auto whitespace-pre-wrap font-mono">
                      {activeVersion.template_text}
                    </pre>
                    {activeVersion.system_prompt && (
                      <div>
                        <h4 className="text-xs font-medium text-muted-foreground mb-2">
                          System Prompt
                        </h4>
                        <pre className="rounded-md bg-muted p-4 text-sm overflow-x-auto whitespace-pre-wrap font-mono">
                          {activeVersion.system_prompt}
                        </pre>
                      </div>
                    )}
                    {activeVersion.model_config && (
                      <div>
                        <h4 className="text-xs font-medium text-muted-foreground mb-2">
                          Model Config
                        </h4>
                        <pre className="rounded-md bg-muted p-3 text-xs overflow-x-auto">
                          {JSON.stringify(activeVersion.model_config, null, 2)}
                        </pre>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="diff">
              {activeVersion && activeCompare && activeVersion.id !== activeCompare.id ? (
                <DiffViewer
                  promptId={promptId}
                  fromVersion={activeCompare.version_number}
                  toVersion={activeVersion.version_number}
                />
              ) : (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    Select two different versions to compare.
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </div>

        {/* Deploy panel sidebar */}
        <div className="col-span-3">
          {activeVersion && (
            <DeployPanel promptId={promptId} prompt={prompt} version={activeVersion} />
          )}
        </div>
      </div>

      <CreateVersionDialog
        open={versionDialogOpen}
        onOpenChange={setVersionDialogOpen}
        promptId={promptId}
        onCreated={() => void refetchVersions()}
      />
    </div>
  );
}
