export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

export type ConnectionEvent =
  | { type: "open" }
  | { type: "message" }
  | { type: "error"; readyState: number }
  /** Reconnecting for too long: the feed should be treated as down. */
  | { type: "timeout" };

/** EventSource.CLOSED: the browser has given up and will not retry on its own. */
const CLOSED = 2;

export function nextConnectionStatus(
  current: ConnectionStatus,
  event: ConnectionEvent,
): ConnectionStatus {
  switch (event.type) {
    case "open":
    case "message":
      return "connected";
    case "error":
      if (event.readyState === CLOSED) return "disconnected";
      // Failed retries while already down must not flip the dot back to yellow.
      return current === "disconnected" ? "disconnected" : "reconnecting";
    case "timeout":
      return current === "reconnecting" ? "disconnected" : current;
  }
}
