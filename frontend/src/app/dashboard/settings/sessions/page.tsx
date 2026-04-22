"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Monitor } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { toast } from "@/shared/hooks/use-toast";
import { sessionService } from "@/services/team-service";
import type { SessionRow } from "@/types/platform";

function formatDt(value: string | null) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export default function SessionsPage() {
  const queryClient = useQueryClient();
  const sessionsQuery = useQuery({
    queryKey: ["auth", "sessions"],
    queryFn: () => sessionService.list(),
  });

  const revokeMutation = useMutation({
    mutationFn: (id: number) => sessionService.revoke(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["auth", "sessions"] });
      toast({ title: "Session revoked" });
    },
    onError: (error: Error) => {
      toast({ title: "Revoke failed", description: error.message, variant: "destructive" });
    },
  });

  const sessions: SessionRow[] = sessionsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <div className="bg-primary/10 text-primary inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-xs font-medium">
            <Monitor className="h-3.5 w-3.5" />
            Sessions
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Active sessions</h1>
          <p className="text-muted-foreground max-w-2xl text-sm">
            Devices and browsers where your account is signed in. Revoke anything you don&apos;t
            recognize.
          </p>
        </div>
        <Button variant="outline" className="rounded-xl" asChild>
          <Link href="/dashboard/settings">← Back to settings</Link>
        </Button>
      </div>

      <div className="space-y-2">
        {sessions.map((session) => {
          const revoked = session.revoked_at !== null;
          return (
            <Card key={session.id} className={`border-primary/10 ${revoked ? "opacity-70" : ""}`}>
              <CardHeader className="pb-2">
                <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                  <div>
                    <CardTitle className="text-base">
                      {session.user_agent.split(" ")[0] || "Unknown client"}
                      {session.isCurrent ? " (this device)" : ""}
                    </CardTitle>
                    <CardDescription>
                      {session.ip_address ?? "—"} · Started {formatDt(session.created_at)}
                    </CardDescription>
                  </div>
                  {!revoked && !session.isCurrent ? (
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      className="rounded-xl"
                      disabled={revokeMutation.isPending}
                      onClick={() => {
                        if (window.confirm("Sign out this device?")) {
                          revokeMutation.mutate(session.id);
                        }
                      }}
                    >
                      Revoke
                    </Button>
                  ) : revoked ? (
                    <span className="text-muted-foreground text-xs font-medium">
                      Revoked {formatDt(session.revoked_at)}
                    </span>
                  ) : null}
                </div>
              </CardHeader>
              <CardContent className="text-muted-foreground grid gap-1 text-xs sm:grid-cols-2">
                <div>
                  <span className="text-foreground font-medium">User agent</span>{" "}
                  <span className="break-all">{session.user_agent || "—"}</span>
                </div>
                <div>
                  <span className="text-foreground font-medium">Expires</span>{" "}
                  {formatDt(session.expires_at)}
                </div>
              </CardContent>
            </Card>
          );
        })}
        {sessions.length === 0 && sessionsQuery.isSuccess ? (
          <p className="text-muted-foreground text-sm">No active sessions recorded.</p>
        ) : null}
      </div>
    </div>
  );
}
