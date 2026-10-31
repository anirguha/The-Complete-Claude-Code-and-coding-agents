import { buyViaApi, closeAllPositions, ensureWatched, expect, openApp, test } from "./fixtures";
import path from "node:path";

const dir = process.env.E2E_SCREENSHOT_DIR ?? "test-results/screenshots";
const shot = (name: string) => path.join(dir, `${name}.png`);

test("capture the live app for a human or agent to look at", async ({ page, request }) => {
  await closeAllPositions(request);
  await page.setViewportSize({ width: 1440, height: 900 });
  await openApp(page);
  await page.waitForTimeout(3_000);
  await page.screenshot({ path: shot("1-no-positions") });

  for (const [ticker, quantity] of [["NVDA", 3], ["AAPL", 8], ["JPM", 5], ["TSLA", 4], ["V", 2]] as const) {
    await ensureWatched(request, ticker);
    await buyViaApi(request, ticker, quantity);
  }
  await page.getByTestId("chat-input").fill("buy 1 MSFT");
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("position-row-MSFT")).toBeVisible();
  await page.getByTestId("chat-input").fill("buy 100000 NVDA");
  await page.getByTestId("chat-send").click();
  await expect(page.locator('[data-testid="chat-action"][data-status="failed"]').last()).toBeVisible();
  await page.getByTestId("watchlist-row-NVDA").click();
  await page.waitForTimeout(12_000);
  await page.screenshot({ path: shot("2-with-positions") });

  await page.setViewportSize({ width: 1024, height: 768 });
  await page.reload();
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");
  await page.waitForTimeout(3_000);
  await page.screenshot({ path: shot("3-tablet"), fullPage: true });
  await page.getByTestId("chat-toggle").click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: shot("4-tablet-chat-open") });

  await closeAllPositions(request);
});
