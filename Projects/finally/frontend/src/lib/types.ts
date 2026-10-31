export type Direction = "up" | "down" | "flat";

export interface PriceTick {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  direction: Direction;
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  pnl_percent: number;
  weight: number;
}

export interface Portfolio {
  cash_balance: number;
  total_value: number;
  positions_value: number;
  unrealized_pnl: number;
  positions: Position[];
}

export interface Snapshot {
  total_value: number;
  recorded_at: string;
}

export interface WatchlistItem {
  ticker: string;
  price: number | null;
}

export type TradeSide = "buy" | "sell";

export interface Trade {
  id: string;
  ticker: string;
  side: TradeSide;
  quantity: number;
  price: number;
  executed_at: string;
}

export interface TradeResponse {
  trade: Trade;
  portfolio: Portfolio;
}

export interface ChatTradeAction {
  ticker: string;
  side: TradeSide;
  quantity: number;
  status: "executed" | "failed";
  price: number | null;
  error: string | null;
}

export interface ChatWatchlistAction {
  ticker: string;
  action: "add" | "remove";
  status: "applied" | "failed";
  error: string | null;
}

export interface ChatActions {
  trades: ChatTradeAction[];
  watchlist_changes: ChatWatchlistAction[];
}

export interface ChatResponse extends ChatActions {
  message: string;
}

export interface StoredChatMessage {
  role: "user" | "assistant";
  content: string;
  actions: ChatActions | null;
  created_at: string;
}
