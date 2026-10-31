import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { priceStore, useTick } from "@/lib/priceStore";
import type { PriceTick, WatchlistItem } from "@/lib/types";
import { ConnectionDot, Header } from "./Header";
import { SessionChange, Watchlist } from "./Watchlist";

const tick = (ticker: string, price: number, timestamp: number): PriceTick => ({
  ticker,
  price,
  previous_price: price,
  timestamp,
  change: 0,
  direction: "flat",
});

let unique = 0;
const freshTicker = () => `T${(unique++).toString(36).toUpperCase()}`;

afterEach(() => {
  document.body.innerHTML = "";
});

describe("SessionChange", () => {
  it("shows a dash until there is a price, then the change since the first", () => {
    const t = freshTicker();
    render(<SessionChange ticker={t} testId={`session-${t}`} />);
    const cell = screen.getByTestId(`session-${t}`);
    expect(cell).toHaveTextContent("—");
    act(() => priceStore.ingest({ [t]: tick(t, 200, 1) }));
    expect(cell).toHaveTextContent("0.00%");
    act(() => priceStore.ingest({ [t]: tick(t, 210, 2) }));
    expect(cell).toHaveTextContent("+5.00%");
    expect(cell).toHaveClass("text-up");
    act(() => priceStore.ingest({ [t]: tick(t, 190, 3) }));
    expect(cell).toHaveTextContent("-5.00%");
    expect(cell).toHaveClass("text-down");
  });
});

describe("render isolation", () => {
  it("re-renders a subscriber only when its own ticker ticks", () => {
    const a = freshTicker();
    const b = freshTicker();
    let renders = 0;
    function Probe() {
      useTick(a);
      renders += 1;
      return null;
    }
    render(<Probe />);
    const initial = renders;
    act(() => priceStore.ingest({ [b]: tick(b, 1, 1) }));
    expect(renders).toBe(initial);
    act(() => priceStore.ingest({ [a]: tick(a, 1, 1) }));
    expect(renders).toBe(initial + 1);
  });
});

describe("Watchlist", () => {
  it("renders only the tickers it is given, even if SSE carries more", () => {
    const watched = freshTicker();
    const heldOnly = freshTicker();
    act(() => priceStore.ingest({ [watched]: tick(watched, 10, 1), [heldOnly]: tick(heldOnly, 20, 1) }));
    const items: WatchlistItem[] = [{ ticker: watched, price: 10 }];
    render(<Watchlist items={items} selected={watched} onSelect={() => {}} onChanged={async () => {}} />);
    expect(screen.getByTestId(`watchlist-row-${watched}`)).toBeInTheDocument();
    expect(screen.getByTestId(`price-${watched}`)).toHaveTextContent("$10.00");
    expect(screen.queryByTestId(`watchlist-row-${heldOnly}`)).not.toBeInTheDocument();
  });
});

describe("Header", () => {
  const portfolio = (cash: number, ticker?: string) => ({
    cash_balance: cash,
    total_value: cash,
    positions_value: 0,
    unrealized_pnl: 0,
    positions: ticker
      ? [
          {
            ticker,
            quantity: 10,
            avg_cost: 100,
            current_price: 100,
            market_value: 1000,
            unrealized_pnl: 0,
            pnl_percent: 0,
            weight: 1,
          },
        ]
      : [],
  });

  it("formats the balance and total as money", () => {
    render(<Header portfolio={portfolio(10000)} status="connected" chatOpen onToggleChat={() => {}} />);
    expect(screen.getByTestId("header-total-value")).toHaveTextContent("$10,000.00");
    expect(screen.getByTestId("header-cash")).toHaveTextContent("$10,000.00");
  });

  it("revalues the total from live prices", () => {
    const t = freshTicker();
    render(<Header portfolio={portfolio(500, t)} status="connected" chatOpen onToggleChat={() => {}} />);
    expect(screen.getByTestId("header-total-value")).toHaveTextContent("$1,500.00");
    act(() => priceStore.ingest({ [t]: tick(t, 120, 1) }));
    expect(screen.getByTestId("header-total-value")).toHaveTextContent("$1,700.00");
    expect(screen.getByTestId("header-pnl")).toHaveTextContent("+$200.00");
    expect(screen.getByTestId("header-cash")).toHaveTextContent("$500.00");
  });

  it("shows a dash before the portfolio loads", () => {
    render(<Header portfolio={null} status="reconnecting" chatOpen onToggleChat={() => {}} />);
    expect(screen.getByTestId("header-total-value")).toHaveTextContent("—");
  });
});

describe("ConnectionDot", () => {
  it.each([
    ["connected", "bg-up"],
    ["reconnecting", "bg-amber"],
    ["disconnected", "bg-down"],
  ] as const)("exposes %s as data-status with the matching color", (status, color) => {
    render(<ConnectionDot status={status} />);
    const dot = screen.getByTestId("connection-status");
    expect(dot).toHaveAttribute("data-status", status);
    expect(dot.querySelector("span")).toHaveClass(color);
  });
});
