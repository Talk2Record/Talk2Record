import type { Metadata } from "next";
import Link from "next/link";
import {
  legalBusinessAddress,
  legalContactEmail,
  legalDocuments,
  legalEntity,
  legalLastUpdated,
} from "@/shared/lib/legal-content";
import { siteConfig } from "@/shared/lib/config/site";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

export const metadata: Metadata = {
  title: `Legal Center | ${siteConfig.appName}`,
  description:
    "Browse Talk2Record's privacy policy, terms of service, DPA, AI policy, cookie policy, acceptable use policy, and billing policy.",
};

const highlights = [
  "GDPR-aligned data handling and data subject rights",
  "AI disclosure, review expectations, and accountability language",
  "Global SaaS billing, subprocessor, and transfer transparency",
];

export default function LegalCenterPage() {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <section className="brand-panel border-primary/10 rounded-4xl border p-8">
        <div className="max-w-4xl space-y-4">
          <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-sm font-medium">
            Legal center
          </div>
          <h1 className="max-w-4xl text-balance">Public legal pages built for a global AI SaaS</h1>
          <p className="text-muted-foreground max-w-3xl text-lg">
            This legal center contains the public-facing policies and agreement templates for
            Talk2Record, including privacy, terms, AI disclosures, billing rules, and processor
            commitments.
          </p>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {highlights.map((item) => (
            <Card key={item} className="border-primary/10">
              <CardContent className="text-muted-foreground pt-6 text-sm">{item}</CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="mt-8 grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="grid gap-4 md:grid-cols-2">
          {legalDocuments.map((document) => (
            <Link key={document.slug} href={`/legal/${document.slug}`} className="group">
              <Card className="border-primary/10 h-full transition-transform group-hover:-translate-y-0.5">
                <CardHeader>
                  <CardTitle>{document.shortTitle}</CardTitle>
                  <CardDescription>{document.description}</CardDescription>
                </CardHeader>
                <CardContent className="text-muted-foreground text-sm">
                  <p>{document.summary}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        <Card className="border-primary/10">
          <CardHeader>
            <CardTitle>Company details</CardTitle>
            <CardDescription>
              Use these details for enterprise diligence and legal contact.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-muted-foreground space-y-3 text-sm">
            <p>
              <span className="text-foreground font-medium">Entity:</span> {legalEntity}
            </p>
            <p>
              <span className="text-foreground font-medium">Email:</span>{" "}
              <a className="text-primary hover:underline" href={`mailto:${legalContactEmail}`}>
                {legalContactEmail}
              </a>
            </p>
            <p>
              <span className="text-foreground font-medium">Address:</span> {legalBusinessAddress}
            </p>
            <p>
              <span className="text-foreground font-medium">Last updated:</span> {legalLastUpdated}
            </p>
            <div className="border-border/80 border-t pt-3">
              A current subprocessor list and enterprise paperwork support are available on request.
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
