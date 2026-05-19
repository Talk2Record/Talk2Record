import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/shared/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
  variant?: "default" | "card" | "compact";
}

/**
 * Visual primitive for "no data yet" surfaces. Three variants:
 *
 *   - `default`   — standalone block with padded background
 *   - `card`      — emphasised, ringed surface for page-level empty states
 *   - `compact`   — inline, low-emphasis row for list slots
 *
 * Always pairs an icon (or illustration glyph) with a title, optional
 * description, and a CTA so users have a clear next step.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
  variant = "default",
}: EmptyStateProps) {
  const base =
    "flex flex-col items-center justify-center gap-3 text-center text-sm text-muted-foreground";

  const variantClass = {
    default: "rounded-2xl border border-dashed border-primary/15 bg-muted/30 px-6 py-10",
    card: "rounded-2xl border border-primary/15 bg-card px-6 py-12 shadow-sm",
    compact: "px-4 py-6",
  }[variant];

  return (
    <div className={cn(base, variantClass, className)} role="status">
      {Icon ? (
        <span className="bg-primary/10 text-primary inline-flex h-12 w-12 items-center justify-center rounded-2xl">
          <Icon className="h-5 w-5" />
        </span>
      ) : null}
      <div className="space-y-1">
        <p className="text-foreground text-sm font-medium">{title}</p>
        {description ? <p className="mx-auto max-w-md text-xs">{description}</p> : null}
      </div>
      {action ? <div className="pt-1">{action}</div> : null}
    </div>
  );
}
