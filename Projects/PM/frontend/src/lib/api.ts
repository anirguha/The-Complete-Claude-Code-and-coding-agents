import type { BoardData } from "@/lib/kanban";

const API_BASE_URL =
  process.env.NODE_ENV === "development"
    ? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
    : "";

const request = async <T>(
  path: string,
  init: RequestInit = {}
): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}/api${path}`, {
    ...init,
    credentials: "include",
    signal: AbortSignal.timeout(90_000),
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  }).catch((error: unknown) => {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new Error("The request timed out. Please try again.");
    }
    throw error;
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? `Request failed (${response.status}).`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
};

export type ChatTurn = {
  role: "user" | "assistant";
  content: string;
};

export type ChatResult = {
  response: string;
  board: BoardData;
};

export const api = {
  currentUser: () => request<{ username: string }>("/auth/me"),
  login: (username: string, password: string) =>
    request<{ username: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () =>
    request<void>("/auth/logout", {
      method: "POST",
    }),
  getBoard: () => request<BoardData>("/board"),
  saveBoard: (board: BoardData) =>
    request<BoardData>("/board", {
      method: "PUT",
      body: JSON.stringify(board),
    }),
  chat: (message: string, history: ChatTurn[]) =>
    request<ChatResult>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, history }),
    }),
};
