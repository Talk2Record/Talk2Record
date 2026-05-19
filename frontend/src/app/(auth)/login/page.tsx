"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import Link from "next/link";
import { PasswordInput } from "@/shared/ui/password-input";
import { getTranslations } from "@/shared/lib/i18n/get-translations";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { useLanguage } from "@/shared/lib/i18n/language-context";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { useTranslations } from "@/shared/lib/i18n/use-translations";
import { sanitizeRedirect } from "@/shared/lib/auth/safe-redirect";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { locale } = useLanguage();
  const { login, signInWithGoogle, isGoogleEnabled, isLoading } = useAuth();
  const messages = getTranslations(locale);
  const { t } = useTranslations(messages);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const redirectTarget = useMemo(
    () => sanitizeRedirect(searchParams?.get("redirect")),
    [searchParams]
  );

  const sessionReason = searchParams?.get("reason");
  const expiredNotice =
    sessionReason === "expired" ? "Your session expired. Please sign in again." : null;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    try {
      const user = await login(email, password);
      const destination = redirectTarget
        ? redirectTarget
        : user.onboardingCompleted
          ? "/dashboard"
          : "/onboarding";
      router.push(destination);
    } catch (submissionError) {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : t("auth.login.invalidCredentials")
      );
    }
  }

  return (
    <Card className="border-primary/10 w-full max-w-md shadow-(--shadow-lg)">
      <CardHeader>
        <div className="bg-primary/10 text-primary inline-flex w-fit rounded-full px-3 py-1 text-xs font-medium">
          Welcome back
        </div>
        <CardTitle>{t("auth.login.title")}</CardTitle>
        <CardDescription>
          Sign in to review extracted records, analytics, and billing activity from one calm
          workspace.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {expiredNotice ? (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-300">
            {expiredNotice}
          </div>
        ) : null}
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid gap-2">
            <Label htmlFor="email">{t("auth.login.email")}</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder={t("auth.login.emailPlaceholder")}
              required
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="password">{t("auth.login.password")}</Label>
            <PasswordInput
              id="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t("auth.login.passwordPlaceholder")}
              required
            />
          </div>
          {error ? <p className="text-destructive text-sm">{error}</p> : null}
          <Button className="w-full rounded-xl" disabled={isLoading} type="submit">
            {t("auth.login.submit")}
          </Button>
        </form>

        {isGoogleEnabled ? (
          <Button
            className="w-full rounded-xl"
            variant="outline"
            onClick={() => signInWithGoogle()}
          >
            {t("auth.login.signInWithGoogle")}
          </Button>
        ) : null}

        <div className="flex items-center justify-between text-sm">
          <Link className="text-primary" href="/forgot-password">
            {t("auth.login.forgotPassword")}
          </Link>
          <Link
            className="text-primary"
            href={
              redirectTarget
                ? `/register?redirect=${encodeURIComponent(redirectTarget)}`
                : "/register"
            }
          >
            {t("auth.login.signUp")}
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
