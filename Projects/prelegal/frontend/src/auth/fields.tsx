"use client";

import { type InputHTMLAttributes, type ReactNode, useId, useState } from "react";

const inputClass =
  "w-full rounded-lg border border-stone-300 bg-white px-3.5 py-2.5 text-sm text-stone-900 shadow-sm placeholder:text-stone-400 focus:border-[#209dd7] focus:outline-none focus:ring-2 focus:ring-[#209dd7]/30";

type FieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string };

export function Field({ label, hint, ...input }: FieldProps) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-stone-800">{label}</span>
      <input className={inputClass} {...input} />
      {hint && <span className="block text-xs text-[#888888]">{hint}</span>}
    </label>
  );
}

/** A password input with a Show/Hide toggle, kept outside the label so it isn't part of the input's name. */
export function PasswordField({ label, hint, ...input }: FieldProps) {
  const [visible, setVisible] = useState(false);
  const id = useId();
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-stone-800">
        {label}
      </label>
      <div className="relative">
        <input id={id} className={`${inputClass} pr-16`} type={visible ? "text" : "password"} {...input} />
        <button
          type="button"
          aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          onClick={() => setVisible(!visible)}
          className="absolute inset-y-0 right-0 px-3 text-xs font-medium text-[#209dd7] hover:text-[#032147]"
        >
          {visible ? "Hide" : "Show"}
        </button>
      </div>
      {hint && <p className="text-xs text-[#888888]">{hint}</p>}
    </div>
  );
}

export function SubmitButton({ busy, children }: { busy: boolean; children: ReactNode }) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="w-full rounded-lg bg-[#753991] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#753991]/90 disabled:cursor-wait disabled:opacity-60"
    >
      {children}
    </button>
  );
}

export function Notice({ tone, children }: { tone: "error" | "success"; children: ReactNode }) {
  const styles =
    tone === "error" ? "border-red-200 bg-red-50 text-red-800" : "border-emerald-200 bg-emerald-50 text-emerald-800";
  return (
    <p role={tone === "error" ? "alert" : "status"} className={`rounded-lg border px-3.5 py-2.5 text-sm ${styles}`}>
      {children}
    </p>
  );
}
