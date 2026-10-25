import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import Home from "../app/page";

describe("board interactions", () => {
  it("renders five named columns and all dummy cards", () => {
    render(<Home />);
    expect(screen.getAllByRole("region")).toHaveLength(5);
    expect(screen.getAllByRole("article")).toHaveLength(9);
    expect(
      screen.getByRole("heading", { name: "Good work starts here." }),
    ).toBeVisible();
  });
  it("validates a blank title and adds a card with details to its selected column", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await user.click(
      within(screen.getByRole("region", { name: "Up next" })).getByRole(
        "button",
        { name: "Add card" },
      ),
    );
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Add card" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Please enter a title.",
    );
    await user.type(screen.getByLabelText("Card title"), "New task");
    await user.type(
      screen.getByLabelText("Details (optional)"),
      "Useful context",
    );
    await user.click(within(dialog).getByRole("button", { name: "Add card" }));
    expect(
      within(screen.getByRole("region", { name: "Up next" })).getByText(
        "New task",
      ),
    ).toBeVisible();
    expect(screen.getByText("Useful context")).toBeVisible();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  it("cancels creation without adding a card", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await user.click(screen.getByRole("button", { name: "New card" }));
    await user.type(screen.getByLabelText("Card title"), "Discard me");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByText("Discard me")).not.toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(9);
  });
  it("validates and saves a column rename without affecting its cards", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await user.click(screen.getByRole("button", { name: "Rename Backlog" }));
    await user.clear(screen.getByLabelText("Column name"));
    await user.click(screen.getByRole("button", { name: "Save name" }));
    expect(screen.getByRole("alert")).toBeVisible();
    await user.type(screen.getByLabelText("Column name"), "Ideas");
    await user.click(screen.getByRole("button", { name: "Save name" }));
    expect(
      within(screen.getByRole("region", { name: "Ideas" })).getAllByRole(
        "article",
      ),
    ).toHaveLength(3);
    expect(screen.getAllByRole("region")).toHaveLength(5);
  });
  it("deletes only the chosen card", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await user.click(
      screen.getByRole("button", { name: "Delete A little inspiration" }),
    );
    expect(screen.queryByText("A little inspiration")).not.toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(8);
    expect(screen.getByText("Map the first impression")).toBeVisible();
  });
});
