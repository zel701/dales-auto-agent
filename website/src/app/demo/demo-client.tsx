"use client";

import { useEffect, useState } from "react";
import type { DemoRequestData, DemoState } from "@/lib/schemas/demo";

const STAGES = ["Availability", "Itemized pricing", "Discount", "Scheduling", "Confirmation"];
type DemoResponse = { state: DemoState | null; error?: string };

export function Demo() {
  const [state, setState] = useState<DemoState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    async function restore() {
      try {
        const response = await fetch("/api/demo", { signal: controller.signal, cache: "no-store" });
        const data: DemoResponse = await response.json();
        setState(data.state);
        setError(data.error ?? null);
      } catch {
        if (!controller.signal.aborted) setError("Could not load the demo. Please try again.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void restore();
    return () => controller.abort();
  }, []);

  async function act(action: DemoRequestData["action"]) {
    const body: DemoRequestData = action === "start"
      ? { action }
      : { action, revision: state?.revision ?? 0 };
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/demo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data: DemoResponse = await response.json();
      if (data.state || response.status === 404) setState(data.state);
      setError(data.error ?? null);
    } catch {
      setError("Could not update the demo. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const complete = state?.status === "appointment_set";
  const stage = state?.stage ?? 1;
  const message = error ?? state?.error;
  const primaryAction = !state ? "start" : state.status === "approval" ? "send" :
    state.status === "dealer_reply" ? "reply" : null;
  const primaryLabel = !state ? "Try demo" : state.status === "approval" ?
    (state.error ? "Retry send" : "Approve & send") : "Simulate dealer reply";

  return (
    <main className="mx-auto max-w-5xl px-5 pb-16 pt-12 sm:px-8 sm:pt-16">
      <p className="mb-3 text-sm font-bold text-pink-dark">Dales Auto Agent</p>
      <h1 className="font-serif text-3xl font-bold tracking-tight text-dark sm:text-4xl">Dealership negotiation demo</h1>
      <p className="mt-3 max-w-xl text-base leading-relaxed">
        Review the agent&apos;s email for a sample Toyota Camry LE order and see how the workflow advances.
        All inventory, emails, and dealer replies are simulated.
      </p>

      <div className="mt-8 grid gap-5 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <ol aria-label="Negotiation stages" className="grid grid-cols-5 gap-2 self-start rounded-2xl bg-white p-3 shadow-sm ring-1 ring-dark/5 sm:block">
          {STAGES.map((name, index) => {
            const number = index + 1;
            const active = number === stage && !complete;
            const done = number < stage || complete;
            return (
              <li key={name} aria-current={active ? "step" : undefined}
                className={`flex items-center justify-center gap-3 rounded-lg px-1 py-1.5 text-sm sm:justify-start sm:px-3 sm:py-2.5 ${active ? "bg-pink/10 font-bold text-dark" : "text-foreground"}`}>
                <span className={`grid h-7 w-7 place-items-center rounded-full text-xs font-bold ${active ? "bg-pink-dark text-white" : "bg-background"}`}>
                  {done ? <><span aria-hidden="true">✓</span><span className="sr-only">Completed</span></> : number}
                </span>
                <span className="sr-only sm:not-sr-only">{name}</span>
              </li>
            );
          })}
        </ol>

        <section aria-labelledby="demo-step" className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-dark/5 sm:p-7">
          {!complete && <p className="mb-2 text-sm font-bold text-pink-dark sm:hidden">Step {stage} of 5 · {STAGES[stage - 1]}</p>}
          <h2 id="demo-step" className="font-serif text-xl font-bold text-dark" aria-live="polite">
            {!state ? "Ready to review" : complete ? "Appointment confirmed" :
              state.status === "dealer_reply" ? "Waiting for dealer reply" :
              state.status === "approval" ? "Pending approval" : "Negotiation paused"}
          </h2>

          {!state && <p className="mt-3">The first send will fail once so you can try the retry flow.</p>}
          {complete && <p className="mt-3 font-bold text-dark">{state.appointment} at Demo Toyota</p>}
          {state && !complete && (
            <div className="mt-4 rounded-xl border border-dark/10 bg-background p-4">
              <p className="text-sm">To Demo Toyota</p>
              <p className="mt-1 font-bold text-dark">{state.subject}</p>
              <p className="mt-2 whitespace-pre-wrap leading-relaxed">{state.draft}</p>
            </div>
          )}
          {state?.latest_reply && (
            <div className="mt-4 border-l-2 border-pink/40 pl-3 text-sm">
              <p className="font-bold text-dark">Latest dealer reply</p>
              <p className="mt-1">{state.latest_reply}</p>
            </div>
          )}

          {message && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800">{message}</p>}

          <div className="mt-5 flex flex-wrap items-center gap-3">
            {primaryAction && (
              <button type="button" disabled={loading || busy} onClick={() => void act(primaryAction)}
                className="rounded-lg bg-pink-dark px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-pink disabled:opacity-60">
                {loading ? "Loading…" : busy ? "Working…" : primaryLabel}
              </button>
            )}
            {state && (
              <button type="button" disabled={busy} onClick={() => void act("restart")}
                className="rounded-lg border border-dark/15 px-4 py-2.5 text-sm font-bold text-dark hover:bg-background disabled:opacity-60">
                Start over
              </button>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
