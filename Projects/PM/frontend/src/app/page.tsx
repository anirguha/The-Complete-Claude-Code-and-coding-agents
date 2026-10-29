"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AIChatSidebar } from "@/components/AIChatSidebar";
import { KanbanBoard } from "@/components/KanbanBoard";
import { SignIn } from "@/components/SignIn";
import { api } from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

type UserState = "loading" | "signed-out" | "signed-in" | "error";

const errorMessage = (error: unknown, fallback: string) =>
  error instanceof Error ? error.message : fallback;

export default function Home() {
  const [userState, setUserState] = useState<UserState>("loading");
  const [board, setBoard] = useState<BoardData | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const saveQueue = useRef<Promise<void>>(Promise.resolve());

  const loadBoard = useCallback(async () => {
    const nextBoard = await api.getBoard();
    setBoard(nextBoard);
    setUserState("signed-in");
  }, []);

  useEffect(() => {
    let mounted = true;
    api
      .currentUser()
      .then(async () => {
        const nextBoard = await api.getBoard();
        if (mounted) {
          setBoard(nextBoard);
          setUserState("signed-in");
        }
      })
      .catch((requestError: unknown) => {
        if (!mounted) return;
        if (
          requestError instanceof Error &&
          requestError.message === "Please sign in."
        ) {
          setUserState("signed-out");
        } else {
          setError(errorMessage(requestError, "Could not connect to the server."));
          setUserState("error");
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleSignIn = async (username: string, password: string) => {
    setError("");
    setBusy(true);
    try {
      await api.login(username, password);
      await loadBoard();
    } catch (requestError) {
      setError(errorMessage(requestError, "Sign in failed."));
    } finally {
      setBusy(false);
    }
  };

  const handleSignOut = async () => {
    setError("");
    try {
      await saveQueue.current;
      await api.logout();
      setBoard(null);
      setUserState("signed-out");
    } catch (requestError) {
      setError(errorMessage(requestError, "Sign out failed."));
    }
  };

  const handleBoardChange = (nextBoard: BoardData) => {
    setBoard(nextBoard);
    saveQueue.current = saveQueue.current
      .then(async () => {
        await api.saveBoard(nextBoard);
        setError("");
      })
      .catch(async (requestError: unknown) => {
        setError(errorMessage(requestError, "Could not save the board."));
        try {
          await loadBoard();
        } catch (reloadError) {
          setError(
            reloadError instanceof Error
              ? `${reloadError.message} The saved board could not be reloaded.`
              : "The saved board could not be reloaded."
          );
        }
      });
  };

  // The server applies AI changes to the latest saved board, so reload it once
  // any pending saves have finished instead of using the chat response board.
  const handleAIBoardUpdate = () => {
    saveQueue.current = saveQueue.current
      .then(loadBoard)
      .catch((requestError: unknown) => {
        setError(errorMessage(requestError, "Could not reload the board."));
      });
  };

  if (userState === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center text-sm text-[var(--gray-text)]">
        Loading workspace...
      </main>
    );
  }

  if (userState === "error") {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <p role="alert" className="max-w-xl text-center text-sm text-red-700">
          {error}
        </p>
      </main>
    );
  }

  if (userState === "signed-out") {
    return <SignIn onSignIn={handleSignIn} error={error} busy={busy} />;
  }

  if (!board) return null;

  return (
    <div className="mx-auto grid min-h-screen max-w-[1800px] gap-6 px-4 py-6 xl:grid-cols-[minmax(0,1fr)_340px] lg:px-6">
      <div className="min-w-0">
        <div className="mb-4 flex justify-end">
          <button
            type="button"
            onClick={handleSignOut}
            className="rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-sm font-semibold text-[var(--navy-dark)] hover:border-[var(--primary-blue)]"
          >
            Sign out
          </button>
        </div>
        {error && (
          <p role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        )}
        <KanbanBoard board={board} onBoardChange={handleBoardChange} />
      </div>
      <AIChatSidebar onBoardUpdated={handleAIBoardUpdate} />
    </div>
  );
}
