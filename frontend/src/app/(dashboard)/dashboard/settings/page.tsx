"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { settingsService } from "@/services/platform-service";
import { usePreferencesStore } from "@/store/preferences-store";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

export default function SettingsPage() {
  const currency = usePreferencesStore((state) => state.currency);
  const setCurrency = usePreferencesStore((state) => state.setCurrency);
  const { data, isLoading } = useQuery({
    queryKey: ["settings-profile"],
    queryFn: settingsService.getProfile,
  });
  const [saved, setSaved] = useState(false);

  if (isLoading || !data) {
    return <div className="text-muted-foreground">Loading settings...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-xs font-medium">
          Workspace controls
        </div>
        <h1>Settings</h1>
        <p className="text-muted-foreground">Manage workspace details, locale defaults, and account preferences.</p>
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Company profile</CardTitle>
          <CardDescription>These fields can map directly to future Django profile endpoints.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="company">Company</Label>
            <Input id="company" defaultValue={data.company} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="email">Contact email</Label>
            <Input id="email" defaultValue={data.contactEmail} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="timezone">Timezone</Label>
            <Input id="timezone" defaultValue={data.timezone} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="currency">Default currency</Label>
            <Input
              id="currency"
              value={currency}
              onChange={(event) => setCurrency(event.target.value as typeof currency)}
            />
          </div>
          <Button
            className="rounded-xl md:col-span-2 md:w-fit"
            onClick={() => {
              setSaved(true);
            }}
          >
            Save preferences
          </Button>
          {saved ? <p className="text-sm text-muted-foreground md:col-span-2">Preferences saved locally for this mock workspace.</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
