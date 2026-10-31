import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TradeBar } from "./TradeBar";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("TradeBar", () => {
  let reply: () => Response;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    reply = () =>
      json({ trade: { id: "1", ticker: "AAPL", side: "buy", quantity: 2, price: 100, executed_at: "" }, portfolio: {} });
    fetchMock = vi.fn(async () => reply());
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("follows the selected ticker", () => {
    const { rerender } = render(<TradeBar selected="AAPL" onTraded={async () => {}} />);
    expect(screen.getByTestId("trade-ticker")).toHaveValue("AAPL");
    rerender(<TradeBar selected="MSFT" onTraded={async () => {}} />);
    expect(screen.getByTestId("trade-ticker")).toHaveValue("MSFT");
  });

  it("posts the order and refreshes", async () => {
    const onTraded = vi.fn(async () => {});
    render(<TradeBar selected="AAPL" onTraded={onTraded} />);
    const user = userEvent.setup();
    await user.type(screen.getByTestId("trade-quantity"), "2");
    await user.click(screen.getByTestId("trade-buy"));
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/portfolio/trade");
    expect(JSON.parse(init.body)).toEqual({ ticker: "AAPL", quantity: 2, side: "buy" });
    expect(onTraded).toHaveBeenCalledOnce();
    expect(screen.getByTestId("trade-status")).toHaveTextContent("Bought 2 AAPL at $100.00");
  });

  it("uppercases a typed ticker and sends sells", async () => {
    render(<TradeBar selected={null} onTraded={async () => {}} />);
    const user = userEvent.setup();
    await user.type(screen.getByTestId("trade-ticker"), "tsla");
    await user.type(screen.getByTestId("trade-quantity"), "1.5");
    await user.click(screen.getByTestId("trade-sell"));
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ ticker: "TSLA", quantity: 1.5, side: "sell" });
  });

  it("shows the API detail in trade-error and does not refresh", async () => {
    reply = () => json({ detail: "Insufficient cash" }, 400);
    const onTraded = vi.fn(async () => {});
    render(<TradeBar selected="AAPL" onTraded={onTraded} />);
    const user = userEvent.setup();
    await user.type(screen.getByTestId("trade-quantity"), "1000");
    await user.click(screen.getByTestId("trade-buy"));
    expect(screen.getByTestId("trade-error")).toHaveTextContent("Insufficient cash");
    expect(onTraded).not.toHaveBeenCalled();
  });

  it("rejects a missing or non-positive quantity before calling the API", async () => {
    render(<TradeBar selected="AAPL" onTraded={async () => {}} />);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("trade-buy"));
    expect(screen.getByTestId("trade-error")).toHaveTextContent("greater than 0");
    await user.type(screen.getByTestId("trade-quantity"), "0");
    await user.click(screen.getByTestId("trade-sell"));
    expect(screen.getByTestId("trade-error")).toHaveTextContent("greater than 0");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
