/** Schema for POST /api/negotiate request body. */

import { z } from "zod";
import { PhoneNumber } from "./fields";

/** FICO tiers, coarse enough that a buyer can answer from memory. */
export const CREDIT_SCORE_RANGES = [
  "780_plus",
  "720_779",
  "660_719",
  "600_659",
  "under_600",
] as const;

export type CreditScoreRange = (typeof CREDIT_SCORE_RANGES)[number];

export const NegotiationPayload = z
  .object({
    results_id: z.string().min(1, "results_id is required"),
    selected_listing_ids: z
      .array(z.string().min(1))
      .min(1, "At least one listing must be selected"),
    first_name: z
      .string()
      .trim()
      .min(1, "First name is required")
      .max(100, "First name is too long"),
    phone: PhoneNumber,
    need_by_date: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/, "need_by_date must be YYYY-MM-DD"),
    payment_method: z.enum(["finance", "cash"]),
    credit_score_range: z.enum(CREDIT_SCORE_RANGES).optional(),
    delivery_method: z.enum(["pickup", "ship"]),
  })
  // Only financed deals need a credit tier; cash buyers are never asked.
  .refine(
    (v) => v.payment_method !== "finance" || v.credit_score_range !== undefined,
    {
      message: "Credit score range is required when financing",
      path: ["credit_score_range"],
    }
  );

export type NegotiationPayloadT = z.infer<typeof NegotiationPayload>;
