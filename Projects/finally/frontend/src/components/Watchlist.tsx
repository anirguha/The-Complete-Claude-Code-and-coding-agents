"use client";

import { useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import { EMPTY, formatPercent, signClass } from "@/lib/format";
import { sessionChangePercent } from "@/lib/portfolio";
import { priceStore, useTick } from "@/lib/priceStore";
import type { WatchlistItem } from "@/lib/types";
import { LivePrice } from "./PriceCell";
import { Sparkline } from "./Sparkline";
import { Panel } from "./Panel";

const COLUMNS = "grid grid-cols-[52px_minmax(36px,1fr)_72px_56px_22px] items-center gap-1.5";

export function SessionChange({ ticker, testId }: { ticker: string; testId?: string }) {
  const tick = useTick(ticker);
  const change = sessionChangePercent(priceStore.getFirstPrice(ticker), tick?.price);
  return (
    <span className={`num block text-right ${signClass(change)}`} data-testid={testId}>
      {change == null ? EMPTY : formatPercent(change)}
    </span>
  );
}

export function Watchlist({
  items,
  selected,
  onSelect,
  onChanged,
}: {
  items: WatchlistItem[] | null;
  selected: string | null;
  onSelect: (ticker: string) => void;
  onChanged: () => Promise<void>;
}) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (action: () => Promise<unknown>) => {
    setError(null);
    setBusy(true);
    try {
      await action();
      await onChanged();
      return true;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't update the watchlist.");
      return false;
    } finally {
      setBusy(false);
    }
  };

  const add = async (event: FormEvent) => {
    event.preventDefault();
    const ticker = draft.trim().toUpperCase();
    if (!ticker) return;
    if (await run(() => api.addWatchlist(ticker))) setDraft("");
  };

  return (
    <Panel title="Watchlist" className="flex-1">
      <div className={`${COLUMNS} h-6 shrink-0 border-b border-edge pl-2.5 pr-1.5 text-[11px] text-faint`}>
        <span>Ticker</span>
        <span>Trend</span>
        <span className="text-right">Price</span>
        <span className="text-right">Session %</span>
        <span />
      </div>
      <div className="pane-scroll flex min-h-0 flex-1 flex-col overflow-y-auto">
        {items?.map((item) => {
          const isSelected = item.ticker === selected;
          return (
            <div
              key={item.ticker}
              data-testid={`watchlist-row-${item.ticker}`}
              aria-current={isSelected ? "true" : undefined}
              onClick={() => onSelect(item.ticker)}
              className={`${COLUMNS} max-h-14 min-h-10 flex-1 cursor-pointer border-b border-l-2 border-b-edge/50 pl-2 pr-1.5 hover:bg-raised ${
                isSelected ? "border-l-amber bg-raised" : "border-l-transparent"
              }`}
            >
              <button
                type="button"
                className={`cursor-pointer text-left text-[13px] font-semibold ${isSelected ? "text-amber" : "text-ink"}`}
              >
                {item.ticker}
              </button>
              <Sparkline ticker={item.ticker} />
              <span className="text-right">
                <LivePrice ticker={item.ticker} testId={`price-${item.ticker}`} />
              </span>
              <SessionChange ticker={item.ticker} testId={`session-${item.ticker}`} />
              <button
                type="button"
                data-testid={`watchlist-remove-${item.ticker}`}
                aria-label={`Remove ${item.ticker} from watchlist`}
                title={`Remove ${item.ticker}`}
                disabled={busy}
                onClick={(event) => {
                  event.stopPropagation();
                  void run(() => api.removeWatchlist(item.ticker));
                }}
                className="flex h-5 w-5 cursor-pointer items-center justify-center rounded-sm text-[15px] leading-none text-faint hover:bg-edge hover:text-ink"
              >
                ×
              </button>
            </div>
          );
        })}
        {items && items.length === 0 ? (
          <p className="p-4 text-dim">Your watchlist is empty. Add a ticker below to start streaming its price.</p>
        ) : null}
      </div>
      <form onSubmit={add} className="flex shrink-0 gap-1.5 border-t border-edge p-2">
        <input
          data-testid="watchlist-add-input"
          aria-label="Ticker to add to watchlist"
          className="field uppercase placeholder:normal-case"
          placeholder="Add a ticker, like PYPL"
          value={draft}
          maxLength={7}
          autoComplete="off"
          spellCheck={false}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button
          type="submit"
          data-testid="watchlist-add-button"
          className="btn-submit shrink-0"
          disabled={busy || !draft.trim()}
        >
          Add
        </button>
      </form>
      {error ? (
        <p role="alert" data-testid="watchlist-error" className="shrink-0 px-2.5 pb-2 text-down">
          {error}
        </p>
      ) : null}
    </Panel>
  );
}
