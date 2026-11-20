import { NextResponse } from "next/server";
import { clearInviteCookie } from "@/lib/invite-session";

/** Drop the caller's invite cookie so the gate reappears. Used when someone's
 * code turns out to be spent and they have a replacement to enter. */
export async function POST() {
  await clearInviteCookie();
  return NextResponse.json({ ok: true });
}
