import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { priceStore } from "@/lib/priceStore";
import type { Portfolio, Snapshot, WatchlistItem } from "@/lib/types";

const POLL_MS = 30_000;
const RETRY_MS = 5_000;

/**
 * Holds the REST-backed state. A counter per resource drops responses that were
 * overtaken by a newer request, so a slow reply cannot undo a fresh trade.
 */
export function useTerminalData() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[] | null>(null);
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [unreachable, setUnreachable] = useState(false);
  const sequence = useRef({ portfolio: 0, watchlist: 0, history: 0 });

  const refreshPortfolio = useCallback(async () => {
    const id = ++sequence.current.portfolio;
    const next = await api.portfolio();
    if (id === sequence.current.portfolio) setPortfolio(next);
  }, []);

  const refreshHistory = useCallback(async () => {
    const id = ++sequence.current.history;
    const next = await api.history();
    if (id === sequence.current.history) setHistory(next);
  }, []);

  const refreshWatchlist = useCallback(async () => {
    const id = ++sequence.current.watchlist;
    const next = await api.watchlist();
    if (id !== sequence.current.watchlist) return;
    for (const item of next) {
      if (item.price != null) priceStore.seed(item.ticker, item.price);
    }
    setWatchlist(next);
  }, []);

  const refreshAll = useCallback(async () => {
    const results = await Promise.allSettled([
      refreshPortfolio(),
      refreshWatchlist(),
      refreshHistory(),
    ]);
    setUnreachable(results.some((r) => r.status === "rejected"));
  }, [refreshPortfolio, refreshWatchlist, refreshHistory]);

  useEffect(() => {
    const first = setTimeout(() => void refreshAll(), 0);
    const poll = setInterval(() => void refreshAll(), POLL_MS);
    return () => {
      clearTimeout(first);
      clearInterval(poll);
    };
  }, [refreshAll]);

  useEffect(() => {
    if (!unreachable) return;
    const retry = setTimeout(() => void refreshAll(), RETRY_MS);
    return () => clearTimeout(retry);
  }, [unreachable, refreshAll]);

  return { portfolio, watchlist, history, unreachable, refreshAll, refreshWatchlist };
}
