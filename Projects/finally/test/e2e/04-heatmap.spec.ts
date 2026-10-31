import { buyViaApi, closeAllPositions, expect, getPortfolio, openApp, test } from "./fixtures";
import type { Locator } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await closeAllPositions(request);
});

/**
 * Reads a cell's state and color together, and says which way the color has moved
 * from the neutral base (34, 43, 56). That base is itself slightly greener than it
 * is red, so a tiny loss cannot be judged by comparing red and green directly.
 */
async function readCell(cell: Locator) {
  return cell.evaluate((el) => {
    const [r, g] = getComputedStyle(el).backgroundColor.match(/\d+/g)!.map(Number);
    const shift = g - 43 - (r - 34);
    return {
      state: el.getAttribute("data-pnl"),
      percent: Number((el.getAttribute("title") ?? "").match(/(-?[\d.]+)%/)![1]),
      hue: shift > 0 ? "green" : shift < 0 ? "red" : "neutral",
    };
  });
}

test("cells sized by weight, and colored by their real, live P&L", async ({ page, request }) => {
  await buyViaApi(request, "NVDA", 2); // about $1,600
  await buyViaApi(request, "JPM", 1); // about $195
  await openApp(page);

  const big = await page.getByTestId("heatmap-cell-NVDA").boundingBox();
  const small = await page.getByTestId("heatmap-cell-JPM").boundingBox();
  const area = (b: { width: number; height: number }) => b.width * b.height;
  expect(area(big!)).toBeGreaterThan(area(small!) * 3);

  // Prices are live and the sign is unknown, so check each state as it comes.
  const seen = new Set<string>();
  const deadline = Date.now() + 8_000;
  while (Date.now() < deadline) {
    for (const ticker of ["NVDA", "JPM"]) {
      const cell = await readCell(page.getByTestId(`heatmap-cell-${ticker}`));
      seen.add(cell.state!);
      // Below about 0.01% the color cannot move a whole 8-bit step from neutral.
      if (cell.state === "profit") expect(["green", "neutral"], JSON.stringify(cell)).toContain(cell.hue);
      if (cell.state === "loss") expect(["red", "neutral"], JSON.stringify(cell)).toContain(cell.hue);
      if (cell.percent >= 0.05) expect(cell.hue, JSON.stringify(cell)).toBe("green");
      if (cell.percent <= -0.05) expect(cell.hue, JSON.stringify(cell)).toBe("red");
      if (cell.percent > 0.005) expect(cell.state).toBe("profit");
      if (cell.percent < -0.005) expect(cell.state).toBe("loss");
    }
    await page.waitForTimeout(400);
  }
  expect(seen.size).toBeGreaterThan(0);
});

test("a profit is green and a loss is red", async ({ page, request }) => {
  await buyViaApi(request, "AAPL", 2);
  await buyViaApi(request, "MSFT", 1);
  // Live P&L hovers near zero just after buying. To see both outcomes for certain, the
  // browser gets the real response with only the cost basis moved far from the price.
  await page.route("**/api/portfolio", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    for (const position of body.positions) {
      position.avg_cost = position.current_price * (position.ticker === "AAPL" ? 0.5 : 2);
    }
    await route.fulfill({ response, json: body });
  });
  await openApp(page);

  const profit = await readCell(page.getByTestId("heatmap-cell-AAPL"));
  expect(profit.state).toBe("profit");
  expect(profit.hue).toBe("green");
  expect(profit.percent).toBeGreaterThan(50);

  const loss = await readCell(page.getByTestId("heatmap-cell-MSFT"));
  expect(loss.state).toBe("loss");
  expect(loss.hue).toBe("red");
  expect(loss.percent).toBeLessThan(-30);

  // The positions table tells the same story in the same colors.
  const aaplRow = page.getByTestId("position-row-AAPL").locator("td").nth(4);
  const msftRow = page.getByTestId("position-row-MSFT").locator("td").nth(4);
  await expect(aaplRow).toHaveClass(/text-up/);
  await expect(msftRow).toHaveClass(/text-down/);
  await expect(aaplRow).toHaveText(/^\+\$/);
  await expect(msftRow).toHaveText(/^-\$/);
  expect((await getPortfolio(request)).positions.length).toBe(2);
});

test("clicking a heatmap cell selects that ticker", async ({ page, request }) => {
  await buyViaApi(request, "GOOGL", 1);
  await openApp(page);
  await page.getByTestId("heatmap-cell-GOOGL").click();
  await expect(page.getByTestId("main-chart-ticker")).toHaveText("GOOGL");
  await expect(page.getByTestId("trade-ticker")).toHaveValue("GOOGL");
});
