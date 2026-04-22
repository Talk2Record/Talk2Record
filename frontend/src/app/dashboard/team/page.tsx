"use client";

import { type FormEvent, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UsersRound } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { toast } from "@/shared/hooks/use-toast";
import { teamService } from "@/services/team-service";
import type { InvitationRow, MembershipRow, OrgRole } from "@/types/platform";

const ROLE_OPTIONS: { value: OrgRole; label: string; hint: string }[] = [
  { value: "operator", label: "Operator", hint: "Day-to-day access; cannot manage the team." },
  { value: "admin", label: "Admin", hint: "Can invite, remove, and change roles for non-owners." },
  { value: "owner", label: "Owner", hint: "Full control. Owners cannot be removed by admins." },
];

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

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast({ title: "Copied to clipboard" });
  } catch {
    toast({ title: "Copy failed", variant: "destructive" });
  }
}

export default function TeamPage() {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<OrgRole>("operator");
  const [revealed, setRevealed] = useState<{ label: string; link: string } | null>(null);

  const membersQuery = useQuery({
    queryKey: ["team", "members"],
    queryFn: () => teamService.listMembers(),
  });

  const invitationsQuery = useQuery({
    queryKey: ["team", "invitations"],
    queryFn: () => teamService.listInvitations(),
  });

  const inviteMutation = useMutation({
    mutationFn: (payload: { email: string; role: OrgRole }) => teamService.invite(payload),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["team"] });
      setEmail("");
      setRole("operator");
      setRevealed({
        label: `Invitation sent to ${data.invitation.email}`,
        link: data.acceptUrl,
      });
      toast({ title: "Invitation sent" });
    },
    onError: (error: Error) => {
      toast({ title: "Could not send invite", description: error.message, variant: "destructive" });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: number) => teamService.revokeInvitation(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["team", "invitations"] });
      toast({ title: "Invitation revoked" });
    },
    onError: (error: Error) => {
      toast({ title: "Revoke failed", description: error.message, variant: "destructive" });
    },
  });

  const changeRoleMutation = useMutation({
    mutationFn: ({ id, role }: { id: number; role: OrgRole }) => teamService.changeRole(id, role),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["team", "members"] });
      toast({ title: "Role updated" });
    },
    onError: (error: Error) => {
      toast({ title: "Role change failed", description: error.message, variant: "destructive" });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (id: number) => teamService.removeMember(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["team", "members"] });
      toast({ title: "Member removed" });
    },
    onError: (error: Error) => {
      toast({ title: "Remove failed", description: error.message, variant: "destructive" });
    },
  });

  const handleInvite = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) {
      toast({ title: "Email required", variant: "destructive" });
      return;
    }
    inviteMutation.mutate({ email: trimmed, role });
  };

  const members: MembershipRow[] = membersQuery.data ?? [];
  const invitations: InvitationRow[] = (invitationsQuery.data ?? []).filter(
    (row) => row.status === "pending"
  );

  const permissionDenied =
    membersQuery.isError &&
    membersQuery.error instanceof Error &&
    membersQuery.error.message.includes("403");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <div className="bg-primary/10 text-primary inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-xs font-medium">
            <UsersRound className="h-3.5 w-3.5" />
            Team
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Team members</h1>
          <p className="text-muted-foreground max-w-2xl text-sm">
            Invite teammates, change roles, and remove members. Only owners and admins can manage
            the team.
          </p>
        </div>
        <Button variant="outline" className="rounded-xl" asChild>
          <Link href="/dashboard/settings">← Back to settings</Link>
        </Button>
      </div>

      {revealed ? (
        <Card className="border-primary/30 bg-primary/5">
          <CardHeader>
            <CardTitle className="text-base">{revealed.label}</CardTitle>
            <CardDescription>
              Share this link with the invitee. They must sign in with the invited email to accept.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <pre className="bg-background max-h-40 overflow-x-auto rounded-lg border p-3 text-xs break-all">
              {revealed.link}
            </pre>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                className="rounded-xl"
                onClick={() => void copy(revealed.link)}
              >
                Copy link
              </Button>
              <Button variant="ghost" className="rounded-xl" onClick={() => setRevealed(null)}>
                Dismiss
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {permissionDenied ? (
        <Card className="border-destructive/40">
          <CardHeader>
            <CardTitle className="text-destructive">No access</CardTitle>
            <CardDescription>
              Only organization owners and admins can view or manage team members.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <>
          <Card className="border-primary/10">
            <CardHeader>
              <CardTitle>Invite a teammate</CardTitle>
              <CardDescription>
                They will receive an invitation link. Choose the role they should have.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4 md:grid-cols-3" onSubmit={handleInvite}>
                <div className="grid gap-2 md:col-span-2">
                  <Label htmlFor="invite-email">Email</Label>
                  <Input
                    id="invite-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="teammate@example.com"
                    className="rounded-xl"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="invite-role">Role</Label>
                  <select
                    id="invite-role"
                    value={role}
                    onChange={(e) => setRole(e.target.value as OrgRole)}
                    className="bg-background rounded-xl border px-3 py-2 text-sm"
                  >
                    {ROLE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="md:col-span-3">
                  <Button type="submit" className="rounded-xl" disabled={inviteMutation.isPending}>
                    {inviteMutation.isPending ? "Sending…" : "Send invitation"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {invitations.length > 0 ? (
            <Card className="border-primary/10">
              <CardHeader>
                <CardTitle>Pending invitations</CardTitle>
                <CardDescription>Waiting to be accepted.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {invitations.map((inv) => (
                  <div
                    key={inv.id}
                    className="flex flex-col justify-between gap-2 rounded-xl border p-3 sm:flex-row sm:items-center"
                  >
                    <div>
                      <p className="text-sm font-medium">{inv.email}</p>
                      <p className="text-muted-foreground text-xs">
                        Role: {inv.role} · Expires {formatDt(inv.expires_at)}
                        {inv.invitedByEmail ? ` · by ${inv.invitedByEmail}` : ""}
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      className="rounded-xl"
                      disabled={revokeMutation.isPending}
                      onClick={() => {
                        if (window.confirm("Revoke this invitation?")) {
                          revokeMutation.mutate(inv.id);
                        }
                      }}
                    >
                      Revoke
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}

          <Card className="border-primary/10">
            <CardHeader>
              <CardTitle>Members</CardTitle>
              <CardDescription>{members.length} active teammates.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {members.map((member) => (
                <div
                  key={member.id}
                  className="flex flex-col justify-between gap-2 rounded-xl border p-3 sm:flex-row sm:items-center"
                >
                  <div>
                    <p className="text-sm font-medium">{member.userName || member.userEmail}</p>
                    <p className="text-muted-foreground text-xs">
                      {member.userEmail} · Joined {formatDt(member.joined_at)}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      value={member.role}
                      onChange={(e) =>
                        changeRoleMutation.mutate({
                          id: member.id,
                          role: e.target.value as OrgRole,
                        })
                      }
                      className="bg-background rounded-xl border px-2 py-1 text-xs"
                      disabled={changeRoleMutation.isPending}
                    >
                      {ROLE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="rounded-xl"
                      disabled={removeMutation.isPending}
                      onClick={() => {
                        if (window.confirm(`Remove ${member.userEmail} from the team?`)) {
                          removeMutation.mutate(member.id);
                        }
                      }}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
              {members.length === 0 && membersQuery.isSuccess ? (
                <p className="text-muted-foreground text-sm">No members yet.</p>
              ) : null}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
