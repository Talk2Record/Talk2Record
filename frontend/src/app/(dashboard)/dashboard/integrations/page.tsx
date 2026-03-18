"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { integrationsService } from "@/services/platform-service";
import { trackEvent } from "@/lib/analytics";
import { getHeatmapAdapter } from "@/lib/heatmap";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";

export default function IntegrationsPage() {
  const heatmap = getHeatmapAdapter();
  const { data = [], isLoading } = useQuery({
    queryKey: ["integrations"],
    queryFn: integrationsService.list,
  });
  const [status, setStatus] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [secret, setSecret] = useState("");
  const [confirmedPermission, setConfirmedPermission] = useState(false);

  async function testIntegration(id: string) {
    heatmap.trackFeatureUsage(`integration-${id}`);
    trackEvent("integration_tested", { integration: id });
    try {
      const response = await integrationsService.testConnection({
        id,
        endpoint,
        secret,
        confirmedPermission,
      });
      setStatus(response.maskedSecret ? `${response.status} Secret stored as ${response.maskedSecret}` : response.status);
      setSecret("");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to test integration.");
    }
  }

  if (isLoading) {
    return <div className="text-muted-foreground">Loading integrations...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-xs font-medium">
          Connected workflows
        </div>
        <h1>Integrations</h1>
        <p className="text-muted-foreground">
          Enable WhatsApp, billing, Sheets, automation, and webhook workflows without persisting raw secrets in the browser.
        </p>
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Test connection</CardTitle>
          <CardDescription>Secrets stay in local form state only and are masked in responses.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <Input placeholder="Webhook endpoint or callback URL" value={endpoint} onChange={(event) => setEndpoint(event.target.value)} />
          <Input placeholder="API key or secret" value={secret} onChange={(event) => setSecret(event.target.value)} />
          <label className="rounded-xl border border-primary/10 bg-background/80 p-3 text-sm text-muted-foreground md:col-span-2">
            <span className="flex items-start gap-3">
              <input
                checked={confirmedPermission}
                className="mt-1 h-4 w-4 rounded border-primary/20"
                onChange={(event) => setConfirmedPermission(event.target.checked)}
                type="checkbox"
              />
              <span>
                You confirm you have permission to process this data before connecting voice or WhatsApp workflows.
                Review the{" "}
                <Link className="text-primary underline-offset-4 hover:underline" href="/legal/acceptable-use-policy">
                  Acceptable Use Policy
                </Link>
                .
              </span>
            </span>
          </label>
          {status ? <p className="text-sm text-muted-foreground md:col-span-2">{status}</p> : null}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        {data.map((integration) => (
          <Card key={integration.id} className="border-primary/10">
            <CardHeader>
              <CardTitle>{integration.name}</CardTitle>
              <CardDescription>{integration.description}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-sm text-muted-foreground">
                <p>Status: {integration.status}</p>
                <p>Last sync: {integration.lastSync}</p>
                {integration.endpoint ? <p>Endpoint: {integration.endpoint}</p> : null}
                {integration.maskedSecret ? <p>Stored secret: {integration.maskedSecret}</p> : null}
              </div>
              <Button className="rounded-xl" onClick={() => testIntegration(integration.id)}>
                Test connection
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
