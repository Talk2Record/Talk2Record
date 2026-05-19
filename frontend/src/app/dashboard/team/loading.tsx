import { Skeleton, TableSkeleton } from "@/shared/ui/skeleton";

export default function TeamLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-64" />
      </div>
      <div className="border-border bg-card rounded-2xl border p-4">
        <TableSkeleton rows={6} columns={4} />
      </div>
    </div>
  );
}
