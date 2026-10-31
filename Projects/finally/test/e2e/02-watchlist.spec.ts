import { buyViaApi, closeAllPositions, ensureNotWatched, ensureWatched, expect, getWatchlist, openApp, test } from "./fixtures";

test.beforeEach(async ({ request }) => {
  await closeAllPositions(request);
});

test("add and remove a ticker", async ({ page, request }) => {
  await ensureNotWatched(request, "PYPL");
  await openApp(page);
  await expect(page.getByTestId("watchlist-row-PYPL")).toHaveCount(0);

  await page.getByTestId("watchlist-add-input").fill("pypl");
  await page.getByTestId("watchlist-add-button").click();

  await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible();
  await expect(page.getByTestId("price-PYPL")).toHaveText(/\$[\d,]+\.\d\d/);
  await expect(page.getByTestId("watchlist-add-input")).toHaveValue("");
  expect(await getWatchlist(request)).toContain("PYPL");
  // Its feed really started: the price keeps moving.
  const firstPrice = await page.getByTestId("price-PYPL").textContent();
  await expect.poll(() => page.getByTestId("price-PYPL").textContent(), { timeout: 20_000 }).not.toBe(firstPrice);

  await page.getByTestId("watchlist-remove-PYPL").click();
  await expect(page.getByTestId("watchlist-row-PYPL")).toHaveCount(0);
  expect(await getWatchlist(request)).not.toContain("PYPL");
});

test("an invalid symbol shows an error and adds nothing", async ({ page, request, errors }) => {
  errors.allowConsoleError(/status of 400/);
  await openApp(page);
  const before = await getWatchlist(request);
  await page.getByTestId("watchlist-add-input").fill("A1-!");
  await page.getByTestId("watchlist-add-button").click();
  await expect(page.getByTestId("watchlist-error")).toBeVisible();
  expect(await getWatchlist(request)).toEqual(before);
});

test("removing the selected ticker moves the chart to another", async ({ page, request }) => {
  await ensureWatched(request, "MSFT");
  await ensureWatched(request, "JPM");
  await openApp(page);
  await page.getByTestId("watchlist-row-MSFT").click();
  await expect(page.getByTestId("main-chart-ticker")).toHaveText("MSFT");
  await page.getByTestId("watchlist-remove-MSFT").click();
  await expect(page.getByTestId("watchlist-row-MSFT")).toHaveCount(0);
  await expect(page.getByTestId("main-chart-ticker")).not.toHaveText("MSFT");
  await ensureWatched(request, "MSFT");
});

test("removing a held ticker keeps the position priced live", async ({ page, request }) => {
  await ensureWatched(request, "V");
  await buyViaApi(request, "V", 1);
  await openApp(page);
  await page.getByTestId("watchlist-remove-V").click();
  await expect(page.getByTestId("watchlist-row-V")).toHaveCount(0);

  const row = page.getByTestId("position-row-V");
  await expect(row).toBeVisible();
  const price = row.locator("td").nth(3);
  const first = await price.textContent();
  await expect.poll(() => price.textContent(), { timeout: 30_000 }).not.toBe(first);

  await closeAllPositions(request);
  await ensureWatched(request, "V");
});
