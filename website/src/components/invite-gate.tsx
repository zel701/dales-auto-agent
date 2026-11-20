"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { normalizeInviteCode } from "@/lib/schemas";

const BODY_LENGTH = 4;

/** Blocks the page behind a blurred backdrop until a valid invitation code is
 * entered. Cosmetic only — /api/submit enforces the real gate server-side. */
export function InviteGate({
  unlocked,
  children,
}: {
  unlocked: boolean;
  children: React.ReactNode;
}) {
  const router = useRouter();
  // `unlockedHere` lifts the blur the instant a code is accepted, without
  // waiting for the server round trip. It must reset whenever the server
  // changes its mind — otherwise clearing the cookie to enter a replacement
  // code would refresh the prop to false while the gate stayed hidden.
  // (React's documented "adjust state during render" pattern.)
  const [unlockedHere, setUnlockedHere] = useState(false);
  const [prevUnlocked, setPrevUnlocked] = useState(unlocked);
  if (prevUnlocked !== unlocked) {
    setPrevUnlocked(unlocked);
    setUnlockedHere(false);
  }

  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (unlocked || unlockedHere) return <>{children}</>;

  function handleChange(raw: string) {
    // Accept a pasted full code (`DALE-7K3M`) as readily as the 4 characters
    // the field actually asks for.
    let next = raw.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
    if (next.startsWith("DALE")) next = next.slice(4);
    setBody(next.slice(0, BODY_LENGTH));
    setError("");
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const code = normalizeInviteCode(body);
    if (code === null) {
      setError("That code doesn't look right. Check the characters and try again.");
      return;
    }

    setBusy(true);
    setError("");
    try {
      const res = await fetch("/api/invite/redeem", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        setError(
          payload?.error?.message ?? "That invitation code isn't valid."
        );
        return;
      }
      // Lift the blur immediately, then let the server component catch up so a
      // later navigation doesn't re-render the locked state.
      setUnlockedHere(true);
      router.refresh();
    } catch {
      setError("Could not connect. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div
        inert
        aria-hidden="true"
        className="pointer-events-none select-none blur-md"
      >
        {children}
      </div>

      <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/60 px-4 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="w-full max-w-md rounded-xl bg-white p-6 shadow-[0_30px_18px_rgba(0,0,0,0.06)] sm:p-8"
        >
          <form onSubmit={submit} className="space-y-6">
            <div>
              <h2 className="mb-2 font-serif text-2xl font-bold text-dark">
                You&apos;re invited
              </h2>
              <p className="text-sm text-foreground/60">
                We&apos;re in a closed beta. Enter the invitation code we sent you
                to get started.
              </p>
            </div>

            <div className="flex items-center gap-2 border-b-2 border-gray-200 py-3 transition-colors focus-within:border-pink">
              <span className="font-mono text-lg tracking-widest text-foreground/40">
                DALE-
              </span>
              <input
                type="text"
                value={body}
                onChange={(e) => handleChange(e.target.value)}
                placeholder="7K3M"
                autoFocus
                autoComplete="off"
                autoCapitalize="characters"
                spellCheck={false}
                disabled={busy}
                aria-label="Invitation code"
                className="w-full bg-transparent font-mono text-lg uppercase tracking-widest text-dark outline-none placeholder:text-foreground/25 disabled:opacity-50"
              />
            </div>

            {error && <p className="text-sm text-red-500">{error}</p>}

            <button
              type="submit"
              disabled={busy || body.length < BODY_LENGTH}
              className="w-full rounded-lg bg-pink px-4 py-3 text-sm font-bold text-white transition-colors hover:bg-pink-dark disabled:opacity-60"
            >
              {busy ? "Checking..." : "Unlock"}
            </button>

            <p className="text-center text-xs text-foreground/50">
              Don&apos;t have a code? Reply to the email that brought you here and
              we&apos;ll sort you out.
            </p>
          </form>
        </motion.div>
      </div>
    </>
  );
}
