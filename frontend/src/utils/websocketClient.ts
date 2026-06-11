const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type WebSocketEnvelope<T = unknown> = {
  type: string;
  payload: T;
  generated_at: string;
};

type WebSocketClientOptions<T> = {
  path: string;
  onMessage: (message: WebSocketEnvelope<T>) => void;
  onError?: (event: Event) => void;
  reconnect?: boolean;
  reconnectDelayMs?: number;
};

export class ReconnectingWebSocketClient<T = unknown> {
  private socket: WebSocket | null = null;
  private stopped = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;

  constructor(private options: WebSocketClientOptions<T>) {}

  connect() {
    this.stopped = false;
    this.socket = new WebSocket(this.url());

    this.socket.onmessage = (event) => {
      try {
        this.options.onMessage(JSON.parse(event.data) as WebSocketEnvelope<T>);
      } catch {
        this.options.onError?.(event);
      }
    };

    this.socket.onerror = (event) => {
      this.options.onError?.(event);
    };

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
    };

    this.socket.onclose = () => {
      this.socket = null;
      if (!this.stopped && this.options.reconnect !== false) {
        this.scheduleReconnect();
      }
    };
  }

  close() {
    this.stopped = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.socket?.close();
    this.socket = null;
  }

  private scheduleReconnect() {
    const baseDelay = this.options.reconnectDelayMs ?? 1000;
    const delay = Math.min(30_000, baseDelay * 2 ** this.reconnectAttempts);
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  private url() {
    const token = localStorage.getItem("trading_ai_token");
    const url = new URL(API_BASE_URL.replace(/^http/, "ws") + this.options.path);
    if (token) {
      url.searchParams.set("token", token);
    }
    return url.toString();
  }
}
