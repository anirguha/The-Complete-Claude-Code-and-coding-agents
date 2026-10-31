"use client";

import { useEffect, useRef, useState } from "react";
import { formatPercent } from "@/lib/format";
import { valuePortfolio } from "@/lib/portfolio";
import { priceStore, useThrottledVersion } from "@/lib/priceStore";
import { heatColor, pnlState, squarify } from "@/lib/squarify";
import type { Position } from "@/lib/types";
import { EmptyState, Panel } from "./Panel";

const REVALUE_MS = 1000;

function useElementSize(ref: React.RefObject<HTMLElement | null>) {
  const [size, setSize] = useState({ width: 0, height: 0 });
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setSize({ width, height });
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);
  return size;
}

export function Heatmap({
  positions,
  onSelect,
}: {
  positions: Position[];
  onSelect: (ticker: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const { width, height } = useElementSize(container);
  // Sizes and colors drift with prices, but once a second is plenty for a treemap.
  useThrottledVersion(REVALUE_MS);

  const valued = valuePortfolio(0, positions, priceStore.getPrice).positions;
  const byTicker = new Map(valued.map((p) => [p.ticker, p]));
  const rects = squarify(
    valued.map((p) => ({ id: p.ticker, value: p.marketValue })),
    width,
    height,
  );

  return (
    <Panel title="Portfolio heatmap" aside="Size by weight, color by P&L" className="h-[240px] desk:h-auto">
      <div ref={container} data-testid="heatmap" className="absolute inset-0 overflow-hidden">
        {rects.map((rect) => {
          const position = byTicker.get(rect.id)!;
          const roomy = rect.width > 52 && rect.height > 36;
          return (
            <button
              key={rect.id}
              type="button"
              data-testid={`heatmap-cell-${rect.id}`}
              data-pnl={pnlState(position.pnlPercent)}
              aria-label={`${rect.id}: ${formatPercent(position.pnlPercent)}, ${(position.weight * 100).toFixed(1)}% of positions`}
              title={`${rect.id} ${formatPercent(position.pnlPercent)}`}
              onClick={() => onSelect(rect.id)}
              style={{
                left: rect.x,
                top: rect.y,
                width: rect.width,
                height: rect.height,
                backgroundColor: heatColor(position.pnlPercent),
              }}
              className="absolute cursor-pointer overflow-hidden border border-pane p-1.5 text-left text-white hover:brightness-110"
            >
              <span className="block truncate text-[13px] font-semibold leading-tight">{rect.id}</span>
              {roomy ? (
                <span className="num block truncate text-[12px] leading-tight">
                  {formatPercent(position.pnlPercent)}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      {positions.length === 0 ? (
        <EmptyState>No positions yet. Each one you buy appears here, sized by its share of your holdings.</EmptyState>
      ) : null}
    </Panel>
  );
}
