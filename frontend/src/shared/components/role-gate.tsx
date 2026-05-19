"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { ShieldOff } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { useRole } from "@/shared/hooks/use-role";
import { useAuth } from "@/shared/lib/auth/auth-context";
import type { OrgRole } from "@/types/platform";

interface RoleGateProps {
  /**
   * Either a list of acceptable roles (any-of), or a single `minimum` role
   * interpreted against the role hierarchy (owner > admin > operator).
   */
  roles?: OrgRole[];
  minimum?: OrgRole;
  /** Optional override for the friendly "no access" headline. */
  title?: string;
  /** Optional override for the body copy. */
  description?: string;
  /** What to render when the role check passes. */
  children: ReactNode;
  /** Render this instead of the default forbidden card. */
  fallback?: ReactNode;
}

/**
 * Page-level role guard. Renders `children` when the user's role satisfies
 * `roles` or `minimum`. Otherwise renders a friendly forbidden card instead
 * of waiting for the API to 403 (which would still work — this just keeps
 * the UI calm).
 *
 *   <RoleGate minimum="admin">…</RoleGate>
 *   <RoleGate roles={["owner", "admin"]}>…</RoleGate>
 */
export function RoleGate({
  roles,
  minimum,
  title = "You don't have access",
  description = "Ask an organization owner or admin to invite you or change your role.",
  children,
  fallback,
}: RoleGateProps) {
  const { status } = useAuth();
  const { is, atLeast } = useRole();

  if (status.kind !== "authenticated") {
    return null;
  }

  const allowed = (roles && is(...roles)) || (minimum && atLeast(minimum));

  if (allowed) return <>{children}</>;
  if (fallback) return <>{fallback}</>;
  return <ForbiddenCard title={title} description={description} />;
}

interface StaffGateProps {
  children: ReactNode;
  /** Require superuser specifically (impersonating other superusers, etc.). */
  requireSuperuser?: boolean;
  fallback?: ReactNode;
}

/**
 * Platform-staff guard. Use for `/dashboard/admin/*` and AI provider
 * routing — anything that's orthogonal to org membership.
 */
export function StaffGate({ children, requireSuperuser = false, fallback }: StaffGateProps) {
  const { status } = useAuth();
  const { isStaff, isSuperuser } = useRole();

  if (status.kind !== "authenticated") return null;

  const allowed = requireSuperuser ? isSuperuser : isStaff || isSuperuser;
  if (allowed) return <>{children}</>;
  if (fallback) return <>{fallback}</>;
  return (
    <ForbiddenCard
      title="Restricted to platform staff"
      description="This area is reserved for Talk2Record administrators."
    />
  );
}

function ForbiddenCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="space-y-4">
      <Card className="border-destructive/30">
        <CardHeader>
          <div className="bg-destructive/10 text-destructive inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-xs font-medium">
            <ShieldOff className="h-3.5 w-3.5" />
            403 — Forbidden
          </div>
          <CardTitle className="text-destructive">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild variant="outline" className="rounded-xl">
            <Link href="/dashboard">Back to dashboard</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
