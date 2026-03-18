"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { useLanguage } from "@/shared/lib/i18n/language-context";
import { getTranslations } from "@/shared/lib/i18n/get-translations";
import { useTranslations } from "@/shared/lib/i18n/use-translations";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { PasswordInput } from "@/shared/ui/password-input";

export default function RegisterPage() {
  const router = useRouter();
  const { locale } = useLanguage();
  const { register, isLoading } = useAuth();
  const messages = getTranslations(locale);
  const { t } = useTranslations(messages);
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [acceptedRequiredTerms, setAcceptedRequiredTerms] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!acceptedRequiredTerms) {
      setError("You must accept the Terms of Service and Privacy Policy to create an account.");
      return;
    }

    try {
      await register({
        name,
        company,
        email,
        password,
        acceptedDocumentKeys: ["terms-of-service", "privacy-policy"],
      });
      router.push("/onboarding");
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Unable to create account.");
    }
  }

  return (
    <Card className="w-full max-w-md border-primary/10 shadow-(--shadow-lg)">
      <CardHeader>
        <div className="bg-primary/10 text-primary inline-flex w-fit rounded-full px-3 py-1 text-xs font-medium">
          Start your workspace
        </div>
        <CardTitle>{t("auth.register.title")}</CardTitle>
        <CardDescription>
          Set up Talk2Record for your operators, finance team, and field staff in one place.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid gap-2">
            <Label htmlFor="name">Full name</Label>
            <Input id="name" value={name} onChange={(event) => setName(event.target.value)} required />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="company">{t("auth.register.company")}</Label>
            <Input
              id="company"
              value={company}
              onChange={(event) => setCompany(event.target.value)}
              required
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="email">{t("auth.login.email")}</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="password">{t("auth.login.password")}</Label>
            <PasswordInput
              id="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          <label className="flex items-start gap-3 rounded-xl border border-primary/10 bg-background/80 p-3 text-sm">
            <input
              checked={acceptedRequiredTerms}
              className="mt-1 h-4 w-4 rounded border-primary/20"
              onChange={(event) => setAcceptedRequiredTerms(event.target.checked)}
              type="checkbox"
            />
            <span className="text-muted-foreground">
              I agree to the{" "}
              <Link className="text-primary underline-offset-4 hover:underline" href="/legal/terms-of-service">
                Terms of Service
              </Link>{" "}
              and{" "}
              <Link className="text-primary underline-offset-4 hover:underline" href="/legal/privacy-policy">
                Privacy Policy
              </Link>
              .
            </span>
          </label>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button className="w-full rounded-xl" disabled={isLoading} type="submit">
            {t("auth.register.submit")}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="text-primary">
            {t("navigation.login")}
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
