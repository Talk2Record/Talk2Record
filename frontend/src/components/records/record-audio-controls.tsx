"use client";

import { Loader2, Pause, Play, RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/shared/ui/button";
import type { RecordStatus } from "@/types/platform";
import { resolveMediaUrl } from "@/lib/api";

const REPROCESSABLE_STATUSES: readonly RecordStatus[] = [
  "failed",
  "dead_letter",
  "review",
  "extracted",
];

interface RecordAudioControlsProps {
  audioUrl: string;
  status: RecordStatus;
  onReprocess: () => Promise<void>;
  isReprocessing: boolean;
  /** Icon-only buttons for dense layouts such as table rows. */
  compact?: boolean;
  /** Coordinates single playback across multiple rows in a list. */
  recordId?: string;
  activePlaybackId?: string | null;
  onPlaybackChange?: (_recordId: string | null) => void;
}

export function RecordAudioControls({
  audioUrl,
  status,
  onReprocess,
  isReprocessing,
  compact = false,
  recordId,
  activePlaybackId = null,
  onPlaybackChange,
}: RecordAudioControlsProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const resolvedUrl = resolveMediaUrl(audioUrl);
  const canReprocess = REPROCESSABLE_STATUSES.includes(status);
  const isActivePlayback = recordId ? activePlaybackId === recordId : isPlaying;

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleEnded = () => {
      setIsPlaying(false);
      onPlaybackChange?.(null);
    };
    const handlePause = () => {
      setIsPlaying(false);
      if (recordId && activePlaybackId === recordId) {
        onPlaybackChange?.(null);
      }
    };
    const handlePlay = () => setIsPlaying(true);

    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("pause", handlePause);
    audio.addEventListener("play", handlePlay);

    return () => {
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("pause", handlePause);
      audio.removeEventListener("play", handlePlay);
    };
  }, [activePlaybackId, onPlaybackChange, recordId, resolvedUrl]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !recordId) return;

    if (activePlaybackId !== recordId && !audio.paused) {
      audio.pause();
      setIsPlaying(false);
    }
  }, [activePlaybackId, recordId]);

  if (!audioUrl) {
    return compact ? <span className="text-muted-foreground text-xs">—</span> : null;
  }

  async function togglePlayback() {
    const audio = audioRef.current;
    if (!audio) return;

    if (audio.paused) {
      if (recordId) {
        onPlaybackChange?.(recordId);
      }
      await audio.play();
      return;
    }

    audio.pause();
    onPlaybackChange?.(null);
  }

  if (compact) {
    return (
      <div className="flex items-center gap-1" onClick={(event) => event.stopPropagation()}>
        <audio ref={audioRef} src={resolvedUrl} preload="metadata" className="hidden" />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          title={isActivePlayback ? "Pause audio" : "Play audio"}
          aria-label={isActivePlayback ? "Pause audio" : "Play audio"}
          onClick={() => void togglePlayback()}
        >
          {isActivePlayback ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>
        {canReprocess ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            title="Retry processing"
            aria-label="Retry processing"
            onClick={() => void onReprocess()}
            disabled={isReprocessing}
          >
            {isReprocessing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RotateCcw className="h-4 w-4" />
            )}
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <audio ref={audioRef} src={resolvedUrl} preload="metadata" className="hidden" />
      <Button variant="outline" size="sm" onClick={() => void togglePlayback()}>
        {isPlaying ? (
          <>
            <Pause className="mr-2 h-4 w-4" />
            Pause
          </>
        ) : (
          <>
            <Play className="mr-2 h-4 w-4" />
            Play audio
          </>
        )}
      </Button>
      {canReprocess ? (
        <Button
          variant="outline"
          size="sm"
          onClick={() => void onReprocess()}
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
      ) : null}
    </div>
  );
}
