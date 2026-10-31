import type { PricePoint } from "./priceStore";
import type { Snapshot } from "./types";

export interface ChartPoint {
  time: number;
  value: number;
}

/**
 * Lightweight Charts needs strictly ascending whole-second times, but ticks come
 * every 500ms. Keep the last value in each second.
 */
export function toSecondPoints(points: { time: number; value: number }[]): ChartPoint[] {
  const sorted = [...points].sort((a, b) => a.time - b.time);
  const out: ChartPoint[] = [];
  for (const point of sorted) {
    const time = Math.floor(point.time);
    const last = out[out.length - 1];
    if (last && last.time === time) last.value = point.value;
    else out.push({ time, value: point.value });
  }
  return out;
}

export function priceHistoryToPoints(history: PricePoint[]): ChartPoint[] {
  return toSecondPoints(history.map((p) => ({ time: p.time, value: p.price })));
}

export function snapshotsToPoints(snapshots: Snapshot[]): ChartPoint[] {
  const parsed = snapshots
    .map((s) => ({ time: Date.parse(s.recorded_at) / 1000, value: s.total_value }))
    .filter((p) => Number.isFinite(p.time));
  return toSecondPoints(parsed);
}
