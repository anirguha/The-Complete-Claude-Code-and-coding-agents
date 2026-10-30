/** Client for the backend's accounts: sign-up, sign-in with a password, and the session. */

import { postJson, request } from "@/lib/http";

export type User = {
  id: number;
  email: string;
  name: string;
};

/** Also enforced by the backend (Password in backend/app/routers/auth.py). */
export const MIN_PASSWORD_LENGTH = 8;

/** The signed-in user, or null when there is no valid session. */
export async function fetchCurrentUser(): Promise<User | null> {
  const res = await fetch("/api/auth/me");
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(`Could not check sign-in status (${res.status})`);
  return res.json();
}

/** Creates an account. It does not sign in: the user goes on to the sign-in screen. */
export function signUp(email: string, name: string, password: string): Promise<User> {
  return request<User>(
    "/api/auth/signup",
    postJson({ email: email.trim(), name: name.trim(), password }),
    {
      409: "An account with this email already exists. Please sign in.",
      422: `Please enter a valid email, your name and a password of at least ${MIN_PASSWORD_LENGTH} characters.`,
    },
    "Could not create your account. Please try again.",
  );
}

export function signIn(email: string, password: string): Promise<User> {
  const wrong = "Incorrect email or password.";
  return request<User>(
    "/api/auth/signin",
    postJson({ email: email.trim(), password }),
    { 401: wrong, 422: wrong },
    "Could not sign in. Please try again.",
  );
}

export function signOut(): Promise<void> {
  return request<void>("/api/auth/signout", { method: "POST" }, {}, "Could not sign out. Please try again.");
}
