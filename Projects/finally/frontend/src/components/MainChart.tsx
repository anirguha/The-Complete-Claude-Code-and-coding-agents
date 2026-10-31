"use client";

import { AreaSeries, createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";
import { priceHistoryToPoints } from "@/lib/chartData";
import { chartOptions } from "@/lib/chartTheme";
import { priceStore, useTick } from "@/lib/priceStore";
import { EmptyState, Panel } from "./Panel";
import { LivePrice } from "./PriceCell";
import { SessionChange } from "./Watchlist";

export function MainChart({ ticker }: { ticker: string | null }) {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<ISeriesApi<"Area"> | null>(null);
  const lastTime = useRef(0);
  const tick = useTick(ticker);

  useEffect(() => {
    if (!container.current) return;
    const instance = createChart(container.current, chartOptions);
    chart.current = instance;
    series.current = instance.addSeries(AreaSeries, {
      lineColor: "#209dd7",
      lineWidth: 2,
      topColor: "rgba(32, 157, 215, 0.28)",
      bottomColor: "rgba(32, 157, 215, 0.02)",
      priceLineColor: "#ecad0a",
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
    });
    return () => {
      instance.remove();
      chart.current = null;
      series.current = null;
    };
  }, []);

  // Switching tickers replaces the series with everything received so far.
  useEffect(() => {
    if (!series.current) return;
    const points = ticker ? priceHistoryToPoints(priceStore.getHistory(ticker)) : [];
    series.current.setData(points.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    lastTime.current = points.at(-1)?.time ?? 0;
    chart.current?.timeScale().fitContent();
  }, [ticker]);

  useEffect(() => {
    if (!series.current || !tick || tick.timestamp <= 0) return;
    const time = Math.floor(tick.timestamp);
    if (time < lastTime.current) return;
    series.current.update({ time: time as UTCTimestamp, value: tick.price });
    lastTime.current = time;
    chart.current?.timeScale().fitContent();
  }, [tick]);

  const pointCount = ticker ? priceStore.getHistory(ticker).length : 0;

  return (
    <Panel
      title={
        <span data-testid="main-chart-ticker" className="text-amber">
          {ticker ?? "No ticker selected"}
        </span>
      }
      aside={
        ticker ? (
          <>
            <LivePrice ticker={ticker} testId="main-chart-price" className="font-semibold text-ink" />
            <span className="flex items-center gap-1.5">
              <span className="text-faint">Session</span>
              <SessionChange ticker={ticker} />
            </span>
          </>
        ) : null
      }
      className="min-h-[280px] desk:min-h-0"
    >
      <div
        ref={container}
        data-testid="main-chart"
        data-points={pointCount}
        className="absolute inset-0"
      />
      <a
        href="https://www.tradingview.com/lightweight-charts/"
        target="_blank"
        rel="noreferrer"
        className="absolute bottom-7 left-2 z-10 text-[10px] text-faint hover:text-dim"
      >
        Charts by TradingView
      </a>
      {pointCount === 0 ? (
        <EmptyState>
          {ticker
            ? `Waiting for ${ticker} prices. The chart fills in as they arrive.`
            : "Pick a ticker from the watchlist to chart it."}
        </EmptyState>
      ) : null}
    </Panel>
  );
}
