import { expect, test as base, type APIRequestContext, type Page } from "@playwright/test";

export interface Portfolio {
  cash_balance: number;
  total_value: number;
  positions: { ticker: string; quantity: number; avg_cost: number; current_price: number }[];
}

export const DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

/** "$10,234.50" or "+$1.25" or "-$3.00" -> number. */
export function money(text: string | null): number {
  const value = Number((text ?? "").replace(/[$,+\s]/g, ""));
  if (!Number.isFinite(value) || !/\d/.test(text ?? "")) throw new Error(`Not a money value: ${text}`);
  return value;
}

export const getPortfolio = async (request: APIRequestContext): Promise<Portfolio> =>
  (await request.get("/api/portfolio")).json();

export const getWatchlist = async (request: APIRequestContext): Promise<string[]> =>
  ((await (await request.get("/api/watchlist")).json()).watchlist as { ticker: string }[]).map((w) => w.ticker);

/** Sell everything, so a spec never depends on what an earlier one left behind. */
export async function closeAllPositions(request: APIRequestContext): Promise<void> {
  for (const { ticker, quantity } of (await getPortfolio(request)).positions) {
    const response = await request.post("/api/portfolio/trade", { data: { ticker, quantity, side: "sell" } });
    expect(response.ok(), `closing ${ticker}: ${await response.text()}`).toBeTruthy();
  }
}

export async function ensureWatched(request: APIRequestContext, ticker: string): Promise<void> {
  expect((await request.post("/api/watchlist", { data: { ticker } })).ok()).toBeTruthy();
}

export async function ensureNotWatched(request: APIRequestContext, ticker: string): Promise<void> {
  const response = await request.delete(`/api/watchlist/${ticker}`);
  expect([200, 404]).toContain(response.status());
}

export async function buyViaApi(request: APIRequestContext, ticker: string, quantity: number): Promise<void> {
  const response = await request.post("/api/portfolio/trade", { data: { ticker, quantity, side: "buy" } });
  expect(response.ok(), await response.text()).toBeTruthy();
}

/** Opens the app and waits until REST data and the live feed have both arrived. */
export async function openApp(page: Page): Promise<void> {
  await page.goto("/");
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");
  await expect(page.getByTestId("header-cash")).toHaveText(/\$[\d,]+\.\d\d/);
}

export const headerCash = async (page: Page): Promise<number> =>
  money(await page.getByTestId("header-cash").textContent());

export const headerTotal = async (page: Page): Promise<number> =>
  money(await page.getByTestId("header-total-value").textContent());

/**
 * Number of canvas pixels that differ from the most common color, across a chart's
 * canvases. A data-points attribute only proves React had data; this proves it drew.
 */
export async function chartInk(page: Page, testId: string): Promise<number> {
  return page.getByTestId(testId).evaluate((root) => {
    let ink = 0;
    for (const canvas of Array.from(root.querySelectorAll("canvas"))) {
      if (canvas.width === 0 || canvas.height === 0) continue;
      const { data } = canvas.getContext("2d")!.getImageData(0, 0, canvas.width, canvas.height);
      const counts = new Map<number, number>();
      for (let i = 0; i < data.length; i += 4) {
        if (data[i + 3] === 0) continue;
        const key = (data[i] << 16) | (data[i + 1] << 8) | data[i + 2];
        counts.set(key, (counts.get(key) ?? 0) + 1);
      }
      const total = Array.from(counts.values()).reduce((a, b) => a + b, 0);
      ink += total - Math.max(0, ...counts.values());
    }
    return ink;
  });
}

interface ErrorGuard {
  /** Declare a console error this test provokes on purpose, such as a 400 from a rejected trade. */
  allowConsoleError: (pattern: RegExp) => void;
  allowed: RegExp[];
}

/** Every test fails on uncaught page errors and on console errors it did not declare. */
export const test = base.extend<{ errors: ErrorGuard; guard: void }>({
  errors: async ({}, use) => {
    const allowed: RegExp[] = [];
    await use({ allowed, allowConsoleError: (pattern) => void allowed.push(pattern) });
  },
  guard: [
    async ({ page, errors }, use) => {
      const problems: { kind: string; text: string }[] = [];
      page.on("pageerror", (error) => problems.push({ kind: "page error", text: String(error) }));
      page.on("console", (message) => {
        if (message.type() === "error") problems.push({ kind: "console error", text: message.text() });
      });
      await use();
      const unexpected = problems.filter(
        (p) => p.kind === "page error" || !errors.allowed.some((pattern) => pattern.test(p.text)),
      );
      expect(unexpected, "uncaught page errors or unexpected console errors").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };
