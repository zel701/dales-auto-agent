/** Submit the wizard payload and decide what to tell the user.
 *
 * The happy path takes 10-30s (MarketCheck search + a long LLM call), but every
 * rejection the user can act on — spent invite code, invalid payload, agent
 * down — is decided in milliseconds, because the agent validates before doing
 * any expensive work. So we race the request against a short timer: a verdict
 * inside the window is real and gets shown; silence means validation already
 * passed and the slow path is underway, so we confirm optimistically.
 *
 * The request is deliberately never aborted — it keeps running to completion
 * after we stop waiting on it. */

import type { SubmissionPayloadT } from "@/lib/schemas";

export const SUBMIT_DECISION_TIMEOUT_MS = 3000;

export type SubmitOutcome =
  /** No verdict in time: the analysis is running, tell the user it worked. */
  | { status: "accepted" }
  /** The server answered 2xx inside the window. */
  | { status: "confirmed" }
  | { status: "error"; code: string; message: string };

const GENERIC_ERROR =
  "Something went wrong submitting your request. Please try again.";

type FetchImpl = typeof fetch;

/** Pull `{ error: { code, message } }` out of a response, tolerating a body
 * that isn't JSON or isn't shaped like our envelope. */
async function readError(res: Response): Promise<SubmitOutcome> {
  const body = await res.json().catch(() => null);
  const err = body?.error;
  return {
    status: "error",
    code: typeof err?.code === "string" ? err.code : "UPSTREAM_ERROR",
    message: typeof err?.message === "string" ? err.message : GENERIC_ERROR,
  };
}

export async function submitAnalysis(
  payload: SubmissionPayloadT,
  {
    timeoutMs = SUBMIT_DECISION_TIMEOUT_MS,
    fetchImpl = fetch,
  }: { timeoutMs?: number; fetchImpl?: FetchImpl } = {}
): Promise<SubmitOutcome> {
  const request: Promise<SubmitOutcome> = fetchImpl("/api/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then(
    async (res) => (res.ok ? { status: "confirmed" } : readError(res)),
    // A rejected fetch is a genuine network failure; an HTTP error status
    // resolves normally and is handled above.
    (): SubmitOutcome => ({
      status: "error",
      code: "NETWORK_ERROR",
      message: "Could not reach the server. Please check your connection.",
    })
  );

  // If the timer wins, `request` is left in flight on purpose. Swallow any
  // later rejection so it doesn't surface as an unhandled promise rejection.
  request.catch(() => {});

  let timer: ReturnType<typeof setTimeout>;
  const deadline = new Promise<SubmitOutcome>((resolve) => {
    timer = setTimeout(() => resolve({ status: "accepted" }), timeoutMs);
  });

  return Promise.race([request, deadline]).finally(() => clearTimeout(timer));
}
