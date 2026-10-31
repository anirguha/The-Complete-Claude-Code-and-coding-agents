import { describe, expect, it } from "vitest";
import { heatColor, pnlState, squarify } from "./squarify";

const area = (r: { width: number; height: number }) => r.width * r.height;

describe("squarify", () => {
  it("returns nothing for empty input or a zero-sized box", () => {
    expect(squarify([], 100, 100)).toEqual([]);
    expect(squarify([{ id: "A", value: 1 }], 0, 100)).toEqual([]);
    expect(squarify([{ id: "A", value: 1 }], 100, 0)).toEqual([]);
  });

  it("gives a single item the whole box", () => {
    expect(squarify([{ id: "A", value: 5 }], 300, 200)).toEqual([{ id: "A", x: 0, y: 0, width: 300, height: 200 }]);
  });

  it("drops zero, negative and non-finite values", () => {
    const rects = squarify(
      [
        { id: "A", value: 1 },
        { id: "B", value: 0 },
        { id: "C", value: -3 },
        { id: "D", value: NaN },
      ],
      100,
      100,
    );
    expect(rects.map((r) => r.id)).toEqual(["A"]);
  });

  it("makes areas proportional to value and fills the box exactly", () => {
    const items = [6, 6, 4, 3, 2, 2, 1].map((value, i) => ({ id: `T${i}`, value }));
    const rects = squarify(items, 600, 400);
    expect(rects).toHaveLength(items.length);
    const total = 24;
    for (const rect of rects) {
      const value = items.find((i) => i.id === rect.id)!.value;
      expect(area(rect)).toBeCloseTo((value / total) * 600 * 400, 6);
    }
    expect(rects.reduce((sum, r) => sum + area(r), 0)).toBeCloseTo(600 * 400, 6);
  });

  it("keeps every rectangle inside the box with no overlaps", () => {
    const items = [40, 25, 13, 9, 7, 3, 2, 1].map((value, i) => ({ id: `T${i}`, value }));
    const rects = squarify(items, 523, 241);
    const eps = 1e-6;
    for (const r of rects) {
      expect(r.x).toBeGreaterThanOrEqual(-eps);
      expect(r.y).toBeGreaterThanOrEqual(-eps);
      expect(r.x + r.width).toBeLessThanOrEqual(523 + eps);
      expect(r.y + r.height).toBeLessThanOrEqual(241 + eps);
    }
    for (let i = 0; i < rects.length; i++) {
      for (let j = i + 1; j < rects.length; j++) {
        const a = rects[i];
        const b = rects[j];
        const overlapX = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
        const overlapY = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
        expect(overlapX <= eps || overlapY <= eps).toBe(true);
      }
    }
  });

  it("produces squarish cells instead of slivers", () => {
    const rects = squarify(
      Array.from({ length: 9 }, (_, i) => ({ id: `T${i}`, value: 1 })),
      300,
      300,
    );
    for (const r of rects) {
      expect(Math.max(r.width / r.height, r.height / r.width)).toBeLessThan(2);
    }
  });
});

describe("heat colors", () => {
  const channels = (color: string) => color.match(/\d+/g)!.map(Number);

  it("is green for profit and red for loss", () => {
    const [gr, gg] = channels(heatColor(4));
    expect(gg).toBeGreaterThan(gr);
    const [rr, rg] = channels(heatColor(-4));
    expect(rr).toBeGreaterThan(rg);
  });

  it("deepens with size and saturates at the cap", () => {
    expect(channels(heatColor(1))[1]).toBeLessThan(channels(heatColor(5))[1]);
    expect(heatColor(50)).toBe(heatColor(6));
  });

  it("classifies P&L", () => {
    expect(pnlState(1)).toBe("profit");
    expect(pnlState(-1)).toBe("loss");
    expect(pnlState(0)).toBe("flat");
  });
});
