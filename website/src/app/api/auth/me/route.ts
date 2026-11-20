import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { fetchMe } from "@/lib/clients/agent-client";

const SESSION_COOKIE = "cs_token";

export async function GET() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value ?? null;
  if (!token) return NextResponse.json({ customer: null });
  try {
    const result = await fetchMe(token);
    return NextResponse.json(result);
  } catch (err) {
    console.error("[auth/me]", err);
    return NextResponse.json({ customer: null });
  }
}
