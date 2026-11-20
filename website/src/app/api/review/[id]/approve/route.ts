import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/errors";
import { approveReview } from "@/lib/clients/agent-client";
import { isReviewer } from "@/lib/review-auth";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!(await isReviewer())) {
    return errorResponse("VALIDATION_ERROR", "Not authenticated", 401);
  }
  const { id } = await params;
  try {
    const result = await approveReview(id);
    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Approve failed";
    return errorResponse("UPSTREAM_ERROR", message, 502);
  }
}
