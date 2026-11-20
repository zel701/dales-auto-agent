"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { ReviewDetail } from "@/types";

type Action = "approve" | "retry" | "cancel";

export function ReviewDetailClient({ data }: { data: ReviewDetail }) {
  const router = useRouter();
  const [pending, setPending] = useState<Action | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);

  const isPending = data.status === "pending";
  const { email } = data.payload;

  async function run(action: Action) {
    setError(null);
    setBanner(null);
    if (action === "approve" && !confirm("Send this email now?")) return;
    if (action === "cancel" && !confirm("Cancel this packet without sending?"))
      return;

    setPending(action);
    try {
      const res = await fetch(`/api/review/${data.id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.error?.message || `${action} failed`);
      }
      const body = await res.json();
      if (action === "approve") {
        const sr = body?.send_result;
        setBanner(
          sr?.dry_run
            ? "Approved (dry-run — no real email sent)."
            : sr?.success
            ? "Approved and sent."
            : `Approved, but send failed: ${sr?.error ?? "unknown"}`
        );
      } else if (action === "cancel") {
        setBanner("Cancelled.");
      } else {
        setBanner("Email redrafted.");
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="min-h-screen px-4 py-12">
      <div className="mx-auto max-w-4xl">
        <Link
          href="/review"
          className="mb-4 inline-flex items-center gap-1 text-sm text-foreground/60 hover:text-dark"
        >
          &larr; Back to queue
        </Link>

        <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
          <div className="mb-2 flex items-center gap-2">
            <span className="rounded bg-background px-2 py-0.5 text-xs font-medium text-foreground/60">
              {data.kind}
            </span>
            <StatusBadge status={data.status} />
          </div>
          <h1 className="font-serif text-2xl font-bold text-dark">
            {data.title}
          </h1>
          <p className="mt-1 text-sm text-foreground/60">
            For {data.customer_email}
          </p>
        </div>

        {banner && (
          <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
            {banner}
          </div>
        )}
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {isPending && (
          <div className="sticky top-2 z-10 mb-6 flex flex-wrap gap-3 rounded-xl bg-white p-4 shadow-md">
            <button
              onClick={() => run("approve")}
              disabled={pending !== null}
              className="rounded-lg bg-pink px-5 py-2.5 font-bold text-white transition-colors hover:bg-pink-dark disabled:opacity-60"
            >
              {pending === "approve" ? "Approving..." : "Approve & Send"}
            </button>
            {data.kind === "initial_strategy_email" && (
              <button
                onClick={() => run("retry")}
                disabled={pending !== null}
                className="rounded-lg border border-gray-300 bg-white px-5 py-2.5 font-bold text-dark transition-colors hover:bg-background disabled:opacity-60"
              >
                {pending === "retry" ? "Redrafting..." : "Retry draft"}
              </button>
            )}
            <button
              onClick={() => run("cancel")}
              disabled={pending !== null}
              className="rounded-lg border border-red-200 bg-white px-5 py-2.5 font-bold text-red-600 transition-colors hover:bg-red-50 disabled:opacity-60"
            >
              {pending === "cancel" ? "Cancelling..." : "Cancel"}
            </button>
          </div>
        )}

        <section className="mb-6 rounded-xl bg-white p-6 shadow-sm">
          <h2 className="mb-3 font-serif text-xl font-bold text-dark">
            Email preview
          </h2>
          <dl className="mb-4 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-foreground/50">To</dt>
            <dd className="text-dark">{email.to}</dd>
            <dt className="text-foreground/50">Subject</dt>
            <dd className="font-medium text-dark">{email.subject}</dd>
          </dl>
          <iframe
            srcDoc={email.full_html}
            sandbox=""
            title="Email preview"
            className="h-[600px] w-full rounded-lg border border-gray-200 bg-white"
          />
        </section>

        <details className="rounded-xl bg-white p-6 shadow-sm">
          <summary className="cursor-pointer font-medium text-dark">
            Raw payload
          </summary>
          <pre className="mt-3 max-h-96 overflow-auto rounded bg-background p-3 text-xs">
            {JSON.stringify(data, null, 2)}
          </pre>
        </details>
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
