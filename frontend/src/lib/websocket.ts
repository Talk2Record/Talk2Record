const DEFAULT_RECONNECT_DELAY = 3000;
const MAX_RECONNECT_DELAY = 30000;

export interface WebSocketClientOptions {
  url: string;
  token: string;
  onMessage: (data: unknown) => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
}

export function createNotificationWebSocket({
  url,
  token,
  onMessage,
  onClose,
  onError,
}: WebSocketClientOptions): WebSocket {
  const wsUrl = `${url}?token=${encodeURIComponent(token)}`;
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch {
      onMessage(event.data);
    }
  };

  ws.onclose = () => {
    onClose?.();
  };

  ws.onerror = (error) => {
    onError?.(error);
  };

  return ws;
}

/**
 * Connects to the notifications WebSocket with automatic reconnect.
 * Returns a cleanup function to disconnect.
 */
export function connectNotificationWebSocket(
  baseUrl: string,
  token: string,
  onMessage: (data: unknown) => void,
  options?: { onConnected?: () => void; onDisconnected?: () => void }
): () => void {
  const wsBase = baseUrl.replace(/^http/, "ws").replace(/\/api\/?$/, "");
  const url = `${wsBase}/ws/notifications/`;

  let ws: WebSocket | null = null;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  let reconnectAttempt = 0;

  const connect = () => {
    ws = createNotificationWebSocket({
      url,
      token,
      onMessage,
      onClose: () => {
        options?.onDisconnected?.();
        const delay = Math.min(
          DEFAULT_RECONNECT_DELAY * Math.pow(2, reconnectAttempt),
          MAX_RECONNECT_DELAY
        );
        reconnectAttempt += 1;
        reconnectTimeout = setTimeout(connect, delay);
      },
      onError: () => {
        // Errors often lead to close; reconnect will happen in onClose
      },
    });

    ws.onopen = () => {
      reconnectAttempt = 0;
      options?.onConnected?.();
    };
  };

  connect();

  return () => {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
    if (ws) {
      ws.close();
      ws = null;
    }
  };
}
