"use client";

import { useAuth } from "@/shared/lib/auth/auth-context";
import type { OrgRole } from "@/types/platform";

/**
 * Strict ordering for the `atLeast` check. Owners can do everything admins
 * can do, and admins can do everything operators can do.
 */
const ROLE_RANK: Record<OrgRole, number> = {
  owner: 3,
  admin: 2,
  operator: 1,
};

export interface UseRoleResult {
  role: OrgRole | null;
  /** True when the active role matches one of the supplied roles. */
  is: (..._roles: OrgRole[]) => boolean;
  /** True when the active role is at least `minimum` in the role hierarchy. */
  atLeast: (_minimum: OrgRole) => boolean;
  /** Platform-staff (Django is_staff / is_superuser). Orthogonal to OrgRole. */
  isStaff: boolean;
  isSuperuser: boolean;
}

export function useRole(): UseRoleResult {
  const { user } = useAuth();
  const role = user?.role ?? null;

  return {
    role,
    is: (...roles) => Boolean(role && roles.includes(role)),
    atLeast: (minimum) => Boolean(role && ROLE_RANK[role] >= ROLE_RANK[minimum]),
    isStaff: Boolean(user?.isStaff),
    isSuperuser: Boolean(user?.isSuperuser),
  };
}
