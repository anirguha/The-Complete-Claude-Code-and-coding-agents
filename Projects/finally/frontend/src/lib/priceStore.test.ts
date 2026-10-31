import { describe, expect, it, vi } from "vitest";
import { PriceStore } from "./priceStore";
import type { PriceTick } from "./types";

const tick = (ticker: string, price: number, timestamp: number): PriceTick => ({
  ticker,
  price,
  previous_price: price,
  timestamp,
  change: 0,
  direction: "flat",
});

describe("PriceStore", () => {
  it("keeps the first price as the session baseline", () => {
    const store = new PriceStore();
    store.ingest({ AAPL: tick("AAPL", 100, 1) });
    store.ingest({ AAPL: tick("AAPL", 110, 2) });
    expect(store.getFirstPrice("AAPL")).toBe(100);
    expect(store.getPrice("AAPL")).toBe(110);
    expect(store.getHistory("AAPL").map((p) => p.price)).toEqual([100, 110]);
  });

  it("ignores tickers that did not change in an event", () => {
    const store = new PriceStore();
    const a = tick("AAPL", 100, 1);
    store.ingest({ AAPL: a, TSLA: tick("TSLA", 50, 1) });
    const listener = vi.fn();
    store.subscribe("AAPL", listener);
    store.ingest({ AAPL: a, TSLA: tick("TSLA", 51, 2) });
    expect(listener).not.toHaveBeenCalled();
    expect(store.getHistory("AAPL")).toHaveLength(1);
  });

  it("notifies only the ticker that changed", () => {
    const store = new PriceStore();
    const aapl = vi.fn();
    const tsla = vi.fn();
    const all = vi.fn();
    store.subscribe("AAPL", aapl);
    store.subscribe("TSLA", tsla);
    store.subscribeAll(all);
    store.ingest({ AAPL: tick("AAPL", 100, 1) });
    expect(aapl).toHaveBeenCalledOnce();
    expect(tsla).not.toHaveBeenCalled();
    expect(all).toHaveBeenCalledOnce();
  });

  it("stops notifying after unsubscribe", () => {
    const store = new PriceStore();
    const listener = vi.fn();
    store.subscribe("AAPL", listener)();
    store.ingest({ AAPL: tick("AAPL", 100, 1) });
    expect(listener).not.toHaveBeenCalled();
  });

  it("seeds from REST without overriding a live tick", () => {
    const store = new PriceStore();
    store.seed("AAPL", 99);
    expect(store.getPrice("AAPL")).toBe(99);
    expect(store.getFirstPrice("AAPL")).toBe(99);
    store.ingest({ AAPL: tick("AAPL", 100, 1) });
    store.seed("AAPL", 50);
    expect(store.getPrice("AAPL")).toBe(100);
    expect(store.getFirstPrice("AAPL")).toBe(99);
  });

  it("skips ticks with no usable price", () => {
    const store = new PriceStore();
    store.ingest({ AAPL: { ...tick("AAPL", 1, 1), price: Number.NaN } });
    expect(store.getTick("AAPL")).toBeUndefined();
  });

  it("caps history length", () => {
    const store = new PriceStore();
    for (let i = 1; i <= 3700; i++) store.ingest({ AAPL: tick("AAPL", i, i) });
    const history = store.getHistory("AAPL");
    expect(history).toHaveLength(3600);
    expect(history.at(-1)?.price).toBe(3700);
  });
});
