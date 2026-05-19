"use client";

import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { recordsService } from "@/services/platform-service";
import { wsBus } from "@/lib/ws-bus";
import { useWsConnectionStatus } from "@/shared/hooks/use-ws-bus";
import type { RecordItem } from "@/types/platform";
import { TERMINAL_RECORD_STATUSES } from "@/types/platform";
import { RECORDS_QUERY_KEY } from "@/shared/hooks/use-records";

export function recordDetailQueryKey(id: string) {
  return ["records", "detail", id] as const;
}

/**
 * Hybrid live-data hook for a single record.
 *
 *   - WS connected: patch the React Query cache on every `record_event` for
 *     this id; no polling.
 *   - WS disconnected: poll every 3s while the record is in a non-terminal
 *     status.
 *   - Once `status` is terminal (stored / failed / dead_letter), both
 *     mechanisms stop.
 *
 * The list query is also invalidated debounced when any matching event
 * arrives so the table stays fresh.
 */
export function useRecord(id: string | undefined) {
  const queryClient = useQueryClient();
  const connectionStatus = useWsConnectionStatus();
  const wsConnected = connectionStatus === "open";

  const query = useQuery({
    queryKey: id ? recordDetailQueryKey(id) : ["records", "detail", "noop"],
    queryFn: () => recordsService.get(id as string),
    enabled: Boolean(id),
    refetchInterval: (q) => {
      const data = q.state.data as RecordItem | undefined;
      if (!data) return 5_000;
      if (TERMINAL_RECORD_STATUSES.includes(data.status)) return false;
      // While WS is open we trust pushes; otherwise poll every 3s.
      return wsConnected ? false : 3_000;
    },
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    if (!id) return;

    return wsBus.on("record_event", (payload) => {
      if (String(payload.record_id) !== id) return;

      queryClient.setQueryData<RecordItem | undefined>(recordDetailQueryKey(id), (prev) => {
        if (!prev) return prev;
        const nextStatus = payload.status as RecordItem["status"] | undefined;
        if (!nextStatus) return prev;
        return { ...prev, status: nextStatus };
      });
      // Force a fresh GET so all derived fields (artifacts, errors) sync.
      void queryClient.invalidateQueries({ queryKey: recordDetailQueryKey(id) });
      void queryClient.invalidateQueries({ queryKey: RECORDS_QUERY_KEY });
    });
  }, [id, queryClient]);

  return query;
}
