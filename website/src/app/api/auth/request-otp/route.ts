import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/errors";
import { RequestOtpPayload } from "@/lib/schemas";
import { requestOtp } from "@/lib/clients/agent-client";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return errorResponse("VALIDATION_ERROR", "Invalid JSON", 400);

  const parsed = RequestOtpPayload.safeParse(body);
  if (!parsed.success) {
    return errorResponse(
      "VALIDATION_ERROR",
      parsed.error.issues[0]?.message ?? "Invalid request",
      400
    );
  }

  try {
    const result = await requestOtp(parsed.data.email);
    return NextResponse.json(result);
  } catch (err) {
    console.error("[auth/request-otp]", err);
    return errorResponse("UPSTREAM_ERROR", "Auth service unavailable", 503);
  }
}
