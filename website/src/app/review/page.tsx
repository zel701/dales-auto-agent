import Link from "next/link";
import { redirect } from "next/navigation";
import { listReviews } from "@/lib/clients/agent-client";
import { isReviewer } from "@/lib/review-auth";
import type { ReviewListItem } from "@/types";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString();
}

const KIND_LABEL: Record<string, string> = {
  initial_strategy_email: "Initial Strategy Email",
};

export default async function ReviewListPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  if (!(await isReviewer())) redirect("/review/login");
  const { status = "pending" } = await searchParams;

  let items: ReviewListItem[] = [];
  let loadError: string | null = null;
  try {
    items = await listReviews(status);
  } catch (err) {
    loadError = err instanceof Error ? err.message : "Failed to load reviews.";
  }

  return (
    <div className="min-h-screen px-4 py-12">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="font-serif text-3xl font-bold text-dark sm:text-4xl">
              Review queue
            </h1>
            <p className="mt-1 text-sm text-foreground/60">
              Approve, retry, or cancel pending agent actions before they run.
            </p>
          </div>
          <div className="flex gap-2 text-sm">
            {(["pending", "approved", "cancelled", "all"] as const).map((s) => (
              <Link
                key={s}
                href={`/review?status=${s}`}
                className={`rounded-full px-3 py-1.5 transition-colors ${
                  status === s
                    ? "bg-pink text-white"
                    : "bg-white text-foreground/60 hover:text-dark"
                }`}
              >
                {s[0].toUpperCase() + s.slice(1)}
              </Link>
            ))}
          </div>
        </div>

        {loadError && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {loadError}
          </div>
        )}

        {!loadError && items.length === 0 && (
          <div className="rounded-xl bg-white p-8 text-center text-foreground/60 shadow-sm">
            No items.
          </div>
        )}

        <div className="space-y-3">
          {items.map((item) => (
            <Link
              key={item.id}
              href={`/review/${item.id}`}
              className="block rounded-xl bg-white p-5 shadow-sm transition-all hover:shadow-md"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-background px-2 py-0.5 text-xs font-medium text-foreground/60">
                      {KIND_LABEL[item.kind] ?? item.kind}
                    </span>
                    <StatusBadge status={item.status} />
                  </div>
                  <h3 className="mt-1 truncate font-semibold text-dark">
                    {item.title}
                  </h3>
                  <p className="text-sm text-foreground/60">
                    {item.customer_email}
                  </p>
                </div>
                <div className="shrink-0 text-right text-xs text-foreground/50">
                  {formatDate(item.created_at)}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-amber-100 text-amber-800",
    approved: "bg-green-100 text-green-800",
    cancelled: "bg-gray-200 text-gray-700",
  };
  const cls = styles[status] ?? "bg-gray-100 text-gray-700";
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}
