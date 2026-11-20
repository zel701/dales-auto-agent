/** Reusable field-level Zod schemas. */

import { z } from "zod";

export const Email = z
  .string()
  .trim()
  .min(1, "Email is required")
  .regex(/^[^\s@]+@[^\s@]+\.[^\s@]+$/, "Please enter a valid email address");

export const ZipCode = z
  .string()
  .trim()
  .regex(/^\d{5}$/, "Please enter a valid 5-digit US zip code");

/** US phone number. Accepts whatever punctuation the user typed and normalizes
 * to bare digits, so the agent and the DB only ever see one format. */
export const PhoneNumber = z
  .string()
  .transform((v) => v.replace(/\D/g, ""))
  .refine(
    (digits) => digits.length === 10 || (digits.length === 11 && digits.startsWith("1")),
    "Please enter a valid 10-digit US phone number"
  )
  .transform((digits) => (digits.length === 11 ? digits.slice(1) : digits));
