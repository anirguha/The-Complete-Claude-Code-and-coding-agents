"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { fetchCurrentUser, signOut, type User } from "./api";

/** Shows its children only to a signed-in user, with a bar to sign out; everyone else goes to /login. */
export function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchCurrentUser()
      .then((current) => {
        if (!active) return;
        if (current) setUser(current);
        else router.replace("/login");
      })
      .catch((err: Error) => active && setError(err.message));
    return () => {
      active = false;
    };
  }, [router]);

  async function handleSignOut() {
    try {
      await signOut();
      router.replace("/login");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (!user) {
    return (
      <p role={error ? "alert" : "status"} className="p-8 text-center text-sm text-stone-600">
        {error ?? "Loading…"}
      </p>
    );
  }

  return (
    <>
      <div className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
          <nav className="flex items-center gap-6">
            <Link href="/" className="text-lg font-bold text-[#032147]">
              prelegal<span className="text-[#ecad0a]">.</span>
            </Link>
            {[
              ["/", "New document"],
              ["/documents", "My documents"],
            ].map(([href, label]) => (
              <Link
                key={href}
                href={href}
                className={`text-sm font-medium ${(pathname.replace(/\/+$/, "") || "/") === href ? "text-[#032147]" : "text-[#888888] hover:text-[#032147]"}`}
              >
                {label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-sm">
            {error && (
              <span role="alert" className="text-red-700">
                {error}
              </span>
            )}
            <span className="text-[#888888]">
              Signed in as <span className="font-medium text-stone-800">{user.name}</span>
            </span>
            <button
              type="button"
              onClick={handleSignOut}
              className="rounded-md border border-stone-300 px-3 py-1.5 font-medium text-stone-700 hover:bg-stone-50"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
      {children}
    </>
  );
}
