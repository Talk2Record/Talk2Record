/**
 * Notification WebSocket bus.
 *
 * Replaces the previous per-hook `connectNotificationWebSocket(...)` call.
 * One singleton socket per browser tab carries every server-pushed message
 * type (notifications, record events, future event types). Subscribers
 * register typed handlers via `wsBus.on(type, handler)` and the manager
 * fan-outs each message.
 *
 * The bus also exposes a `replace(token)` method called when the access
 * token rotates — the backend reads `?token=` from the URL on connect, so
 * we cannot mutate auth on an open socket; we close and reopen instead.
 *
 * Connection status is exported as a tiny pub/sub so a "Live" indicator in
 * the topbar can subscribe without pulling the manager into React state.
 */

export type WsConnectionStatus = "idle" | "connecting" | "open" | "reconnecting" | "failed";

/**
 * Inbound message envelope shapes the backend currently sends:
 *
 *   - notification persisted rows (full NotificationSerializer)
 *       { id, type, title, message, link_url, read_at, created_at }
 *
 *   - lightweight record-pipeline updates from `broadcast_record_event`
 *       { eventType: "record_updated", record_id, status, summary? }
 *
 * We model these as a discriminated union so consumers don't have to do
 * runtime detection in their handlers.
 */
export interface WsNotificationMessage {
  type: "notification";
  payload: {
    id: number;
    type: string;
    title: string;
    message: string;
    link_url: string;
    read_at: string | null;
    created_at: string;
  };
}

export interface WsRecordEventMessage {
  type: "record_event";
  payload: {
    eventType: string;
    record_id: string;
    status?: string;
    summary?: string;
  };
}

export interface WsUnknownMessage {
  type: "unknown";
  payload: unknown;
}

export type WsMessage = WsNotificationMessage | WsRecordEventMessage | WsUnknownMessage;

type EventType = WsMessage["type"];
type HandlerFor<T extends EventType> = (
  _payload: Extract<WsMessage, { type: T }>["payload"]
) => void;

interface StatusListener {
  (_status: WsConnectionStatus): void;
}

const DEFAULT_RECONNECT_DELAY = 3_000;
const MAX_RECONNECT_DELAY = 30_000;

class WsBus {
  private socket: WebSocket | null = null;
  private token: string | null = null;
  private wsBaseUrl: string | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempt = 0;
  private explicitClose = false;
  private statusValue: WsConnectionStatus = "idle";
  private statusListeners = new Set<StatusListener>();
  /**
   * Per-event-type subscribers. Using `Set` keeps handler de-dup automatic
   * even if a component re-runs its `useEffect`.
   */
  private handlers: { [T in EventType]: Set<HandlerFor<T>> } = {
    notification: new Set(),
    record_event: new Set(),
    unknown: new Set(),
  };

  get status(): WsConnectionStatus {
    return this.statusValue;
  }

  /** Subscribe to connection status changes. Returns an unsubscribe fn. */
  onStatusChange(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    listener(this.statusValue);
    return () => this.statusListeners.delete(listener);
  }

  /** Subscribe to a typed inbound event. Returns an unsubscribe fn. */
  on<T extends EventType>(type: T, handler: HandlerFor<T>): () => void {
    const set = this.handlers[type] as Set<HandlerFor<T>>;
    set.add(handler);
    return () => set.delete(handler);
  }

  /**
   * Open (or re-open) the socket with the given token. Safe to call
   * repeatedly — subsequent calls with the same token are no-ops.
   */
  connect(wsBaseUrl: string, token: string) {
    if (this.socket && this.token === token && !this.explicitClose) return;
    this.wsBaseUrl = wsBaseUrl;
    this.token = token;
    this.explicitClose = false;
    this.openSocket();
  }

  /**
   * Replace the access token on the open socket. Because the server only
   * reads the token from the initial URL, we close the current socket and
   * reopen with the new one. Subscribers are preserved.
   */
  replace(token: string) {
    if (!this.wsBaseUrl) return;
    if (this.token === token) return;
    this.token = token;
    this.closeSocket();
    this.reconnectAttempt = 0;
    this.openSocket();
  }

