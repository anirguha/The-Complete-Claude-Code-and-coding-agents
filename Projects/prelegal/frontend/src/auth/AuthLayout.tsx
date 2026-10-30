import type { ReactNode } from "react";

const POINTS = [
  "Tell the assistant what you need; it picks the right agreement",
  "11 Common Paper templates, from NDAs to cloud service agreements",
  "Your documents are saved to Confluence, ready when you return",
];

function Check() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" className="mt-0.5 h-5 w-5 flex-none text-[#ecad0a]" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M16.7 5.3a1 1 0 0 1 0 1.4l-8 8a1 1 0 0 1-1.4 0l-4-4a1 1 0 1 1 1.4-1.4L8 12.6l7.3-7.3a1 1 0 0 1 1.4 0Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`text-2xl font-bold tracking-tight ${className}`}>
      prelegal<span className="text-[#ecad0a]">.</span>
    </span>
  );
}

type Props = {
  title: string;
  subtitle: string;
  children: ReactNode;
  /** A line under the form, such as a link to the other auth screen. */
  footer: ReactNode;
};

/** The sign-in and sign-up screens: a brand panel beside a form card. */
export function AuthLayout({ title, subtitle, children, footer }: Props) {
  return (
    <main className="grid min-h-screen flex-1 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <section className="relative hidden overflow-hidden bg-[#032147] px-12 py-14 text-white lg:flex lg:flex-col lg:justify-between">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-[#209dd7]/20 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-[#753991]/25 blur-3xl"
        />
        <Wordmark className="relative" />
        <div className="relative max-w-md space-y-8">
          <div className="space-y-4">
            <h2 className="text-4xl font-semibold leading-tight">Draft agreements in minutes, not days.</h2>
            <p className="text-base text-white/70">
              Prelegal turns a conversation into a ready-to-sign legal document, built on trusted standard terms.
            </p>
          </div>
          <ul className="space-y-4">
            {POINTS.map((point) => (
              <li key={point} className="flex gap-3 text-sm text-white/90">
                <Check />
                {point}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-white/50">
          Built on Common Paper standard terms, free to use under CC BY 4.0.
        </p>
      </section>

      <section className="flex items-center justify-center bg-stone-50 px-4 py-12 sm:px-8">
        <div className="w-full max-w-md space-y-8">
          <Wordmark className="block text-center text-[#032147] lg:hidden" />
          <div className="space-y-6 rounded-2xl border border-stone-200 bg-white p-8 shadow-sm sm:p-10">
            <header className="space-y-2">
              <h1 className="text-2xl font-semibold text-[#032147]">{title}</h1>
              <p className="text-sm text-[#888888]">{subtitle}</p>
            </header>
            {children}
          </div>
          <p className="text-center text-sm text-stone-600">{footer}</p>
        </div>
      </section>
    </main>
  );
}
