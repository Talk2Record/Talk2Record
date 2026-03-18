"use client";

import { useState } from "react";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { useLanguage } from "@/shared/lib/i18n/language-context";
import { getTranslations } from "@/shared/lib/i18n/get-translations";
import { useTranslations } from "@/shared/lib/i18n/use-translations";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

export default function ForgotPasswordPage() {
  const { locale } = useLanguage();
  const { requestPasswordReset, isLoading } = useAuth();
  const messages = getTranslations(locale);
  const { t } = useTranslations(messages);
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await requestPasswordReset(email);
    setStatus(response.status);
  }

  return (
    <Card className="w-full max-w-md border-primary/10 shadow-(--shadow-lg)">
      <CardHeader>
        <div className="bg-primary/10 text-primary inline-flex w-fit rounded-full px-3 py-1 text-xs font-medium">
          Account recovery
        </div>
        <CardTitle>{t("auth.forgot.title")}</CardTitle>
        <CardDescription>
          Reset access to your workspace and get back to your records, analytics, and billing controls.
        </CardDescription>
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
              required
            />
          </div>
          <Button className="w-full rounded-xl" disabled={isLoading} type="submit">
            {t("auth.forgot.submit")}
          </Button>
        </form>
        {status ? <p className="text-sm text-muted-foreground">{status}</p> : null}
      </CardContent>
    </Card>
  );
}
