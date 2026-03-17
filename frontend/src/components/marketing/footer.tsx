import Link from "next/link";

export function MarketingFooter() {
  return (
    <footer className="border-border mt-auto border-t">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <div>
          <p className="font-medium text-foreground">Talk2Record</p>
          <p>WhatsApp voice notes into structured business records.</p>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/features">Features</Link>
          <Link href="/pricing">Pricing</Link>
          <Link href="/docs">Docs</Link>
        </div>
      </div>
    </footer>
  );
}
