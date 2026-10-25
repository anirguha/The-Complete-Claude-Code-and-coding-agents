import { test, expect, type Page } from "@playwright/test";

const consoleErrors = new WeakMap<Page, string[]>();
test.afterEach(async ({ page }) => {
  expect(consoleErrors.get(page) ?? []).toEqual([]);
});

test.beforeEach(async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Good work starts here." }),
  ).toBeVisible();
  consoleErrors.set(page, errors);
});

test("complete card and column workflow with validation, cancellation, focus, and reload", async ({
  page,
}) => {
  await expect(page.getByRole("region")).toHaveCount(5);
  await expect(page.getByRole("article")).toHaveCount(9);
  const opener = page.getByRole("button", { name: "New card", exact: true });
  await opener.click();
  await expect(page.getByLabel("Card title")).toBeFocused();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Add card", exact: true })
    .click();
  await expect(page.getByRole("dialog").getByRole("alert")).toHaveText(
    "Please enter a title.",
  );
  await page.getByLabel("Card title").fill("A new beginning");
  await page.getByLabel("Details (optional)").fill("Make the next step clear.");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Add card", exact: true })
    .click();
  await expect(opener).toBeFocused();
  await expect(
    page.getByRole("region", { name: "Backlog" }).getByText("A new beginning"),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Delete A new beginning", exact: true })
    .click();
  await expect(page.getByText("A new beginning")).toHaveCount(0);
  await opener.click();
  await page.getByLabel("Card title").fill("Discarded");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("article")).toHaveCount(9);
  await opener.click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(opener).toBeFocused();
  await page
    .getByRole("button", { name: "Rename Backlog", exact: true })
    .click();
  await page.getByLabel("Column name").fill(" ");
  await page.getByRole("button", { name: "Save name" }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toBeVisible();
  await page.getByLabel("Column name").fill("Fresh ideas");
  await page.getByRole("button", { name: "Save name" }).click();
  await expect(page.getByRole("region", { name: "Fresh ideas" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("region", { name: "Backlog" })).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(9);
});

test("adds into any column with long text and empty details", async ({
  page,
}) => {
  const column = page.getByTestId("column-done");
  await column.getByRole("button", { name: "Add card", exact: true }).click();
  const title = "A".repeat(150);
  await page.getByLabel("Card title").fill(title);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Add card", exact: true })
    .click();
  await expect(column.getByRole("heading", { name: title })).toBeVisible();
  const card = column.getByRole("article").last();
  expect(await card.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(
    true,
  );
  await page.screenshot({
    path: `test-results/${test.info().project.name}-long-text.png`,
    fullPage: true,
  });
});

test("keyboard moves into an empty column and Escape cancels", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Delete Take a fresh look", exact: true })
    .click();
  await expect(
    page.getByTestId("column-review").getByText("A little breathing room."),
  ).toBeVisible();
  const handle = page.getByRole("button", {
    name: "Move Build the essentials",
    exact: true,
  });
  await handle.focus();
  await page.keyboard.press("Space");
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("status")).toContainText(
    "over droppable area review",
  );
  await page.keyboard.press("Space");
  await expect(
    page
      .getByTestId("column-review")
      .getByRole("heading", { name: "Build the essentials" }),
  ).toBeVisible();
  const moved = page
    .getByTestId("column-review")
    .getByRole("button", { name: "Move Build the essentials", exact: true });
  await moved.focus();
  await page.keyboard.press("Space");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("Escape");
  await expect(
    page
      .getByTestId("column-review")
      .getByRole("heading", { name: "Build the essentials" }),
  ).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(8);
});

test("pointer moves cards and dropping outside preserves state", async ({
  page,
  isMobile,
}) => {
  const session = isMobile ? await page.context().newCDPSession(page) : null;
  async function drag(
    from: { x: number; y: number },
    to: { x: number; y: number },
  ) {
    if (session) {
      await session.send("Input.dispatchTouchEvent", {
        type: "touchStart",
        touchPoints: [from],
      });
      for (let step = 1; step <= 20; step++) {
        await session.send("Input.dispatchTouchEvent", {
          type: "touchMove",
          touchPoints: [
            {
              x: from.x + ((to.x - from.x) * step) / 20,
              y: from.y + ((to.y - from.y) * step) / 20,
            },
          ],
        });
      }
      await session.send("Input.dispatchTouchEvent", {
        type: "touchEnd",
        touchPoints: [],
      });
    } else {
      await page.mouse.move(from.x, from.y);
      await page.mouse.down();
      await page.mouse.move(to.x, to.y, { steps: 20 });
      await page.mouse.up();
    }
  }
  const handle = page.getByRole("button", {
    name: "Move A little inspiration",
    exact: true,
  });
  await handle.scrollIntoViewIfNeeded();
  const start = await handle.boundingBox();
  const target = await page.getByTestId("drop-next").boundingBox();
  await drag(
    { x: start!.x + start!.width / 2, y: start!.y + start!.height / 2 },
    {
      x: Math.min(
        target!.x + target!.width / 2,
        page.viewportSize()!.width - 20,
      ),
      y: target!.y + 80,
    },
  );
  await expect(
    page
      .getByTestId("column-next")
      .getByRole("heading", { name: "A little inspiration" }),
  ).toBeVisible();
  const movedHandle = page
    .getByTestId("column-next")
    .getByRole("button", { name: "Move A little inspiration", exact: true });
  await movedHandle.scrollIntoViewIfNeeded();
  const moved = await movedHandle.boundingBox();
  await drag({ x: moved!.x + 10, y: moved!.y + 10 }, { x: 5, y: 90 });
  await expect(
    page
      .getByTestId("column-next")
      .getByRole("heading", { name: "A little inspiration" }),
  ).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(9);
  await session?.detach();
});

test("responsive board and modal keyboard navigation", async ({ page }) => {
  await page.screenshot({
    path: `test-results/${test.info().project.name}-board.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page
    .getByTestId("column-done")
    .getByRole("button", { name: "Add card", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Details (optional)")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("button", { name: "Cancel", exact: true }),
  ).toBeFocused();
  await page.screenshot({
    path: `test-results/${test.info().project.name}-dialog.png`,
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await expect(
    page
      .getByTestId("column-done")
      .getByRole("button", { name: "Add card", exact: true }),
  ).toBeFocused();
});
