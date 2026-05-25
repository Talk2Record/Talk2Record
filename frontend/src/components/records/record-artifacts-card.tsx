"use client";

import { useState } from "react";
import { Copy, ExternalLink } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";
import { formatDate } from "@/lib/format";
import { toast } from "@/shared/hooks/use-toast";
import type { RecordArtifact } from "@/types/platform";

interface RecordArtifactsCardProps {
  artifacts: RecordArtifact[];
}

function hasArtifactContent(content: unknown): boolean {
  if (content === null || content === undefined) return false;
  if (typeof content === "string") return content.trim().length > 0;
  if (Array.isArray(content)) return content.length > 0;
  if (typeof content === "object") return Object.keys(content).length > 0;
  return true;
}

function formatArtifactContent(content: unknown): string {
  if (typeof content === "string") return content;
  return JSON.stringify(content, null, 2);
}

export function RecordArtifactsCard({ artifacts }: RecordArtifactsCardProps) {
  const [selectedArtifact, setSelectedArtifact] = useState<RecordArtifact | null>(null);

  return (
    <>
      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Artifacts</CardTitle>
          <CardDescription>
            Pipeline step outputs stored for this record. View raw JSON for audit and debugging.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {artifacts.length === 0 ? (
            <p className="text-muted-foreground text-sm">No artifacts available yet.</p>
          ) : (
            <ul className="divide-border divide-y">
              {artifacts.map((artifact) => {
                const isReady = Boolean(artifact.url) || hasArtifactContent(artifact.content);

                return (
                  <li
                    key={String(artifact.id)}
                    className="flex items-center justify-between gap-3 py-2 text-sm"
                  >
                    <div>
                      <p className="font-medium capitalize">{artifact.kind.replace(/_/g, " ")}</p>
                      {artifact.created_at ? (
                        <p className="text-muted-foreground text-xs">
                          {formatDate(artifact.created_at)}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {isReady ? (
                        <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                          Ready
                        </span>
                      ) : (
                        <span className="text-muted-foreground text-xs">Pending</span>
                      )}
                      {artifact.url ? (
                        <a
                          href={artifact.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary inline-flex items-center gap-1 text-xs hover:underline"
                        >
                          Open <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : isReady ? (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-7 px-2 text-xs"
                          onClick={() => setSelectedArtifact(artifact)}
                        >
                          View JSON
                        </Button>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={selectedArtifact !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedArtifact(null);
        }}
      >
        <DialogContent className="max-h-[85vh] max-w-3xl overflow-hidden sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle className="capitalize">
              {selectedArtifact?.kind.replace(/_/g, " ") ?? "Artifact"}
            </DialogTitle>
            <DialogDescription>
              Raw pipeline output ({selectedArtifact?.artifactType ?? "json"}).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="flex justify-end">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  if (!selectedArtifact) return;
                  void navigator.clipboard.writeText(
                    formatArtifactContent(selectedArtifact.content)
                  );
                  toast({ title: "Artifact JSON copied" });
                }}
              >
                <Copy className="mr-2 h-3.5 w-3.5" />
                Copy
              </Button>
            </div>
            <pre className="bg-muted/50 max-h-[55vh] overflow-auto rounded-md p-3 text-xs whitespace-pre-wrap">
              {selectedArtifact ? formatArtifactContent(selectedArtifact.content) : null}
            </pre>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
