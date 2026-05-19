/**
 * Single source of truth for whether the Google Workspace sign-in flow is
 * enabled. We previously gated this behind TWO env vars
 * (`NEXT_PUBLIC_GOOGLE_AUTH_ENABLED` + `NEXT_PUBLIC_GOOGLE_WORKSPACE_LOGIN`)
 * which meant operators frequently set one but not the other and ended up
 * with an inconsistent UI.
 *
 * The supported switch is now a single flag:
 *
 *   NEXT_PUBLIC_GOOGLE_SIGN_IN_ENABLED=true
 *
 * The two legacy vars are still honoured for backwards compatibility — if
 * either is "true" the flow is enabled. A warning is logged in development
 * so operators get nudged towards the new variable.
 */

const LEGACY_VARS = [
  "NEXT_PUBLIC_GOOGLE_AUTH_ENABLED",
  "NEXT_PUBLIC_GOOGLE_WORKSPACE_LOGIN",
] as const;

const PRIMARY_VAR = "NEXT_PUBLIC_GOOGLE_SIGN_IN_ENABLED";

let hasWarnedAboutLegacyFlag = false;

export function isGoogleSignInEnabled(): boolean {
  const primary = process.env.NEXT_PUBLIC_GOOGLE_SIGN_IN_ENABLED === "true";
  const legacyAuth = process.env.NEXT_PUBLIC_GOOGLE_AUTH_ENABLED === "true";
  const legacyWorkspace = process.env.NEXT_PUBLIC_GOOGLE_WORKSPACE_LOGIN === "true";

  const enabled = primary || legacyAuth || legacyWorkspace;

  if (!hasWarnedAboutLegacyFlag && enabled && !primary && process.env.NODE_ENV !== "production") {
    hasWarnedAboutLegacyFlag = true;
    const set = LEGACY_VARS.filter((name) => process.env[name] === "true").join(", ");
    console.warn(
      `[auth] Google sign-in is enabled via legacy env var(s) (${set}). ` +
        `Please migrate to ${PRIMARY_VAR}=true; the legacy variables will be removed in a future release.`
    );
  }

  return enabled;
}
