import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/errors";
import { VerifyOtpPayload } from "@/lib/schemas";
import { verifyOtpRaw } from "@/lib/clients/agent-client";

const SESSION_COOKIE = "cs_token";

/** Parse the session token out of an upstream Set-Cookie header.
 * The agent always names its session cookie `cs_token`. */
function extractToken(setCookie: string | null): string | null {
  if (!setCookie) return null;
  const m = setCookie.match(/cs_token=([^;]+)/);
  return m ? m[1] : null;
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return errorResponse("VALIDATION_ERROR", "Invalid JSON", 400);

  const parsed = VerifyOtpPayload.safeParse(body);
  if (!parsed.success) {
    return errorResponse(
      "VALIDATION_ERROR",
      parsed.error.issues[0]?.message ?? "Invalid request",
      400
    );
  }

  try {
    const upstream = await verifyOtpRaw(parsed.data.email, parsed.data.code);
    const json = await upstream.json().catch(() => ({}));
    if (!upstream.ok) {
      return NextResponse.json(json, { status: upstream.status });
    }

    const token = extractToken(upstream.headers.get("set-cookie"));
    if (token) {
      const store = await cookies();
      store.set(SESSION_COOKIE, token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 30 * 24 * 60 * 60,
      });
    }
    return NextResponse.json(json);
  } catch (err) {
    console.error("[auth/verify-otp]", err);
    return errorResponse("UPSTREAM_ERROR", "Auth service unavailable", 503);
  }
}
