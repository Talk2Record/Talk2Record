"use client";

import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { toast } from "@/shared/hooks/use-toast";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { teamService } from "@/services/team-service";

export default function InviteAcceptPage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const { isAuthenticated, isLoading, user } = useAuth();

  const token = params?.token ?? "";

  const lookupQuery = useQuery({
    queryKey: ["invitation", token],
    queryFn: () => teamService.lookupInvitation(token),
    enabled: Boolean(token),
    retry: false,
  });

  const acceptMutation = useMutation({
    mutationFn: () => teamService.acceptInvitation(token),
    onSuccess: () => {
      toast({ title: "Invitation accepted" });
      router.replace("/dashboard");
    },
    onError: (error: Error) => {
      toast({ title: "Could not accept", description: error.message, variant: "destructive" });
    },
  });

  if (!token) {
    return (
      <div className="bg-muted/30 flex min-h-screen items-center justify-center px-4">
        <Card className="border-destructive/40 max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Missing invitation token</CardTitle>
          </CardHeader>
        </Card>
      </div>
    );
  }

  if (lookupQuery.isLoading || isLoading) {
    return (
      <div className="bg-muted/30 flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground text-sm">Loading invitation…</p>
      </div>
    );
  }

  if (lookupQuery.isError) {
    return (
      <div className="bg-muted/30 flex min-h-screen items-center justify-center px-4">
        <Card className="border-destructive/40 max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Invitation invalid</CardTitle>
            <CardDescription>
              {lookupQuery.error instanceof Error
                ? lookupQuery.error.message
                : "This invitation link is no longer valid."}
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  const invitation = lookupQuery.data;
  if (!invitation) return null;

  const emailMatches = user?.email?.toLowerCase() === invitation.email.toLowerCase();

  return (
    <div className="bg-muted/30 flex min-h-screen items-center justify-center px-4">
      <Card className="border-primary/20 w-full max-w-md">
        <CardHeader>
          <CardTitle>You&apos;re invited to {invitation.organization.name}</CardTitle>
          <CardDescription>
            Role: <strong>{invitation.role}</strong> · Invited email: {invitation.email}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          {invitation.status !== "pending" ? (
            <p className="text-muted-foreground">
              This invitation is {invitation.status}. Ask the inviter to send a new one.
            </p>
          ) : !isAuthenticated ? (
            <>
              <p className="text-muted-foreground">
                Sign in (or create an account) using <strong>{invitation.email}</strong> to accept
                this invitation.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button asChild className="rounded-xl">
                  <a href={`/login?redirect=/invite/${encodeURIComponent(token)}`}>Sign in</a>
                </Button>
                <Button asChild variant="outline" className="rounded-xl">
                  <a href={`/register?redirect=/invite/${encodeURIComponent(token)}`}>
                    Create account
                  </a>
                </Button>
              </div>
            </>
          ) : !emailMatches ? (
            <p className="text-destructive">
              You&apos;re signed in as {user?.email}, but this invitation was sent to{" "}
              {invitation.email}. Sign out and use the invited address.
            </p>
          ) : (
            <>
              <p className="text-muted-foreground">
                Accept to join <strong>{invitation.organization.name}</strong>.
              </p>
              <Button
                className="rounded-xl"
                disabled={acceptMutation.isPending}
                onClick={() => acceptMutation.mutate()}
              >
                {acceptMutation.isPending ? "Accepting…" : "Accept invitation"}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
