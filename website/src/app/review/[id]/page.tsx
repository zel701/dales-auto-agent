import { redirect } from "next/navigation";
import { getReview } from "@/lib/clients/agent-client";
import { isReviewer } from "@/lib/review-auth";
import type { ReviewDetail } from "@/types";
import { ReviewDetailClient } from "./review-detail-client";

export default async function ReviewDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  if (!(await isReviewer())) redirect("/review/login");
  const { id } = await params;

  let data: ReviewDetail;
  try {
    data = await getReview(id);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to load.";
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-md rounded-xl bg-white p-8 text-center shadow-lg">
          <h2 className="mb-3 font-serif text-2xl font-bold text-dark">Oops</h2>
          <p className="text-foreground/70">{message}</p>
        </div>
      </div>
    );
  }
  return <ReviewDetailClient data={data} />;
}
