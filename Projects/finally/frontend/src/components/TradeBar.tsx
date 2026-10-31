"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { formatMoney, formatQuantity } from "@/lib/format";
import type { TradeSide } from "@/lib/types";

export function TradeBar({
  selected,
  onTraded,
}: {
  selected: string | null;
  onTraded: () => Promise<void>;
}) {
  const [ticker, setTicker] = useState(selected ?? "");
  const [quantity, setQuantity] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [filled, setFilled] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Clicking a ticker elsewhere loads it into the ticket, without clobbering
  // anything typed while the selection stays put.
  const [lastSelected, setLastSelected] = useState(selected);
  if (selected !== lastSelected) {
    setLastSelected(selected);
    if (selected) setTicker(selected);
  }

  const submit = async (side: TradeSide) => {
    const symbol = ticker.trim().toUpperCase();
    const shares = Number(quantity);
    setFilled(null);
    if (!symbol) {
      setError("Enter a ticker.");
      return;
    }
    if (!quantity.trim() || !Number.isFinite(shares) || shares <= 0) {
      setError("Enter a quantity greater than 0.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const { trade } = await api.trade(symbol, shares, side);
      setFilled(
        `${side === "buy" ? "Bought" : "Sold"} ${formatQuantity(trade.quantity)} ${trade.ticker} at ${formatMoney(trade.price)}`,
      );
      await onTraded();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The trade didn't go through. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-label="Trade" className="shrink-0 bg-pane p-2">
      <div className="grid grid-cols-[1fr_1fr_auto_auto] items-center gap-1.5">
        <input
          data-testid="trade-ticker"
          aria-label="Ticker"
          className="field font-semibold uppercase placeholder:font-normal placeholder:normal-case"
          placeholder="Ticker"
          value={ticker}
          maxLength={7}
          autoComplete="off"
          spellCheck={false}
          onChange={(e) => setTicker(e.target.value)}
        />
        <input
          data-testid="trade-quantity"
          aria-label="Quantity"
          className="field num"
          placeholder="Qty"
          type="number"
          min="0"
          step="any"
          inputMode="decimal"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
        />
        <button
          type="button"
          data-testid="trade-buy"
          className="btn-submit"
          disabled={busy}
          onClick={() => void submit("buy")}
        >
          Buy
        </button>
        <button
          type="button"
          data-testid="trade-sell"
          className="btn-submit"
          disabled={busy}
          onClick={() => void submit("sell")}
        >
          Sell
        </button>
      </div>
      {error ? (
        <p role="alert" data-testid="trade-error" className="pt-1.5 text-down">
          {error}
        </p>
      ) : null}
      {filled ? (
        <p role="status" data-testid="trade-status" className="pt-1.5 text-up">
          {filled}
        </p>
      ) : null}
    </section>
  );
}
