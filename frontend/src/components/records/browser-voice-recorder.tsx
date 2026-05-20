"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Loader2, Mic, MicOff, Upload } from "lucide-react";

import { recordsService } from "@/services/platform-service";
import { Button } from "@/shared/ui/button";
import { toast } from "@/shared/hooks/use-toast";
import { notifyApiError } from "@/shared/lib/notify-api-error";

interface BrowserVoiceRecorderProps {
  onUploaded?: () => void;
  title?: string;
  description?: string;
  className?: string;
}

export function BrowserVoiceRecorder({
  onUploaded,
  title = "Record in browser",
  description = "Record a short voice note here. Talk2Record will transcribe and extract structured data.",
  className,
}: BrowserVoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: (blob: Blob) => recordsService.uploadVoice(blob),
    onSuccess: () => {
      toast({ title: "Voice note uploaded", description: "Processing will begin shortly." });
      onUploaded?.();
    },
    onError: (caughtError) => notifyApiError(caughtError, { title: "Upload failed" }),
  });

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
      mediaRecorderRef.current?.stream.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        upload.mutate(blob);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
      setRecordingSeconds(0);
      timerRef.current = window.setInterval(() => {
        setRecordingSeconds((value) => value + 1);
      }, 1000);
    } catch {
      toast({
        title: "Microphone access denied",
        description: "Allow microphone access to record a voice note in the browser.",
        variant: "destructive",
      });
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (!file.type.startsWith("audio/") && !/\.(webm|ogg|mp3|wav|m4a)$/i.test(file.name)) {
      toast({
        title: "Unsupported file",
        description: "Choose an audio file (webm, ogg, mp3, wav, or m4a).",
        variant: "destructive",
      });
      return;
    }

    upload.mutate(file);
  }

  return (
    <div className={className ?? "border-primary/10 space-y-3 rounded-2xl border p-4"}>
      <p className="text-sm font-medium">{title}</p>
      <p className="text-muted-foreground text-sm">{description}</p>
      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          className="rounded-xl"
          variant={isRecording ? "destructive" : "default"}
          disabled={upload.isPending}
          onClick={() => (isRecording ? stopRecording() : void startRecording())}
        >
          {upload.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Uploading…
            </>
          ) : isRecording ? (
            <>
              <MicOff className="mr-2 h-4 w-4" />
              Stop ({recordingSeconds}s)
            </>
          ) : (
            <>
              <Mic className="mr-2 h-4 w-4" />
              Start recording
            </>
          )}
        </Button>
        <Button
          type="button"
          variant="outline"
          className="rounded-xl"
          disabled={upload.isPending || isRecording}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="mr-2 h-4 w-4" />
          Upload audio
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*,.webm,.ogg,.mp3,.wav,.m4a"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>
    </div>
  );
}
