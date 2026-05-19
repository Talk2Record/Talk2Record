import axios, {
  AxiosError,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";
import { useAuthStore } from "@/store/auth-store";
import { getActiveOrgId } from "@/store/org-store";

export function normalizeApiBaseUrl(value?: string) {
  const baseUrl = (value || "http://localhost:8000").replace(/\/$/, "");
  return baseUrl.endsWith("/api") ? baseUrl : `${baseUrl}/api`;
}

/**
 * Custom event names used to communicate cross-module signals without
 * importing the router/store into the axios module (which would create cycles
 * and break SSR / test environments).
 */
export const AUTH_LOGOUT_EVENT = "talk2record:auth:logout";

export interface ApiErrorOptions {
  status: number;
  code?: string;
  message: string;
  fields?: Record<string, string[]>;
  cause?: unknown;
}

/**
 * Normalized error thrown by every axios call so UI code reads a single shape:
 * `err instanceof ApiError` → `{ status, code, message, fields }`.
 *
 * `fields` carries DRF's `{ field: [errors] }` shape so forms can map errors
 * to inputs via the existing `<InputError />` primitive.
 */
export class ApiError extends Error {
  public readonly status: number;
  public readonly code?: string;
  public readonly fields?: Record<string, string[]>;

  constructor({ status, code, message, fields, cause }: ApiErrorOptions) {
    super(message, cause ? { cause } : undefined);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }

  /** Convenience: is this error a 401/403 auth problem? */
  get isAuthError() {
    return this.status === 401 || this.status === 403;
  }

  get isNetworkError() {
    return this.status === 0;
  }
}

interface DRFErrorBody {
  detail?: string;
  code?: string;
  message?: string;
  errors?: Record<string, string[]>;
  [field: string]: unknown;
}

function extractFieldErrors(data: DRFErrorBody | undefined): Record<string, string[]> | undefined {
  if (!data || typeof data !== "object") return undefined;

  if (data.errors && typeof data.errors === "object") {
    return data.errors;
  }

  const fields: Record<string, string[]> = {};
  for (const [key, value] of Object.entries(data)) {
    if (key === "detail" || key === "code" || key === "message") continue;
    if (Array.isArray(value) && value.every((v) => typeof v === "string")) {
      fields[key] = value;
    } else if (typeof value === "string") {
      fields[key] = [value];
    }
  }
  return Object.keys(fields).length ? fields : undefined;
}

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<DRFErrorBody>;
    const status = axiosError.response?.status ?? 0;
    const data = axiosError.response?.data;

    const message =
      data?.detail ||
      data?.message ||
      axiosError.message ||
      "Something went wrong while calling the API.";

    return new ApiError({
      status,
      code: data?.code,
      message,
      fields: extractFieldErrors(data),
      cause: error,
    });
  }

  const message = error instanceof Error ? error.message : "Unknown error";
  return new ApiError({ status: 0, message, cause: error });
}

export const api = axios.create({
  baseURL: normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL),
  timeout: 10_000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const accessToken = useAuthStore.getState().accessToken;

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  // Forward-compatible org context: today the backend resolves the active
  // organization from the JWT `org_id` claim, but we attach `X-Org-Id` from
  // the persisted selection so a header-driven switch lands without a UI
  // change. Skip on the public refresh endpoint to keep the body minimal.
  const orgId = getActiveOrgId();
  if (orgId && !config.url?.includes("/auth/refresh/")) {
    config.headers["X-Org-Id"] = String(orgId);
  }

  return config;
});

/* ---------------------------------------------------------------------------
 * Single-flight refresh + request queue
 *
 * Problem the previous interceptor had:
 *   - Five concurrent requests that all 401 at the same time triggered five
 *     parallel refresh calls (race) and only the first retry got the new
 *     token; the others either failed or used a stale token.
 *
 * Solution:
 *   - One in-flight `refreshPromise`. Subsequent 401s subscribe to that same
 *     promise and replay their original request once it resolves.
 *   - If the refresh fails, we dispatch a `auth:logout` event (handled in
 *     `AppProviders`) which clears the session and redirects to /login.
 * ------------------------------------------------------------------------- */

type RetryableRequest = InternalAxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string> | null = null;

async function performTokenRefresh(): Promise<string> {
  const { refreshToken } = useAuthStore.getState();
  if (!refreshToken) {
    throw new ApiError({ status: 401, message: "No refresh token available" });
  }

  const response = await axios.post<{ access: string }>(
    `${api.defaults.baseURL}/auth/refresh/`,
    { refresh: refreshToken },
    { headers: { "Content-Type": "application/json" }, timeout: 10_000 }
  );

  const newAccessToken = response.data.access;
  useAuthStore.getState().setTokens({
    accessToken: newAccessToken,
    refreshToken,
  });

  return newAccessToken;
}

function getOrCreateRefresh(): Promise<string> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = performTokenRefresh().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

function dispatchLogout(reason: "expired" | "unauthorized" = "expired") {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(AUTH_LOGOUT_EVENT, { detail: { reason } }));
}

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error)) {
      return Promise.reject(toApiError(error));
    }

    const axiosError = error as AxiosError<DRFErrorBody>;
    const originalRequest = axiosError.config as RetryableRequest | undefined;
    const status = axiosError.response?.status;

    const isRefreshCall = originalRequest?.url?.includes("/auth/refresh/");
    const canAttemptRefresh =
      status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !isRefreshCall &&
      Boolean(useAuthStore.getState().refreshToken);

    if (canAttemptRefresh) {
      originalRequest._retry = true;

      try {
        const newAccessToken = await getOrCreateRefresh();

        originalRequest.headers = originalRequest.headers ?? {};
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;

        return api(originalRequest as AxiosRequestConfig);
      } catch (refreshError) {
        useAuthStore.getState().clearSession();
        dispatchLogout("expired");
        return Promise.reject(toApiError(refreshError));
      }
    }

    if (status === 401 && !isRefreshCall) {
      // No refresh token, or already retried: hard logout.
      useAuthStore.getState().clearSession();
      dispatchLogout("unauthorized");
    }

    return Promise.reject(toApiError(error));
  }
);
