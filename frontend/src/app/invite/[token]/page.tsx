"use client";

import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Mail, ShieldCheck } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Skeleton } from "@/shared/ui/skeleton";
import { toast } from "@/shared/hooks/use-toast";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { teamService } from "@/services/team-service";
import { ORGANIZATIONS_QUERY_KEY } from "@/shared/hooks/use-organizations";
import { useOrgStore } from "@/store/org-store";
import { notifyApiError } from "@/shared/lib/notify-api-error";

/**
 * Invitation acceptance flow.
 *
 *   - Unauthenticated visitors are nudged to login/register with the invite
 *     URL preserved in `?redirect=`. Both auth pages already honour that
 *     param via `sanitizeRedirect`.
 *   - Authenticated visitors see a confirmation card. If the invited email
 *     doesn't match the logged-in user, we tell them rather than silently
 *     swallowing the mismatch.
 *   - On accept we invalidate the org list, set the new org as active, and
 *     push the user into the dashboard.
 */
export default function InviteAcceptPage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading, user } = useAuth();
  const setActiveOrg = useOrgStore((state) => state.setActiveOrg);

  const token = params?.token ?? "";

  const lookupQuery = useQuery({
    queryKey: ["invitation", token],
    queryFn: () => teamService.lookupInvitation(token),
    enabled: Boolean(token),
    retry: false,
    staleTime: 30_000,
  });

  const acceptMutation = useMutation({
    mutationFn: () => teamService.acceptInvitation(token),
    onSuccess: (membership) => {
      toast({
        title: "Invitation accepted",
        description: `You've joined ${membership.organization.name}.`,
      });
      setActiveOrg({
        id: membership.organization.id,
        slug: membership.organization.slug,
      });
      void queryClient.invalidateQueries({ queryKey: ORGANIZATIONS_QUERY_KEY });
      // Drop everything else so the dashboard repaints under the new org.
      void queryClient.invalidateQueries({
        predicate: (q) =>
          Array.isArray(q.queryKey) &&
          q.queryKey[0] !== "auth" &&
          q.queryKey[0] !== "organizations",
      });
      router.replace("/dashboard");
    },
    onError: (caughtError) => notifyApiError(caughtError, { title: "Could not accept invitation" }),
  });

  // Whether the logged-in user's email matches the invited email. Pure
  // derivation from store and query state — no need for memoization.
  const invitationEmail = lookupQuery.data?.email;
  const userEmail = user?.email;
  const emailMatches =
    Boolean(invitationEmail) &&
    Boolean(userEmail) &&
    userEmail!.toLowerCase() === invitationEmail!.toLowerCase();

  if (!token) {
    return (
      <div className="bg-muted/30 flex min-h-screen items-center justify-center px-4">
        <Card className="border-destructive/40 max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Missing invitation token</CardTitle>
            <CardDescription>
              The invite link you opened is incomplete. Ask the inviter to send a fresh link.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  if (lookupQuery.isLoading || isLoading) {
    return (
      <div className="bg-muted/30 flex min-h-screen items-center justify-center px-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <Skeleton className="h-5 w-1/2" />
            <Skeleton className="h-4 w-2/3" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-9 w-32 rounded-xl" />
          </CardContent>
        </Card>
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
                : "This invitation link is no longer valid. Ask the inviter to send a new one."}
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  const invitation = lookupQuery.data;
  if (!invitation) return null;

  const inviteRedirect = `/invite/${encodeURIComponent(token)}`;

  return (
    <div className="bg-muted/30 flex min-h-screen items-center justify-center px-4 py-10">
      <Card className="border-primary/20 w-full max-w-md">
        <CardHeader>
          <div className="bg-primary/10 text-primary inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-xs font-medium">
            <Mail className="h-3.5 w-3.5" />
            Workspace invitation
          </div>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="text-primary h-5 w-5" />
            Join {invitation.organization.name}
          </CardTitle>
          <CardDescription>
            Role: <strong>{invitation.role}</strong> · Invited email: {invitation.email}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          {invitation.status !== "pending" ? (
            <p className="text-muted-foreground">
              This invitation is <strong>{invitation.status}</strong>. Ask the inviter to send a
              fresh link.
            </p>
          ) : !isAuthenticated ? (
            <>
              <p className="text-muted-foreground">
                Sign in (or create an account) using <strong>{invitation.email}</strong> to accept
                this invitation.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button asChild className="rounded-xl">
                  <a href={`/login?redirect=${encodeURIComponent(inviteRedirect)}`}>Sign in</a>
                </Button>
                <Button asChild variant="outline" className="rounded-xl">
                  <a href={`/register?redirect=${encodeURIComponent(inviteRedirect)}`}>
                    Create account
                  </a>
                </Button>
              </div>
            </>
          ) : !emailMatches ? (
            <div className="space-y-3">
              <div className="border-destructive/30 bg-destructive/10 text-destructive flex items-start gap-2 rounded-xl border p-3">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  You're signed in as <strong>{user?.email}</strong>, but this invitation was sent
                  to <strong>{invitation.email}</strong>. Sign out and use the invited address.
                </div>
              </div>
              <Button asChild variant="outline" className="rounded-xl">
                <a href={`/login?redirect=${encodeURIComponent(inviteRedirect)}`}>
                  Switch accounts
                </a>
              </Button>
            </div>
          ) : (
            <>
              <p className="text-muted-foreground">
                Accept to join <strong>{invitation.organization.name}</strong> as{" "}
                <strong>{invitation.role}</strong>.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  className="rounded-xl"
                  disabled={acceptMutation.isPending}
                  onClick={() => acceptMutation.mutate()}
                >
                  {acceptMutation.isPending ? "Accepting…" : "Accept invitation"}
                </Button>
                <Button
                  asChild
                  variant="outline"
                  className="rounded-xl"
                  disabled={acceptMutation.isPending}
                >
                  <a href="/dashboard">Decide later</a>
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
