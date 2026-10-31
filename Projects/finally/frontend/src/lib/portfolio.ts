import type { Position } from "./types";

export interface ValuedPosition {
  ticker: string;
  quantity: number;
  avgCost: number;
  price: number;
  marketValue: number;
  unrealizedPnl: number;
  pnlPercent: number;
  weight: number;
}

export interface PortfolioValuation {
  total: number;
  positionsValue: number;
  unrealizedPnl: number;
  positions: ValuedPosition[];
}

type PriceLookup = (ticker: string) => number | undefined;

export function valuePosition(position: Position, livePrice: number | undefined) {
  const price = livePrice ?? position.current_price;
  const marketValue = price * position.quantity;
  const unrealizedPnl = (price - position.avg_cost) * position.quantity;
  const pnlPercent = position.avg_cost > 0 ? (price / position.avg_cost - 1) * 100 : 0;
  return { price, marketValue, unrealizedPnl, pnlPercent };
}

/** Client-side valuation: cash + sum(latest SSE price x quantity). */
export function valuePortfolio(
  cash: number,
  positions: Position[],
  priceOf: PriceLookup,
): PortfolioValuation {
  const valued = positions.map((p) => ({
    ticker: p.ticker,
    quantity: p.quantity,
    avgCost: p.avg_cost,
    ...valuePosition(p, priceOf(p.ticker)),
  }));
  const positionsValue = valued.reduce((sum, p) => sum + p.marketValue, 0);
  const unrealizedPnl = valued.reduce((sum, p) => sum + p.unrealizedPnl, 0);
  return {
    total: cash + positionsValue,
    positionsValue,
    unrealizedPnl,
    positions: valued.map((p) => ({
      ...p,
      weight: positionsValue > 0 ? p.marketValue / positionsValue : 0,
    })),
  };
}

/** Change since the first price this client saw for a ticker, in percent. */
export function sessionChangePercent(
  first: number | undefined,
  current: number | undefined,
): number | null {
  if (first == null || current == null || first <= 0) return null;
  return (current / first - 1) * 100;
}
