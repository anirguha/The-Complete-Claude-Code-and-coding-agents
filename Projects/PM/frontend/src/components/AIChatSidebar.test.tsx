import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "@/lib/api";
import { initialData } from "@/lib/kanban";
import { AIChatSidebar } from "@/components/AIChatSidebar";

vi.mock("@/lib/api", () => ({
  api: {
    chat: vi.fn(),
  },
}));

describe("AIChatSidebar", () => {
  it("sends on Enter and keeps Shift+Enter for new lines", async () => {
    vi.mocked(api.chat).mockResolvedValue({
      response: "Hi.",
      board: initialData,
    });
    render(<AIChatSidebar onBoardUpdated={vi.fn()} />);
    const input = screen.getByRole("textbox", {
      name: "Message the board assistant",
    });

    await userEvent.type(input, "line one{Shift>}{Enter}{/Shift}line two");
    expect(api.chat).not.toHaveBeenCalled();
    await userEvent.type(input, "{Enter}");

    expect(await screen.findByText("Hi.")).toBeInTheDocument();
    expect(api.chat).toHaveBeenCalledWith("line one\nline two", []);
  });

  it("shows the assistant reply and reports the board update", async () => {
    const onBoardUpdated = vi.fn();
    vi.mocked(api.chat).mockResolvedValue({
      response: "I renamed the column.",
      board: initialData,
    });
    render(<AIChatSidebar onBoardUpdated={onBoardUpdated} />);

    await userEvent.type(
      screen.getByRole("textbox", { name: "Message the board assistant" }),
      "Rename backlog to queued"
    );
    await userEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("I renamed the column.")).toBeInTheDocument();
    expect(api.chat).toHaveBeenCalledWith("Rename backlog to queued", []);
    expect(onBoardUpdated).toHaveBeenCalledOnce();
  });

  it("shows chat errors and restores the message draft", async () => {
    vi.mocked(api.chat).mockRejectedValue(new Error("AI provider unavailable."));
    render(<AIChatSidebar onBoardUpdated={vi.fn()} />);
    const input = screen.getByRole("textbox", {
      name: "Message the board assistant",
    });
    await userEvent.type(input, "Summarize the board");
    await userEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "AI provider unavailable."
    );
    expect(input).toHaveValue("Summarize the board");
  });
});
