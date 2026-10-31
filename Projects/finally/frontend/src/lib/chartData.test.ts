import { describe, expect, it } from "vitest";
import { priceHistoryToPoints, snapshotsToPoints } from "./chartData";
import { sparklinePoints } from "./sparkline";

describe("priceHistoryToPoints", () => {
  it("merges sub-second ticks, keeping the last value in each second", () => {
    expect(
      priceHistoryToPoints([
        { time: 100.2, price: 1 },
        { time: 100.7, price: 2 },
        { time: 101.2, price: 3 },
      ]),
    ).toEqual([
      { time: 100, value: 2 },
      { time: 101, value: 3 },
    ]);
  });
});

describe("snapshotsToPoints", () => {
  it("sorts, parses ISO times and drops bad ones", () => {
    const points = snapshotsToPoints([
      { total_value: 2, recorded_at: "2026-01-01T00:00:10+00:00" },
      { total_value: 1, recorded_at: "2026-01-01T00:00:00Z" },
      { total_value: 9, recorded_at: "garbage" },
    ]);
    expect(points.map((p) => p.value)).toEqual([1, 2]);
    expect(points[1].time - points[0].time).toBe(10);
  });
});

describe("sparklinePoints", () => {
  it("needs two values to draw", () => {
    expect(sparklinePoints([], 60, 20)).toBe("");
    expect(sparklinePoints([1], 60, 20)).toBe("");
  });

  it("spans the width, with the high at the top and the low at the bottom", () => {
    expect(sparklinePoints([0, 10], 60, 20, 2)).toBe("0.0,18.0 60.0,2.0");
  });

  it("draws a flat series through the middle", () => {
    expect(sparklinePoints([5, 5], 60, 20)).toBe("0.0,10.0 60.0,10.0");
  });
});
