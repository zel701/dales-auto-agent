import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { z } from "zod";
import { DemoRequest, DemoStateSchema, type DemoState } from "@/lib/schemas/demo";

const COOKIE = "dales_demo_session";
const SessionId = z.uuid();
const StartedSession = z.object({ session_id: SessionId, state: DemoStateSchema });

function respond(state: DemoState | null, status = 200, error?: string) {
  return NextResponse.json({ state, error }, {
    status,
    headers: { "Cache-Control": "no-store" },
  });
}

async function agentRequest(path: string, init?: RequestInit) {
  const url = process.env.DEMO_API_URL?.replace(/\/+$/, "");
  if (!url) throw new Error("DEMO_API_URL is not configured");
  return fetch(`${url}${path}`, { ...init, cache: "no-store", signal: AbortSignal.timeout(8000) });
}

function unavailable() {
  return respond(null, 503, "The demo is unavailable right now. Please try again.");
}

export async function GET() {
  if (!process.env.DEMO_API_URL) return respond(null, 404);
  const id = SessionId.safeParse((await cookies()).get(COOKIE)?.value);
  if (!id.success) return respond(null);
  try {
    const res = await agentRequest(`/sessions/${id.data}`);
    if (res.status === 404) return respond(null);
    if (!res.ok) return unavailable();
    return respond(DemoStateSchema.parse(await res.json()));
  } catch {
    return unavailable();
  }
}

export async function POST(request: Request) {
  if (!process.env.DEMO_API_URL) return respond(null, 404);
  if (!request.headers.get("content-type")?.includes("application/json")) {
    return respond(null, 415, "Expected a JSON request.");
  }
  const parsed = DemoRequest.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return respond(null, 400, "Invalid demo action.");

  try {
    if (parsed.data.action === "start") {
      const res = await agentRequest("/sessions", { method: "POST" });
      if (res.status === 429) return respond(null, 429, "The demo is busy. Please try again later.");
      if (!res.ok) return unavailable();
      const { session_id, state } = StartedSession.parse(await res.json());
      const response = respond(state, 201);
      response.cookies.set(COOKIE, session_id, {
        httpOnly: true,
        sameSite: "strict",
        secure: process.env.NODE_ENV === "production",
        path: "/api/demo",
        maxAge: 30 * 60,
      });
      return response;
    }

    const id = SessionId.safeParse((await cookies()).get(COOKIE)?.value);
    if (!id.success) return respond(null, 404, "Demo session expired. Start a new demo.");
    const res = await agentRequest(`/sessions/${id.data}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed.data),
    });
    if (res.status === 404) return respond(null, 404, "Demo session expired. Start a new demo.");
    if (!res.ok && res.status !== 502 && res.status !== 409) return unavailable();
    const state = DemoStateSchema.parse(await res.json());
    const message = res.status === 409 ? "This session changed. Check the current step and try again." : undefined;
    return respond(state, res.status, message);
  } catch {
    return unavailable();
  }
}
