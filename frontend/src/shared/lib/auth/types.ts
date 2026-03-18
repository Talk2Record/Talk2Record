import type { AuthUser } from "@/types/platform";

export type UserRole = AuthUser["role"];

export interface AuthContext {
  user: AuthUser | null;
  isLoading: boolean;
  login: (_email: string, _password: string) => Promise<AuthUser>;
  register: (_payload: {
    name: string;
    company: string;
    email: string;
    password: string;
    acceptedDocumentKeys: string[];
  }) => Promise<AuthUser>;
  requestPasswordReset: (_email: string) => Promise<{ status: string }>;
  completeOnboarding: (_payload: {
    voiceDataConsent: boolean;
    aiReviewAcknowledged: boolean;
    recordVerificationAcknowledged: boolean;
  }) => Promise<void>;
  logout: () => void;
  signInWithGoogle: () => Promise<void>;
  isAuthenticated: boolean;
  isGoogleEnabled: boolean;
}
