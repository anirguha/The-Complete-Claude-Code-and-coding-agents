const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const quantity = new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 });

export const EMPTY = "—";

export function formatMoney(value: number | null | undefined): string {
  return value == null || !Number.isFinite(value) ? EMPTY : money.format(value);
}

/** Dollar amount with an explicit sign, for P&L: +$12.50, -$3.00. */
export function formatSignedMoney(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return EMPTY;
  // Decide the sign on the rounded figure, so -0.001 reads $0.00, not -$0.00.
  const cents = Math.round(value * 100);
  const sign = cents > 0 ? "+" : cents < 0 ? "-" : "";
  return sign + money.format(Math.abs(value));
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return EMPTY;
  const hundredths = Math.round(value * 100);
  const sign = hundredths > 0 ? "+" : "";
  return `${sign}${(hundredths === 0 ? 0 : value).toFixed(2)}%`;
}

export function formatQuantity(value: number): string {
  return quantity.format(value);
}

/** Tailwind text color for a signed figure. */
export function signClass(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value) || value === 0) return "text-dim";
  return value > 0 ? "text-up" : "text-down";
}
