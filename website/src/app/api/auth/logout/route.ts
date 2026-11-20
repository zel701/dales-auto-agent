import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { logoutAgent } from "@/lib/clients/agent-client";

const SESSION_COOKIE = "cs_token";

export async function POST() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value ?? null;
  try {
    await logoutAgent(token);
  } catch (err) {
    console.error("[auth/logout]", err);
  }
  store.delete(SESSION_COOKIE);
  return NextResponse.json({ ok: true });
}
