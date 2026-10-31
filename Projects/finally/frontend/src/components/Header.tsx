"use client";

import type { ConnectionStatus } from "@/lib/connection";
import { formatMoney, formatSignedMoney, signClass } from "@/lib/format";
import { valuePortfolio } from "@/lib/portfolio";
import { priceStore, useStoreVersion } from "@/lib/priceStore";
import type { Portfolio } from "@/lib/types";

const STATUS: Record<ConnectionStatus, { dot: string; label: string }> = {
  connected: { dot: "bg-up", label: "Live" },
  reconnecting: { dot: "bg-amber", label: "Reconnecting" },
  disconnected: { dot: "bg-down", label: "Disconnected" },
};

export function ConnectionDot({ status }: { status: ConnectionStatus }) {
  const { dot, label } = STATUS[status];
  return (
    <div
      data-testid="connection-status"
      data-status={status}
      className="flex items-center gap-1.5 text-dim"
      title={`Price feed: ${label.toLowerCase()}`}
    >
      <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden="true" />
      <span className="hidden sm:inline">{label}</span>
    </div>
  );
}

function Figure({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] leading-tight text-faint">{label}</div>
      <div className="num whitespace-nowrap text-[15px] font-medium leading-tight">{children}</div>
    </div>
  );
}

/** Revalues on every price event; the only part of the header that does. */
function LiveFigures({ portfolio }: { portfolio: Portfolio | null }) {
  useStoreVersion();
  const valuation = portfolio
    ? valuePortfolio(portfolio.cash_balance, portfolio.positions, priceStore.getPrice)
    : null;
  return (
    <>
      <div className="min-w-0">
        <div className="text-[11px] leading-tight text-faint">Portfolio value</div>
        <div
          data-testid="header-total-value"
          className="display-figure whitespace-nowrap text-[32px] leading-[1.05] text-amber"
        >
          {formatMoney(valuation?.total)}
        </div>
      </div>
      <Figure label="Cash">
        <span data-testid="header-cash">{formatMoney(portfolio?.cash_balance)}</span>
      </Figure>
      <div className="hidden md:block">
        <Figure label="Positions">{formatMoney(valuation?.positionsValue)}</Figure>
      </div>
      <div className="hidden sm:block">
        <Figure label="Unrealized P&L">
          <span data-testid="header-pnl" className={signClass(valuation?.unrealizedPnl)}>
            {formatSignedMoney(valuation?.unrealizedPnl)}
          </span>
        </Figure>
      </div>
    </>
  );
}

export function Header({
  portfolio,
  status,
  chatOpen,
  onToggleChat,
}: {
  portfolio: Portfolio | null;
  status: ConnectionStatus;
  chatOpen: boolean;
  onToggleChat: () => void;
}) {
  return (
    <header className="flex h-[58px] shrink-0 items-center gap-5 border-b border-edge bg-strip px-3 md:gap-8">
      <h1 className="text-[17px] font-bold tracking-tight text-ink">
        Fin<span className="text-amber">Ally</span>
      </h1>
      <LiveFigures portfolio={portfolio} />
      <div className="ml-auto flex shrink-0 items-center gap-4">
        <ConnectionDot status={status} />
        <button
          type="button"
          data-testid="chat-toggle"
          aria-expanded={chatOpen}
          onClick={onToggleChat}
          className={`h-7 cursor-pointer rounded-sm border px-2.5 font-medium ${
            chatOpen ? "border-blue text-blue" : "border-edge text-ink hover:border-blue"
          }`}
        >
          {chatOpen ? "Hide AI chat" : "AI chat"}
        </button>
      </div>
    </header>
  );
}
