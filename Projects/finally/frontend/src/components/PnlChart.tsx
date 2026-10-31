"use client";

import { BaselineSeries, createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useMemo, useRef } from "react";
import { snapshotsToPoints } from "@/lib/chartData";
import { chartOptions } from "@/lib/chartTheme";
import { formatMoney, formatSignedMoney, signClass } from "@/lib/format";
import type { Snapshot } from "@/lib/types";
import { EmptyState, Panel } from "./Panel";

const TOP_FILL_1 = "rgba(60, 201, 133, 0.26)";
const TOP_FILL_2 = "rgba(60, 201, 133, 0.03)";

export function PnlChart({ snapshots }: { snapshots: Snapshot[] }) {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<ISeriesApi<"Baseline"> | null>(null);
  const points = useMemo(() => snapshotsToPoints(snapshots), [snapshots]);

  useEffect(() => {
    if (!container.current) return;
    const instance = createChart(container.current, chartOptions);
    chart.current = instance;
    series.current = instance.addSeries(BaselineSeries, {
      topLineColor: "#3cc985",
      topFillColor1: TOP_FILL_1,
      topFillColor2: TOP_FILL_2,
      bottomLineColor: "#f4645f",
      bottomFillColor1: "rgba(244, 100, 95, 0.03)",
      bottomFillColor2: "rgba(244, 100, 95, 0.26)",
      lineWidth: 2,
      pointMarkersVisible: false,
      priceLineVisible: false,
      baseLineColor: "#4a5666",
      priceFormat: { type: "custom", minMove: 0.01, formatter: formatMoney },
    });
    return () => {
      instance.remove();
      chart.current = null;
      series.current = null;
    };
  }, []);

  useEffect(() => {
    if (!series.current) return;
    // Green above and red below where the recorded history starts.
    const lone = points.length === 1;
    series.current.applyOptions({
      // A value exactly on the baseline counts as below it, so a lone snapshot would
      // read as a loss. Nothing has changed yet: keep its base under it, to draw green.
      baseValue: { type: "price", price: (points[0]?.value ?? 0) - (lone ? 1 : 0) },
      // A lone snapshot has no line to draw, so show it as a dot, not the chart's short dash.
      lineVisible: !lone,
      pointMarkersVisible: lone,
      topFillColor1: lone ? "transparent" : TOP_FILL_1,
      topFillColor2: lone ? "transparent" : TOP_FILL_2,
      baseLineVisible: points.length > 1,
    });
    series.current.setData(points.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    chart.current?.timeScale().fitContent();
  }, [points]);

  const change = points.length > 0 ? points[points.length - 1].value - points[0].value : null;

  return (
    <Panel
      title="Portfolio value over time"
      aside={<span className={`num ${signClass(change)}`}>{formatSignedMoney(change)}</span>}
      className="h-[240px] desk:h-auto"
    >
      <div ref={container} data-testid="pnl-chart" data-points={points.length} className="absolute inset-0" />
      {points.length === 0 ? (
        <EmptyState>Portfolio value is recorded every 30 seconds and after each trade.</EmptyState>
      ) : null}
    </Panel>
  );
}
