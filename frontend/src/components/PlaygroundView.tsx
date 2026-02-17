"use client";

import React, { useState, useCallback, useMemo } from "react";
import { FlaskConical, Play, Loader2 } from "lucide-react";
import * as api from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { MultiExecutionResponse, Prompt, PromptVersion } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const DEFAULT_PROVIDERS = [
  "openai/gpt-4o-mini",
  "anthropic/claude-3-haiku-20240307",
];

export default function PlaygroundView() {
  const [selectedPromptId, setSelectedPromptId] = useState("");
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [variables, setVariables] = useState("");
  const [providers, setProviders] = useState(DEFAULT_PROVIDERS.join("\n"));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MultiExecutionResponse | null>(null);

  // Fetch all prompts for the selector
  const promptsFetcher = useCallback(() => api.listPrompts(), []);
  const { data: promptsData } = useAsync(promptsFetcher);
  const prompts = useMemo(() => promptsData?.items ?? [], [promptsData]);

  // Fetch versions when a prompt is selected
  const versionsFetcher = useMemo(
    () => (selectedPromptId ? () => api.listVersions(selectedPromptId) : null),
    [selectedPromptId],
  );
  const { data: versionsData } = useAsync(versionsFetcher, [selectedPromptId]);
  const versions = useMemo(
    () =>
      versionsData
        ? [...versionsData.items].sort((a, b) => b.version_number - a.version_number)
        : [],
    [versionsData],
  );

  // Find selected version to show its variables
  const activeVersion = useMemo(
    () => versions.find((v) => v.id === selectedVersionId),
    [versions, selectedVersionId],
  );

  const handleExecute = useCallback(async () => {
    if (!selectedVersionId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      let vars: Record<string, string> = {};
      if (variables.trim()) {
        try {
          vars = JSON.parse(variables);
        } catch {
          throw new Error("Invalid JSON in variables field. Please check your syntax.");
        }
      }

      const providerList = providers
        .split("\n")
        .map((p) => p.trim())
        .filter(Boolean);

      const res = await api.executePrompt({
        prompt_version_id: selectedVersionId,
        variables: vars,
        providers: providerList,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Execution failed");
    } finally {
      setLoading(false);
    }
  }, [selectedVersionId, variables, providers]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <FlaskConical className="h-6 w-6 text-primary" />
        <h1 className="text-3xl font-bold tracking-tight">Playground</h1>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Input panel */}
        <div className="col-span-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Execute Prompt</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Prompt</Label>
                <Select value={selectedPromptId} onValueChange={(v) => { setSelectedPromptId(v); setSelectedVersionId(""); }}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a prompt..." />
                  </SelectTrigger>
                  <SelectContent>
                    {prompts.map((p: Prompt) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Version</Label>
                <Select value={selectedVersionId} onValueChange={setSelectedVersionId} disabled={!selectedPromptId}>
                  <SelectTrigger>
                    <SelectValue placeholder={selectedPromptId ? "Select a version..." : "Select a prompt first"} />
                  </SelectTrigger>
                  <SelectContent>
                    {versions.map((v: PromptVersion) => (
                      <SelectItem key={v.id} value={v.id}>
                        v{v.version_number} — {v.commit_message}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {activeVersion && activeVersion.variables.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {activeVersion.variables.map((vr) => (
                      <Badge key={vr} variant="outline" className="text-[10px]">
                        {`{{${vr}}}`}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="vars">Variables (JSON)</Label>
                <Textarea
                  id="vars"
                  value={variables}
                  onChange={(e) => setVariables(e.target.value)}
                  rows={4}
                  placeholder={'{\n  "name": "Alice",\n  "topic": "AI"\n}'}
                  className="font-mono text-xs"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="providers">Providers (one per line)</Label>
                <Textarea
                  id="providers"
                  value={providers}
                  onChange={(e) => setProviders(e.target.value)}
                  rows={3}
                  className="font-mono text-xs"
                />
              </div>

              <Button onClick={handleExecute} disabled={loading || !selectedVersionId} className="w-full">
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Executing...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Execute
                  </>
                )}
              </Button>

              {error && <p className="text-sm text-destructive">{error}</p>}
            </CardContent>
          </Card>
        </div>

        {/* Results panel */}
        <div className="col-span-8 space-y-4">
          {result && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Rendered Prompt</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="rounded-md bg-muted p-4 text-sm whitespace-pre-wrap font-mono">
                    {result.rendered_prompt}
                  </pre>
                </CardContent>
              </Card>

              {result.results.map((r) => (
                <Card key={r.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">
                        {r.model_provider}/{r.model_name}
                      </CardTitle>
                      <Badge variant={r.status === "success" ? "success" : "destructive"}>
                        {r.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {r.response_text && (
                      <pre className="rounded-md bg-muted p-4 text-sm whitespace-pre-wrap">
                        {r.response_text}
                      </pre>
                    )}
                    {r.error_message && (
                      <p className="text-sm text-destructive">{r.error_message}</p>
                    )}
                    <div className="flex gap-4 text-xs text-muted-foreground">
                      {r.tokens_in !== null && <span>In: {r.tokens_in} tokens</span>}
                      {r.tokens_out !== null && <span>Out: {r.tokens_out} tokens</span>}
                      {r.latency_ms !== null && <span>{r.latency_ms}ms</span>}
                      {r.cost_estimate !== null && (
                        <span>${r.cost_estimate.toFixed(6)}</span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </>
          )}

          {!result && !loading && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                <FlaskConical className="h-12 w-12 mb-4 opacity-20" />
                <p>Select a prompt and version above, then click Execute.</p>
                <p className="text-xs mt-1">
                  Supports side-by-side comparison across multiple providers.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
