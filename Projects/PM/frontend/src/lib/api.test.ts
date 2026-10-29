import { api } from "@/lib/api";

describe("api", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses a string error detail as the message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Please sign in." }), { status: 401 })
      )
    );
    await expect(api.getBoard()).rejects.toThrow("Please sign in.");
  });

  it("does not show validation error objects as the message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: [{ msg: "too long" }] }), {
          status: 422,
        })
      )
    );
    await expect(api.getBoard()).rejects.toThrow("Request failed (422).");
  });
});
