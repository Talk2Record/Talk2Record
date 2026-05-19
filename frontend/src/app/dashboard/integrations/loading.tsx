import { CardSkeleton, Skeleton } from "@/shared/ui/skeleton";

export default function IntegrationsLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-1/3" />
        <Skeleton className="h-4 w-2/3" />
      </div>
      <CardSkeleton lines={5} />
      <CardSkeleton lines={3} />
    </div>
  );
}
