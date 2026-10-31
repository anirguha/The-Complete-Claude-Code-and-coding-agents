import { describe, expect, it } from "vitest";
import { EMPTY, formatMoney, formatPercent, formatQuantity, formatSignedMoney, signClass } from "./format";

describe("format", () => {
  it("formats money the way the header contract requires", () => {
    expect(formatMoney(10000)).toBe("$10,000.00");
    expect(formatMoney(1234.5)).toBe("$1,234.50");
    expect(formatMoney(null)).toBe(EMPTY);
    expect(formatMoney(Number.NaN)).toBe(EMPTY);
  });

  it("signs P&L", () => {
    expect(formatSignedMoney(12.5)).toBe("+$12.50");
    expect(formatSignedMoney(-3)).toBe("-$3.00");
    expect(formatSignedMoney(0)).toBe("$0.00");
  });

  it("never shows a negative zero", () => {
    expect(formatPercent(-0.001)).toBe("0.00%");
    expect(formatSignedMoney(-0.001)).toBe("$0.00");
  });

  it("signs percentages", () => {
    expect(formatPercent(5)).toBe("+5.00%");
    expect(formatPercent(-5)).toBe("-5.00%");
  });

  it("keeps up to four decimals of quantity", () => {
    expect(formatQuantity(1.23456)).toBe("1.2346");
    expect(formatQuantity(10)).toBe("10");
  });

  it("colors by sign", () => {
    expect(signClass(1)).toBe("text-up");
    expect(signClass(-1)).toBe("text-down");
    expect(signClass(0)).toBe("text-dim");
    expect(signClass(null)).toBe("text-dim");
  });
});
