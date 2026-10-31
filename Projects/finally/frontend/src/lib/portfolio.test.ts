import { describe, expect, it } from "vitest";
import { sessionChangePercent, valuePortfolio, valuePosition } from "./portfolio";
import type { Position } from "./types";

const position = (ticker: string, quantity: number, avg_cost: number, current_price: number): Position => ({
  ticker,
  quantity,
  avg_cost,
  current_price,
  market_value: quantity * current_price,
  unrealized_pnl: 0,
  pnl_percent: 0,
  weight: 0,
});

describe("valuePortfolio", () => {
  it("is cash when there are no positions", () => {
    expect(valuePortfolio(10_000, [], () => undefined)).toEqual({
      total: 10_000,
      positionsValue: 0,
      unrealizedPnl: 0,
      positions: [],
    });
  });

  it("is cash plus live price x quantity", () => {
    const prices: Record<string, number> = { AAPL: 200, TSLA: 90 };
    const v = valuePortfolio(1000, [position("AAPL", 10, 190, 195), position("TSLA", 5, 100, 95)], (t) => prices[t]);
    expect(v.positionsValue).toBe(2450);
    expect(v.total).toBe(3450);
    expect(v.unrealizedPnl).toBe(100 - 50);
  });

  it("falls back to the REST price when no tick has arrived", () => {
    const v = valuePortfolio(0, [position("AAPL", 2, 100, 110)], () => undefined);
    expect(v.total).toBe(220);
    expect(v.positions[0].price).toBe(110);
  });

  it("computes weights that sum to 1", () => {
    const v = valuePortfolio(500, [position("A", 1, 10, 75), position("B", 1, 10, 25)], () => undefined);
    expect(v.positions.map((p) => p.weight)).toEqual([0.75, 0.25]);
  });

  it("handles fractional shares", () => {
    const v = valuePortfolio(0, [position("A", 0.5, 100, 100)], () => 120);
    expect(v.total).toBe(60);
    expect(v.unrealizedPnl).toBe(10);
  });
});

describe("valuePosition", () => {
  it("reports a profit", () => {
    const r = valuePosition(position("A", 10, 100, 100), 112.5);
    expect(r.unrealizedPnl).toBe(125);
    expect(r.pnlPercent).toBeCloseTo(12.5);
  });

  it("reports a loss", () => {
    const r = valuePosition(position("A", 4, 50, 50), 40);
    expect(r.unrealizedPnl).toBe(-40);
    expect(r.pnlPercent).toBeCloseTo(-20);
  });

  it("does not divide by a zero cost", () => {
    expect(valuePosition(position("A", 1, 0, 5), 5).pnlPercent).toBe(0);
  });
});

describe("sessionChangePercent", () => {
  it("measures from the first price received", () => {
    expect(sessionChangePercent(100, 105)).toBeCloseTo(5);
    expect(sessionChangePercent(200, 150)).toBeCloseTo(-25);
    expect(sessionChangePercent(100, 100)).toBe(0);
  });

  it("is null without prices to compare", () => {
    expect(sessionChangePercent(undefined, 100)).toBeNull();
    expect(sessionChangePercent(100, undefined)).toBeNull();
    expect(sessionChangePercent(0, 100)).toBeNull();
  });
});
