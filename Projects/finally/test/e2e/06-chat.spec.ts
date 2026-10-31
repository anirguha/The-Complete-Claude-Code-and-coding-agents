import { closeAllPositions, ensureNotWatched, expect, getPortfolio, headerCash, openApp, test } from "./fixtures";
import type { Page } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await closeAllPositions(request);
});

async function send(page: Page, text: string) {
  const before = await page.locator('[data-testid="chat-message"][data-role="assistant"]').count();
  await page.getByTestId("chat-input").fill(text);
  await page.getByTestId("chat-send").click();
  const reply = page.locator('[data-testid="chat-message"][data-role="assistant"]').nth(before);
  await expect(reply).toBeVisible();
  return reply;
}

test("a plain message gets the mock reply and no actions", async ({ page }) => {
  await openApp(page);
  const reply = await send(page, "How concentrated am I?");
  await expect(reply).toContainText("Mock response: I am FinAlly, your AI trading assistant.");
  await expect(reply.getByTestId("chat-action")).toHaveCount(0);
  await expect(page.locator('[data-testid="chat-message"][data-role="user"]').last()).toContainText(
    "How concentrated am I?",
  );
  await expect(page.getByTestId("chat-input")).toHaveValue("");
});

test("Enter sends the message", async ({ page }) => {
  await openApp(page);
  const before = await page.locator('[data-testid="chat-message"][data-role="assistant"]').count();
  await page.getByTestId("chat-input").fill("sent with enter");
  await page.getByTestId("chat-input").press("Enter");
  await expect(page.locator('[data-testid="chat-message"][data-role="assistant"]').nth(before)).toBeVisible();
});

test("an executed trade shows inline and updates the portfolio without a reload", async ({ page }) => {
  await openApp(page);
  const cash = await headerCash(page);
  const reply = await send(page, "buy 2 JPM");
  await expect(reply).toContainText("Mock: buying 2 shares of JPM.");
  const action = reply.getByTestId("chat-action");
  await expect(action).toHaveAttribute("data-status", "executed");
  await expect(action).toContainText(/Bought 2 JPM at \$[\d,]+\.\d\d/);
  await expect(page.getByTestId("position-row-JPM")).toBeVisible();
  await expect(page.getByTestId("heatmap-cell-JPM")).toBeVisible();
  await expect.poll(() => headerCash(page)).toBeLessThan(cash);

  const sold = await send(page, "sell 2 JPM");
  await expect(sold.getByTestId("chat-action")).toHaveAttribute("data-status", "executed");
  await expect(sold.getByTestId("chat-action")).toContainText(/Sold 2 JPM at \$/);
  await expect(page.getByTestId("position-row-JPM")).toHaveCount(0);
});

test("a failed trade shows its reason inline and changes nothing", async ({ page, request }) => {
  await openApp(page);
  const before = await getPortfolio(request);
  const reply = await send(page, "buy 100000 NVDA");
  const action = reply.getByTestId("chat-action");
  await expect(action).toHaveAttribute("data-status", "failed");
  await expect(action).toContainText(/Buy 100,000 NVDA failed: Insufficient cash/);
  const after = await getPortfolio(request);
  expect(after.cash_balance).toBe(before.cash_balance);
  expect(after.positions).toEqual([]);
});

test("watchlist changes show inline and reach the watchlist", async ({ page, request }) => {
  await ensureNotWatched(request, "SQ");
  await openApp(page);

  const added = await send(page, "add SQ");
  await expect(added.getByTestId("chat-action")).toHaveAttribute("data-status", "applied");
  await expect(added.getByTestId("chat-action")).toContainText("Added SQ to the watchlist");
  await expect(page.getByTestId("watchlist-row-SQ")).toBeVisible();
  await expect(page.getByTestId("price-SQ")).toHaveText(/\$[\d,]+\.\d\d/);

  const removed = await send(page, "remove SQ");
  await expect(removed.getByTestId("chat-action")).toContainText("Removed SQ from the watchlist");
  await expect(page.getByTestId("watchlist-row-SQ")).toHaveCount(0);

  const bad = await send(page, "add NOT-A-TICKER");
  await expect(bad.getByTestId("chat-action")).toHaveAttribute("data-status", "failed");
  await expect(bad.getByTestId("chat-action")).toContainText("failed");
});

test("the loading indicator shows while waiting for a reply", async ({ page }) => {
  await page.route("**/api/chat", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 700));
    await route.continue();
  });
  await openApp(page);
  await page.getByTestId("chat-input").fill("anyone there?");
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("chat-loading")).toBeVisible();
  await expect(page.getByTestId("chat-send")).toBeDisabled();
  await expect(page.getByTestId("chat-loading")).toHaveCount(0);
});

test("below 1200px chat is a closed drawer that opens from the header", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await openApp(page);
  await expect(page.getByTestId("chat-input")).toBeHidden();
  await page.getByTestId("chat-toggle").click();
  await expect(page.getByTestId("chat-input")).toBeVisible();
  const reply = await send(page, "hello from the drawer");
  await expect(reply).toContainText("Mock response");
});
