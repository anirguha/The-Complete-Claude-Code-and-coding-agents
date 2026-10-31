import { useEffect, useLayoutEffect, useRef, type RefObject } from "react";

/** How long the highlight stays on before the CSS fade (about 500ms) begins. */
export const FLASH_HOLD_MS = 90;

export function flashDirection(
  previous: number | undefined,
  next: number | undefined,
): "up" | "down" | null {
  if (previous == null || next == null || previous === next) return null;
  return next > previous ? "up" : "down";
}

/**
 * Flash an element when `price` changes. Classes are toggled directly on the DOM
 * node, so a flash costs no extra React render and a new tick simply restarts it.
 */
export function usePriceFlash(ref: RefObject<HTMLElement | null>, price: number | undefined): void {
  const previous = useRef(price);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useLayoutEffect(() => {
    const direction = flashDirection(previous.current, price);
    previous.current = price;
    const element = ref.current;
    if (!direction || !element) return;

    element.classList.remove("flash-up", "flash-down");
    element.classList.add(`flash-${direction}`);
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      element.classList.remove("flash-up", "flash-down");
      timer.current = null;
    }, FLASH_HOLD_MS);
  }, [price, ref]);

  useEffect(
    () => () => {
      if (timer.current !== null) clearTimeout(timer.current);
    },
    [],
  );
}
