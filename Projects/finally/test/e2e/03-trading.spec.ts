import { buyViaApi, chartInk, closeAllPositions, ensureNotWatched, ensureWatched, expect, getPortfolio, getWatchlist, headerCash, headerTotal, money, openApp, test } from "./fixtures";
import type { Page } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await closeAllPositions(request);
});

async function trade(page: Page, ticker: string, quantity: string, side: "buy" | "sell") {
  await page.getByTestId("trade-ticker").fill(ticker);
  await page.getByTestId("trade-quantity").fill(quantity);
  await page.getByTestId(`trade-${side}`).click();
}

/** The fill price from the ticket's confirmation, like "Bought 2 JPM at $195.10". */
async function filledPrice(page: Page): Promise<number> {
  const text = await page.getByTestId("trade-status").textContent();
  return money(text?.split(" at ")[1] ?? "");
}

test("buy: cash falls, position, heatmap and P&L data appear", async ({ page, request }) => {
  await openApp(page);
  const cashBefore = await headerCash(page);
  const historyBefore = (await (await request.get("/api/portfolio/history")).json()).snapshots.length;

  await trade(page, "JPM", "2", "buy");
  await expect(page.getByTestId("trade-status")).toHaveText(/^Bought 2 JPM at \$/);
  const price = await filledPrice(page);

  await expect.poll(() => headerCash(page)).toBeCloseTo(cashBefore - 2 * price, 1);

  const row = page.getByTestId("position-row-JPM");
  await expect(row).toBeVisible();
  await expect(row.locator("td").nth(1)).toHaveText("2");
  await expect(row.locator("td").nth(2)).toHaveText(new RegExp(`^\\$${price.toFixed(2).replace(".", "\\.")}$`));

  const cell = page.getByTestId("heatmap-cell-JPM");
  await expect(cell).toBeVisible();
  const box = await cell.boundingBox();
  expect(box!.width).toBeGreaterThan(50);
  expect(box!.height).toBeGreaterThan(50);

  await expect(page.getByTestId("pnl-chart")).not.toHaveAttribute("data-points", "0");
  await expect.poll(() => chartInk(page, "pnl-chart")).toBeGreaterThan(50);
  const historyAfter = (await (await request.get("/api/portfolio/history")).json()).snapshots.length;
  expect(historyAfter === 500 || historyAfter > historyBefore).toBe(true);
});

test("the header total is cash plus live positions and updates by itself", async ({ page, request }) => {
  await buyViaApi(request, "TSLA", 10);
  await openApp(page);
  const cash = await headerCash(page);
  const row = page.getByTestId("position-row-TSLA");
  await expect(row).toBeVisible();

  // Read in one go in the page, since these change twice a second.
  const consistent = await page.evaluate(() => {
    const total = document.querySelector('[data-testid="header-total-value"]')!.textContent!;
    const price = document.querySelector('[data-testid="price-TSLA"]')!.textContent!;
    return { total, price };
  });
  const expected = cash + 10 * money(consistent.price);
  expect(Math.abs(money(consistent.total) - expected)).toBeLessThan(expected * 0.005);

  const first = await headerTotal(page);
  await expect.poll(() => headerTotal(page), { timeout: 15_000 }).not.toBe(first);
  expect(await headerCash(page)).toBe(cash);
});

test("sell part: cash rises, the position shrinks", async ({ page, request }) => {
  await buyViaApi(request, "V", 3);
  await openApp(page);
  const cashBefore = await headerCash(page);

  await trade(page, "V", "1", "sell");
  await expect(page.getByTestId("trade-status")).toHaveText(/^Sold 1 V at \$/);
  const price = await filledPrice(page);

  await expect.poll(() => headerCash(page)).toBeCloseTo(cashBefore + price, 1);
  await expect(page.getByTestId("position-row-V").locator("td").nth(1)).toHaveText("2");
  await expect(page.getByTestId("heatmap-cell-V")).toBeVisible();
});

test("sell all: the position and its heatmap cell disappear", async ({ page, request }) => {
  await buyViaApi(request, "V", 2);
  await openApp(page);
  const cashBefore = await headerCash(page);

  await trade(page, "V", "2", "sell");
  await expect(page.getByTestId("trade-status")).toHaveText(/^Sold 2 V at \$/);

  await expect(page.getByTestId("position-row-V")).toHaveCount(0);
  await expect(page.getByTestId("heatmap-cell-V")).toHaveCount(0);
  await expect.poll(() => headerCash(page)).toBeGreaterThan(cashBefore);
});

test("rejected trades show the reason and change nothing", async ({ page, request, errors }) => {
  errors.allowConsoleError(/status of 400/);
  await openApp(page);
  const before = await getPortfolio(request);

  await trade(page, "NFLX", "5", "sell");
  await expect(page.getByTestId("trade-error")).toContainText("Insufficient shares");
  await trade(page, "NVDA", "100000", "buy");
  await expect(page.getByTestId("trade-error")).toContainText("Insufficient cash");
  await trade(page, "AAPL", "0", "buy");
  await expect(page.getByTestId("trade-error")).toContainText("greater than 0");

  const after = await getPortfolio(request);
  expect(after.cash_balance).toBe(before.cash_balance);
  expect(after.positions).toEqual([]);
  expect(await headerCash(page)).toBe(before.cash_balance);
});

test("buying an unwatched ticker adds it to the watchlist", async ({ page, request }) => {
  await ensureNotWatched(request, "DIS");
  await openApp(page);
  await trade(page, "dis", "1", "buy");
  await expect(page.getByTestId("trade-status")).toHaveText(/^Bought 1 DIS at \$/);
  await expect(page.getByTestId("watchlist-row-DIS")).toBeVisible();
  await expect(page.getByTestId("position-row-DIS")).toBeVisible();
  expect(await getWatchlist(request)).toContain("DIS");
  await closeAllPositions(request);
  await ensureNotWatched(request, "DIS");
});

test("fractional shares round trip", async ({ page, request }) => {
  await ensureWatched(request, "AMZN");
  await openApp(page);
  await trade(page, "AMZN", "0.5", "buy");
  await expect(page.getByTestId("trade-status")).toHaveText(/^Bought 0\.5 AMZN at \$/);
  await expect(page.getByTestId("position-row-AMZN").locator("td").nth(1)).toHaveText("0.5");
  await trade(page, "AMZN", "0.5", "sell");
  await expect(page.getByTestId("position-row-AMZN")).toHaveCount(0);
});
