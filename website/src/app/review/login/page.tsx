import { redirect } from "next/navigation";
import { setReviewerCookie } from "@/lib/review-auth";

async function login(formData: FormData) {
  "use server";
  const password = String(formData.get("password") ?? "");
  const expected = process.env.REVIEW_PASSWORD ?? "";
  if (!expected || password !== expected) {
    redirect("/review/login?error=1");
  }
  await setReviewerCookie(password);
  redirect("/review");
}

export default async function ReviewLoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg">
        <h1 className="mb-2 font-serif text-2xl font-bold text-dark">
          Review console
        </h1>
        <p className="mb-6 text-sm text-foreground/60">
          Enter the shared review password to continue.
        </p>
        <form action={login} className="space-y-4">
          <input
            name="password"
            type="password"
            autoFocus
            required
            placeholder="Password"
            className="w-full rounded-lg border border-gray-200 px-4 py-3 text-base focus:border-pink focus:outline-none"
          />
          {error && (
            <p className="text-sm text-red-500">Incorrect password.</p>
          )}
          <button
            type="submit"
            className="w-full rounded-lg bg-pink py-3 font-bold text-white transition-colors hover:bg-pink-dark"
          >
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}
