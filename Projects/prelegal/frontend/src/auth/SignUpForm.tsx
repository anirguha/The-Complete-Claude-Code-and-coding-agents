"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { MIN_PASSWORD_LENGTH, signUp } from "./api";
import { Field, Notice, PasswordField, SubmitButton } from "./fields";
import { useFormSubmit } from "./useFormSubmit";

/** Creates an account, then sends the user to the sign-in screen with their email filled in. */
export function SignUpForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const { submitting, error, onSubmit } = useFormSubmit(async () => {
    if (password !== confirm) throw new Error("The passwords do not match.");
    const user = await signUp(email, name, password);
    router.replace(`/login?registered=1&email=${encodeURIComponent(user.email)}`);
  });

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      {error && <Notice tone="error">{error}</Notice>}
      <Field
        label="Full name"
        required
        autoComplete="name"
        placeholder="Jane Doe"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <Field
        label="Work email"
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
        minLength={MIN_PASSWORD_LENGTH}
        autoComplete="new-password"
        hint={`At least ${MIN_PASSWORD_LENGTH} characters.`}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <PasswordField
        label="Confirm password"
        required
        minLength={MIN_PASSWORD_LENGTH}
        autoComplete="new-password"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
      />
      <SubmitButton busy={submitting}>{submitting ? "Creating account…" : "Create account"}</SubmitButton>
    </form>
  );
}
