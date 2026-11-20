import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/errors";
import { setInviteCookie } from "@/lib/invite-session";
import { InviteCodePayload } from "@/lib/schemas";
import { redeemInvite } from "@/lib/services/invite-service";

/** The browser's IP, for the agent's rate limiter. Behind a proxy the real
 * client is the first hop of X-Forwarded-For. */
function clientIp(request: Request): string | null {
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",")[0].trim();
  return request.headers.get("x-real-ip");
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return errorResponse("VALIDATION_ERROR", "Invalid JSON", 400);

  const parsed = InviteCodePayload.safeParse(body);
  if (!parsed.success) {
    return errorResponse(
      "VALIDATION_ERROR",
      parsed.error.issues[0]?.message ?? "Invalid request",
      400
    );
  }

  try {
    const outcome = await redeemInvite(parsed.data.code, clientIp(request));

    if (outcome.status === "rate_limited") {
      return errorResponse("RATE_LIMITED", outcome.message, 429);
    }
    if (outcome.status === "invalid") {
      return errorResponse(
        "INVITE_REQUIRED",
        "That invitation code isn't valid.",
        401
      );
    }

    await setInviteCookie(outcome.code);
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("[invite/redeem] Service error:", err);
    return errorResponse(
      "UPSTREAM_ERROR",
      "Could not check your code right now. Please try again.",
      503
    );
  }
}
