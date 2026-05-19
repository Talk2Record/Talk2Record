import { Check, AlertTriangle, Loader2 } from "lucide-react";
import { cn } from "@/shared/lib/utils";
import { RECORD_PIPELINE_STEPS, type RecordStatus } from "@/types/platform";

interface RecordPipelineStepperProps {
  status: RecordStatus;
  errorStep?: string | null;
}

/**
 * Maps the granular RecordStatus enum (which has 6+ states) onto the four
 * visible pipeline stages: received → transcribing → extracting → stored.
 * The "active" step is whichever stage the current status falls into;
 * earlier stages are marked complete.
 */
function statusToStageIndex(status: RecordStatus): number {
  switch (status) {
    case "received":
      return 0;
    case "transcribing":
    case "transcribed":
      return 1;
    case "extracting":
    case "extracted":
    case "review":
      return 2;
    case "stored":
      return 3;
    case "failed":
    case "dead_letter":
      // Failure: figure out the highest stage reached from the errorStep.
      return -1;
    default:
      return 0;
  }
}

function errorStepToIndex(errorStep: string | null | undefined): number {
  if (!errorStep) return 0;
  switch (errorStep) {
    case "download_media":
    case "download_media_quota":
      return 0;
    case "transcribe":
      return 1;
    case "extract":
      return 2;
    case "store":
      return 3;
    default:
      return 0;
  }
}

export function RecordPipelineStepper({ status, errorStep }: RecordPipelineStepperProps) {
  const isFailed = status === "failed" || status === "dead_letter";
  const activeIndex = isFailed ? errorStepToIndex(errorStep) : statusToStageIndex(status);

  return (
    <ol className="flex items-center gap-2">
      {RECORD_PIPELINE_STEPS.map((step, index) => {
        const completed = !isFailed && index < activeIndex;
        const active = !isFailed && index === activeIndex && status !== "stored";
        const failedHere = isFailed && index === activeIndex;
        const stored = index === activeIndex && status === "stored";

        return (
          <li key={step} className="flex flex-1 items-center gap-2">
            <div
              className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold transition-colors",
                completed && "border-emerald-500 bg-emerald-500 text-white",
                stored && "border-emerald-500 bg-emerald-500 text-white",
                active && "border-primary text-primary",
                failedHere && "bg-destructive text-destructive-foreground border-destructive",
                !completed &&
                  !active &&
                  !failedHere &&
                  !stored &&
                  "border-border text-muted-foreground"
              )}
            >
              {completed || stored ? (
                <Check className="h-4 w-4" />
              ) : failedHere ? (
                <AlertTriangle className="h-4 w-4" />
              ) : active ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                index + 1
              )}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium capitalize">{stepLabel(step)}</p>
              <p className="text-muted-foreground text-[10px] tracking-wide uppercase">
                {completed || stored
                  ? "Done"
                  : active
                    ? "Working"
                    : failedHere
                      ? "Failed"
                      : "Pending"}
              </p>
            </div>
            {index < RECORD_PIPELINE_STEPS.length - 1 ? (
              <div
                className={cn("ml-auto h-px flex-1", completed ? "bg-emerald-500" : "bg-border")}
              />
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

function stepLabel(step: RecordStatus): string {
  switch (step) {
    case "received":
      return "Received";
    case "transcribing":
      return "Transcribe";
    case "extracting":
      return "Extract";
    case "stored":
      return "Stored";
    default:
      return step;
  }
}
