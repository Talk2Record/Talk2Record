import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";

const docsCards = [
  "Voice ingestion and record extraction flow",
  "Dashboard metrics, review queues, and table behavior",
  "Integrations for WhatsApp, billing, Sheets, Zapier, and webhooks",
  "Pricing logic, billing handoff, and workspace setup guidance",
];

export default function DocsPage() {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <div className="max-w-3xl space-y-4">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-sm font-medium">
          Documentation
        </div>
        <h1>Everything your team needs to understand the workflow</h1>
        <p className="text-muted-foreground text-lg">
          Use the docs to align product, engineering, and operations around how Talk2Record captures
          voice, structures records, and routes them into downstream actions.
        </p>
      </div>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        {docsCards.map((item) => (
          <Card key={item} className="border-primary/10">
            <CardHeader>
              <CardTitle className="text-lg">{item}</CardTitle>
            </CardHeader>
            <CardContent className="text-muted-foreground text-sm">
              Reference the shared service contracts in `src/services` and `src/types` when
              connecting real backend endpoints and preserving the brand-driven UX patterns across
              the app.
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
