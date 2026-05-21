"use client";

import { cn } from "@/shared/lib/utils";
import type {
  ExtractedData,
  ExtractedDataValue,
  ExtractionValidationError,
} from "@/types/platform";

interface ExtractedDataViewProps {
  data: ExtractedData;
  validationErrors?: ExtractionValidationError[];
  className?: string;
}

/**
 * Generic renderer for the backend's `extracted_data` JSON.
 *
 * The shape is fully dynamic — it depends on the `ExtractionSchema` the
 * pipeline used. Top-level may be a single category's dict (industry +
 * category resolved to one) or a list of `{industry, category, extraction,
 * validation}` entries (multi-category audio).
 */
export function ExtractedDataView({
  data,
  validationErrors = [],
  className,
}: ExtractedDataViewProps) {
  const errorsByPath = new Map<string, ExtractionValidationError[]>();
  for (const error of validationErrors) {
    const key = error.path ?? "";
    errorsByPath.set(key, [...(errorsByPath.get(key) ?? []), error]);
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return <EmptyExtraction className={className} />;
    }
    return (
      <div className={cn("space-y-4", className)}>
        {data.map((entry, idx) => (
          <CategoryEntry key={idx} entry={entry} errorsByPath={errorsByPath} />
        ))}
      </div>
    );
  }

  if (!data || Object.keys(data).length === 0) {
    return <EmptyExtraction className={className} />;
  }

  return (
    <div className={cn("space-y-2", className)}>
      <RecordCard payload={data} errorsByPath={errorsByPath} />
    </div>
  );
}

function EmptyExtraction({ className }: { className?: string }) {
  return (
    <div className={cn("text-muted-foreground text-sm", className)}>
      No extracted data yet. This view updates automatically as the pipeline progresses.
    </div>
  );
}

/**
 * Renders one entry from a multi-category extraction. The backend writes
 * each entry as `{industry, category, classification_confidence, extraction:
 * {provider, model, prompt_version, schema_version, confidence, data},
 * validation: {ok, errors}}`.
 */
function CategoryEntry({
  entry,
  errorsByPath,
}: {
  entry: ExtractedDataValue;
  errorsByPath: Map<string, ExtractionValidationError[]>;
}) {
  if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
    return <PrimitiveValue value={entry} />;
  }
  const record = entry as Record<string, ExtractedDataValue>;
  const industry = typeof record.industry === "string" ? record.industry : "";
  const category = typeof record.category === "string" ? record.category : "";
  const classificationConfidence =
    typeof record.classification_confidence === "number" ? record.classification_confidence : null;

  const extraction = (record.extraction ?? {}) as Record<string, ExtractedDataValue>;
  const data = (extraction.data ?? {}) as Record<string, ExtractedDataValue>;
  const validation = (record.validation ?? {}) as Record<string, ExtractedDataValue>;
  const validationOk = validation.ok !== false;

  return (
    <div className="border-primary/10 rounded-md border p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="bg-primary/10 text-primary inline-flex rounded-full px-2 py-0.5 text-xs font-medium">
            {industry}.{category}
          </span>
          {classificationConfidence !== null ? (
            <span className="text-muted-foreground text-xs">
              {(classificationConfidence * 100).toFixed(0)}% match
            </span>
          ) : null}
        </div>
        <div
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium",
            validationOk
              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
              : "bg-amber-500/10 text-amber-700 dark:text-amber-300"
          )}
        >
          {validationOk ? "Valid" : "Needs review"}
        </div>
      </div>
      <RecordCard payload={data} errorsByPath={errorsByPath} />
    </div>
  );
}

function RecordCard({
  payload,
  errorsByPath,
}: {
  payload: Record<string, ExtractedDataValue>;
  errorsByPath: Map<string, ExtractionValidationError[]>;
}) {
  const entries = Object.entries(payload);
  if (entries.length === 0) {
    return <EmptyExtraction />;
  }
  return (
    <dl className="divide-border divide-y">
      {entries.map(([key, value]) => (
        <FieldRow key={key} fieldKey={key} value={value} errorsByPath={errorsByPath} />
      ))}
    </dl>
  );
}

function FieldRow({
  fieldKey,
  value,
  errorsByPath,
  depth = 0,
}: {
  fieldKey: string;
  value: ExtractedDataValue;
  errorsByPath: Map<string, ExtractedDataValue> | Map<string, ExtractionValidationError[]>;
  depth?: number;
}) {
  const errors = (errorsByPath as Map<string, ExtractionValidationError[]>).get(fieldKey);
  return (
    <div
      className={cn(
        "grid gap-3 py-2 text-sm",
        depth === 0
          ? "sm:grid-cols-[minmax(140px,1fr)_2fr]"
          : "sm:grid-cols-[minmax(120px,1fr)_2fr]"
      )}
    >
      <dt className="text-muted-foreground font-medium capitalize">
        {fieldKey.replace(/_/g, " ")}
      </dt>
      <dd className="text-foreground">
        <ValueRenderer value={value} />
        {errors && errors.length > 0 ? (
          <ul className="text-destructive mt-1 space-y-0.5 text-xs">
            {errors.map((error, idx) => (
              <li key={idx}>{error.message ?? "Validation error"}</li>
            ))}
          </ul>
        ) : null}
      </dd>
    </div>
  );
}

function ValueRenderer({ value }: { value: ExtractedDataValue }) {
  if (value === null || value === undefined || value === "") {
    return <span className="text-muted-foreground italic">—</span>;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="text-muted-foreground italic">none</span>;
    }
    return (
      <ul className="space-y-1">
        {value.map((entry, idx) => (
          <li key={idx} className="border-primary/10 bg-muted/30 rounded-md border p-2 text-xs">
            <ValueRenderer value={entry} />
          </li>
        ))}
      </ul>
    );
  }
  if (typeof value === "object") {
    return (
      <dl className="border-primary/10 bg-muted/30 divide-border space-y-1 divide-y rounded-md border p-2">
        {Object.entries(value).map(([k, v]) => (
          <div key={k} className="grid gap-2 pt-1 first:pt-0 sm:grid-cols-[minmax(110px,1fr)_2fr]">
            <dt className="text-muted-foreground text-xs capitalize">{k.replace(/_/g, " ")}</dt>
            <dd className="text-xs">
              <ValueRenderer value={v} />
            </dd>
          </div>
        ))}
      </dl>
    );
  }
  return <PrimitiveValue value={value} />;
}

function PrimitiveValue({ value }: { value: ExtractedDataValue }) {
  if (typeof value === "boolean") {
    return <span>{value ? "Yes" : "No"}</span>;
  }
  if (typeof value === "number") {
    return <span>{value.toLocaleString()}</span>;
  }
  return <span>{String(value)}</span>;
}
