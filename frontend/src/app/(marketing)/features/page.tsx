import { Bot, ChartColumnBig, MessageSquareText, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

const featureGroups = [
  {
    title: "Voice capture",
    description: "Turn WhatsApp voice notes into structured records without forcing teams to change how they report.",
    detail: "Talk2Record keeps transcript, confidence, payment context, and extracted entities in one reviewable record.",
    icon: MessageSquareText,
  },
  {
    title: "Reliable review",
    description: "Prioritize low-confidence entries before they affect billing, stock, or customer updates.",
    detail: "Operators can quickly confirm or correct the details that matter most to downstream workflows.",
    icon: ShieldCheck,
  },
  {
    title: "Operational analytics",
    description: "Track volume, revenue, processing quality, and trends from one calm dashboard.",
    detail: "Managers get the visibility they need without waiting for manual spreadsheets to be cleaned up.",
    icon: ChartColumnBig,
  },
  {
    title: "Invisible AI",
    description: "Use AI where it helps, but keep the product predictable, understandable, and globally friendly.",
    detail: "Branding, copy, and workflows stay practical so the automation feels trustworthy instead of experimental.",
    icon: Bot,
  },
];

export default function FeaturesPage() {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <div className="brand-panel rounded-4xl border border-primary/10 p-8">
        <div className="max-w-3xl space-y-4">
          <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-sm font-medium">
            Product capabilities
          </div>
          <h1 className="max-w-3xl text-balance">
            Built for teams that need records, not more admin work
          </h1>
          <p className="text-muted-foreground text-lg">
            Talk2Record combines voice capture, structured extraction, review workflows, analytics, and integrations in one brand-consistent workspace.
          </p>
        </div>
      </div>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        {featureGroups.map((feature) => {
          const Icon = feature.icon;

          return (
            <Card key={feature.title} className="border-primary/10">
              <CardHeader>
                <div className="bg-primary/10 text-primary flex h-11 w-11 items-center justify-center rounded-2xl">
                  <Icon className="h-5 w-5" />
                </div>
                <CardTitle className="pt-2">{feature.title}</CardTitle>
                <CardDescription>{feature.description}</CardDescription>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {feature.detail}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
