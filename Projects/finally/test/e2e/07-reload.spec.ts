import { buyViaApi, closeAllPositions, expect, getPortfolio, headerCash, openApp, test } from "./fixtures";

test("a reload keeps the portfolio and the chat, with its actions", async ({ page, request }) => {
  await closeAllPositions(request);
  await buyViaApi(request, "GOOGL", 2);
  await openApp(page);

  const marker = `remember this ${Date.now()}`;
  await page.getByTestId("chat-input").fill(marker);
  await page.getByTestId("chat-send").click();
  await expect(page.locator('[data-testid="chat-message"]', { hasText: marker })).toBeVisible();

  await page.getByTestId("chat-input").fill("buy 1 META");
  await page.getByTestId("chat-send").click();
  const action = page.locator('[data-testid="chat-action"]', { hasText: "Bought 1 META" }).last();
  await expect(action).toBeVisible();
  const actionText = await action.textContent();
  await expect(page.getByTestId("position-row-META")).toBeVisible();
  const cash = await headerCash(page);

  await page.reload();
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");

  await expect(page.locator('[data-testid="chat-message"][data-role="user"]', { hasText: marker })).toHaveCount(1);
  await expect(page.locator('[data-testid="chat-message"][data-role="user"]', { hasText: "buy 1 META" }).last()).toBeVisible();
  const restored = page.locator('[data-testid="chat-action"]', { hasText: actionText! });
  await expect(restored.last()).toHaveAttribute("data-status", "executed");

  await expect(page.getByTestId("position-row-GOOGL")).toBeVisible();
  await expect(page.getByTestId("position-row-META")).toBeVisible();
  await expect(page.getByTestId("heatmap-cell-GOOGL")).toBeVisible();
  await expect.poll(() => headerCash(page)).toBe(cash);
  expect((await getPortfolio(request)).cash_balance).toBe(cash);
  await expect(page.getByTestId("pnl-chart")).not.toHaveAttribute("data-points", "0");

  await closeAllPositions(request);
});
