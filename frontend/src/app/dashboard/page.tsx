"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardService } from "@/services/platform-service";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: dashboardService.getOverview,
  });

  if (isLoading || !data) {
    return <div className="text-muted-foreground">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-xs font-medium">
          Executive overview
        </div>
        <h1>Operations overview</h1>
        <p className="text-muted-foreground">
          Monitor extraction quality, review queues, and the speed at which voice becomes usable business data.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        {data.metrics.map((metric) => (
          <Card key={metric.label} className="border-primary/10">
            <CardHeader>
              <CardDescription>{metric.label}</CardDescription>
              <CardTitle className="text-3xl">{metric.value}</CardTitle>
            </CardHeader>
            <CardContent>
              <span
                className={metric.tone === "positive" ? "text-sm text-emerald-600" : "text-sm text-muted-foreground"}
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
              className="flex flex-col gap-2 rounded-2xl border border-primary/10 bg-background/80 p-4 md:flex-row md:items-center md:justify-between"
            >
              <div>
                <p className="font-medium">{activity.customer}</p>
                <p className="text-sm text-muted-foreground">{activity.transcriptSnippet}</p>
              </div>
              <div className="text-sm text-muted-foreground">
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
