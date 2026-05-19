"use client";

import { Component, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (_props: { error: Error; reset: () => void }) => ReactNode;
  /** Called when the boundary catches an error. Useful for analytics/logging. */
  onError?: (_error: Error, _info: { componentStack?: string }) => void;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Catches render-time errors anywhere below it. Next.js `error.tsx` files
 * already cover route-segment errors, but a global boundary is still useful
 * for component-tree errors raised outside a router segment (e.g. inside
 * persistent shell pieces like the topbar/sidebar) so the whole app doesn't
 * white-screen.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack?: string }) {
    if (this.props.onError) {
      this.props.onError(error, info);
    } else if (typeof window !== "undefined") {
      console.error("[ErrorBoundary]", error, info);
    }
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    if (this.props.fallback) {
      return this.props.fallback({ error, reset: this.reset });
    }

    return <DefaultErrorFallback error={error} reset={this.reset} />;
  }
}

function DefaultErrorFallback({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="bg-background flex min-h-screen items-center justify-center px-4">
      <div className="max-w-md space-y-4 text-center">
        <h1 className="text-2xl font-semibold">Something went wrong</h1>
        <p className="text-muted-foreground text-sm">{error.message}</p>
        <div className="flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={reset}
            className="bg-primary text-primary-foreground rounded-md px-4 py-2 text-sm font-medium"
          >
            Try again
          </button>
          <a
            href="/dashboard"
            className="text-foreground rounded-md border px-4 py-2 text-sm font-medium"
          >
            Back to dashboard
          </a>
        </div>
      </div>
    </div>
  );
}
