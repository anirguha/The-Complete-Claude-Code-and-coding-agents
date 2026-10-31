import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FLASH_HOLD_MS, flashDirection } from "@/hooks/usePriceFlash";
import { FlashingPrice } from "./PriceCell";

describe("flashDirection", () => {
  it("compares the previous price to the new one", () => {
    expect(flashDirection(100, 101)).toBe("up");
    expect(flashDirection(101, 100)).toBe("down");
    expect(flashDirection(100, 100)).toBeNull();
    expect(flashDirection(undefined, 100)).toBeNull();
  });
});

describe("FlashingPrice", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  const cell = () => screen.getByTestId("p");
  const show = (price: number | undefined) => <FlashingPrice price={price} testId="p" />;

  it("does not flash on the first price", () => {
    render(show(100));
    expect(cell()).not.toHaveClass("flash-up");
    expect(cell()).not.toHaveClass("flash-down");
    expect(cell()).toHaveTextContent("$100.00");
  });

  it("does not flash when a price first arrives after being empty", () => {
    const { rerender } = render(show(undefined));
    rerender(show(100));
    expect(cell()).not.toHaveClass("flash-up");
  });

  it("flashes green on an uptick, then clears so the CSS fade can run", () => {
    const { rerender } = render(show(100));
    rerender(show(101));
    expect(cell()).toHaveClass("flash-up");
    act(() => vi.advanceTimersByTime(FLASH_HOLD_MS));
    expect(cell()).not.toHaveClass("flash-up");
    expect(cell()).toHaveClass("price-cell");
  });

  it("flashes red on a downtick", () => {
    const { rerender } = render(show(100));
    rerender(show(99));
    expect(cell()).toHaveClass("flash-down");
    expect(cell()).not.toHaveClass("flash-up");
  });

  it("does not flash when a re-render carries the same price", () => {
    const { rerender } = render(show(100));
    rerender(show(100));
    expect(cell()).not.toHaveClass("flash-up");
    expect(cell()).not.toHaveClass("flash-down");
  });

  it("switches color when the direction flips mid-flash", () => {
    const { rerender } = render(show(100));
    rerender(show(101));
    rerender(show(100.5));
    expect(cell()).toHaveClass("flash-down");
    expect(cell()).not.toHaveClass("flash-up");
  });

  it("restarts the hold on each tick rather than clearing early", () => {
    const { rerender } = render(show(100));
    rerender(show(101));
    act(() => vi.advanceTimersByTime(FLASH_HOLD_MS - 1));
    rerender(show(102));
    act(() => vi.advanceTimersByTime(FLASH_HOLD_MS - 1));
    expect(cell()).toHaveClass("flash-up");
    act(() => vi.advanceTimersByTime(1));
    expect(cell()).not.toHaveClass("flash-up");
  });
});
