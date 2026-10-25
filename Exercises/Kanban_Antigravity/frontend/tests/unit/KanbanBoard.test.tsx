import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import Home from "../../app/page";

describe("KanbanBoard UI component", () => {
  it("renders five named columns and all 9 dummy cards", () => {
    render(<Home />);
    expect(screen.getAllByRole("region")).toHaveLength(5);
    expect(screen.getAllByRole("article")).toHaveLength(9);
    expect(
      screen.getByRole("heading", { name: "Execution starts here." }),
    ).toBeVisible();
  });

  it("validates a blank title and adds a card with details to selected column", async () => {
    const user = userEvent.setup();
    render(<Home />);

    const readyRegion = screen.getByRole("region", { name: "Ready" });
    await user.click(
      within(readyRegion).getByRole("button", { name: "Add card" }),
    );

    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Add card" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Please enter a title.",
    );

    await user.type(
      screen.getByLabelText("Card title"),
      "Antigravity Pipeline Feature",
    );
    await user.type(
      screen.getByLabelText("Details (optional)"),
      "High priority execution task",
    );
    await user.click(within(dialog).getByRole("button", { name: "Add card" }));

    expect(
      within(screen.getByRole("region", { name: "Ready" })).getByText(
        "Antigravity Pipeline Feature",
      ),
    ).toBeVisible();
    expect(screen.getByText("High priority execution task")).toBeVisible();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("cancels creation without adding a card", async () => {
    const user = userEvent.setup();
    render(<Home />);

    await user.click(screen.getByRole("button", { name: "New card" }));
    await user.type(screen.getByLabelText("Card title"), "Discarded Task");
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByText("Discarded Task")).not.toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(9);
  });

  it("renames column inline by clicking title or pencil button", async () => {
    const user = userEvent.setup();
    render(<Home />);

    // Click the Rename button on Backlog
    const renameButtons = screen.getAllByRole("button", { name: "Rename Backlog" });
    await user.click(renameButtons[0]);

    // An input with aria-label="Column name" appears
    const input = screen.getByLabelText("Column name");
    await user.clear(input);
    await user.click(screen.getByRole("button", { name: "Save name" }));

    // Shows validation error
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Please enter a column name.",
    );

    // Enter valid new name and save
    await user.type(input, "Sprint Backlog");
    await user.click(screen.getByRole("button", { name: "Save name" }));

    // Verify column title updated
    expect(
      within(screen.getByRole("region", { name: "Sprint Backlog" })).getAllByRole(
        "article",
      ),
    ).toHaveLength(3);
    expect(screen.getAllByRole("region")).toHaveLength(5);
  });

  it("deletes only the chosen card", async () => {
    const user = userEvent.setup();
    render(<Home />);

    await user.click(
      screen.getByRole("button", {
        name: "Delete Explore agent orchestration workflows",
      }),
    );

    expect(
      screen.queryByText("Explore agent orchestration workflows"),
    ).not.toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(8);
    expect(screen.getByText("Refactor telemetry pipeline")).toBeVisible();
  });
});
