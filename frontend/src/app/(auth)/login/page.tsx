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

export default function LoginPage() {
  const router = useRouter();
  const { locale } = useLanguage();
  const { login, signInWithGoogle, isLoading } = useAuth();
  const messages = getTranslations(locale);
  const { t } = useTranslations(messages);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    try {
      const user = await login(email, password);
      router.push(user.onboardingCompleted ? "/dashboard" : "/onboarding");
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : t("auth.login.invalidCredentials"));
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>{t("auth.login.title")}</CardTitle>
        <CardDescription>Use a valid email and any password with 6 or more characters.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
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
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button className="w-full" disabled={isLoading} type="submit">
            {t("auth.login.submit")}
          </Button>
        </form>

        <Button className="w-full" variant="outline" onClick={() => signInWithGoogle()}>
          {t("auth.login.signInWithGoogle")}
        </Button>

        <div className="flex items-center justify-between text-sm">
          <Link className="text-primary" href="/forgot-password">
            {t("auth.login.forgotPassword")}
          </Link>
          <Link className="text-primary" href="/register">
            {t("auth.login.signUp")}
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
