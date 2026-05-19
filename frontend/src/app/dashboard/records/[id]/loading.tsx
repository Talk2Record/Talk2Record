import { CardSkeleton, Skeleton } from "@/shared/ui/skeleton";

export default function RecordDetailLoading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-32" />
      <div className="border-border bg-card rounded-2xl border p-5">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-6 w-24" />
        </div>
        <div className="mt-6 flex items-center gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex flex-1 items-center gap-2">
              <Skeleton className="h-8 w-8 rounded-full" />
              <div className="flex-1 space-y-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-2 w-10" />
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <CardSkeleton lines={6} />
        </div>
        <CardSkeleton lines={4} />
      </div>
    </div>
  );
}
