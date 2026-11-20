import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/errors";
import { NegotiationPayload } from "@/lib/schemas";
import { requestNegotiation } from "@/lib/services/negotiation-service";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return errorResponse("VALIDATION_ERROR", "Invalid JSON", 400);

  const parsed = NegotiationPayload.safeParse(body);
  if (!parsed.success) {
    return errorResponse(
      "VALIDATION_ERROR",
      parsed.error.issues[0]?.message ?? "Invalid request",
      400
    );
  }

  try {
    const result = await requestNegotiation(parsed.data);
    return NextResponse.json(result);
  } catch (err) {
    console.error("[negotiate] Service error:", err);
    const message =
      err instanceof Error ? err.message : "Service unavailable";
    return errorResponse("UPSTREAM_ERROR", message, 503);
  }
}
