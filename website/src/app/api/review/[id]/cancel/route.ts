import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/errors";
import { cancelReview } from "@/lib/clients/agent-client";
import { isReviewer } from "@/lib/review-auth";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!(await isReviewer())) {
    return errorResponse("VALIDATION_ERROR", "Not authenticated", 401);
  }
  const { id } = await params;
  const body = await request.json().catch(() => ({}));
  const reason: string | undefined =
    typeof body?.reason === "string" ? body.reason : undefined;
  try {
    const result = await cancelReview(id, reason);
    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Cancel failed";
    return errorResponse("UPSTREAM_ERROR", message, 502);
  }
}
