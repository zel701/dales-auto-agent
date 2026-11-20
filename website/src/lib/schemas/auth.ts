/** Zod schemas for the customer auth endpoints. */

import { z } from "zod";

export const RequestOtpPayload = z.object({
  email: z.email().max(200),
});

export const VerifyOtpPayload = z.object({
  email: z.email().max(200),
  code: z
    .string()
    .regex(/^\d{6}$/, "Code must be 6 digits"),
});

export type RequestOtpPayloadT = z.infer<typeof RequestOtpPayload>;
export type VerifyOtpPayloadT = z.infer<typeof VerifyOtpPayload>;
