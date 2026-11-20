"use client";

import { useEffect, useState } from "react";
import { OtpInput } from "@/components/otp-input";
import { Email } from "@/lib/schemas";
import { useCustomerSession } from "@/lib/customer-session";

type Step = "email" | "code";

export function LoginModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { refresh } = useCustomerSession();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setStep("email");
      setEmail("");
      setCode("");
      setBusy(false);
      setError("");
    }
  }, [open]);

  if (!open) return null;

  async function sendCode(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const parsed = Email.safeParse(email);
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Invalid email");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/api/auth/request-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: parsed.data }),
      });
      if (!res.ok) {
        setError("Could not send code. Please try again.");
        return;
      }
      setStep("code");
    } catch {
      setError("Could not connect. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function verifyCode(submittedCode: string) {
    setBusy(true);
    setError("");
    try {
      const res = await fetch("/api/auth/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code: submittedCode }),
      });
      if (!res.ok) {
        setError("Invalid or expired code. Try again.");
        setCode("");
        return;
      }
      await refresh();
      onClose();
    } catch {
      setError("Could not connect. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      onClick={busy ? undefined : onClose}
    >
      <div
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-[0_30px_18px_rgba(0,0,0,0.06)] sm:p-8"
        onClick={(e) => e.stopPropagation()}
      >
        {step === "email" ? (
          <form onSubmit={sendCode} className="space-y-6">
            <div>
              <h2 className="mb-2 font-serif text-2xl font-bold text-dark">
                Sign in
              </h2>
              <p className="text-sm text-foreground/60">
                Enter your email and we&apos;ll send you a 6-digit code.
              </p>
            </div>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoFocus
              disabled={busy}
              className="w-full border-b-2 border-gray-200 bg-transparent py-3 text-lg text-dark outline-none transition-colors focus:border-pink disabled:opacity-50"
            />
            {error && <p className="text-sm text-red-500">{error}</p>}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={busy}
                className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm font-bold text-dark transition-colors hover:bg-background disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={busy}
                className="flex-[2] rounded-lg bg-pink px-4 py-3 text-sm font-bold text-white transition-colors hover:bg-pink-dark disabled:opacity-60"
              >
                {busy ? "Sending..." : "Send code"}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-6">
            <div>
              <h2 className="mb-2 font-serif text-2xl font-bold text-dark">
                Enter your code
              </h2>
              <p className="text-sm text-foreground/60">
                We sent a 6-digit code to <strong>{email}</strong>.
              </p>
            </div>
            <OtpInput
              value={code}
              onChange={setCode}
              onComplete={verifyCode}
              disabled={busy}
            />
            {error && (
              <p className="text-center text-sm text-red-500">{error}</p>
            )}
            <div className="flex justify-between text-sm">
              <button
                type="button"
                onClick={() => setStep("email")}
                disabled={busy}
                className="text-foreground/70 hover:text-dark disabled:opacity-60"
              >
                ← Use a different email
              </button>
              <button
                type="button"
                onClick={() =>
                  sendCode({ preventDefault: () => {} } as React.FormEvent)
                }
                disabled={busy}
                className="text-pink hover:text-pink-dark disabled:opacity-60"
              >
                Resend code
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
