import { CardSkeleton, Skeleton } from "@/shared/ui/skeleton";

export default function SettingsLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-32" />
        <Skeleton className="h-4 w-72" />
      </div>
      <CardSkeleton lines={5} />
      <CardSkeleton lines={4} />
    </div>
  );
}
