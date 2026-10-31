"use client";

import { useRef } from "react";
import { usePriceFlash } from "@/hooks/usePriceFlash";
import { formatMoney } from "@/lib/format";
import { useTick } from "@/lib/priceStore";

export function FlashingPrice({
  price,
  testId,
  className = "",
}: {
  price: number | undefined;
  testId?: string;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  usePriceFlash(ref, price);
  return (
    <span ref={ref} data-testid={testId} className={`price-cell num inline-block ${className}`}>
      {formatMoney(price)}
    </span>
  );
}

/** Subscribes to one ticker, so only this cell re-renders on its tick. */
export function LivePrice({ ticker, testId, className }: { ticker: string; testId?: string; className?: string }) {
  const tick = useTick(ticker);
  return <FlashingPrice price={tick?.price} testId={testId} className={className} />;
}
