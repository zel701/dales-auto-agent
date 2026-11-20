import { NextResponse } from "next/server";
import { AgentError } from "@/lib/clients/agent-client";
import { errorResponse } from "@/lib/errors";
import { getInviteCode } from "@/lib/invite-session";
import { SubmissionPayload } from "@/lib/schemas";
import { submitCar } from "@/lib/services/submission-service";

export async function POST(request: Request) {
  // The real gate. The blurred landing page is only cosmetic — this is what
  // stops an uninvited submit, and the cookie is httpOnly so it can't be forged.
  const inviteCode = await getInviteCode();
  if (!inviteCode) {
    return errorResponse(
      "INVITE_REQUIRED",
      "An invitation code is required to request an analysis.",
      403
    );
  }

  const body = await request.json().catch(() => null);
  if (!body) return errorResponse("VALIDATION_ERROR", "Invalid JSON", 400);

  const parsed = SubmissionPayload.safeParse(body);
  if (!parsed.success) {
    return errorResponse(
      "VALIDATION_ERROR",
      parsed.error.issues[0]?.message ?? "Invalid request",
      400
    );
  }

  try {
    const result = await submitCar(parsed.data, inviteCode);
    return NextResponse.json(result);
  } catch (err) {
    // 403 from the agent means the code was spent or revoked between unlocking
    // and submitting — a user error, not an outage.
    if (err instanceof AgentError && err.status === 403) {
      return errorResponse("INVITE_REQUIRED", err.message, 403);
    }
    console.error("[submit] Service error:", err);
    return errorResponse(
      "UPSTREAM_ERROR",
      "Analysis service is unavailable. Please try again later.",
      503
    );
  }
}
