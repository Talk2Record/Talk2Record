"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cpu, KeyRound, Trash2 } from "lucide-react";

import {
  aiService,
  type AIProviderSpec,
  type AITaskValue,
  type CreateProviderConfigInput,
  type CreateTaskBindingInput,
} from "@/services/ai-service";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { toast } from "@/shared/hooks/use-toast";
import { RoleGate } from "@/shared/components/role-gate";

const selectClass =
  "flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm ring-offset-background " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50";

const TASK_OPTIONS: { value: AITaskValue; label: string }[] = [
  { value: "transcription", label: "Transcription" },
  { value: "extraction", label: "Extraction" },
  { value: "summarization", label: "Summarization" },
  { value: "chat", label: "Chat" },
  { value: "embedding", label: "Embedding" },
];

function errorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export default function AISettingsPage() {
  return (
    <RoleGate
      minimum="admin"
      title="AI configuration is admin-only"
      description="Only organization owners and admins can connect AI providers or change task routing."
    >
      <AISettingsPageInner />
    </RoleGate>
  );
}

function AISettingsPageInner() {
  const queryClient = useQueryClient();

  const providersQuery = useQuery({
    queryKey: ["ai", "providers"],
    queryFn: () => aiService.listProviders(),
  });

  const modelsQuery = useQuery({
    queryKey: ["ai", "models"],
    queryFn: () => aiService.listModels(),
  });

  const configsQuery = useQuery({
    queryKey: ["ai", "provider-configs"],
    queryFn: () => aiService.listProviderConfigs(),
  });

  const bindingsQuery = useQuery({
    queryKey: ["ai", "task-bindings"],
    queryFn: () => aiService.listTaskBindings(),
  });

  const [configForm, setConfigForm] = useState<CreateProviderConfigInput>({
    provider: "",
    api_key: "",
    base_url: "",
    display_name: "",
    active: true,
  });
  const [bindingForm, setBindingForm] = useState<CreateTaskBindingInput>({
    task: "extraction",
    provider: "",
    model_id: "",
    active: true,
  });

  const createConfig = useMutation({
    mutationFn: (payload: CreateProviderConfigInput) => aiService.createProviderConfig(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ai", "provider-configs"] });
      toast({ title: "Provider connected" });
      setConfigForm({
        provider: "",
        api_key: "",
        base_url: "",
        display_name: "",
        active: true,
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Could not save provider",
        description: errorMessage(error, "Unexpected error"),
        variant: "destructive",
      });
    },
  });

  const deleteConfig = useMutation({
    mutationFn: (id: number) => aiService.deleteProviderConfig(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ai", "provider-configs"] });
      toast({ title: "Provider removed" });
    },
  });

  const createBinding = useMutation({
    mutationFn: (payload: CreateTaskBindingInput) => aiService.createTaskBinding(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ai", "task-bindings"] });
      toast({ title: "Task binding saved" });
      setBindingForm({ task: "extraction", provider: "", model_id: "", active: true });
    },
    onError: (error: Error) => {
      toast({
        title: "Could not save binding",
        description: errorMessage(error, "Unexpected error"),
        variant: "destructive",
      });
    },
  });

  const deleteBinding = useMutation({
    mutationFn: (id: number) => aiService.deleteTaskBinding(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ai", "task-bindings"] });
      toast({ title: "Binding removed" });
    },
  });

  const providers: AIProviderSpec[] = providersQuery.data ?? [];
  const providerBySlug = new Map(providers.map((p) => [p.slug, p]));

  const onSubmitConfig = (event: FormEvent) => {
    event.preventDefault();
    if (!configForm.provider) {
      toast({ title: "Choose a provider", variant: "destructive" });
      return;
    }
    createConfig.mutate({
      ...configForm,
      api_key: configForm.api_key?.trim() ? configForm.api_key : undefined,
    });
  };

  const onSubmitBinding = (event: FormEvent) => {
    event.preventDefault();
    if (!bindingForm.provider || !bindingForm.model_id) {
      toast({ title: "Pick a provider and model", variant: "destructive" });
      return;
    }
    createBinding.mutate(bindingForm);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold">
            <Cpu className="h-5 w-5" /> AI settings
          </h1>
          <p className="text-muted-foreground text-sm">
            Connect AI providers and decide which one powers each task.
          </p>
        </div>
        <Link href="/dashboard/settings" className="text-muted-foreground text-sm underline">
          Back to settings
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Available providers</CardTitle>
          <CardDescription>
            Platform-supported providers. Connect one below to start using it.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {providersQuery.isLoading ? (
            <p className="text-muted-foreground text-sm">Loading providers…</p>
          ) : (
            <div className="grid gap-2 md:grid-cols-2">
              {providers.map((provider) => (
                <div key={provider.slug} className="rounded-md border p-3 text-sm">
                  <div className="font-medium">{provider.display_name}</div>
                  <div className="text-muted-foreground text-xs">
                    {provider.capabilities.join(", ") || "—"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Connected providers</CardTitle>
          <CardDescription>
            Per-organisation API credentials. Keys are stored encrypted.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <form onSubmit={onSubmitConfig} className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <Label>Provider</Label>
              <select
                className={selectClass}
                value={configForm.provider}
                onChange={(event) =>
                  setConfigForm((prev) => ({ ...prev, provider: event.target.value }))
                }
              >
                <option value="">Select provider</option>
                {providers.map((p) => (
                  <option key={p.slug} value={p.slug}>
                    {p.display_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <Label>Display name</Label>
              <Input
                value={configForm.display_name ?? ""}
                onChange={(event) =>
                  setConfigForm((prev) => ({ ...prev, display_name: event.target.value }))
                }
                placeholder="Production key"
              />
            </div>
            <div className="space-y-1 md:col-span-2">
              <Label>API key</Label>
              <Input
                type="password"
                value={configForm.api_key ?? ""}
                onChange={(event) =>
                  setConfigForm((prev) => ({ ...prev, api_key: event.target.value }))
                }
                placeholder="sk-…"
              />
            </div>
            <div className="space-y-1 md:col-span-2">
              <Label>Base URL (optional override)</Label>
              <Input
                value={configForm.base_url ?? ""}
                onChange={(event) =>
                  setConfigForm((prev) => ({ ...prev, base_url: event.target.value }))
                }
                placeholder={providerBySlug.get(configForm.provider)?.default_base_url ?? ""}
              />
            </div>
            <div className="md:col-span-2">
              <Button type="submit" disabled={createConfig.isPending}>
                <KeyRound className="mr-2 h-4 w-4" />
                {createConfig.isPending ? "Saving…" : "Connect provider"}
              </Button>
            </div>
          </form>

          <div className="space-y-2">
            {configsQuery.data?.length ? (
              configsQuery.data.map((config) => (
                <div
                  key={config.id}
                  className="flex items-center justify-between rounded-md border p-3 text-sm"
                >
                  <div>
                    <div className="font-medium">
                      {config.display_name ||
                        providerBySlug.get(config.provider)?.display_name ||
                        config.provider}
                    </div>
                    <div className="text-muted-foreground text-xs">
                      {config.provider} · key {config.api_key_masked || "—"}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => deleteConfig.mutate(config.id)}
                    aria-label="Remove"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))
            ) : (
              <p className="text-muted-foreground text-sm">No providers connected yet.</p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Task routing</CardTitle>
          <CardDescription>Decide which provider/model serves each AI task.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <form onSubmit={onSubmitBinding} className="grid gap-3 md:grid-cols-3">
            <div className="space-y-1">
              <Label>Task</Label>
              <select
                className={selectClass}
                value={bindingForm.task}
                onChange={(event) =>
                  setBindingForm((prev) => ({
                    ...prev,
                    task: event.target.value as AITaskValue,
                  }))
                }
              >
                {TASK_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <Label>Provider</Label>
              <select
                className={selectClass}
                value={bindingForm.provider}
                onChange={(event) =>
                  setBindingForm((prev) => ({
                    ...prev,
                    provider: event.target.value,
                    model_id: "",
                  }))
                }
              >
                <option value="">Select provider</option>
                {providers.map((p) => (
                  <option key={p.slug} value={p.slug}>
                    {p.display_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <Label>Model</Label>
              <Input
                value={bindingForm.model_id}
                onChange={(event) =>
                  setBindingForm((prev) => ({ ...prev, model_id: event.target.value }))
                }
                placeholder="gpt-4o-mini"
                list="ai-model-ids"
              />
              <datalist id="ai-model-ids">
                {modelsQuery.data
                  ?.filter((m) => !bindingForm.provider || m.provider === bindingForm.provider)
                  .map((m) => (
                    <option key={m.id} value={m.model_id}>
                      {m.display_name}
                    </option>
                  ))}
              </datalist>
            </div>
            <div className="md:col-span-3">
              <Button type="submit" disabled={createBinding.isPending}>
                {createBinding.isPending ? "Saving…" : "Save binding"}
              </Button>
            </div>
          </form>

          <div className="space-y-2">
            {bindingsQuery.data?.length ? (
              bindingsQuery.data.map((binding) => (
                <div
                  key={binding.id}
                  className="flex items-center justify-between rounded-md border p-3 text-sm"
                >
                  <div>
                    <div className="font-medium">
                      {TASK_OPTIONS.find((t) => t.value === binding.task)?.label ?? binding.task}
                    </div>
                    <div className="text-muted-foreground text-xs">
                      {binding.provider}:{binding.model_id}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => deleteBinding.mutate(binding.id)}
                    aria-label="Remove"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))
            ) : (
              <p className="text-muted-foreground text-sm">
                No task bindings yet — each task will fall back to platform defaults.
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
