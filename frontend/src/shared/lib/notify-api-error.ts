import { ApiError } from "@/lib/api";
import { toast } from "@/shared/hooks/use-toast";

interface NotifyOptions {
  /** Title shown above the error message. Defaults to "Something went wrong". */
  title?: string;
  /** Suppress the toast when the error is a 401/403 (those have global handlers). */
  silent401?: boolean;
}

/**
 * Single helper used by every mutation `onError` to show a consistent error
 * toast. Recognises our `ApiError` shape so we can:
 *   - skip 401s (they're handled by the axios interceptor + AuthGate);
 *   - surface 403s with a permission-specific message;
 *   - show field errors as a compact list.
 */
export function notifyApiError(error: unknown, options: NotifyOptions = {}) {
  const { title = "Something went wrong", silent401 = true } = options;
  const apiError = toApiError(error);

  if (silent401 && apiError.status === 401) return;

  const description = buildDescription(apiError);

  toast({
    title: deriveTitle(apiError, title),
    description,
    variant: "destructive",
  });
}

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof Error) {
    return new ApiError({ status: 0, message: error.message });
  }
  return new ApiError({ status: 0, message: "Unknown error" });
}

function deriveTitle(error: ApiError, fallback: string): string {
  switch (error.status) {
    case 0:
      return "Network problem";
    case 403:
      return "You don't have permission";
    case 404:
      return "Not found";
    case 429:
      return "Too many requests";
    default:
      if (error.status >= 500) return "Server error";
      return fallback;
  }
}

function buildDescription(error: ApiError): string {
  if (error.fields && Object.keys(error.fields).length) {
    const lines = Object.entries(error.fields).map(
      ([field, messages]) => `${field}: ${messages.join(", ")}`
    );
    return lines.join("\n");
  }
  return error.message;
}
