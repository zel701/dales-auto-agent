/** Invite service: redeem an invitation code with the agent. */

import { redeemInvite as redeemInviteUpstream } from "@/lib/clients/agent-client";
import { logger } from "@/lib/logger";
import { normalizeInviteCode } from "@/lib/schemas";

export type RedeemOutcome =
  | { status: "ok"; code: string }
  | { status: "invalid" }
  | { status: "rate_limited"; message: string };

/**
 * Validate a code and, on success, return its canonical form for the cookie.
 *
 * Malformed input is rejected here rather than upstream — it keeps obvious junk
 * off the agent's rate limiter, where budget is reserved for real guesses.
 */
export async function redeemInvite(
  rawCode: string,
  clientIp: string | null
): Promise<RedeemOutcome> {
  const code = normalizeInviteCode(rawCode);
  if (code === null) return { status: "invalid" };

  const res = await redeemInviteUpstream(code, clientIp);

  if (res.status === 429) {
    const body = await res.json().catch(() => ({}));
    logger.warn("Invite redemption rate-limited", { clientIp });
    return {
      status: "rate_limited",
      message:
        body.detail ?? "Too many attempts. Please wait a few minutes and try again.",
    };
  }

  if (!res.ok) {
    logger.info("Invite redemption rejected", { status: res.status });
    return { status: "invalid" };
  }

  const body = (await res.json()) as { ok: boolean; code: string };
  logger.info("Invite redeemed");
  return { status: "ok", code: body.code };
}
