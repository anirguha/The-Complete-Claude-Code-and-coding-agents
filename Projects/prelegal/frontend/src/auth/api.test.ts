import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchCurrentUser, signIn, signOut, signUp } from "./api";

const alice = { id: 1, email: "alice@example.com", name: "Alice" };

function mockFetch(status: number, body?: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), { status }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchCurrentUser", () => {
  it("returns the signed-in user", async () => {
    const fetchMock = mockFetch(200, alice);
    await expect(fetchCurrentUser()).resolves.toEqual(alice);
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/me");
  });

  it("returns null when not signed in", async () => {
    mockFetch(401, { detail: "Not signed in" });
    await expect(fetchCurrentUser()).resolves.toBeNull();
  });

  it("throws on other errors", async () => {
    mockFetch(500);
    await expect(fetchCurrentUser()).rejects.toThrow("Could not check sign-in status (500)");
  });
});

describe("signUp", () => {
  it("posts the trimmed email and name with the password as typed", async () => {
    const fetchMock = mockFetch(201, alice);
    await expect(signUp(" alice@example.com ", " Alice ", " pass word ")).resolves.toEqual(alice);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/signup");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ email: "alice@example.com", name: "Alice", password: " pass word " });
  });

  it("explains a taken email and invalid input", async () => {
    mockFetch(409, { detail: "taken" });
    await expect(signUp("a@example.com", "A", "password1")).rejects.toThrow("already exists");
    mockFetch(422, { detail: [] });
    await expect(signUp("nope", "A", "short")).rejects.toThrow("at least 8 characters");
  });

  it("reports other failures", async () => {
    mockFetch(500);
    await expect(signUp("a@example.com", "A", "password1")).rejects.toThrow("Could not create your account");
  });
});

describe("signIn", () => {
  it("posts the email and password", async () => {
    const fetchMock = mockFetch(200, alice);
    await expect(signIn(" alice@example.com ", "password1")).resolves.toEqual(alice);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/signin");
    expect(JSON.parse(init.body)).toEqual({ email: "alice@example.com", password: "password1" });
  });

  it("does not say whether the email or the password was wrong", async () => {
    mockFetch(401, { detail: "Incorrect email or password" });
    await expect(signIn("a@example.com", "wrong")).rejects.toThrow("Incorrect email or password.");
  });

  it("reports other failures", async () => {
    mockFetch(500);
    await expect(signIn("a@example.com", "password1")).rejects.toThrow("Could not sign in");
  });
});

describe("signOut", () => {
  it("posts to the sign-out endpoint", async () => {
    const fetchMock = mockFetch(204);
    await signOut();
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/signout", { method: "POST" });
  });

  it("throws when the request fails", async () => {
    mockFetch(500);
    await expect(signOut()).rejects.toThrow("Could not sign out");
  });
});
