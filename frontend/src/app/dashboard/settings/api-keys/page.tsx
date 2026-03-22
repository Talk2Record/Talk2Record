"use client";

import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { KeyRound } from "lucide-react";
import { organizationApiKeysService } from "@/services/platform-service";
import type {
  CreateOrganizationApiKeyInput,
  OrganizationApiKeyAuditEvent,
  OrganizationApiKeyRow,
  OrganizationApiKeyScopePreset,
} from "@/types/platform";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { toast } from "@/shared/hooks/use-toast";

const SCOPE_PRESET_OPTIONS: {
  value: OrganizationApiKeyScopePreset;
  label: string;
  hint: string;
}[] = [
  {
    value: "ingestion",
    label: "Ingestion only",
    hint: "Write access for public ingestion endpoints.",
  },
  {
    value: "ingestion_plus_read",
    label: "Ingestion + read records",
    hint: "Ingestion plus read-only access to records where the backend allows it.",
  },
];

function formatDt(value: string | null) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast({ title: "Copied", description: "Value copied to clipboard." });
  } catch {
    toast({
      title: "Copy failed",
      description: "Your browser blocked clipboard access.",
      variant: "destructive",
    });
  }
}

function isPermissionDeniedApiError(error: unknown): boolean {
  if (!error || !(error instanceof Error)) return false;
  const m = error.message.toLowerCase();
  return m.includes("403") || m.includes("admin") || m.includes("permission");
}

