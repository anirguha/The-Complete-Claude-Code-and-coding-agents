import type {
  ChatResponse,
  Portfolio,
  Snapshot,
  StoredChatMessage,
  TradeResponse,
  TradeSide,
  WatchlistItem,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Turn a FastAPI error body into one readable line. */
export function errorMessage(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    // 422 validation errors arrive as a list of {loc, msg}.
    const first = detail[0] as { msg?: unknown };
    if (typeof first?.msg === "string") return first.msg;
  }
  return `Request failed with status ${status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: init?.body ? { "Content-Type": "application/json" } : undefined,
    });
  } catch {
    throw new ApiError("Can't reach the server. Check that it is running.", 0);
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(errorMessage(response.status, body), response.status);
  return body as T;
}

const post = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });

export const api = {
  portfolio: () => request<Portfolio>("/api/portfolio"),
  history: () =>
    request<{ snapshots: Snapshot[] }>("/api/portfolio/history").then((r) => r.snapshots),
  trade: (ticker: string, quantity: number, side: TradeSide) =>
    request<TradeResponse>("/api/portfolio/trade", post({ ticker, quantity, side })),
  watchlist: () =>
    request<{ watchlist: WatchlistItem[] }>("/api/watchlist").then((r) => r.watchlist),
  addWatchlist: (ticker: string) => request<WatchlistItem>("/api/watchlist", post({ ticker })),
  removeWatchlist: (ticker: string) =>
    request<{ ticker: string; removed: boolean }>(
      `/api/watchlist/${encodeURIComponent(ticker)}`,
      { method: "DELETE" },
    ),
  chat: (message: string) => request<ChatResponse>("/api/chat", post({ message })),
  chatHistory: () =>
    request<{ messages: StoredChatMessage[] }>("/api/chat/history").then((r) => r.messages),
};
