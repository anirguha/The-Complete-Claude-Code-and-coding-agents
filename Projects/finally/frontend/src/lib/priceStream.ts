import { nextConnectionStatus, type ConnectionEvent, type ConnectionStatus } from "./connection";
import type { PriceTick } from "./types";

export const RECONNECT_TIMEOUT_MS = 10_000;
export const RETRY_DELAY_MS = 3_000;

export interface PriceStreamOptions {
  url?: string;
  onStatus: (status: ConnectionStatus) => void;
  onPrices: (payload: Record<string, PriceTick>) => void;
  createSource?: (url: string) => EventSource;
}

/**
 * Own the single EventSource. The browser retries network drops by itself, but
 * gives up for good on an HTTP error response, so that case reopens manually.
 * Returns a function that closes the stream.
 */
export function connectPriceStream({
  url = "/api/stream/prices",
  onStatus,
  onPrices,
  createSource = (u) => new EventSource(u),
}: PriceStreamOptions): () => void {
  let status: ConnectionStatus = "reconnecting";
  let source: EventSource | null = null;
  let downTimer: ReturnType<typeof setTimeout> | null = null;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  const clearDownTimer = () => {
    if (downTimer !== null) clearTimeout(downTimer);
    downTimer = null;
  };

  const apply = (event: ConnectionEvent) => {
    const next = nextConnectionStatus(status, event);
    if (next === "reconnecting" && downTimer === null) {
      downTimer = setTimeout(() => {
        downTimer = null;
        apply({ type: "timeout" });
      }, RECONNECT_TIMEOUT_MS);
    }
    if (next !== "reconnecting") clearDownTimer();
    if (next !== status) {
      status = next;
      onStatus(next);
    }
  };

  const open = () => {
    if (disposed) return;
    const es = createSource(url);
    source = es;
    es.onopen = () => apply({ type: "open" });
    es.onmessage = (event: MessageEvent<string>) => {
      apply({ type: "message" });
      try {
        onPrices(JSON.parse(event.data) as Record<string, PriceTick>);
      } catch (error) {
        console.warn("Ignoring malformed price event", error);
      }
    };
    es.onerror = () => {
      apply({ type: "error", readyState: es.readyState });
      if (es.readyState === 2 && !disposed) {
        es.close();
        if (retryTimer === null) {
          retryTimer = setTimeout(() => {
            retryTimer = null;
            open();
          }, RETRY_DELAY_MS);
        }
      }
    };
  };

  onStatus(status);
  // Start the "too long to connect" clock from the very first attempt too.
  downTimer = setTimeout(() => {
    downTimer = null;
    apply({ type: "timeout" });
  }, RECONNECT_TIMEOUT_MS);
  open();

  return () => {
    disposed = true;
    clearDownTimer();
    if (retryTimer !== null) clearTimeout(retryTimer);
    source?.close();
  };
}
