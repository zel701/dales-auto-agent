/** Server-only helpers for the invitation-code cookie.
 *
 * The cookie holds the canonical code and is httpOnly: the browser must not be
 * able to forge an unlock, because this same cookie is what authorizes the
 * analysis submit in /api/submit. */

import "server-only";
import { cookies } from "next/headers";

const COOKIE_NAME = "ic_code";
const MAX_AGE = 30 * 24 * 60 * 60;

export async function getInviteCode(): Promise<string | null> {
  const store = await cookies();
  return store.get(COOKIE_NAME)?.value ?? null;
}

export async function hasInvite(): Promise<boolean> {
  return (await getInviteCode()) !== null;
}

/** Drop the unlock, so the gate reappears and a different code can be entered. */
export async function clearInviteCookie(): Promise<void> {
  const store = await cookies();
  store.delete(COOKIE_NAME);
}

export async function setInviteCookie(code: string): Promise<void> {
  const store = await cookies();
  store.set({
    name: COOKIE_NAME,
    value: code,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: MAX_AGE,
  });
}
