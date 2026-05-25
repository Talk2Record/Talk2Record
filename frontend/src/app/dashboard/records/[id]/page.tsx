"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Copy } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useRecord, recordDetailQueryKey } from "@/shared/hooks/use-record";
import { RecordPipelineStepper } from "@/components/records/record-pipeline-stepper";
import { RecordStatusBadge } from "@/components/records/record-status-badge";
import { ExtractedDataView } from "@/components/records/extracted-data-view";
import { RecordArtifactsCard } from "@/components/records/record-artifacts-card";
import { RecordAudioControls } from "@/components/records/record-audio-controls";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { formatDate } from "@/lib/format";
import RecordDetailLoading from "@/app/dashboard/records/[id]/loading";
import { toast } from "@/shared/hooks/use-toast";
import { recordsService } from "@/services/platform-service";
import { notifyApiError } from "@/shared/lib/notify-api-error";
import { cn } from "@/shared/lib/utils";
import type { DetectedCategory } from "@/types/platform";

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
  const recordId = record.id;

  async function handleReprocess() {
    setIsReprocessing(true);
    try {
      await recordsService.reprocess(recordId);
      toast({
        title: "Reprocessing started",
        description:
          "The voice note pipeline is running again. This page will update automatically.",
      });
      void queryClient.invalidateQueries({ queryKey: recordDetailQueryKey(recordId) });
    } catch (error) {
      notifyApiError(error, { title: "Could not reprocess record" });
    } finally {
      setIsReprocessing(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <Link
          href="/dashboard/records"
          className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-sm"
        >
          <ArrowLeft className="h-4 w-4" /> Back to records
        </Link>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <RecordAudioControls
            audioUrl={record.audioUrl}
            status={record.status}
            onReprocess={handleReprocess}
            isReprocessing={isReprocessing}
          />
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
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div className="space-y-2">
              <CardTitle className="flex flex-wrap items-center gap-3">
                <span>{record.id}</span>
                <RecordStatusBadge status={record.status} />
              </CardTitle>
              <CardDescription className="flex flex-wrap items-center gap-2">
                <span>{formatDate(record.date)}</span>
                <span>·</span>
                <span>Confidence {Math.round(record.confidenceScore * 100)}%</span>
                {record.detectedCategories.slice(0, 3).map((category) => (
                  <CategoryBadge
                    key={`${category.industry}.${category.slug}`}
                    category={category}
                  />
                ))}
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
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="border-primary/10 lg:col-span-2">
          <CardHeader>
            <CardTitle>Transcript</CardTitle>
            <CardDescription>
              Confidence {Math.round(record.confidenceScore * 100)}%
              {record.processingStep ? ` · current step: ${record.processingStep}` : null}
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
            <CardTitle>Classification</CardTitle>
            <CardDescription>
              Detected industries and categories with their confidence.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <ClassificationList
              industries={record.detectedIndustries}
              categories={record.detectedCategories}
            />
          </CardContent>
        </Card>
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Extracted data</CardTitle>
          <CardDescription>
            Schema-driven structured output. Fields depend on the resolved category schema.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ExtractedDataView
            data={record.extractedData}
            validationErrors={record.validationErrors}
          />
        </CardContent>
      </Card>

      {record.validationErrors.length > 0 ? (
        <Card className="border-amber-500/40">
          <CardHeader>
            <CardTitle>Validation errors</CardTitle>
            <CardDescription>
              These fields failed JSON Schema validation. Fix them in the admin or via the review
              flow.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {record.validationErrors.map((error, idx) => (
                <li key={idx} className="text-foreground">
                  {error.category ? (
                    <span className="text-muted-foreground mr-2">[{error.category}]</span>
                  ) : null}
                  <span className="font-medium">{error.path || "(root)"}</span>
                  <span className="text-muted-foreground"> — {error.message}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      <RecordArtifactsCard artifacts={record.artifacts} />
    </div>
  );
}

function CategoryBadge({ category }: { category: DetectedCategory }) {
  const confidence = Math.round((category.confidence ?? 0) * 100);
  return (
    <span
      className={cn(
        "bg-primary/10 text-primary inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
      )}
    >
      {category.industry}.{category.slug} · {confidence}%
    </span>
  );
}

function ClassificationList({
  industries,
  categories,
}: {
  industries: DetectedCategory[] | { slug: string; confidence: number }[];
  categories: DetectedCategory[];
}) {
  if (industries.length === 0 && categories.length === 0) {
    return (
      <p className="text-muted-foreground">
        No classification yet. This card populates after the pipeline runs.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      {industries.length > 0 ? (
        <div>
          <div className="text-muted-foreground mb-1 text-xs font-medium uppercase">Industries</div>
          <div className="flex flex-wrap gap-1.5">
            {industries.map((entry) => (
              <span
                key={"industry" in entry ? `${entry.industry}.${entry.slug}` : entry.slug}
                className="border-primary/20 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs"
              >
                {"industry" in entry ? `${entry.industry}.${entry.slug}` : entry.slug}
                {" · "}
                {Math.round(entry.confidence * 100)}%
              </span>
            ))}
          </div>
        </div>
      ) : null}
      {categories.length > 0 ? (
        <div>
          <div className="text-muted-foreground mb-1 text-xs font-medium uppercase">Categories</div>
          <div className="flex flex-wrap gap-1.5">
            {categories.map((category) => (
              <CategoryBadge key={`${category.industry}.${category.slug}`} category={category} />
            ))}
          </div>
        </div>
      ) : null}
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
