"use client";

import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { recordsService } from "@/services/platform-service";
import { wsBus } from "@/lib/ws-bus";

export const RECORDS_QUERY_KEY = ["records", "list"] as const;

const LIST_INVALIDATE_DEBOUNCE_MS = 500;

/**
 * Subscribes the records-list cache to record-event pushes. Any change to
 * any record in the user's org invalidates the list (debounced 500ms to
 * coalesce bursts when several records progress at once).
 */
export function useRecords() {
  const queryClient = useQueryClient();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const query = useQuery({
    queryKey: RECORDS_QUERY_KEY,
    queryFn: () => recordsService.list(),
  });

  useEffect(() => {
    const unsubscribe = wsBus.on("record_event", () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        void queryClient.invalidateQueries({ queryKey: RECORDS_QUERY_KEY });
      }, LIST_INVALIDATE_DEBOUNCE_MS);
    });

    return () => {
      unsubscribe();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [queryClient]);

  return query;
}
