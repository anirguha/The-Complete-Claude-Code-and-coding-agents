"use client";

import { priceStore, useTick } from "@/lib/priceStore";
import { sparklinePoints } from "@/lib/sparkline";

const WIDTH = 64;
const HEIGHT = 22;
/** Two minutes of ticks at 500ms. */
const WINDOW = 240;

export function Sparkline({ ticker }: { ticker: string }) {
  // The tick is the change signal; the series itself is read from the store.
  useTick(ticker);
  const values = priceStore.getHistory(ticker).slice(-WINDOW).map((p) => p.price);
  const points = sparklinePoints(values, WIDTH, HEIGHT);
  const rising = values.length > 1 && values[values.length - 1] >= values[0];
  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      preserveAspectRatio="none"
      className="h-[22px] w-full"
      aria-hidden="true"
      data-testid={`sparkline-${ticker}`}
    >
      {points ? (
        <polyline
          points={points}
          fill="none"
          stroke={rising ? "var(--color-up)" : "var(--color-down)"}
          strokeWidth="1.2"
          vectorEffect="non-scaling-stroke"
        />
      ) : (
        <line x1="0" x2={WIDTH} y1={HEIGHT / 2} y2={HEIGHT / 2} stroke="var(--color-edge)" strokeDasharray="2 3" />
      )}
    </svg>
  );
}
