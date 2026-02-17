"use client";

import React, { useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { Plus, Search } from "lucide-react";
import * as api from "@/lib/api";
import { useAsync, useDebounce } from "@/lib/hooks";
import type { Prompt } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import CreatePromptDialog from "@/components/CreatePromptDialog";

export default function PromptListView() {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 300);
  const [dialogOpen, setDialogOpen] = useState(false);

  const fetcher = useCallback(() => api.listPrompts(debouncedSearch || undefined), [debouncedSearch]);
  const { data, loading, error, refetch } = useAsync(fetcher, [debouncedSearch]);

  const prompts = useMemo(() => data?.items ?? [], [data]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Prompts</h1>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New Prompt
        </Button>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search prompts..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {loading && <p className="text-muted-foreground">Loading...</p>}
      {error && <p className="text-destructive">{error.message}</p>}

      {prompts.length === 0 && !loading && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <p>No prompts yet. Create one to get started.</p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-3">
        {prompts.map((p: Prompt) => (
          <Link key={p.id} href={`/prompts/${p.id}`}>
            <Card className="transition-colors hover:bg-accent/50 cursor-pointer">
              <CardContent className="flex items-center justify-between p-4">
                <div className="space-y-1">
                  <h3 className="font-semibold">{p.name}</h3>
                  <p className="text-xs text-muted-foreground font-mono">{p.slug}</p>
                  {p.description && (
                    <p className="text-sm text-muted-foreground line-clamp-1">{p.description}</p>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1">
                  <div className="flex gap-1">
                    {p.tags.map((t) => (
                      <Badge key={t} variant="secondary" className="text-xs">
                        {t}
                      </Badge>
                    ))}
                  </div>
                  {p.latest_version !== null && (
                    <span className="text-xs text-muted-foreground">
                      v{p.latest_version}
                    </span>
                  )}
                  <time className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(p.updated_at), { addSuffix: true })}
                  </time>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <CreatePromptDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onCreated={() => void refetch()}
      />
    </div>
  );
}
