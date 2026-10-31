export interface TreemapItem {
  id: string;
  value: number;
}

export interface TreemapRect {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface Sized {
  id: string;
  area: number;
}

function worstRatio(row: Sized[], side: number): number {
  let sum = 0;
  let max = 0;
  let min = Infinity;
  for (const { area } of row) {
    sum += area;
    if (area > max) max = area;
    if (area < min) min = area;
  }
  const sideSq = side * side;
  const sumSq = sum * sum;
  return Math.max((sideSq * max) / sumSq, sumSq / (sideSq * min));
}

/**
 * Squarified treemap (Bruls, Huizing, van Wijk). Rectangles fill width x height
 * exactly, with areas proportional to value. Non-positive values are dropped.
 */
export function squarify(items: TreemapItem[], width: number, height: number): TreemapRect[] {
  const positive = items.filter((i) => Number.isFinite(i.value) && i.value > 0);
  if (positive.length === 0 || width <= 0 || height <= 0) return [];

  const total = positive.reduce((sum, i) => sum + i.value, 0);
  const scale = (width * height) / total;
  const queue: Sized[] = positive
    .map((i) => ({ id: i.id, area: i.value * scale }))
    .sort((a, b) => b.area - a.area);

  const rects: TreemapRect[] = [];
  let x = 0;
  let y = 0;
  let w = width;
  let h = height;

  const place = (row: Sized[]) => {
    const rowArea = row.reduce((sum, r) => sum + r.area, 0);
    if (w >= h) {
      // Column on the left edge, cells stacked top to bottom.
      const columnWidth = rowArea / h;
      let cy = y;
      for (const r of row) {
        const cellHeight = r.area / columnWidth;
        rects.push({ id: r.id, x, y: cy, width: columnWidth, height: cellHeight });
        cy += cellHeight;
      }
      x += columnWidth;
      w -= columnWidth;
    } else {
      // Row along the top edge, cells laid left to right.
      const rowHeight = rowArea / w;
      let cx = x;
      for (const r of row) {
        const cellWidth = r.area / rowHeight;
        rects.push({ id: r.id, x: cx, y, width: cellWidth, height: rowHeight });
        cx += cellWidth;
      }
      y += rowHeight;
      h -= rowHeight;
    }
  };

  let row: Sized[] = [];
  for (const item of queue) {
    const side = Math.min(w, h);
    if (row.length === 0 || worstRatio([...row, item], side) <= worstRatio(row, side)) {
      row.push(item);
    } else {
      place(row);
      row = [item];
    }
  }
  if (row.length > 0) place(row);
  return rects;
}

const NEUTRAL = [34, 43, 56];
const PROFIT = [24, 148, 92];
const LOSS = [196, 58, 54];
/** P&L at which a cell reaches full color. */
const FULL_COLOR_PERCENT = 6;

/** Diverging color for a heatmap cell: green for profit, red for loss. */
export function heatColor(pnlPercent: number): string {
  const strength = Math.min(Math.abs(pnlPercent) / FULL_COLOR_PERCENT, 1);
  // A square root keeps small moves readable instead of nearly neutral.
  const t = Math.sqrt(strength);
  const target = pnlPercent >= 0 ? PROFIT : LOSS;
  const [r, g, b] = NEUTRAL.map((n, i) => Math.round(n + (target[i] - n) * t));
  return `rgb(${r}, ${g}, ${b})`;
}

export function pnlState(pnlPercent: number): "profit" | "loss" | "flat" {
  if (pnlPercent > 0) return "profit";
  if (pnlPercent < 0) return "loss";
  return "flat";
}
