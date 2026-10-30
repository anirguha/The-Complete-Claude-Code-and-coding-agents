"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { signIn } from "./api";
import { Field, Notice, PasswordField, SubmitButton } from "./fields";
import { useFormSubmit } from "./useFormSubmit";

/** Signs in and goes to the app. After sign-up, the URL carries ?registered=1&email=... */
export function SignInForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState(params.get("email") ?? "");
  const [password, setPassword] = useState("");
  const { submitting, error, onSubmit } = useFormSubmit(async () => {
    await signIn(email, password);
    router.replace("/");
  });

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      {params.get("registered") && !error && (
        <Notice tone="success">Your account is ready. Sign in to start drafting.</Notice>
      )}
      {error && <Notice tone="error">{error}</Notice>}
      <Field
        label="Email"
        type="email"
        required
        autoComplete="email"
        placeholder="you@company.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <PasswordField
        label="Password"
        required
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <SubmitButton busy={submitting}>{submitting ? "Signing in…" : "Sign in"}</SubmitButton>
    </form>
  );
}
