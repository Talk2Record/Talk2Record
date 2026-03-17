"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, PlayCircle } from "lucide-react";
import { formatCurrency } from "@/lib/format";
import { usePreferencesStore } from "@/store/preferences-store";
import { useLanguage } from "@/shared/lib/i18n/language-context";
import { getTranslations } from "@/shared/lib/i18n/get-translations";
import { useTranslations } from "@/shared/lib/i18n/use-translations";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

const benefits = [
  "Capture sales and inventory updates from voice notes",
  "Extract customers, products, quantities, and payment methods",
  "Review low-confidence entries before they hit operations",
  "Push records into billing and integration workflows",
];

const pricingTiers = [
  { name: "Starter", monthly: 19, notes: "500 voice notes / month" },
  { name: "Growth", monthly: 49, notes: "1,500 voice notes / month" },
  { name: "Scale", monthly: 99, notes: "5,000 voice notes / month" },
];

export default function HomePage() {
  const { locale } = useLanguage();
  const currency = usePreferencesStore((state) => state.currency);
  const messages = getTranslations(locale);
  const { t } = useTranslations(messages);

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-12 px-4 py-10 sm:px-6 lg:px-8">
      <section className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div className="space-y-6">
          <span className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-sm font-medium">
            {t("marketing.hero.eyebrow")}
          </span>
          <div className="space-y-4">
            <h1 className="max-w-3xl text-balance">{t("marketing.hero.title")}</h1>
            <p className="text-muted-foreground max-w-2xl text-lg">
              {t("marketing.hero.subtitle")}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/register">
              <Button size="lg">
                {t("marketing.hero.primaryCta")}
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button size="lg" variant="outline">
                <PlayCircle className="h-4 w-4" />
                {t("marketing.hero.secondaryCta")}
              </Button>
            </Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {benefits.map((item) => (
              <div key={item} className="flex items-start gap-2 rounded-xl border p-4">
                <CheckCircle2 className="text-primary mt-0.5 h-4 w-4 shrink-0" />
                <span className="text-sm">{item}</span>
              </div>
            ))}
          </div>
        </div>

        <Card className="border-primary/10 bg-card/80 shadow-lg">
          <CardHeader>
            <CardTitle>{t("marketing.demo.title")}</CardTitle>
            <CardDescription>{t("marketing.demo.description")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-xl border p-4">
              <p className="text-xs uppercase text-muted-foreground">Incoming WhatsApp note</p>
              <p className="mt-2 text-sm">
                "Sold twelve cooking oil cartons to Kifaru Wholesalers. Cash on delivery.
                Deliver before lunch."
              </p>
            </div>
            <div className="rounded-xl border p-4">
              <p className="text-xs uppercase text-muted-foreground">Structured record</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs text-muted-foreground">Customer</p>
                  <p className="text-sm font-medium">Kifaru Wholesalers</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Product</p>
                  <p className="text-sm font-medium">Cooking Oil Carton</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Quantity</p>
                  <p className="text-sm font-medium">12</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Payment</p>
                  <p className="text-sm font-medium">Cash on delivery</p>
                </div>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border p-4">
                <p className="text-xs text-muted-foreground">Accuracy</p>
                <p className="text-xl font-semibold">96%</p>
              </div>
              <div className="rounded-xl border p-4">
                <p className="text-xs text-muted-foreground">Review queue</p>
                <p className="text-xl font-semibold">26</p>
              </div>
              <div className="rounded-xl border p-4">
                <p className="text-xs text-muted-foreground">Saved hours</p>
                <p className="text-xl font-semibold">18/wk</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="space-y-6">
        <div className="space-y-2">
          <p className="text-primary text-sm font-medium">{t("marketing.pricing.title")}</p>
          <h2 className="text-3xl">Localized pricing that maps to your region</h2>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {pricingTiers.map((tier) => (
            <Card key={tier.name}>
              <CardHeader>
                <CardTitle>{tier.name}</CardTitle>
                <CardDescription>{tier.notes}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-3xl font-semibold">
                  {formatCurrency(tier.monthly, currency)}
                  <span className="text-sm font-normal text-muted-foreground"> / month</span>
                </p>
                <Link href="/pricing">
                  <Button className="w-full" variant={tier.name === "Growth" ? "default" : "outline"}>
                    View plan details
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("marketing.testimonials.title")}</CardTitle>
            <CardDescription>
              Teams across operations, distribution, and field sales use Talk2Record.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <p>
              "We went from replaying hundreds of notes to approving structured records in one place."
            </p>
            <p>"Regional managers finally see the same dashboard without waiting for manual entry."</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t("marketing.faq.title")}</CardTitle>
            <CardDescription>Common questions from teams moving off manual voice-note workflows.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <p className="font-medium">Does Talk2Record store API keys in the browser?</p>
              <p className="text-muted-foreground">No. Integration secrets stay masked and are never persisted client-side.</p>
            </div>
            <div>
              <p className="font-medium">Can we review low-confidence extractions?</p>
              <p className="text-muted-foreground">Yes. Records with weaker confidence are routed to review before downstream export.</p>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
