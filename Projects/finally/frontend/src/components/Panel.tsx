import type { ReactNode } from "react";

/** A terminal pane: a slim title strip over content that fills what is left. */
export function Panel({
  title,
  aside,
  className = "",
  children,
}: {
  title: ReactNode;
  aside?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={`flex min-h-0 min-w-0 flex-col bg-pane ${className}`}>
      <header className="flex h-7 shrink-0 items-center justify-between gap-3 border-b border-edge bg-strip px-2.5">
        <h2 className="truncate text-[12px] font-semibold text-ink">{title}</h2>
        {aside ? <div className="flex min-w-0 items-center gap-3 text-[12px] text-dim">{aside}</div> : null}
      </header>
      <div className="relative flex min-h-0 flex-1 flex-col">{children}</div>
    </section>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center p-4 text-center text-dim">
      <p className="max-w-[34ch]">{children}</p>
    </div>
  );
}
