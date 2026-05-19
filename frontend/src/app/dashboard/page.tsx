"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardService } from "@/services/platform-service";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import DashboardLoading from "@/app/dashboard/loading";
import { OnboardingCard } from "@/components/dashboard/onboarding-card";
import { UsageCard } from "@/components/billing/usage-card";

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: dashboardService.getOverview,
  });

  if (isLoading || !data) {
    return <DashboardLoading />;
  }

  return (
    <div className="space-y-6">
      <OnboardingCard />

      <div className="space-y-2">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-xs font-medium">
          Executive overview
        </div>
        <h1>Operations overview</h1>
        <p className="text-muted-foreground">
          Monitor extraction quality, review queues, and the speed at which voice becomes usable
          business data.
        </p>
      </div>

      <UsageCard />

      <div className="grid gap-4 lg:grid-cols-4">
        {data.metrics.map((metric) => (
          <Card key={metric.label} className="border-primary/10">
            <CardHeader>
              <CardDescription>{metric.label}</CardDescription>
              <CardTitle className="text-3xl">{metric.value}</CardTitle>
            </CardHeader>
            <CardContent>
              <span
                className={
                  metric.tone === "positive"
                    ? "text-sm text-emerald-600"
                    : "text-muted-foreground text-sm"
                }
              >
                {metric.delta}
              </span>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Recent processing activity</CardTitle>
          <CardDescription>Latest records flowing from WhatsApp into Talk2Record.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.activities.map((activity) => (
            <div
              key={activity.id}
              className="border-primary/10 bg-background/80 flex flex-col gap-2 rounded-2xl border p-4 md:flex-row md:items-center md:justify-between"
            >
              <div>
                <p className="font-medium">{activity.customer}</p>
                <p className="text-muted-foreground text-sm">{activity.transcriptSnippet}</p>
              </div>
              <div className="text-muted-foreground text-sm">
                <p>{activity.status}</p>
                <p>{new Date(activity.createdAt).toLocaleString()}</p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
