import { Skeleton, TableSkeleton } from "@/shared/ui/skeleton";

export default function RecordsLoading() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>
      <div className="border-border bg-card rounded-2xl border p-4">
        <TableSkeleton rows={8} columns={6} />
      </div>
    </div>
  );
}
