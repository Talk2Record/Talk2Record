"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { Mic, ScrollText } from "lucide-react";
import { formatDate } from "@/lib/format";
import { useRecords, RECORDS_QUERY_KEY } from "@/shared/hooks/use-records";
import { Input } from "@/shared/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { EmptyState } from "@/shared/components/empty-state";
import RecordsLoading from "@/app/dashboard/records/loading";
import { RecordStatusBadge } from "@/components/records/record-status-badge";
import { BrowserVoiceRecorder } from "@/components/records/browser-voice-recorder";
import type { DetectedCategory, ExtractedData, RecordItem, RecordStatus } from "@/types/platform";

const STATUS_FILTERS: Array<{ value: RecordStatus | "all"; label: string }> = [
  { value: "all", label: "All" },
  { value: "stored", label: "Stored" },
  { value: "review", label: "Review" },
  { value: "extracting", label: "Processing" },
  { value: "transcribing", label: "Processing" },
  { value: "failed", label: "Failed" },
  { value: "dead_letter", label: "Dead letter" },
];

export default function RecordsPage() {
  const queryClient = useQueryClient();
  const { data = [], isLoading } = useRecords();
  const [industryFilter, setIndustryFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<RecordStatus | "all">("all");

  const filtered = useMemo(
    () =>
      data.filter((item) => {
        const detectedCats = item.detectedCategories ?? [];
        const industryMatches =
          industryFilter.length === 0 ||
          detectedCats.some((cat) =>
            cat.industry.toLowerCase().includes(industryFilter.toLowerCase())
          );
        const categoryMatches =
          categoryFilter.length === 0 ||
          detectedCats.some((cat) => cat.slug.toLowerCase().includes(categoryFilter.toLowerCase()));
        if (!industryMatches || !categoryMatches) return false;
        if (statusFilter === "all") return true;
        if (statusFilter === "extracting" || statusFilter === "transcribing") {
          // "Processing" pseudo-filter — match any in-flight status.
          return ["transcribing", "transcribed", "extracting", "extracted"].includes(item.status);
        }
        return item.status === statusFilter;
      }),
    [categoryFilter, data, industryFilter, statusFilter]
  );

  if (isLoading) {
    return <RecordsLoading />;
  }

  const hasAnyRecords = data.length > 0;

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-xs font-medium">
          Record review
        </div>
        <h1>Records</h1>
        <p className="text-muted-foreground">
          Filter extracted records by customer or product before export or downstream automation.
        </p>
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Add a voice note</CardTitle>
          <CardDescription>
            Record from your browser or upload an audio file. It will appear in the table once
            processing starts.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <BrowserVoiceRecorder
            className="space-y-3"
            onUploaded={() => {
              void queryClient.invalidateQueries({ queryKey: RECORDS_QUERY_KEY });
            }}
          />
        </CardContent>
      </Card>

      {!hasAnyRecords ? (
        <Card className="border-primary/10">
          <CardContent className="pt-6">
            <EmptyState
              icon={Mic}
              title="No records yet"
              description={
                <>
                  Record a voice note below, upload an audio file, or send one to your connected
                  WhatsApp number.
                </>
              }
              action={
                <Link
                  href="/dashboard/integrations"
                  className="bg-primary text-primary-foreground inline-flex items-center rounded-full px-4 py-2 text-xs font-medium"
                >
                  Set up WhatsApp
                </Link>
              }
              variant="compact"
            />
          </CardContent>
        </Card>
      ) : null}

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>
            Filter by detected industry, category, or pipeline status.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <Input
              placeholder="Filter by industry (e.g. construction)"
              value={industryFilter}
              onChange={(event) => setIndustryFilter(event.target.value)}
            />
            <Input
              placeholder="Filter by category (e.g. material_delivery)"
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {dedupeFilters(STATUS_FILTERS).map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setStatusFilter(option.value)}
                className={
                  option.value === statusFilter
                    ? "bg-primary text-primary-foreground rounded-full px-3 py-1 text-xs font-medium"
                    : "border-primary/20 text-muted-foreground hover:bg-muted rounded-full border px-3 py-1 text-xs font-medium"
                }
              >
                {option.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Extracted records</CardTitle>
          <CardDescription>Click a row to open the pipeline + transcript view.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[960px] text-left text-sm">
            <thead className="text-muted-foreground">
              <tr className="border-primary/10 border-b">
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Date</th>
                <th className="py-3 pr-4">Industry / Category</th>
                <th className="py-3 pr-4">Summary</th>
                <th className="py-3">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-6">
                    <EmptyState
                      icon={ScrollText}
                      title={hasAnyRecords ? "No matches" : "No records yet"}
                      description={
                        hasAnyRecords
                          ? "Try clearing a filter or broadening the industry or category term."
                          : "Send a voice note to populate this view."
                      }
                      variant="compact"
                    />
                  </td>
                </tr>
              ) : (
                filtered.map((item) => (
                  <tr
                    key={item.id}
                    className="border-primary/10 hover:bg-muted/30 group border-b align-top transition-colors"
                  >
                    <td className="py-4 pr-4">
                      <RecordStatusBadge status={item.status} />
                    </td>
                    <td className="py-4 pr-4">
                      <Link
                        href={`/dashboard/records/${item.id}`}
                        className="group-hover:text-primary text-foreground hover:underline"
                      >
                        {formatDate(item.date)}
                      </Link>
                    </td>
                    <td className="py-4 pr-4">
                      <CategoryBadges categories={item.detectedCategories} />
                    </td>
                    <td className="text-muted-foreground py-4 pr-4">
                      {summarizeExtractedData(item)}
                    </td>
                    <td className="py-4">{Math.round(item.confidenceScore * 100)}%</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * The list has two "processing" rows pointing at different statuses so we
 * de-duplicate by label before rendering.
 */
function dedupeFilters<T extends { label: string }>(filters: T[]): T[] {
  const seen = new Set<string>();
  return filters.filter((f) => {
    if (seen.has(f.label)) return false;
    seen.add(f.label);
    return true;
  });
}

function CategoryBadges({ categories }: { categories: DetectedCategory[] }) {
  if (categories.length === 0) {
    return <span className="text-muted-foreground italic">unclassified</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {categories.slice(0, 3).map((category) => (
        <span
          key={`${category.industry}.${category.slug}`}
          className="bg-primary/10 text-primary rounded-full px-2 py-0.5 text-xs font-medium"
        >
          {category.industry}.{category.slug}
        </span>
      ))}
    </div>
  );
}

/**
 * Best-effort short summary of the extracted JSON for the table row. Tries
 * to surface the first 2-3 meaningful primitive values; falls back to the
 * legacy sales-flavored fields when present.
 */
function summarizeExtractedData(item: RecordItem): string {
  const data = item.extractedData as ExtractedData;
  if (Array.isArray(data) && data.length > 0) {
    const first = data[0];
    if (first && typeof first === "object" && !Array.isArray(first)) {
      const inner = (first as Record<string, unknown>).extraction;
      if (inner && typeof inner === "object" && !Array.isArray(inner)) {
        const innerData = (inner as Record<string, unknown>).data;
        if (innerData && typeof innerData === "object") {
          return primitiveSummary(innerData as Record<string, unknown>) || "—";
        }
      }
    }
    return "—";
  }
  if (data && typeof data === "object" && Object.keys(data).length > 0) {
    return primitiveSummary(data as Record<string, unknown>) || "—";
  }
  // Legacy fallback.
  if (item.customer || item.product) {
    return [item.customer, item.product].filter(Boolean).join(" · ");
  }
  return "—";
}

function primitiveSummary(payload: Record<string, unknown>): string {
  const bits: string[] = [];
  for (const [key, value] of Object.entries(payload)) {
    if (value === null || value === undefined || value === "") continue;
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      bits.push(`${key.replace(/_/g, " ")}: ${value}`);
    }
    if (bits.length >= 3) break;
  }
  return bits.join(", ");
}
