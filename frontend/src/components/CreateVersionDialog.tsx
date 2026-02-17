"use client";

import React, { useState, useCallback } from "react";
import * as api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Props {
  open: boolean;
  onOpenChange: (_open: boolean) => void;
  promptId: string;
  onCreated: () => void;
}

export default function CreateVersionDialog({ open, onOpenChange, promptId, onCreated }: Props) {
  const [templateText, setTemplateText] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [commitMessage, setCommitMessage] = useState("");
  const [temperature, setTemperature] = useState("");
  const [maxTokens, setMaxTokens] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetForm = useCallback(() => {
    setTemplateText("");
    setSystemPrompt("");
    setCommitMessage("");
    setTemperature("");
    setMaxTokens("");
    setError(null);
  }, []);

  const handleOpenChange = useCallback(
    (isOpen: boolean) => {
      if (!isOpen) resetForm();
      onOpenChange(isOpen);
    },
    [onOpenChange, resetForm],
  );

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setLoading(true);
      setError(null);
      try {
        const modelConfig =
          temperature || maxTokens
            ? {
                temperature: temperature ? parseFloat(temperature) : undefined,
                max_tokens: maxTokens ? parseInt(maxTokens, 10) : undefined,
              }
            : undefined;

        await api.createVersion(promptId, {
          template_text: templateText,
          system_prompt: systemPrompt || undefined,
          model_config_data: modelConfig,
          commit_message: commitMessage,
        });
        onCreated();
        handleOpenChange(false);
        setTemplateText("");
        setSystemPrompt("");
        setCommitMessage("");
        setTemperature("");
        setMaxTokens("");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create version");
      } finally {
        setLoading(false);
      }
    },
    [promptId, templateText, systemPrompt, commitMessage, temperature, maxTokens, onCreated, handleOpenChange],
  );

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>New Version</DialogTitle>
          <DialogDescription>
            Create an immutable version of your prompt template. Use {"{{variable}}"} syntax for
            variables.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="template">Template Text *</Label>
            <Textarea
              id="template"
              value={templateText}
              onChange={(e) => setTemplateText(e.target.value)}
              required
              rows={6}
              placeholder="You are a helpful assistant. Summarize the following: {{content}}"
              className="font-mono text-sm"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="system">System Prompt</Label>
            <Textarea
              id="system"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={2}
              className="font-mono text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="temp">Temperature</Label>
              <Input
                id="temp"
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={temperature}
                onChange={(e) => setTemperature(e.target.value)}
                placeholder="0.7"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tokens">Max Tokens</Label>
              <Input
                id="tokens"
                type="number"
                min="1"
                value={maxTokens}
                onChange={(e) => setMaxTokens(e.target.value)}
                placeholder="1024"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="commit">Commit Message *</Label>
            <Input
              id="commit"
              value={commitMessage}
              onChange={(e) => setCommitMessage(e.target.value)}
              required
              placeholder="Add summarization prompt"
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !templateText || !commitMessage}>
              {loading ? "Saving..." : "Create Version"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
