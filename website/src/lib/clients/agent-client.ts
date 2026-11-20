/** Typed client for the car-agent API with retry on 5xx. */

import type { NegotiationPayloadT } from "@/lib/schemas";
import type {
  ReviewDetail,
  ReviewListItem,
  ReviewApproveResult,
  SearchData,
} from "@/types";

const BASE_URL = process.env.LANGGRAPH_API_URL || "http://localhost:8000";
const MAX_RETRIES = 2;

/** An error carrying the agent's HTTP status, so callers can tell a rejected
 * request (bad invite code) from an unavailable service. */
export class AgentError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
    this.name = "AgentError";
  }
}

function reviewHeaders(): HeadersInit {
  const token = process.env.REVIEW_API_TOKEN || "";
  return {
    "Content-Type": "application/json",
    "X-Review-Token": token,
  };
}

async function fetchWithRetry(
  url: string,
  init: RequestInit,
  attempt = 0
): Promise<Response> {
  const res = await fetch(url, init);
  if (res.status >= 500 && attempt < MAX_RETRIES) {
    const delay = 500 * 2 ** attempt;
    await new Promise((r) => setTimeout(r, delay));
    return fetchWithRetry(url, init, attempt + 1);
  }
  return res;
}

export type AnalyzeResult = {
  success: boolean;
  dry_run?: boolean;
  subject?: string;
  results_id?: string;
  num_found?: number;
  queued_for_review?: boolean;
  checkpoint_id?: string;
  error?: string | null;
};

export type NegotiateResult = {
  success: boolean;
  message: string;
  selected_count: number;
  customer_email: string;
  account_message: string;
};

export type CustomerSummary = { id: string; email: string };
export type AuthMeResult = { customer: CustomerSummary | null };
export type AuthVerifyResult = { customer: CustomerSummary };

export type RedeemInviteResult = { ok: boolean; code: string };

/** Redeem an invitation code for site access.
 *
 * `clientIp` is forwarded as X-Forwarded-For because the agent's rate limiter
 * would otherwise see this server's IP for every browser on the internet. */
export async function redeemInvite(
  code: string,
  clientIp: string | null
): Promise<Response> {
  return fetch(`${BASE_URL}/api/invites/redeem`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(clientIp ? { "X-Forwarded-For": clientIp } : {}),
    },
    body: JSON.stringify({ code }),
  });
}

export async function analyzeListings(payload: {
  make: string;
  model: string;
  trims: string[];
  colors: string[];
  zipcode: string;
  radius: string;
  email: string;
  invite_code: string;
}): Promise<AnalyzeResult> {
  const res = await fetchWithRetry(`${BASE_URL}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(120000),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new AgentError(
      err.detail || `Agent API error: ${res.status}`,
      res.status
    );
  }

  return res.json();
}

export async function getResults(uuid: string): Promise<SearchData> {
  const res = await fetch(`${BASE_URL}/api/results/${uuid}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    if (res.status === 404) throw new Error("Results not found.");
    if (res.status === 410) {
      const body = await res.json().catch(() => ({}));
      throw new Error(
        body.detail ||
          "This request has already been submitted. Our team will be in touch soon."
      );
    }
    throw new Error("Failed to load results.");
  }

  return res.json();
}

export async function submitNegotiation(
  payload: NegotiationPayloadT
): Promise<NegotiateResult> {
  const res = await fetchWithRetry(`${BASE_URL}/api/negotiate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(30000),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to submit negotiation request");
  }

  return res.json();
}

export async function listReviews(
  status: string = "pending"
): Promise<ReviewListItem[]> {
  const res = await fetch(`${BASE_URL}/api/reviews?status=${status}`, {
    headers: reviewHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to list reviews: ${res.status}`);
  const data = (await res.json()) as { items: ReviewListItem[] };
  return data.items;
}

export async function getReview(id: string): Promise<ReviewDetail> {
  const res = await fetch(`${BASE_URL}/api/reviews/${id}`, {
    headers: reviewHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    if (res.status === 404) throw new Error("Checkpoint not found");
    throw new Error(`Failed to load checkpoint: ${res.status}`);
  }
  return res.json();
}

export async function approveReview(id: string): Promise<ReviewApproveResult> {
  const res = await fetch(`${BASE_URL}/api/reviews/${id}/approve`, {
    method: "POST",
    headers: reviewHeaders(),
    body: "{}",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Approve failed: ${res.status}`);
  }
  return res.json();
}

export async function retryReview(id: string): Promise<ReviewDetail> {
  const res = await fetch(`${BASE_URL}/api/reviews/${id}/retry`, {
    method: "POST",
    headers: reviewHeaders(),
    body: "{}",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Retry failed: ${res.status}`);
  }
  return res.json();
}

/** Customer auth helpers. The /verify-otp call returns the agent's raw
 * Response so the proxy can lift the Set-Cookie header onto its own response;
 * /me and /logout forward the customer's session token. */

export async function requestOtp(email: string): Promise<{ ok: boolean }> {
  const res = await fetch(`${BASE_URL}/api/auth/request-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `request-otp failed: ${res.status}`);
  }
  return res.json();
}

export async function verifyOtpRaw(
  email: string,
  code: string
): Promise<Response> {
  return fetch(`${BASE_URL}/api/auth/verify-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
}

export async function fetchMe(token: string | null): Promise<AuthMeResult> {
  const res = await fetch(`${BASE_URL}/api/auth/me`, {
    headers: token ? { Cookie: `cs_token=${token}` } : {},
    cache: "no-store",
  });
  if (!res.ok) return { customer: null };
  return res.json();
}

export async function logoutAgent(token: string | null): Promise<void> {
  await fetch(`${BASE_URL}/api/auth/logout`, {
    method: "POST",
    headers: token ? { Cookie: `cs_token=${token}` } : {},
  });
}

export async function cancelReview(
  id: string,
  reason?: string
): Promise<{ success: boolean }> {
  const res = await fetch(`${BASE_URL}/api/reviews/${id}/cancel`, {
    method: "POST",
    headers: reviewHeaders(),
    body: JSON.stringify(reason ? { reason } : {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Cancel failed: ${res.status}`);
  }
  return res.json();
}
