import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { LegalDocumentPage } from "@/components/legal/legal-document-page";
import { getLegalDocument, legalDocuments } from "@/shared/lib/legal-content";
import { siteConfig } from "@/shared/lib/config/site";

interface LegalDocumentPageProps {
  params: Promise<{
    slug: string;
  }>;
}

export function generateStaticParams() {
  return legalDocuments.map((document) => ({ slug: document.slug }));
}

export async function generateMetadata({ params }: LegalDocumentPageProps): Promise<Metadata> {
  const { slug } = await params;
  const document = getLegalDocument(slug);

  if (!document) {
    return {
      title: `Legal | ${siteConfig.appName}`,
    };
  }

  return {
    title: `${document.shortTitle} | ${siteConfig.appName}`,
    description: document.description,
    alternates: {
      canonical: `/legal/${document.slug}`,
    },
  };
}

export default async function LegalPolicyPage({ params }: LegalDocumentPageProps) {
  const { slug } = await params;
  const document = getLegalDocument(slug);

  if (!document) {
    notFound();
  }

  return <LegalDocumentPage document={document} />;
}
