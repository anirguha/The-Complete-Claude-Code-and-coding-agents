import { test, expect, type Page, type Locator } from "@playwright/test";

const consoleErrors = new WeakMap<Page, string[]>();

test.beforeEach(async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });

  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Execution starts here." }),
  ).toBeVisible();

  consoleErrors.set(page, errors);
});

test.afterEach(async ({ page }) => {
  expect(consoleErrors.get(page) ?? []).toEqual([]);
});

async function dragCard(
  page: Page,
  handle: Locator,
  target: Locator,
  isMobile = false,
) {
  await handle.scrollIntoViewIfNeeded();
  const from = await handle.boundingBox();
  const to = await target.boundingBox();
  if (!from || !to) throw new Error("missing drag target");

  const fromPoint = { x: from.x + from.width / 2, y: from.y + from.height / 2 };
  const toPoint = {
    x: isMobile
      ? Math.min(to.x + to.width / 2, (page.viewportSize()?.width ?? 390) - 25)
      : to.x + to.width / 2,
    y: to.y + Math.min(80, to.height / 2),
  };

  if (isMobile) {
    const session = await page.context().newCDPSession(page);
    await session.send("Input.dispatchTouchEvent", {
      type: "touchStart",
      touchPoints: [fromPoint],
    });
    for (let step = 1; step <= 25; step++) {
      await session.send("Input.dispatchTouchEvent", {
        type: "touchMove",
        touchPoints: [
          {
            x: fromPoint.x + ((toPoint.x - fromPoint.x) * step) / 25,
            y: fromPoint.y + ((toPoint.y - fromPoint.y) * step) / 25,
          },
        ],
      });
    }
    await session.send("Input.dispatchTouchEvent", {
      type: "touchEnd",
      touchPoints: [],
    });
    await session.detach();
  } else {
    await page.mouse.move(fromPoint.x, fromPoint.y);
    await page.mouse.down();
    await page.mouse.move(toPoint.x, toPoint.y, { steps: 25 });
    await page.mouse.up();
  }
}

async function dragToCoords(
  page: Page,
  handle: Locator,
  toPoint: { x: number; y: number },
  isMobile = false,
) {
  await handle.scrollIntoViewIfNeeded();
  const from = await handle.boundingBox();
  if (!from) throw new Error("missing drag handle");

  const fromPoint = { x: from.x + from.width / 2, y: from.y + from.height / 2 };

  if (isMobile) {
    const session = await page.context().newCDPSession(page);
    await session.send("Input.dispatchTouchEvent", {
      type: "touchStart",
      touchPoints: [fromPoint],
    });
    for (let step = 1; step <= 25; step++) {
      await session.send("Input.dispatchTouchEvent", {
        type: "touchMove",
        touchPoints: [
          {
            x: fromPoint.x + ((toPoint.x - fromPoint.x) * step) / 25,
            y: fromPoint.y + ((toPoint.y - fromPoint.y) * step) / 25,
          },
        ],
      });
    }
    await session.send("Input.dispatchTouchEvent", {
      type: "touchEnd",
      touchPoints: [],
    });
    await session.detach();
  } else {
    await page.mouse.move(fromPoint.x, fromPoint.y);
    await page.mouse.down();
    await page.mouse.move(toPoint.x, toPoint.y, { steps: 25 });
    await page.mouse.up();
  }
}

