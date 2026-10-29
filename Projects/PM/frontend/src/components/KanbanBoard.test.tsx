import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

describe("KanbanBoard", () => {
  it("renders five columns", () => {
    render(<KanbanBoard />);
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name{Enter}");
    expect(input).toHaveValue("New Name");
    expect(within(column).getByLabelText("Column title")).toHaveValue("New Name");
  });

  it("saves a column rename once, on Enter", async () => {
    const onBoardChange = vi.fn();
    render(<KanbanBoard onBoardChange={onBoardChange} />);
    const input = within(getFirstColumn()).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "Queued");
    expect(onBoardChange).not.toHaveBeenCalled();
    await userEvent.type(input, "{Enter}");
    expect(onBoardChange).toHaveBeenCalledOnce();
    expect(onBoardChange.mock.calls[0][0].columns[0].title).toBe("Queued");
  });

  it("reverts a column rename on Escape", async () => {
    const onBoardChange = vi.fn();
    render(<KanbanBoard onBoardChange={onBoardChange} />);
    const input = within(getFirstColumn()).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "Discarded{Escape}");
    expect(onBoardChange).not.toHaveBeenCalled();
    expect(input).toHaveValue("Backlog");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("edits a card title and details", async () => {
    render(<KanbanBoard />);
    const card = screen.getByTestId("card-card-1");
    await userEvent.click(
      within(card).getByRole("button", { name: "Edit Align roadmap themes" })
    );
    const title = within(card).getByRole("textbox", {
      name: "Title for Align roadmap themes",
    });
    await userEvent.clear(title);
    await userEvent.type(title, "Updated roadmap");
    await userEvent.click(
      within(card).getByRole("button", { name: "Save changes" })
    );
    expect(within(card).getByText("Updated roadmap")).toBeInTheDocument();
  });
});
