import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import type { PriceTick } from "./types";

/** About 30 minutes of 500ms ticks per ticker. */
const MAX_HISTORY = 3600;

export interface PricePoint {
  time: number;
  price: number;
}

type Listener = () => void;

const NO_HISTORY: PricePoint[] = [];

/**
 * Prices live outside React. Each leaf that shows a ticker subscribes to just
 * that ticker, so a 500ms tick repaints a few cells rather than the whole tree.
 */
export class PriceStore {
  private ticks = new Map<string, PriceTick>();
  private first = new Map<string, number>();
  private history = new Map<string, PricePoint[]>();
  private tickerListeners = new Map<string, Set<Listener>>();
  private allListeners = new Set<Listener>();
  private version = 0;

  /** Apply an SSE event. Each event repeats every ticker; unchanged ones are ignored. */
  ingest(payload: Record<string, PriceTick>): void {
    const changed: string[] = [];
    for (const [ticker, tick] of Object.entries(payload)) {
      if (!tick || !Number.isFinite(tick.price)) continue;
      const previous = this.ticks.get(ticker);
      if (previous && previous.timestamp === tick.timestamp && previous.price === tick.price) {
        continue;
      }
      this.ticks.set(ticker, tick);
      if (!this.first.has(ticker)) this.first.set(ticker, tick.price);
      this.pushHistory(ticker, { time: tick.timestamp, price: tick.price });
      changed.push(ticker);
    }
    if (changed.length > 0) this.notify(changed);
  }

  /** Use a REST price until the first SSE tick for the ticker arrives. */
  seed(ticker: string, price: number): void {
    if (this.ticks.has(ticker) || !Number.isFinite(price)) return;
    this.ticks.set(ticker, {
      ticker,
      price,
      previous_price: price,
      timestamp: 0,
      change: 0,
      direction: "flat",
    });
    this.first.set(ticker, price);
    this.notify([ticker]);
  }

  private pushHistory(ticker: string, point: PricePoint): void {
    const series = this.history.get(ticker);
    if (!series) {
      this.history.set(ticker, [point]);
      return;
    }
    // New array so anything holding the old reference never sees it mutate.
    const next = series.length >= MAX_HISTORY ? series.slice(1) : series.slice();
    next.push(point);
    this.history.set(ticker, next);
  }

  private notify(tickers: string[]): void {
    this.version += 1;
    for (const ticker of tickers) {
      this.tickerListeners.get(ticker)?.forEach((listener) => listener());
    }
    this.allListeners.forEach((listener) => listener());
  }

  getTick = (ticker: string): PriceTick | undefined => this.ticks.get(ticker);
  getPrice = (ticker: string): number | undefined => this.ticks.get(ticker)?.price;
  getFirstPrice = (ticker: string): number | undefined => this.first.get(ticker);
  getHistory = (ticker: string): PricePoint[] => this.history.get(ticker) ?? NO_HISTORY;
  getVersion = (): number => this.version;

  subscribe = (ticker: string, listener: Listener): (() => void) => {
    let listeners = this.tickerListeners.get(ticker);
    if (!listeners) {
      listeners = new Set();
      this.tickerListeners.set(ticker, listeners);
    }
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  };

  subscribeAll = (listener: Listener): (() => void) => {
    this.allListeners.add(listener);
    return () => {
      this.allListeners.delete(listener);
    };
  };
}

export const priceStore = new PriceStore();

/** Latest tick for one ticker; re-renders only when that ticker changes. */
export function useTick(ticker: string | null, store: PriceStore = priceStore) {
  const subscribe = useCallback(
    (listener: Listener) => (ticker ? store.subscribe(ticker, listener) : () => {}),
    [ticker, store],
  );
  return useSyncExternalStore(
    subscribe,
    () => (ticker ? store.getTick(ticker) : undefined),
    () => undefined,
  );
}

/** Re-renders on every event that changes any price. */
export function useStoreVersion(store: PriceStore = priceStore): number {
  return useSyncExternalStore(store.subscribeAll, store.getVersion, () => 0);
}

/** Re-renders on price changes, at most once every `ms`. */
export function useThrottledVersion(ms: number, store: PriceStore = priceStore): number {
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    const unsubscribe = store.subscribeAll(() => {
      if (timer !== null) return;
      timer = setTimeout(() => {
        timer = null;
        setVersion((v) => v + 1);
      }, ms);
    });
    return () => {
      unsubscribe();
      if (timer !== null) clearTimeout(timer);
    };
  }, [ms, store]);
  return version;
}
