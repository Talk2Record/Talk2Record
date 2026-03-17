"use client";

import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, CartesianGrid, LineChart, Line, PieChart, Pie, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { analyticsService } from "@/services/platform-service";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

const COLORS = ["#18181b", "#52525b", "#71717a", "#a1a1aa"];

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics"],
    queryFn: analyticsService.getSnapshot,
  });

  if (isLoading || !data) {
    return <div>Loading analytics...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1>Analytics</h1>
        <p className="text-muted-foreground">
          Review sales per day, product mix, revenue trends, and voice processing performance.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Sales per day</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.salesPerDay}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="label" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#18181b" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Revenue trends</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.revenueTrends}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="label" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#18181b" strokeWidth={3} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sales by product</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.salesPerProduct} dataKey="value" nameKey="label" outerRadius={90}>
                  {data.salesPerProduct.map((entry, index) => (
                    <Cell key={entry.label} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Processing stats</CardTitle>
            <CardDescription>Heatmap and product analytics remain abstracted behind feature-safe adapters.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {data.processingStats.map((stat) => (
              <div key={stat.label} className="rounded-xl border p-4">
                <p className="font-medium">{stat.label}</p>
                <p className="text-2xl font-semibold">{stat.value}%</p>
              </div>
            ))}
            <div className="rounded-xl border p-4">
              <p className="font-medium">Heatmap summary</p>
              <ul className="mt-2 space-y-2 text-sm text-muted-foreground">
                {data.heatmapSummary.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
