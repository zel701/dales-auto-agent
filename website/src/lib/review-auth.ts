/** Server-only helpers for the shared-password review session cookie. */

import "server-only";
import { cookies } from "next/headers";

const COOKIE_NAME = "review_session";

export async function isReviewer(): Promise<boolean> {
  const expected = process.env.REVIEW_PASSWORD;
  if (!expected) return false;
  const store = await cookies();
  return store.get(COOKIE_NAME)?.value === expected;
}

export async function setReviewerCookie(value: string): Promise<void> {
  const store = await cookies();
  store.set({
    name: COOKIE_NAME,
    value,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
}

export async function clearReviewerCookie(): Promise<void> {
  const store = await cookies();
  store.delete(COOKIE_NAME);
}