export default function OrganizationApiKeysPage() {
  const queryClient = useQueryClient();
  const [includeInactive, setIncludeInactive] = useState(false);
  const [name, setName] = useState("");
  const [scopePreset, setScopePreset] = useState<OrganizationApiKeyScopePreset>("ingestion");
  const [expiresInDays, setExpiresInDays] = useState("");
  const [rateLimitPerMinute, setRateLimitPerMinute] = useState("");
  const [revealedSecret, setRevealedSecret] = useState<{ label: string; secret: string } | null>(
    null
  );
  const [auditForKey, setAuditForKey] = useState<{
    id: number;
    label: string;
    events: OrganizationApiKeyAuditEvent[];
  } | null>(null);
  const [auditLoadingId, setAuditLoadingId] = useState<number | null>(null);

  const keysQuery = useQuery({
    queryKey: ["organization-api-keys", includeInactive],
    queryFn: () => organizationApiKeysService.list(includeInactive),
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateOrganizationApiKeyInput) =>
      organizationApiKeysService.create(payload),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["organization-api-keys"] });
      setName("");
      setExpiresInDays("");
      setRateLimitPerMinute("");
      setRevealedSecret({
        label: `New key: ${data.key.name}`,
        secret: data.apiKey,
      });
      toast({
        title: "API key created",
        description: "Copy the secret now — it will not be shown again.",
      });
    },
    onError: (error: Error) => {
      toast({ title: "Could not create key", description: error.message, variant: "destructive" });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: number) => organizationApiKeysService.revoke(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["organization-api-keys"] });
      toast({ title: "Key revoked" });
    },
    onError: (error: Error) => {
      toast({ title: "Revoke failed", description: error.message, variant: "destructive" });
    },
  });

  const rotateMutation = useMutation({
    mutationFn: (id: number) => organizationApiKeysService.rotate(id),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["organization-api-keys"] });
      setRevealedSecret({
        label: `Rotated key: ${data.key.name}`,
        secret: data.apiKey,
      });
      toast({
        title: "Key rotated",
        description: "Copy the new secret now — it will not be shown again.",
      });
    },
    onError: (error: Error) => {
      toast({ title: "Rotate failed", description: error.message, variant: "destructive" });
    },
  });

  const keys = keysQuery.data ?? [];

  const permissionDenied = isPermissionDeniedApiError(keysQuery.error);

  const handleCreate = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      toast({ title: "Name required", variant: "destructive" });
      return;
    }
    const payload: CreateOrganizationApiKeyInput = {
      name: trimmed,
      scopePreset,
    };
    const exp = expiresInDays.trim() ? Number.parseInt(expiresInDays, 10) : NaN;
    if (!Number.isNaN(exp) && exp > 0) {
      payload.expiresInDays = exp;
    }
    const rpm = rateLimitPerMinute.trim() ? Number.parseInt(rateLimitPerMinute, 10) : NaN;
    if (!Number.isNaN(rpm) && rpm > 0) {
      payload.rateLimitPerMinute = rpm;
    }
    createMutation.mutate(payload);
  };

  const loadAudit = async (row: OrganizationApiKeyRow) => {
    setAuditLoadingId(row.id);
    try {
      const events = await organizationApiKeysService.auditEvents(row.id);
      setAuditForKey({ id: row.id, label: row.name, events });
    } catch (e) {
      const message = e instanceof Error ? e.message : "Failed to load audit events.";
      toast({ title: "Audit load failed", description: message, variant: "destructive" });
    } finally {
      setAuditLoadingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <div className="bg-primary/10 text-primary inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-xs font-medium">
            <KeyRound className="h-3.5 w-3.5" />
            API access
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Organization API keys</h1>
          <p className="text-muted-foreground max-w-2xl text-sm">
            Create scoped keys for public ingestion and integrations. Secrets are shown only once at
            creation or rotation. Only organization owners and admins can manage keys.
          </p>
        </div>
        <Button variant="outline" className="rounded-xl" asChild>
          <Link href="/dashboard/settings">← Back to settings</Link>
        </Button>
      </div>

      {keysQuery.isLoading ? <p className="text-muted-foreground text-sm">Loading keys…</p> : null}

      {keysQuery.isError && permissionDenied ? (
        <Card className="border-destructive/40">
          <CardHeader>
            <CardTitle className="text-destructive">No access</CardTitle>
            <CardDescription>
              {keysQuery.error instanceof Error
                ? keysQuery.error.message
                : "Only organization owners and admins can view or manage API keys."}
            </CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      {keysQuery.isError && !permissionDenied ? (
        <Card className="border-destructive/40">
          <CardHeader>
            <CardTitle className="text-destructive">Could not load keys</CardTitle>
            <CardDescription>
              {keysQuery.error instanceof Error ? keysQuery.error.message : "Unexpected error."}
            </CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      {revealedSecret ? (
        <Card className="border-primary/30 bg-primary/5">
          <CardHeader>
            <CardTitle className="text-base">Save this secret</CardTitle>
            <CardDescription>
              {revealedSecret.label}. Store it in a secret manager — it cannot be retrieved later.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <pre className="bg-background max-h-40 overflow-x-auto rounded-lg border p-3 text-xs break-all">
              {revealedSecret.secret}
            </pre>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="secondary"
                className="rounded-xl"
                onClick={() => void copyText(revealedSecret.secret)}
              >
                Copy secret
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="rounded-xl"
                onClick={() => setRevealedSecret(null)}
              >
                Dismiss
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {!permissionDenied && !keysQuery.isError ? (
        <>
          <Card className="border-primary/10">
            <CardHeader>
              <CardTitle>Create a key</CardTitle>
              <CardDescription>
                Pick a scope preset. Use optional expiry and per-minute rate override when needed.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4 md:grid-cols-2" onSubmit={handleCreate}>
                <div className="grid gap-2 md:col-span-2">
                  <Label htmlFor="key-name">Display name</Label>
                  <Input
                    id="key-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Production WhatsApp ingestion"
                    className="rounded-xl"
                  />
                </div>
                <div className="grid gap-2 md:col-span-2">
                  <Label>Scope preset</Label>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {SCOPE_PRESET_OPTIONS.map((opt) => (
                      <label
                        key={opt.value}
                        className={`hover:bg-accent/40 flex cursor-pointer flex-col gap-1 rounded-xl border p-3 text-sm ${
                          scopePreset === opt.value ? "border-primary ring-primary/20 ring-2" : ""
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="radio"
                            name="scopePreset"
                            value={opt.value}
                            checked={scopePreset === opt.value}
                            onChange={() => setScopePreset(opt.value)}
                          />
                          <span className="font-medium">{opt.label}</span>
                        </div>
                        <span className="text-muted-foreground pl-6 text-xs">{opt.hint}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="exp-days">Expires in days (optional)</Label>
                  <Input
                    id="exp-days"
                    type="number"
                    min={1}
                    max={365}
                    value={expiresInDays}
                    onChange={(e) => setExpiresInDays(e.target.value)}
                    placeholder="e.g. 90"
                    className="rounded-xl"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="rpm">Rate limit / minute (optional)</Label>
                  <Input
                    id="rpm"
                    type="number"
                    min={1}
                    max={10000}
                    value={rateLimitPerMinute}
                    onChange={(e) => setRateLimitPerMinute(e.target.value)}
                    placeholder="Override default"
                    className="rounded-xl"
                  />
                </div>
                <div className="md:col-span-2">
                  <Button type="submit" className="rounded-xl" disabled={createMutation.isPending}>
                    {createMutation.isPending ? "Creating…" : "Create API key"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-muted-foreground text-sm">
              {keys.length} key{keys.length === 1 ? "" : "s"} loaded
              {includeInactive ? " (including inactive)" : ""}.
            </p>
            <label className="text-muted-foreground flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(e) => setIncludeInactive(e.target.checked)}
              />
              Show revoked / rotated keys
            </label>
          </div>

          <div className="space-y-3">
            {keys.map((row) => (
              <Card
                key={row.id}
                className={`border-primary/10 ${row.is_active ? "" : "opacity-80"}`}
              >
                <CardHeader className="pb-2">
                  <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                    <div>
                      <CardTitle className="text-base">{row.name}</CardTitle>
                      <CardDescription className="font-mono text-xs">
                        Key id {row.id} · {row.is_active ? "Active" : "Inactive"}
                      </CardDescription>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="rounded-xl"
                        disabled={auditLoadingId === row.id}
                        onClick={() => void loadAudit(row)}
                      >
                        {auditLoadingId === row.id ? "Loading…" : "Audit log"}
                      </Button>
                      {row.is_active ? (
                        <>
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            className="rounded-xl"
                            disabled={rotateMutation.isPending}
                            onClick={() => {
                              if (
                                window.confirm(
                                  "Rotate this key? The current secret will stop working immediately."
                                )
                              ) {
                                rotateMutation.mutate(row.id);
                              }
                            }}
                          >
                            Rotate
                          </Button>
                          <Button
                            type="button"
                            variant="destructive"
                            size="sm"
                            className="rounded-xl"
                            disabled={revokeMutation.isPending}
                            onClick={() => {
                              if (window.confirm("Revoke this key? This cannot be undone.")) {
                                revokeMutation.mutate(row.id);
                              }
                            }}
                          >
                            Revoke
                          </Button>
                        </>
                      ) : (
                        <span className="text-muted-foreground text-xs font-medium">Inactive</span>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="text-muted-foreground grid gap-1 text-xs sm:grid-cols-2">
                  <div>
                    <span className="text-foreground font-medium">Scopes</span>{" "}
                    {row.scopes.length ? row.scopes.join(", ") : "—"}
                  </div>
                  <div>
                    <span className="text-foreground font-medium">Created</span>{" "}
                    {formatDt(row.created_at)}
                  </div>
                  <div>
                    <span className="text-foreground font-medium">Expires</span>{" "}
                    {formatDt(row.expiresAt)}
                  </div>
                  <div>
                    <span className="text-foreground font-medium">Revoked</span>{" "}
                    {formatDt(row.revokedAt)}
                  </div>
                  <div>
                    <span className="text-foreground font-medium">Last used</span>{" "}
                    {formatDt(row.lastUsedAt)}
                  </div>
                  <div>
                    <span className="text-foreground font-medium">Rate limit / min</span>{" "}
                    {row.rate_limit_per_minute ?? "default"}
                  </div>
                </CardContent>
              </Card>
            ))}
            {!keys.length && keysQuery.isSuccess ? (
              <p className="text-muted-foreground text-sm">No API keys yet. Create one above.</p>
            ) : null}
          </div>
        </>
      ) : null}

      {auditForKey ? (
        <Card className="border-primary/10">
          <CardHeader className="flex flex-row items-start justify-between space-y-0">
            <div>
              <CardTitle className="text-base">Audit: {auditForKey.label}</CardTitle>
              <CardDescription>Recent events for this key (newest first).</CardDescription>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="rounded-xl"
              onClick={() => setAuditForKey(null)}
            >
              Close
            </Button>
          </CardHeader>
          <CardContent className="max-h-80 space-y-2 overflow-y-auto text-xs">
            {auditForKey.events.length === 0 ? (
              <p className="text-muted-foreground">No audit events yet.</p>
            ) : (
              auditForKey.events.map((ev) => (
                <div key={ev.id} className="bg-muted/40 rounded-lg border p-2">
                  <div className="flex flex-wrap justify-between gap-1">
                    <span className="font-mono font-medium">{ev.action}</span>
                    <span className="text-muted-foreground">{formatDt(ev.created_at)}</span>
                  </div>
                  {ev.actorEmail ? (
                    <div className="text-muted-foreground mt-1">Actor: {ev.actorEmail}</div>
                  ) : null}
                  {Object.keys(ev.metadata).length > 0 ? (
                    <pre className="bg-background/80 mt-2 max-h-24 overflow-auto rounded p-2">
                      {JSON.stringify(ev.metadata, null, 2)}
                    </pre>
                  ) : null}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
