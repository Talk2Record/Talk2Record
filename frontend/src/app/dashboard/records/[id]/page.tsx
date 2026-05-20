"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Copy, ExternalLink, Loader2, RotateCcw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useRecord, recordDetailQueryKey } from "@/shared/hooks/use-record";
import { RecordPipelineStepper } from "@/components/records/record-pipeline-stepper";
import { RecordStatusBadge } from "@/components/records/record-status-badge";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { formatCurrency, formatDate } from "@/lib/format";
import RecordDetailLoading from "@/app/dashboard/records/[id]/loading";
import { toast } from "@/shared/hooks/use-toast";
import { recordsService } from "@/services/platform-service";
import { notifyApiError } from "@/shared/lib/notify-api-error";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function RecordDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const queryClient = useQueryClient();
  const recordQuery = useRecord(id);
  const record = recordQuery.data;
  const [isReprocessing, setIsReprocessing] = useState(false);

  if (recordQuery.isLoading || !record) {
    if (recordQuery.isError) {
      return <RecordNotFound id={id} />;
    }
    return <RecordDetailLoading />;
  }

  const isFailed = record.status === "failed" || record.status === "dead_letter";

  async function handleReprocess() {
    setIsReprocessing(true);
    try {
      await recordsService.reprocess(record.id);
      toast({
        title: "Reprocessing started",
        description: "The voice note pipeline is running again. This page will update automatically.",
      });
      void queryClient.invalidateQueries({ queryKey: recordDetailQueryKey(record.id) });
    } catch (error) {
      notifyApiError(error, { title: "Could not reprocess record" });
    } finally {
      setIsReprocessing(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link
          href="/dashboard/records"
          className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-sm"
        >
          <ArrowLeft className="h-4 w-4" /> Back to records
        </Link>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            void navigator.clipboard.writeText(record.id);
            toast({ title: "Record ID copied" });
          }}
        >
          <Copy className="mr-2 h-3.5 w-3.5" /> Copy ID
        </Button>
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle className="flex items-center gap-3">
                {record.customer}
                <RecordStatusBadge status={record.status} />
              </CardTitle>
              <CardDescription>
                {record.product} · {formatCurrency(record.amount, record.currency)} ·{" "}
                {formatDate(record.date)}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <RecordPipelineStepper status={record.status} errorStep={record.processingErrorStep} />
        </CardContent>
      </Card>

      {isFailed ? (
        <Card className="border-destructive/40">
          <CardHeader>
            <CardTitle>Processing failed</CardTitle>
            <CardDescription>
              {record.processingErrorStep
                ? `The "${record.processingErrorStep}" step did not complete.`
                : "An unrecoverable error stopped this record."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {record.processingError ? (
              <pre className="bg-muted/50 max-h-48 overflow-auto rounded-md p-3 text-xs whitespace-pre-wrap">
                {record.processingError}
              </pre>
            ) : null}
            <div className="text-muted-foreground flex flex-wrap items-center gap-3 text-xs">
              <span>Retries attempted: {record.processingRetryCount}</span>
              {record.lastFailedAt ? (
                <span>Last failed: {formatDate(record.lastFailedAt)}</span>
              ) : null}
              {record.deadLetteredAt ? (
                <span>Dead lettered: {formatDate(record.deadLetteredAt)}</span>
              ) : null}
            </div>
            <p className="text-muted-foreground text-sm">
              You can retry processing without uploading the audio again.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleReprocess()}
              disabled={isReprocessing}
            >
              {isReprocessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Retrying…
                </>
              ) : (
                <>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Retry processing
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="border-primary/10 lg:col-span-2">
          <CardHeader>
            <CardTitle>Transcript</CardTitle>
            <CardDescription>
              Confidence {Math.round(record.confidenceScore * 100)}%
            </CardDescription>
          </CardHeader>
          <CardContent>
            {record.transcript ? (
              <p className="text-foreground text-sm leading-relaxed whitespace-pre-wrap">
                {record.transcript}
              </p>
            ) : (
              <p className="text-muted-foreground text-sm">
                Transcript not yet available. This page updates automatically as the pipeline
                progresses.
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="border-primary/10">
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <DetailRow label="Quantity" value={String(record.quantity)} />
            <DetailRow label="Amount" value={formatCurrency(record.amount, record.currency)} />
            <DetailRow label="Payment" value={record.paymentMethod || "—"} />
            <DetailRow label="Created" value={formatDate(record.date)} />
          </CardContent>
        </Card>
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Artifacts</CardTitle>
          <CardDescription>Files generated by the pipeline for this record.</CardDescription>
        </CardHeader>
        <CardContent>
          {record.artifacts.length === 0 ? (
            <p className="text-muted-foreground text-sm">No artifacts available yet.</p>
          ) : (
            <ul className="divide-border divide-y">
              {record.artifacts.map((artifact) => (
                <li
                  key={String(artifact.id)}
                  className="flex items-center justify-between py-2 text-sm"
                >
                  <div>
                    <p className="font-medium capitalize">{artifact.kind.replace(/_/g, " ")}</p>
                    {artifact.created_at ? (
                      <p className="text-muted-foreground text-xs">
                        {formatDate(artifact.created_at)}
                      </p>
                    ) : null}
                  </div>
                  {artifact.url ? (
                    <a
                      href={artifact.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-primary inline-flex items-center gap-1 text-xs hover:underline"
                    >
                      Open <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : (
                    <span className="text-muted-foreground text-xs">Pending</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function RecordNotFound({ id }: { id: string }) {
  return (
    <div className="mx-auto max-w-xl py-12">
      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle>Record not found</CardTitle>
          <CardDescription>
            We couldn&apos;t load record <code>{id}</code>. It may have been deleted or belongs to a
            different workspace.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Link
            href="/dashboard/records"
            className="text-primary inline-flex items-center gap-1 text-sm hover:underline"
          >
            <ArrowLeft className="h-4 w-4" /> Back to records
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
