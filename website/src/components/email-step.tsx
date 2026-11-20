"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Email } from "@/lib/schemas";
import type { SubmitError } from "./use-wizard";

export function EmailStep({
  onSubmit,
  busy = false,
  error = null,
  onClearError,
}: {
  onSubmit: (email: string) => void;
  busy?: boolean;
  error?: SubmitError | null;
  onClearError?: () => void;
}) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [validationError, setValidationError] = useState("");
  const [clearing, setClearing] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError("");

    const result = Email.safeParse(email);
    if (!result.success) {
      setValidationError(result.error.issues[0]?.message ?? "Invalid email");
      return;
    }

    onSubmit(result.data);
  };

  /** Drop the spent code so InviteGate takes over and a new one can be entered. */
  async function useDifferentCode() {
    setClearing(true);
    try {
      await fetch("/api/invite/clear", { method: "POST" });
      router.refresh();
    } finally {
      setClearing(false);
    }
  }

  const message = validationError || error?.message;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <p className="text-foreground/70">
        We&apos;ll send you a detailed analysis of your car&apos;s market value,
        insurance estimates, and common issues to watch for.
      </p>
      <div>
        <input
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            setValidationError("");
            onClearError?.();
          }}
          placeholder="you@example.com"
          disabled={busy}
          className="w-full border-b-2 border-gray-200 bg-transparent py-3 text-lg text-dark outline-none transition-colors duration-300 placeholder:text-gray-300 focus:border-pink disabled:opacity-50"
          autoFocus
        />
        {message && <p className="mt-2 text-sm text-red-500">{message}</p>}
        {error?.code === "INVITE_REQUIRED" && (
          <button
            type="button"
            onClick={useDifferentCode}
            disabled={clearing}
            className="mt-2 text-sm font-medium text-pink underline transition-colors hover:text-pink-dark disabled:opacity-60"
          >
            {clearing ? "One moment..." : "Use a different invitation code"}
          </button>
        )}
      </div>
      <button
        type="submit"
        disabled={busy}
        className="w-full rounded-lg bg-pink px-8 py-4 text-sm font-bold uppercase tracking-wider text-white transition-colors duration-300 hover:bg-pink-dark disabled:opacity-60 sm:w-auto"
      >
        {busy ? "Submitting..." : "Get My Analysis"}
      </button>
    </form>
  );
}
