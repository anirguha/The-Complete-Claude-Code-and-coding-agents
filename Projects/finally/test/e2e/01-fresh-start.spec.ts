import { DEFAULT_TICKERS, expect, getPortfolio, getWatchlist, headerCash, headerTotal, openApp, test } from "./fixtures";

// Runs first. A database that has been used cannot show first-launch state, so this
// test reports itself as skipped there, unless E2E_REQUIRE_FRESH=1 makes that a failure.
test("first launch shows the default watchlist and $10,000", async ({ page, request }) => {
  const portfolio = await getPortfolio(request);
  const watchlist = await getWatchlist(request);
  const fresh =
    portfolio.cash_balance === 10000 &&
    portfolio.positions.length === 0 &&
    watchlist.join() === DEFAULT_TICKERS.join();
  if (process.env.E2E_REQUIRE_FRESH === "1") {
    expect(fresh, "E2E_REQUIRE_FRESH=1 but the database has been used").toBe(true);
  }
  test.skip(!fresh, "The database is not fresh, so first-launch state cannot be checked.");

  await openApp(page);
  for (const ticker of DEFAULT_TICKERS) {
    await expect(page.getByTestId(`watchlist-row-${ticker}`)).toBeVisible();
    await expect(page.getByTestId(`price-${ticker}`)).toHaveText(/\$[\d,]+\.\d\d/);
  }
  await expect(page.locator('[data-testid^="watchlist-row-"]')).toHaveCount(10);
  await expect(page.getByTestId("header-cash")).toHaveText("$10,000.00");
  await expect(page.getByTestId("header-total-value")).toHaveText("$10,000.00");
  await expect(page.getByTestId("chat-input")).toBeVisible();
  await expect(page.locator('[data-testid^="position-row-"]')).toHaveCount(0);
  await expect(page.locator('[data-testid^="heatmap-cell-"]')).toHaveCount(0);

  // One snapshot, no change yet: the P&L chart must not draw that as a red line.
  await expect(page.getByTestId("pnl-chart")).toHaveAttribute("data-points", "1");
  await page.waitForTimeout(300); // chart repaints on the next animation frame
  const redPixels = await page.getByTestId("pnl-chart").evaluate((root) => {
    let red = 0;
    for (const canvas of Array.from(root.querySelectorAll("canvas"))) {
      if (canvas.width === 0 || canvas.height === 0) continue;
      const { data } = canvas.getContext("2d")!.getImageData(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < data.length; i += 4) {
        if (data[i + 3] > 200 && data[i] > 200 && data[i + 1] < 130 && data[i + 2] < 130) red += 1;
      }
    }
    return red;
  });
  expect(redPixels).toBe(0);
});

test("prices stream, change, flash and draw sparklines; the status dot is connected", async ({ page, request }) => {
  await openApp(page);
  const tickers = await getWatchlist(request);
  expect(tickers.length).toBeGreaterThan(0);
  const read = async () =>
    Object.fromEntries(
      await Promise.all(tickers.map(async (t) => [t, await page.getByTestId(`price-${t}`).textContent()])),
    );

  const first = await read();
  await expect
    .poll(async () => {
      const now = await read();
      return tickers.filter((t) => now[t] !== first[t]).length;
    }, { timeout: 15_000, message: "several tickers should have moved" })
    .toBeGreaterThanOrEqual(Math.min(3, tickers.length));

  // Flash classes are short-lived, so watch for them from inside the page.
  const flashed = await page.evaluate(
    () =>
      new Promise<string>((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error("No price flash seen in 10s")), 10_000);
        const observer = new MutationObserver((records) => {
          for (const record of records) {
            const el = record.target as HTMLElement;
            const match = el.className.match?.(/flash-(up|down)/);
            if (match) {
              clearTimeout(timer);
              observer.disconnect();
              resolve(match[1]);
              return;
            }
          }
        });
        observer.observe(document.body, { attributes: true, attributeFilter: ["class"], subtree: true });
      }),
  );
  expect(["up", "down"]).toContain(flashed);

  await expect(page.getByTestId(`sparkline-${tickers[0]}`).locator("polyline")).toBeAttached();
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");
  await expect(page.getByTestId("load-error")).toHaveCount(0);

  // With or without positions, the header must be internally consistent.
  const portfolio = await getPortfolio(request);
  expect(await headerCash(page)).toBeCloseTo(portfolio.cash_balance, 2);
  expect(await headerTotal(page)).toBeGreaterThanOrEqual(portfolio.cash_balance);
});
