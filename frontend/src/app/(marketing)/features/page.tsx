import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

const featureGroups = [
  {
    title: "Capture and extraction",
    description: "Convert WhatsApp voice notes into structured records with transcript and confidence metadata.",
  },
  {
    title: "Operations dashboard",
    description: "Review records, track recent processing, and identify revenue and queue bottlenecks fast.",
  },
  {
    title: "Analytics and heatmaps",
    description: "Measure sales trends, product performance, and onboarding friction with instrumentation hooks.",
  },
  {
    title: "Integrations and billing",
    description: "Prepare for Stripe, Paddle, Sheets, Zapier, and webhook workflows without storing secrets client-side.",
  },
];

export default function FeaturesPage() {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="max-w-3xl space-y-3">
        <h1>Everything needed for a Talk2Record MVP</h1>
        <p className="text-muted-foreground">
          The frontend is structured around marketing, onboarding, dashboard operations, analytics, and billing so the Django API can slot in later without a UI rewrite.
        </p>
      </div>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        {featureGroups.map((feature) => (
          <Card key={feature.title}>
            <CardHeader>
              <CardTitle>{feature.title}</CardTitle>
              <CardDescription>{feature.description}</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Mock-backed services, React Query, Zustand preferences, and locale-aware pricing are all wired in.
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
