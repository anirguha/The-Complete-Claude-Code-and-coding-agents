import { expect, test, type Locator, type Page } from "@playwright/test";

const columns = ["Backlog", "To Do", "In Progress", "Review", "Done"];

async function dragCard(page: Page, handle: Locator, target: Locator) {
  await expect(handle).toHaveAttribute("aria-roledescription", "sortable");
  const from = await handle.boundingBox();
  const to = await target.boundingBox();
  if (!from || !to) throw new Error("missing drag target");

  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2, { steps: 25 });
  await page.mouse.up();
}

test("loads the seeded board", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Kanban", level: 1 })).toBeVisible();
  for (const name of columns) {
    await expect(page.getByRole("heading", { name, level: 2 })).toBeVisible();
  }
  await expect(page.getByText("Draft the launch brief")).toBeVisible();
  await expect(page.getByText("Seed the dummy board")).toBeVisible();
});

test("renames a column", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("heading", { name: "Backlog", level: 2 }).getByRole("button").click();
  const input = page.getByLabel("Column name");
  await input.fill("Ideas");
  await input.press("Enter");

  await expect(page.getByRole("heading", { name: "Ideas", level: 2 })).toBeVisible();
});

test("adds and deletes a card", async ({ page }) => {
  await page.goto("/");
  const column = page.getByTestId("column-backlog");

  await column.getByLabel("Title").fill("Ship the board");
  await column.getByLabel("Details").fill("Polish the empty state");
  await column.getByRole("button", { name: "Add" }).click();

  await expect(column.getByText("Ship the board")).toBeVisible();
  await expect(column.getByText("Polish the empty state")).toBeVisible();

  await column.getByRole("button", { name: "Delete Ship the board" }).click();
  await expect(column.getByText("Ship the board")).toHaveCount(0);
});

test("drags a card to another column", async ({ page }) => {
  await page.goto("/");

  const handle = page.getByRole("button", { name: "Drag Draft the launch brief" });
  const target = page.getByTestId("column-done");
  await dragCard(page, handle, target);

  await expect(target.getByText("Draft the launch brief")).toBeVisible();
  await expect(page.getByTestId("column-backlog").getByText("Draft the launch brief")).toHaveCount(
    0,
  );
});

test("drops a card onto an empty column", async ({ page }) => {
  await page.goto("/");
  const review = page.getByTestId("column-review");

  await review.getByRole("button", { name: "Delete QA the drag and drop" }).click();
  await expect(review.getByRole("article")).toHaveCount(0);

  await dragCard(page, page.getByRole("button", { name: "Drag Write the hero copy" }), review);

  await expect(review.getByText("Write the hero copy")).toBeVisible();
  await expect(page.getByTestId("column-todo").getByText("Write the hero copy")).toHaveCount(0);
});

test("reorders a card within a column", async ({ page }) => {
  await page.goto("/");
  const column = page.getByTestId("column-backlog");

  await dragCard(
    page,
    page.getByRole("button", { name: "Drag Draft the launch brief" }),
    page.getByTestId("card-competitor-notes"),
  );

  const titles = column.getByRole("heading", { level: 3 });
  await expect(titles.nth(0)).toHaveText("Collect competitor notes");
  await expect(titles.nth(1)).toHaveText("Draft the launch brief");
});

test("renames a card title and details", async ({ page }) => {
  await page.goto("/");
  const column = page.getByTestId("column-backlog");

  await column.getByRole("button", { name: "Draft the launch brief", exact: true }).click();
  const title = page.getByLabel("Card title");
  await title.fill("Launch notes");
  await title.press("Enter");
  await expect(column.getByRole("heading", { name: "Launch notes", level: 3 })).toBeVisible();

  await column
    .getByRole("button", { name: "Capture the audience, the promise, and the one metric that matters." })
    .click();
  const details = page.getByLabel("Card details");
  await details.fill("A shorter brief");
  await details.press("Enter");
  await expect(column.getByText("A shorter brief")).toBeVisible();
});

test("reload restores the dummy data", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("heading", { name: "Done", level: 2 }).getByRole("button").click();
  const input = page.getByLabel("Column name");
  await input.fill("Shipped");
  await input.press("Enter");
  await expect(page.getByRole("heading", { name: "Shipped", level: 2 })).toBeVisible();

  await page.reload();

  await expect(page.getByRole("heading", { name: "Done", level: 2 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Shipped" })).toHaveCount(0);
  await expect(page.getByText("Draft the launch brief")).toBeVisible();
});
