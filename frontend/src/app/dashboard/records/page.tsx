"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { Mic, ScrollText } from "lucide-react";
import { formatCurrency, formatDate } from "@/lib/format";
import { useRecords, RECORDS_QUERY_KEY } from "@/shared/hooks/use-records";
import { Input } from "@/shared/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { EmptyState } from "@/shared/components/empty-state";
import RecordsLoading from "@/app/dashboard/records/loading";
import { RecordStatusBadge } from "@/components/records/record-status-badge";
import { BrowserVoiceRecorder } from "@/components/records/browser-voice-recorder";
import type { RecordStatus } from "@/types/platform";

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
  const [customerFilter, setCustomerFilter] = useState("");
  const [productFilter, setProductFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<RecordStatus | "all">("all");

  const filtered = useMemo(
    () =>
      data.filter((item) => {
        if (
          !(item.customer ?? "").toLowerCase().includes(customerFilter.toLowerCase()) ||
          !(item.product ?? "").toLowerCase().includes(productFilter.toLowerCase())
        ) {
          return false;
        }
        if (statusFilter === "all") return true;
        if (statusFilter === "extracting" || statusFilter === "transcribing") {
          // "Processing" pseudo-filter — match any in-flight status.
          return ["transcribing", "transcribed", "extracting", "extracted"].includes(item.status);
        }
        return item.status === statusFilter;
      }),
    [customerFilter, data, productFilter, statusFilter]
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
            Date, product, amount, and customer filters can map to backend params later.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <Input
              placeholder="Filter by customer"
              value={customerFilter}
              onChange={(event) => setCustomerFilter(event.target.value)}
            />
            <Input
              placeholder="Filter by product"
              value={productFilter}
              onChange={(event) => setProductFilter(event.target.value)}
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
                <th className="py-3 pr-4">Customer</th>
                <th className="py-3 pr-4">Product</th>
                <th className="py-3 pr-4">Quantity</th>
                <th className="py-3 pr-4">Amount</th>
                <th className="py-3 pr-4">Payment Method</th>
                <th className="py-3">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-6">
                    <EmptyState
                      icon={ScrollText}
                      title={hasAnyRecords ? "No matches" : "No records yet"}
                      description={
                        hasAnyRecords
                          ? "Try clearing a filter or broadening the customer or product term."
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
                    <td className="py-4 pr-4 font-medium">{item.customer}</td>
                    <td className="py-4 pr-4">{item.product}</td>
                    <td className="py-4 pr-4">{item.quantity}</td>
                    <td className="py-4 pr-4">{formatCurrency(item.amount, item.currency)}</td>
                    <td className="py-4 pr-4">{item.paymentMethod}</td>
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
