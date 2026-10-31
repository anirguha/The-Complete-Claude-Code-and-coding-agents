import { describe, expect, it } from "vitest";
import { errorMessage } from "./api";

describe("errorMessage", () => {
  it("uses a string detail", () => {
    expect(errorMessage(400, { detail: "Insufficient cash" })).toBe("Insufficient cash");
  });

  it("uses the first 422 validation message", () => {
    expect(errorMessage(422, { detail: [{ loc: ["body"], msg: "Field required" }] })).toBe("Field required");
  });

  it("falls back to the status for unknown bodies", () => {
    expect(errorMessage(500, null)).toBe("Request failed with status 500");
    expect(errorMessage(500, { detail: [] })).toBe("Request failed with status 500");
  });
});
