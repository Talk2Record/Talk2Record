"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { toast } from "@/shared/hooks/use-toast";
import { adminUsersService } from "@/services/team-service";
import { StaffGate } from "@/shared/components/role-gate";
import { useImpersonationSession } from "@/shared/hooks/use-impersonation";
import type { AdminUserRow } from "@/types/platform";

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

export default function AdminUsersPage() {
  return (
    <StaffGate>
      <AdminUsersPageInner />
    </StaffGate>
  );
}

function AdminUsersPageInner() {
  const queryClient = useQueryClient();
  const { startImpersonation, active: activeImpersonation } = useImpersonationSession();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"active" | "suspended" | "inactive" | "">("");

  const usersQuery = useQuery({
    queryKey: ["admin", "users", search, statusFilter],
    queryFn: () =>
      adminUsersService.list({
        search: search || undefined,
        status: statusFilter || undefined,
      }),
  });

  const suspendMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      adminUsersService.suspend(id, reason),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      toast({ title: "User suspended" });
    },
    onError: (error: Error) => {
      toast({ title: "Suspend failed", description: error.message, variant: "destructive" });
    },
  });

  const reactivateMutation = useMutation({
    mutationFn: (id: number) => adminUsersService.reactivate(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      toast({ title: "User reactivated" });
    },
    onError: (error: Error) => {
      toast({ title: "Reactivate failed", description: error.message, variant: "destructive" });
    },
  });

  /**
   * Impersonation is intentionally not a React Query mutation — the
   * `useImpersonationSession` hook orchestrates the whole flow (token swap,
   * cache clear, redirect) and persists state so it survives reloads.
   */
  const [isStartingImpersonation, setIsStartingImpersonation] = useState(false);
  const beginImpersonation = async (target: AdminUserRow) => {
    setIsStartingImpersonation(true);
    try {
      await startImpersonation(target);
    } finally {
      setIsStartingImpersonation(false);
    }
  };

  const permissionDenied =
    usersQuery.isError &&
    usersQuery.error instanceof Error &&
    usersQuery.error.message.includes("403");

  const users: AdminUserRow[] = usersQuery.data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <div className="bg-primary/10 text-primary inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-xs font-medium">
            <ShieldAlert className="h-3.5 w-3.5" />
            Platform admin
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">All users</h1>
          <p className="text-muted-foreground max-w-2xl text-sm">
            Platform staff can search, suspend, and impersonate users. All actions are audited.
          </p>
        </div>
        <Button variant="outline" className="rounded-xl" asChild>
          <Link href="/dashboard">← Back to dashboard</Link>
        </Button>
      </div>

      {permissionDenied ? (
        <Card className="border-destructive/40">
          <CardHeader>
            <CardTitle className="text-destructive">No access</CardTitle>
            <CardDescription>This page is restricted to platform staff.</CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <>
          <Card className="border-primary/10">
            <CardHeader>
              <CardTitle>Filters</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 sm:flex-row">
              <Input
                placeholder="Search by name or email"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="rounded-xl"
              />
              <select
                value={statusFilter}
                onChange={(e) =>
                  setStatusFilter(e.target.value as "active" | "suspended" | "inactive" | "")
                }
                className="bg-background rounded-xl border px-3 py-2 text-sm"
              >
                <option value="">All statuses</option>
                <option value="active">Active</option>
                <option value="suspended">Suspended</option>
                <option value="inactive">Inactive</option>
              </select>
            </CardContent>
          </Card>

          <div className="space-y-2">
            {users.map((user) => (
              <Card key={user.id} className="border-primary/10">
                <CardHeader className="pb-2">
                  <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                    <div>
                      <CardTitle className="text-base">{user.name || user.email}</CardTitle>
                      <CardDescription>
                        {user.email} · {user.organizationsCount} org(s) · Joined{" "}
                        {formatDt(user.date_joined)}
                        {user.is_superuser ? " · Superuser" : user.is_staff ? " · Staff" : ""}
                      </CardDescription>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {user.suspended_at ? (
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          className="rounded-xl"
                          disabled={reactivateMutation.isPending}
                          onClick={() => reactivateMutation.mutate(user.id)}
                        >
                          Reactivate
                        </Button>
                      ) : (
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          className="rounded-xl"
                          disabled={suspendMutation.isPending}
                          onClick={() => {
                            const reason = window.prompt("Reason for suspension?") || "";
                            if (reason !== null) {
                              suspendMutation.mutate({ id: user.id, reason });
                            }
                          }}
                        >
                          Suspend
                        </Button>
                      )}
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="rounded-xl"
                        disabled={
                          isStartingImpersonation || !user.is_active || Boolean(activeImpersonation)
                        }
                        onClick={() => {
                          if (
                            window.confirm(
                              `Impersonate ${user.email}? Your session will swap for 15 minutes. An audit event will be recorded.`
                            )
                          ) {
                            void beginImpersonation(user);
                          }
                        }}
                      >
                        Impersonate
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="text-muted-foreground grid gap-1 text-xs sm:grid-cols-2">
                  <div>
                    <span className="text-foreground font-medium">Status</span>{" "}
                    {user.suspended_at
                      ? `Suspended (${user.suspended_reason || "no reason"})`
                      : user.is_active
                        ? "Active"
                        : "Inactive"}
                  </div>
                  <div>
                    <span className="text-foreground font-medium">Last login</span>{" "}
                    {formatDt(user.last_login)}
                  </div>
                </CardContent>
              </Card>
            ))}
            {users.length === 0 && usersQuery.isSuccess ? (
              <p className="text-muted-foreground text-sm">No users match your filters.</p>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}
