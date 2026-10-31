import { formatMoney, formatQuantity } from "./format";
import type { ChatTradeAction, ChatWatchlistAction } from "./types";

export function describeTrade(trade: ChatTradeAction): string {
  const shares = `${formatQuantity(trade.quantity)} ${trade.ticker}`;
  if (trade.status === "failed") {
    const verb = trade.side === "buy" ? "Buy" : "Sell";
    return `${verb} ${shares} failed: ${trade.error ?? "unknown error"}`;
  }
  const verb = trade.side === "buy" ? "Bought" : "Sold";
  return trade.price == null ? `${verb} ${shares}` : `${verb} ${shares} at ${formatMoney(trade.price)}`;
}

export function describeWatchlistChange(change: ChatWatchlistAction): string {
  if (change.status === "failed") {
    const verb = change.action === "add" ? "Add" : "Remove";
    return `${verb} ${change.ticker} failed: ${change.error ?? "unknown error"}`;
  }
  return change.action === "add"
    ? `Added ${change.ticker} to the watchlist`
    : `Removed ${change.ticker} from the watchlist`;
}
