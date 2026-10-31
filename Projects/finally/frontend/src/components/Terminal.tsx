"use client";

import { useEffect, useState } from "react";
import { useTerminalData } from "@/hooks/useTerminalData";
import type { ConnectionStatus } from "@/lib/connection";
import { priceStore } from "@/lib/priceStore";
import { connectPriceStream } from "@/lib/priceStream";
import { ChatPanel } from "./ChatPanel";
import { Header } from "./Header";
import { Heatmap } from "./Heatmap";
import { MainChart } from "./MainChart";
import { PnlChart } from "./PnlChart";
import { PositionsTable } from "./PositionsTable";
import { TradeBar } from "./TradeBar";
import { Watchlist } from "./Watchlist";

/** Below this width the chat is a drawer over the terminal, closed by default. */
const DOCKED_CHAT_WIDTH = 1200;

export function Terminal() {
  const { portfolio, watchlist, history, unreachable, refreshAll, refreshWatchlist } = useTerminalData();
  const [status, setStatus] = useState<ConnectionStatus>("reconnecting");
  const [picked, setPicked] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(true);

  useEffect(() => {
    if (window.innerWidth >= DOCKED_CHAT_WIDTH) return;
    const frame = requestAnimationFrame(() => setChatOpen(false));
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    let seenConnected = false;
    let lostFeed = false;
    return connectPriceStream({
      onPrices: (payload) => priceStore.ingest(payload),
      onStatus: (next) => {
        setStatus(next);
        if (next !== "connected") {
          lostFeed = seenConnected;
          return;
        }
        // Back from an outage: REST state may be stale too.
        if (lostFeed) void refreshAll();
        seenConnected = true;
        lostFeed = false;
      },
    });
  }, [refreshAll]);

  const positions = portfolio?.positions ?? [];
  const knownTicker = (t: string | null) =>
    t != null && (watchlist?.some((w) => w.ticker === t) || positions.some((p) => p.ticker === t));
  // A removed ticker falls back to the top of the watchlist.
  const selected = knownTicker(picked) ? picked : (watchlist?.[0]?.ticker ?? positions[0]?.ticker ?? null);

  return (
    <div className="flex min-h-screen flex-col desk:h-screen desk:overflow-hidden">
      <Header
        portfolio={portfolio}
        status={status}
        chatOpen={chatOpen}
        onToggleChat={() => setChatOpen((open) => !open)}
      />
      {unreachable ? (
        <p role="alert" data-testid="load-error" className="shrink-0 bg-raised px-3 py-1 text-amber">
          Can&apos;t reach the server. Retrying every few seconds.
        </p>
      ) : null}
      <div className="flex min-h-0 flex-1">
        <main className="grid min-h-0 min-w-0 flex-1 grid-cols-1 gap-px bg-edge md:grid-cols-[280px_minmax(0,1fr)] desk:grid-cols-[320px_minmax(0,1fr)]">
          <div className="flex min-h-0 min-w-0 flex-col gap-px">
            <Watchlist
              items={watchlist}
              selected={selected}
              onSelect={setPicked}
              onChanged={refreshWatchlist}
            />
            <TradeBar selected={selected} onTraded={refreshAll} />
          </div>
          <div className="grid min-h-0 min-w-0 grid-cols-1 grid-rows-[minmax(280px,1fr)_auto_auto] gap-px desk:grid-rows-[minmax(0,1.2fr)_minmax(0,0.95fr)_minmax(0,0.85fr)]">
            <MainChart ticker={selected} />
            <div className="grid min-h-0 min-w-0 grid-cols-1 gap-px lg:grid-cols-2">
              <Heatmap positions={positions} onSelect={setPicked} />
              <PnlChart snapshots={history} />
            </div>
            <PositionsTable positions={positions} onSelect={setPicked} />
          </div>
        </main>
        <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} onActions={() => void refreshAll()} />
      </div>
    </div>
  );
}
