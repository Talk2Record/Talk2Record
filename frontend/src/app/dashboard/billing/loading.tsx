import { CardSkeleton, Skeleton, StatCardsSkeleton } from "@/shared/ui/skeleton";

export default function BillingLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-72" />
      </div>
      <StatCardsSkeleton count={3} />
      <CardSkeleton lines={4} />
      <CardSkeleton lines={4} />
    </div>
  );
}