test("initial board state renders 5 columns and 9 seed cards", async ({
  page,
}) => {
  await expect(page.getByRole("region")).toHaveCount(5);
  await expect(page.getByRole("article")).toHaveCount(9);

  await expect(page.getByRole("region", { name: "Backlog" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Ready" })).toBeVisible();
  await expect(page.getByRole("region", { name: "In Progress" })).toBeVisible();
  await expect(page.getByRole("region", { name: "In Review" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Done" })).toBeVisible();
});

test("complete card lifecycle: validation, creation, deletion, and cancellation", async ({
  page,
}) => {
  const newCardButton = page.getByRole("button", {
    name: "New card",
    exact: true,
  });
  await newCardButton.click();

  await expect(page.getByLabel("Card title")).toBeFocused();

  // Validate blank title error
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Add card", exact: true })
    .click();
  await expect(page.getByRole("dialog").getByRole("alert")).toHaveText(
    "Please enter a title.",
  );

  // Fill and create card
  await page.getByLabel("Card title").fill("Verify Playwright Automation");
  await page
    .getByLabel("Details (optional)")
    .fill("Ensure end-to-end integration suite runs cleanly.");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Add card", exact: true })
    .click();

  await expect(
    page
      .getByRole("region", { name: "Backlog" })
      .getByText("Verify Playwright Automation"),
  ).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(10);

  // Delete newly added card
  await page
    .getByRole("button", {
      name: "Delete Verify Playwright Automation",
      exact: true,
    })
    .click();
  await expect(page.getByText("Verify Playwright Automation")).toHaveCount(0);
  await expect(page.getByRole("article")).toHaveCount(9);

  // Test modal cancellation with Cancel button
  await newCardButton.click();
  await page.getByLabel("Card title").fill("Temporary card");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByText("Temporary card")).toHaveCount(0);
  await expect(page.getByRole("article")).toHaveCount(9);

  // Test modal cancellation with Escape key
  await newCardButton.click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("column renaming inline with validation, cancellation, and reset on reload", async ({
  page,
}) => {
  // Test rename via pencil button
  const renameButton = page.getByRole("button", {
    name: "Rename Backlog",
    exact: true,
  });
  await renameButton.click();

  // Validate blank column name
  await page.getByLabel("Column name").fill(" ");
  await page.getByRole("button", { name: "Save name" }).click();
  await expect(page.getByText("Please enter a column name.")).toBeVisible();

  // Cancel rename via Escape key
  await page.keyboard.press("Escape");
  await expect(page.getByRole("region", { name: "Backlog" })).toBeVisible();

  // Test rename via clicking column title button
  await page.getByRole("button", { name: "Backlog", exact: true }).click();
  await page.getByLabel("Column name").fill("Sprint Backlog");
  await page.getByRole("button", { name: "Save name" }).click();
  await expect(
    page.getByRole("region", { name: "Sprint Backlog" }),
  ).toBeVisible();

  // Reload page to verify in-memory contract (resets without persistence)
  await page.reload();
  await expect(page.getByRole("region", { name: "Backlog" })).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(9);
});

test("arranges cards within the same column", async ({ page, isMobile }) => {
  const backlog = page.getByRole("region", { name: "Backlog" });
  const articlesBefore = backlog.getByRole("article");
  await expect(articlesBefore).toHaveCount(3);
  await expect(articlesBefore.nth(0)).toContainText(
    "Explore agent orchestration workflows",
  );
  await expect(articlesBefore.nth(1)).toContainText(
    "Refactor telemetry pipeline",
  );
  await expect(articlesBefore.nth(2)).toContainText(
    "Audit keyboard navigation flows",
  );

  // Drag card 2 ("Refactor telemetry pipeline") onto card 1 ("Explore agent orchestration workflows")
  const handle2 = backlog.getByRole("button", {
    name: "Move Refactor telemetry pipeline",
    exact: true,
  });
  const targetCard = page.getByTestId("card-card-1");
  await dragCard(page, handle2, targetCard, isMobile);

  // Verify Explore card moved down below Refactor telemetry pipeline!
  const articlesAfter = backlog.getByRole("article");
  await expect(articlesAfter.nth(0)).toContainText(
    "Refactor telemetry pipeline",
  );
  await expect(articlesAfter.nth(1)).toContainText(
    "Explore agent orchestration workflows",
  );
  await expect(articlesAfter.nth(2)).toContainText(
    "Audit keyboard navigation flows",
  );
});

test("adds card into specific column with long text", async ({ page }) => {
  const doneColumn = page.getByTestId("column-done");
  await doneColumn
    .getByRole("button", { name: "Add card", exact: true })
    .click();

  const longTitle =
    "Card with very long title text that must wrap cleanly without overflowing or breaking layout boundaries in the board";
  await page.getByLabel("Card title").fill(longTitle);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Add card", exact: true })
    .click();

  await expect(
    doneColumn.getByRole("heading", { name: longTitle }),
  ).toBeVisible();

  const cardElement = doneColumn.getByRole("article").last();
  const fitsWithinBounds = await cardElement.evaluate(
    (el) => el.scrollWidth <= el.clientWidth,
  );
  expect(fitsWithinBounds).toBe(true);
});

test("drags a card across columns", async ({ page, isMobile }) => {
  const handle = page.getByRole("button", {
    name: "Move Explore agent orchestration workflows",
    exact: true,
  });
  const targetCol = page.getByTestId("drop-ready");
  await dragCard(page, handle, targetCol, isMobile);

  await expect(
    page
      .getByTestId("column-ready")
      .getByRole("heading", { name: "Explore agent orchestration workflows" }),
  ).toBeVisible();
  await expect(
    page
      .getByTestId("column-backlog")
      .getByRole("heading", { name: "Explore agent orchestration workflows" }),
  ).toHaveCount(0);
});

test("drops a card onto an empty column", async ({ page, isMobile }) => {
  const readyCol = page.getByTestId("column-ready");
  await readyCol
    .getByRole("button", {
      name: "Delete Define brand typography tokens",
      exact: true,
    })
    .click();
  await readyCol
    .getByRole("button", {
      name: "Delete Implement drag overlay feedback",
      exact: true,
    })
    .click();
  await expect(readyCol.getByRole("article")).toHaveCount(0);
  await expect(readyCol.getByText("No cards in this column.")).toBeVisible();

  const handle = page.getByRole("button", {
    name: "Move Refactor telemetry pipeline",
    exact: true,
  });
  const readyDrop = page.getByTestId("drop-ready");
  await dragCard(page, handle, readyDrop, isMobile);

  await expect(
    readyCol.getByRole("heading", { name: "Refactor telemetry pipeline" }),
  ).toBeVisible();
  await expect(readyCol.getByRole("article")).toHaveCount(1);
});

test("pointer drag dropping outside preserves state", async ({
  page,
  isMobile,
}) => {
  const handle = page.getByRole("button", {
    name: "Move Explore agent orchestration workflows",
    exact: true,
  });

  // Drag outside to the top header area (y: 20 is above all columns)
  await dragToCoords(page, handle, { x: 200, y: 20 }, isMobile);

  await expect(
    page
      .getByTestId("column-backlog")
      .getByRole("heading", { name: "Explore agent orchestration workflows" }),
  ).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(9);
});

test("responsive layout and keyboard dialog navigation", async ({ page }) => {
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

  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
