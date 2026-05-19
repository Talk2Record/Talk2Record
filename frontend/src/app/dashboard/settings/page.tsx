"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { settingsService } from "@/services/platform-service";
import { ONBOARDING_STEPS_QUERY_KEY } from "@/shared/hooks/use-onboarding";
import { usePreferencesStore } from "@/store/preferences-store";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import type { SettingsProfile } from "@/types/platform";
import SettingsLoading from "@/app/dashboard/settings/loading";

export default function SettingsPage() {
  const setCurrency = usePreferencesStore((state) => state.setCurrency);
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["settings-profile"],
    queryFn: settingsService.getProfile,
  });
  const [draft, setDraft] = useState<SettingsProfile | null>(null);
  const [status, setStatus] = useState("");

  const updateProfile = useMutation({
    mutationFn: settingsService.updateProfile,
    onSuccess: (nextProfile) => {
      queryClient.setQueryData(["settings-profile"], nextProfile);
      void queryClient.invalidateQueries({ queryKey: ONBOARDING_STEPS_QUERY_KEY });
      setDraft(null);
      setCurrency(nextProfile.defaultCurrency);
      setStatus("Preferences saved.");
    },
    onError: (error) => {
      setStatus(error instanceof Error ? error.message : "Unable to save preferences.");
    },
  });

  const form = draft ?? data;

  if (isLoading || !form) {
    return <SettingsLoading />;
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-xs font-medium">
          Workspace controls
        </div>
        <h1>Settings</h1>
        <p className="text-muted-foreground">
          Manage workspace details, locale defaults, and account preferences.
        </p>
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>API keys</CardTitle>
          <CardDescription>
            Issue scoped keys for public ingestion and integrations. Owners and admins only.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" className="rounded-xl" asChild>
            <Link href="/dashboard/settings/api-keys">Manage API keys</Link>
          </Button>
        </CardContent>
      </Card>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Company profile</CardTitle>
          <CardDescription>
            Workspace profile, timezone, and currency now persist through the backend settings API.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="company">Company</Label>
            <Input
              id="company"
              value={form.company}
              onChange={(event) => setDraft({ ...form, company: event.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="email">Contact email</Label>
            <Input
              id="email"
              value={form.contactEmail}
              onChange={(event) => setDraft({ ...form, contactEmail: event.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="timezone">Timezone</Label>
            <Input
              id="timezone"
              value={form.timezone}
              onChange={(event) => setDraft({ ...form, timezone: event.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="currency">Default currency</Label>
            <Input
              id="currency"
              value={form.defaultCurrency}
              onChange={(event) =>
                setDraft({
                  ...form,
                  defaultCurrency: event.target.value as typeof form.defaultCurrency,
                })
              }
            />
          </div>
          <Button
            className="rounded-xl md:col-span-2 md:w-fit"
            disabled={updateProfile.isPending}
            onClick={() => {
              setStatus("");
              updateProfile.mutate(form);
            }}
          >
            {updateProfile.isPending ? "Saving..." : "Save preferences"}
          </Button>
          {status ? <p className="text-muted-foreground text-sm md:col-span-2">{status}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
