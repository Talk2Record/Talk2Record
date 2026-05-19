"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, CheckCircle2, Cpu, KeyRound, MessageCircle, Plug } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { whatsappService, type WhatsAppAccount } from "@/services/platform-service";
import { useRole } from "@/shared/hooks/use-role";
import IntegrationsLoading from "@/app/dashboard/integrations/loading";

const STATUS_LABEL: Record<string, { label: string; tone: "ok" | "pending" | "off" }> = {
  active: { label: "Connected", tone: "ok" },
  verified: { label: "Verified", tone: "ok" },
  pending: { label: "Pending verification", tone: "pending" },
  disabled: { label: "Disabled", tone: "off" },
};

/**
 * Integrations surface. Today we only have two integrations to expose:
 *
 *   - WhatsApp Cloud API ingestion — surfaced via `GET /whatsapp/accounts/`.
 *     We render each account's verification status; setup itself happens in
 *     the Meta Business Manager (we link to the Talk2Record docs anchor).
 *
 *   - AI provider catalog — admins can connect models on
 *     `/dashboard/settings/ai`. This page just deep-links there.
 */
export default function IntegrationsPage() {
  const { atLeast } = useRole();
  const isAdmin = atLeast("admin");

  const accountsQuery = useQuery({
    queryKey: ["whatsapp", "accounts"],
    queryFn: () => whatsappService.listAccounts(),
  });

  if (accountsQuery.isLoading) {
    return <IntegrationsLoading />;
  }

  const accounts = accountsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <div className="bg-primary/10 text-primary inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-xs font-medium">
            <Plug className="h-3.5 w-3.5" />
            Integrations
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Connected services</h1>
          <p className="text-muted-foreground max-w-2xl text-sm">
            Talk2Record listens to WhatsApp business messages and routes them through your selected
            AI providers. Keep this page open when wiring a new channel.
          </p>
        </div>
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <MessageCircle className="h-4 w-4" />
            </span>
            <div>
              <CardTitle>WhatsApp Cloud API</CardTitle>
              <CardDescription>
                Inbound ingestion from your business numbers. Configured per organization.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {accountsQuery.isError ? (
            <p className="text-destructive text-sm">
              Couldn't load your WhatsApp accounts. Try refreshing the page.
            </p>
          ) : accounts.length === 0 ? (
            <div className="border-primary/10 bg-background/80 rounded-xl border p-4 text-sm">
              <p className="font-medium">No WhatsApp accounts connected yet</p>
              <p className="text-muted-foreground mt-1">
                Configure a phone number in Meta Business Manager, then point its webhook at
                Talk2Record. Once verified it will appear here automatically.
              </p>
              <Button asChild variant="outline" size="sm" className="mt-3 rounded-xl">
                <a
                  href="https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"
                  rel="noreferrer"
                  target="_blank"
                >
                  WhatsApp setup guide
                  <ArrowUpRight className="ml-1 h-3 w-3" />
                </a>
              </Button>
            </div>
          ) : (
            <ul className="space-y-2">
              {accounts.map((account) => (
                <WhatsAppAccountRow key={account.id} account={account} />
              ))}
            </ul>
          )}
          <p className="text-muted-foreground text-xs">
            Need an additional number? Talk to your admin or open a ticket — provisioning currently
            happens out of band.
          </p>
        </CardContent>
      </Card>

      <Card className="border-primary/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-violet-500/10 text-violet-600 dark:text-violet-400">
              <Cpu className="h-4 w-4" />
            </span>
            <div>
              <CardTitle>AI providers</CardTitle>
              <CardDescription>
                Connect OpenAI, Anthropic, or compatible APIs and route each task to the right
                model.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-muted-foreground text-sm">
            Manage which provider powers transcription, extraction, summarization, and embeddings.
          </p>
          {isAdmin ? (
            <Button asChild className="rounded-xl">
              <Link href="/dashboard/settings/ai">
                Open AI settings
                <ArrowUpRight className="ml-1 h-3 w-3" />
              </Link>
            </Button>
          ) : (
            <p className="text-muted-foreground text-sm">
              Only owners and admins can change AI provider configuration. Ask an admin if you need
              this updated.
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="border-primary/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <KeyRound className="h-4 w-4" />
            </span>
            <div>
              <CardTitle>Public ingestion API keys</CardTitle>
              <CardDescription>
                Issue scoped tokens so your own systems can post voice notes directly.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {isAdmin ? (
            <Button asChild variant="outline" className="rounded-xl">
              <Link href="/dashboard/settings/api-keys">
                Manage API keys
                <ArrowUpRight className="ml-1 h-3 w-3" />
              </Link>
            </Button>
          ) : (
            <p className="text-muted-foreground text-sm">
              Owners and admins manage these from settings. Ping them if you need a new key.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function WhatsAppAccountRow({ account }: { account: WhatsAppAccount }) {
  const meta = STATUS_LABEL[account.status?.toLowerCase()] ?? {
    label: account.status || "Unknown",
    tone: "off" as const,
  };

  const toneClass =
    meta.tone === "ok"
      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
      : meta.tone === "pending"
        ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
        : "bg-muted text-muted-foreground";

  return (
    <li className="border-primary/10 bg-background/80 flex flex-col gap-2 rounded-xl border p-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="text-sm font-medium">{account.display_number || account.phone_number_id}</p>
        <p className="text-muted-foreground text-xs">
          Phone number id {account.phone_number_id}
          {account.business_account_id ? ` · WABA ${account.business_account_id}` : ""}
        </p>
      </div>
      <span
        className={`${toneClass} inline-flex items-center gap-1 self-start rounded-full px-3 py-1 text-xs font-medium sm:self-auto`}
      >
        {meta.tone === "ok" ? (
          <CheckCircle2 className="h-3.5 w-3.5" />
        ) : (
          <Plug className="h-3.5 w-3.5" />
        )}
        {meta.label}
      </span>
    </li>
  );
}
