"use client";

import React, { useState, useCallback } from "react";
import { formatDistanceToNow } from "date-fns";
import { Rocket, AlertTriangle } from "lucide-react";
import * as api from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { Prompt, PromptVersion } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Props {
  promptId: string;
  prompt?: Prompt;
  version: PromptVersion;
}

export default function DeployPanel({ promptId, prompt, version }: Props) {
  const [env, setEnv] = useState("production");
  const [deploying, setDeploying] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const deployFetcher = useCallback(() => api.listDeployments(promptId), [promptId]);
  const { data: deployments, refetch } = useAsync(deployFetcher, [promptId]);

  const handleDeploy = useCallback(async () => {
    setDeploying(true);
    setMessage(null);
    try {
      await api.deploy(promptId, {
        prompt_version_id: version.id,
        environment: env,
      });
      setMessage({ text: `Deployed v${version.version_number} to ${env}`, type: "success" });
      await refetch();
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : "Deploy failed", type: "error" });
    } finally {
      setDeploying(false);
      setConfirmOpen(false);
    }
  }, [promptId, version, env, refetch]);

  const requestDeploy = useCallback(() => {
    if (env === "production") {
      setConfirmOpen(true);
    } else {
      void handleDeploy();
    }
  }, [env, handleDeploy]);

  const envBadgeVariant = (e: string) => {
    if (e === "production") return "success" as const;
    if (e === "staging") return "warning" as const;
    return "secondary" as const;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Rocket className="h-4 w-4" />
          Deploy
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Select value={env} onValueChange={setEnv}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="production">production</SelectItem>
              <SelectItem value="staging">staging</SelectItem>
              <SelectItem value="development">development</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={requestDeploy} disabled={deploying} size="sm">
            {deploying ? "Deploying..." : "Deploy"}
          </Button>
        </div>

        {message && (
          <p className={`text-xs ${message.type === "error" ? "text-destructive" : "text-green-600 dark:text-green-400"}`}>
            {message.text}
          </p>
        )}

        <div className="text-xs text-muted-foreground">
          Deploying <strong>v{version.version_number}</strong>
        </div>

        {deployments && deployments.items.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-muted-foreground">Active Deployments</h4>
            <ul className="space-y-1">
              {deployments.items
                .filter((d) => d.is_active)
                .map((d) => (
                  <li key={d.id} className="flex items-center gap-2 text-xs">
                    <Badge variant={envBadgeVariant(d.environment)} className="text-[10px]">
                      {d.environment}
                    </Badge>
                    <time className="text-muted-foreground ml-auto">
                      {formatDistanceToNow(new Date(d.deployed_at), { addSuffix: true })}
                    </time>
                  </li>
                ))}
            </ul>
          </div>
        )}

        {/* Serve endpoint hint */}
        <div className="rounded-md bg-muted p-3 space-y-1">
          <p className="text-xs font-medium">Serve Endpoint</p>
          <code className="text-[11px] text-muted-foreground break-all">
            POST /api/v1/serve/{prompt?.slug ?? "your-slug"}
          </code>
        </div>

        {/* Production deploy confirmation */}
        <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
                Deploy to Production
              </DialogTitle>
              <DialogDescription>
                You are about to deploy <strong>v{version.version_number}</strong> to{" "}
                <strong>production</strong>. This will serve live traffic immediately.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setConfirmOpen(false)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={() => void handleDeploy()} disabled={deploying}>
                {deploying ? "Deploying..." : "Confirm Deploy"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
