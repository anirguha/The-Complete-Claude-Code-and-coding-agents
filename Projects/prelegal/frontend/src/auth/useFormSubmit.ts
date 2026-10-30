"use client";

import { type FormEvent, useState } from "react";

/**
 * Runs a form's action on submit, tracking whether it is running and the message of any error it throws.
 * The action can throw its own validation errors too.
 */
export function useFormSubmit(action: () => Promise<void>) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return { submitting, error, onSubmit };
}
