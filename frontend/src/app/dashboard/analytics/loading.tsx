import { CardSkeleton, Skeleton, StatCardsSkeleton } from "@/shared/ui/skeleton";

export default function AnalyticsLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-72" />
      </div>
      <StatCardsSkeleton count={4} />
      <CardSkeleton lines={6} />
    </div>
  );
}
