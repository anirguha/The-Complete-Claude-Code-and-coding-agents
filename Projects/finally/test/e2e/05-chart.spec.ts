import { buyViaApi, chartInk, closeAllPositions, ensureNotWatched, ensureWatched, expect, money, openApp, test } from "./fixtures";

test("selecting a ticker updates the main chart, and the ticket", async ({ page, request }) => {
  await ensureWatched(request, "TSLA");
  await ensureWatched(request, "META");
  await openApp(page);
  const chart = page.getByTestId("main-chart");

  await page.getByTestId("watchlist-row-TSLA").click();
  await expect(page.getByTestId("main-chart-ticker")).toHaveText("TSLA");
  await expect(page.getByTestId("watchlist-row-TSLA")).toHaveAttribute("aria-current", "true");
  await expect(page.getByTestId("trade-ticker")).toHaveValue("TSLA");

  // Points accumulate and the line is really drawn on the canvas.
  await expect.poll(async () => Number(await chart.getAttribute("data-points")), { timeout: 15_000 }).toBeGreaterThan(3);
  await expect.poll(() => chartInk(page, "main-chart"), { timeout: 10_000 }).toBeGreaterThan(200);
  const tslaPicture = await chart.locator("canvas").first().evaluate((c: HTMLCanvasElement) => c.toDataURL());

  await page.getByTestId("watchlist-row-META").click();
  await expect(page.getByTestId("main-chart-ticker")).toHaveText("META");
  await expect(page.getByTestId("watchlist-row-META")).toHaveAttribute("aria-current", "true");
  await expect(page.getByTestId("watchlist-row-TSLA")).not.toHaveAttribute("aria-current", "true");
  // META already has its ticks since page load, so nothing is lost by selecting it late.
  expect(Number(await chart.getAttribute("data-points"))).toBeGreaterThan(3);
  await expect
    .poll(() => chart.locator("canvas").first().evaluate((c: HTMLCanvasElement) => c.toDataURL()))
    .not.toBe(tslaPicture);

  // The title price follows the selected ticker.
  const gap = async () =>
    Math.abs(
      money(await page.getByTestId("price-META").textContent()) -
        money(await page.getByTestId("main-chart-price").textContent()),
    );
  await expect.poll(gap).toBeLessThan(5);
});

test("a held ticker off the watchlist can still be charted from the positions table", async ({ page, request }) => {
  await closeAllPositions(request);
  await buyViaApi(request, "NFLX", 1);
  await ensureNotWatched(request, "NFLX");
  await openApp(page);
  await page.getByTestId("position-row-NFLX").click();
  await expect(page.getByTestId("main-chart-ticker")).toHaveText("NFLX");
  await expect
    .poll(async () => Number(await page.getByTestId("main-chart").getAttribute("data-points")), { timeout: 15_000 })
    .toBeGreaterThan(1);
  await closeAllPositions(request);
  await ensureWatched(request, "NFLX");
});