  /** Fully tear down: no auto-reconnect. */
  disconnect() {
    this.explicitClose = true;
    this.token = null;
    this.closeSocket();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.setStatus("idle");
  }

  private openSocket() {
    if (!this.wsBaseUrl || !this.token) return;
    if (typeof window === "undefined" || typeof WebSocket === "undefined") return;

    this.setStatus(this.reconnectAttempt === 0 ? "connecting" : "reconnecting");

    const url = `${this.wsBaseUrl}/ws/notifications/?token=${encodeURIComponent(this.token)}`;
    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      this.scheduleReconnect();
      return;
    }
    this.socket = ws;

    ws.onopen = () => {
      this.reconnectAttempt = 0;
      this.setStatus("open");
    };

    ws.onmessage = (event) => {
      this.dispatchRaw(event.data);
    };

    ws.onclose = () => {
      this.socket = null;
      if (this.explicitClose) {
        this.setStatus("idle");
        return;
      }
      this.scheduleReconnect();
    };

    ws.onerror = () => {
      // onclose follows; let it drive reconnect.
    };
  }

  private closeSocket() {
    if (this.socket) {
      try {
        this.socket.close();
      } catch {
        // ignore
      }
      this.socket = null;
    }
  }

  private scheduleReconnect() {
    if (this.explicitClose) return;
    this.setStatus("reconnecting");
    const delay = Math.min(
      DEFAULT_RECONNECT_DELAY * Math.pow(2, this.reconnectAttempt),
      MAX_RECONNECT_DELAY
    );
    this.reconnectAttempt += 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.openSocket();
    }, delay);
  }

  private setStatus(next: WsConnectionStatus) {
    if (this.statusValue === next) return;
    this.statusValue = next;
    this.statusListeners.forEach((listener) => listener(next));
  }

  /**
   * Classify a raw message into one of our typed message shapes. The
   * notification serializer always sends `id + title`, while record events
   * carry `eventType` (and `record_id`). We default to `unknown` so
   * consumers that opt-in to that channel can still inspect novel shapes.
   */
  private dispatchRaw(raw: unknown) {
    let payload: unknown;
    if (typeof raw === "string") {
      try {
        payload = JSON.parse(raw);
      } catch {
        payload = raw;
      }
    } else {
      payload = raw;
    }

    if (isRecordEvent(payload)) {
      this.fanoutRecordEvent(payload);
      return;
    }
    if (isNotification(payload)) {
      this.fanoutNotification(payload);
      return;
    }
    this.fanoutUnknown(payload);
  }

  private fanoutNotification(payload: WsNotificationMessage["payload"]) {
    this.handlers.notification.forEach((handler) => {
      try {
        handler(payload);
      } catch (err) {
        console.error('[wsBus] handler for "notification" threw', err);
      }
    });
  }

  private fanoutRecordEvent(payload: WsRecordEventMessage["payload"]) {
    this.handlers.record_event.forEach((handler) => {
      try {
        handler(payload);
      } catch (err) {
        console.error('[wsBus] handler for "record_event" threw', err);
      }
    });
  }

  private fanoutUnknown(payload: unknown) {
    this.handlers.unknown.forEach((handler) => {
      try {
        handler(payload);
      } catch (err) {
        console.error('[wsBus] handler for "unknown" threw', err);
      }
    });
  }
}

function isRecordEvent(value: unknown): value is WsRecordEventMessage["payload"] {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return typeof v.eventType === "string" && typeof v.record_id !== "undefined";
}

function isNotification(value: unknown): value is WsNotificationMessage["payload"] {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return typeof v.id === "number" && typeof v.title === "string";
}

export const wsBus = new WsBus();

/**
 * Convert an HTTP(S) API base URL into the websocket base URL the backend
 * expects: same host/port, `ws(s)://` scheme, with `/api` stripped (the
 * WebSocket route is mounted at `/ws/...` at the project root).
 */
export function deriveWsBaseUrl(httpBaseUrl: string): string {
  return httpBaseUrl
    .replace(/^http/, "ws")
    .replace(/\/api\/?$/, "")
    .replace(/\/$/, "");
}
