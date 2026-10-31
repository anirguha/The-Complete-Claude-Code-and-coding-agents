import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { describeTrade, describeWatchlistChange } from "@/lib/chatActions";
import type { ChatActions, ChatResponse } from "@/lib/types";
import { ChatActionList, ChatPanel } from "./ChatPanel";

describe("action descriptions", () => {
  it("describes executed trades", () => {
    expect(
      describeTrade({ ticker: "AAPL", side: "buy", quantity: 10, status: "executed", price: 191.2, error: null }),
    ).toBe("Bought 10 AAPL at $191.20");
    expect(
      describeTrade({ ticker: "AAPL", side: "sell", quantity: 0.5, status: "executed", price: 200, error: null }),
    ).toBe("Sold 0.5 AAPL at $200.00");
  });

  it("describes failed trades with their error", () => {
    expect(
      describeTrade({ ticker: "TSLA", side: "buy", quantity: 10, status: "failed", price: null, error: "Insufficient cash" }),
    ).toBe("Buy 10 TSLA failed: Insufficient cash");
  });

  it("describes watchlist changes", () => {
    expect(describeWatchlistChange({ ticker: "PYPL", action: "add", status: "applied", error: null })).toBe(
      "Added PYPL to the watchlist",
    );
    expect(describeWatchlistChange({ ticker: "PYPL", action: "remove", status: "applied", error: null })).toBe(
      "Removed PYPL from the watchlist",
    );
    expect(describeWatchlistChange({ ticker: "ZZ", action: "remove", status: "failed", error: "Not found" })).toBe(
      "Remove ZZ failed: Not found",
    );
  });
});

describe("ChatActionList", () => {
  it("renders nothing without actions", () => {
    const { container, rerender } = render(<ChatActionList actions={null} />);
    expect(container).toBeEmptyDOMElement();
    rerender(<ChatActionList actions={{ trades: [], watchlist_changes: [] }} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders successes and failures with their status", () => {
    const actions: ChatActions = {
      trades: [
        { ticker: "AAPL", side: "buy", quantity: 1, status: "executed", price: 10, error: null },
        { ticker: "TSLA", side: "sell", quantity: 9, status: "failed", price: null, error: "Not enough shares" },
      ],
      watchlist_changes: [{ ticker: "PYPL", action: "add", status: "applied", error: null }],
    };
    render(<ChatActionList actions={actions} />);
    const rows = screen.getAllByTestId("chat-action");
    expect(rows.map((r) => r.getAttribute("data-status"))).toEqual(["executed", "failed", "applied"]);
    expect(rows[1]).toHaveTextContent("Sell 9 TSLA failed: Not enough shares");
    expect(rows[1]).toHaveClass("text-down");
  });
});

describe("ChatPanel", () => {
  const stored = [
    {
      role: "user",
      content: "buy 1 AAPL",
      actions: null,
      created_at: "2026-01-01T00:00:00Z",
    },
    {
      role: "assistant",
      content: "Done.",
      actions: {
        trades: [{ ticker: "AAPL", side: "buy", quantity: 1, status: "executed", price: 5, error: null }],
        watchlist_changes: [],
      },
      created_at: "2026-01-01T00:00:01Z",
    },
  ];

  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

  let chatReply: () => Promise<Response>;

  beforeEach(() => {
    Element.prototype.scrollTo = vi.fn();
    chatReply = async () => json({ message: "Hi", trades: [], watchlist_changes: [] });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url === "/api/chat/history") return json({ messages: stored });
        return chatReply();
      }),
    );
  });

  afterEach(() => vi.unstubAllGlobals());

  const renderPanel = (onActions = vi.fn()) => {
    render(<ChatPanel open onClose={() => {}} onActions={onActions} />);
    return onActions;
  };

  it("loads history, including stored actions", async () => {
    renderPanel();
    await waitFor(() => expect(screen.getAllByTestId("chat-message")).toHaveLength(2));
    const assistant = screen.getAllByTestId("chat-message")[1];
    expect(assistant).toHaveAttribute("data-role", "assistant");
    expect(within(assistant).getByTestId("chat-action")).toHaveAttribute("data-status", "executed");
  });

  it("shows a loading indicator, then the reply, and skips refresh with no actions", async () => {
    let release: (r: Response) => void = () => {};
    chatReply = () => new Promise((resolve) => (release = resolve));
    const onActions = renderPanel();
    const user = userEvent.setup();
    await user.type(screen.getByTestId("chat-input"), "hello");
    await user.click(screen.getByTestId("chat-send"));
    expect(await screen.findByTestId("chat-loading")).toBeInTheDocument();
    expect(screen.getByTestId("chat-input")).toHaveValue("");
    release(json({ message: "Hi there", trades: [], watchlist_changes: [] }));
    await screen.findByText("Hi there");
    expect(screen.queryByTestId("chat-loading")).not.toBeInTheDocument();
    expect(onActions).not.toHaveBeenCalled();
  });

  it("requests a refresh when the reply has actions, even failed ones", async () => {
    const reply: ChatResponse = {
      message: "Couldn't do that.",
      trades: [{ ticker: "TSLA", side: "buy", quantity: 99, status: "failed", price: null, error: "Insufficient cash" }],
      watchlist_changes: [],
    };
    chatReply = async () => json(reply);
    const onActions = renderPanel();
    const user = userEvent.setup();
    await user.type(screen.getByTestId("chat-input"), "buy{enter}");
    const row = await screen.findByText(/Buy 99 TSLA failed: Insufficient cash/);
    expect(row.closest("[data-testid=chat-action]")).toHaveAttribute("data-status", "failed");
    expect(onActions).toHaveBeenCalledOnce();
  });

  it("shows an error when the request itself fails, and recovers", async () => {
    chatReply = async () => json({ detail: "Boom" }, 500);
    renderPanel();
    const user = userEvent.setup();
    await user.type(screen.getByTestId("chat-input"), "x{enter}");
    expect(await screen.findByTestId("chat-error")).toHaveTextContent("Boom");
    expect(screen.queryByTestId("chat-loading")).not.toBeInTheDocument();
  });

  it("won't send a blank message", async () => {
    renderPanel();
    expect(screen.getByTestId("chat-send")).toBeDisabled();
  });
});
