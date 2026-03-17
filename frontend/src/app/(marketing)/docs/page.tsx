import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";

const docsCards = [
  "Voice-note ingestion and record extraction flow",
  "Dashboard metrics and records table expectations",
  "Integrations contract for WhatsApp, Stripe, Paddle, Sheets, Zapier, and Webhooks",
  "Billing endpoints and checkout scaffolding",
];

export default function DocsPage() {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="max-w-3xl space-y-3">
        <h1>Docs overview</h1>
        <p className="text-muted-foreground">
          This mock-backed frontend is organized so the eventual Django endpoints can replace the placeholder routes one surface at a time.
        </p>
      </div>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        {docsCards.map((item) => (
          <Card key={item}>
            <CardHeader>
              <CardTitle className="text-lg">{item}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Reference the shared service contracts in `src/services` and `src/types` when connecting real backend endpoints.
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
