import Link from "next/link";
import { legalContactEmail } from "@/shared/lib/legal-content";

export function MarketingFooter() {
  return (
    <footer className="border-border/80 mt-auto border-t bg-background/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8 text-sm text-muted-foreground sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-2">
            <div className="inline-flex rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
              Talk2Record
            </div>
            <p className="max-w-xl text-foreground text-base font-medium">
              Turn conversations into structured business intelligence.
            </p>
            <p className="max-w-2xl">
              Capture voice notes, review clean records, and keep operations, billing, and analytics in sync.
            </p>
          </div>
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Global, calm, reliable AI</p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <Link href="/features">Features</Link>
          <Link href="/pricing">Pricing</Link>
          <Link href="/docs">Docs</Link>
          <Link href="/legal">Legal center</Link>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-xs">
          <Link href="/legal/privacy-policy">Privacy</Link>
          <Link href="/legal/terms-of-service">Terms</Link>
          <Link href="/legal/data-processing-agreement">DPA</Link>
          <Link href="/legal/ai-usage-disclaimer">AI policy</Link>
          <Link href="/legal/cookie-policy">Cookies</Link>
          <Link href="/legal/acceptable-use-policy">Acceptable use</Link>
          <Link href="/legal/billing-policy">Billing</Link>
        </div>
        <p className="text-xs">
          Legal and enterprise requests:{" "}
          <a className="text-primary hover:underline" href={`mailto:${legalContactEmail}`}>
            {legalContactEmail}
          </a>
        </p>
        <div className="text-xs text-muted-foreground/80">
          AI outputs require human review before business, compliance, or financial reliance.
        </div>
      </div>
    </footer>
  );
}
