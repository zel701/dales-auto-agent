/** Schema + normalization for invitation codes. Mirrors the agent's
 * `invite_repo.normalize_code` so malformed input is rejected before a
 * network hop. */

import { z } from "zod";

// Crockford-ish: no 0/1/I/L/O/U, so a code survives being read aloud.
const ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ";
const PREFIX = "DALE";
const BODY_LENGTH = 4;

const CANONICAL = new RegExp(`^${PREFIX}-[${ALPHABET}]{${BODY_LENGTH}}$`);

/** Coerce user input to canonical `DALE-XXXX`, or null if it can't be one.
 * Accepts `dale7k3m`, `DALE 7K3M`, and the bare body `7k3m` — the prefix is
 * constant, so people drop it. */
export function normalizeInviteCode(raw: string): string | null {
  if (!raw) return null;
  let body = raw.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
  if (body.startsWith(PREFIX)) body = body.slice(PREFIX.length);
  const candidate = `${PREFIX}-${body}`;
  return CANONICAL.test(candidate) ? candidate : null;
}

export const InviteCodePayload = z.object({
  code: z.string().trim().min(1, "Enter your invitation code").max(64),
});

export type InviteCodePayloadT = z.infer<typeof InviteCodePayload>;
