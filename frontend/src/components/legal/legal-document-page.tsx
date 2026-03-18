import Link from "next/link";
import { legalBusinessAddress, legalContactEmail, legalDocuments, legalEntity, legalLastUpdated, type LegalDocument } from "@/shared/lib/legal-content";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

interface LegalDocumentPageProps {
  document: LegalDocument;
}

export function LegalDocumentPage({ document }: LegalDocumentPageProps) {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_18rem] lg:items-start">
        <main className="space-y-6">
          <section className="brand-panel rounded-4xl border border-primary/10 p-8">
            <div className="max-w-4xl space-y-4">
              <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-sm font-medium">
                Legal
              </div>
              <h1 className="max-w-4xl text-balance">{document.shortTitle}</h1>
              <p className="text-muted-foreground max-w-3xl text-lg">{document.summary}</p>
            </div>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <Card className="border-primary/10">
                <CardHeader>
                  <CardTitle className="text-base">Last updated</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">{legalLastUpdated}</CardContent>
              </Card>
              <Card className="border-primary/10">
                <CardHeader>
                  <CardTitle className="text-base">Contact</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  <a className="text-primary hover:underline" href={`mailto:${legalContactEmail}`}>
                    {legalContactEmail}
                  </a>
                </CardContent>
              </Card>
              <Card className="border-primary/10">
                <CardHeader>
                  <CardTitle className="text-base">Entity</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">{legalEntity}</CardContent>
              </Card>
            </div>
            <p className="text-muted-foreground mt-4 text-sm">{legalBusinessAddress}</p>
          </section>

          {document.sections.map((section, index) => (
            <Card key={section.title} className="border-primary/10">
              <CardHeader>
                <CardTitle className="text-xl">
                  {index + 1}. {section.title}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm text-muted-foreground">
                {section.paragraphs.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
                {section.bullets ? (
                  <ul className="space-y-2 pl-5">
                    {section.bullets.map((bullet) => (
                      <li key={bullet} className="list-disc">
                        {bullet}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </main>

        <aside className="lg:sticky lg:top-24">
          <Card className="border-primary/10">
            <CardHeader>
              <CardTitle>Legal center</CardTitle>
              <CardDescription>Browse every public policy and agreement.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {legalDocuments.map((item) => (
                <Link
                  key={item.slug}
                  href={`/legal/${item.slug}`}
                  className={`block rounded-xl px-3 py-2 transition-colors ${
                    item.slug === document.slug
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  }`}
                >
                  {item.shortTitle}
                </Link>
              ))}
              <div className="border-border/80 mt-4 border-t pt-4 text-muted-foreground">
                <p>A current subprocessor list is available on request.</p>
                <p className="mt-2">
                  Email{" "}
                  <a className="text-primary hover:underline" href={`mailto:${legalContactEmail}`}>
                    {legalContactEmail}
                  </a>
                  .
                </p>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}
