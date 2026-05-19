/**
 * Validate a `?redirect=` query param so a malicious link can't bounce the user
 * to an external URL after login. Only same-origin paths starting with `/`
 * (but not protocol-relative `//`) and within an allow-listed set of prefixes
 * are accepted.
 */
const ALLOWED_PREFIXES = ["/dashboard", "/invite", "/onboarding"] as const;

export function sanitizeRedirect(value: string | null | undefined): string | null {
  if (!value) return null;
  if (typeof value !== "string") return null;

  // Disallow protocol-relative and absolute URLs.
  if (!value.startsWith("/") || value.startsWith("//")) return null;

  // Strip query/hash before prefix check.
  const path = value.split(/[?#]/, 1)[0];
  if (!ALLOWED_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`))) {
    return null;
  }

  return value;
}

/**
 * Build a login URL preserving the current location as `?redirect=`. Returns
 * `/login` plain when on the marketing site or already on /login.
 */
export function buildLoginRedirect(currentPath: string): string {
  if (!currentPath || currentPath === "/login" || currentPath.startsWith("/login")) {
    return "/login";
  }
  const safe = sanitizeRedirect(currentPath);
  if (!safe) return "/login";
  return `/login?redirect=${encodeURIComponent(safe)}`;
}
