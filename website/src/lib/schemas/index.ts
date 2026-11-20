/**
 * Zod schemas for every input boundary (form fields, API request bodies).
 *
 * One module per resource. Each module exports its schema and the inferred
 * TypeScript type. Use the schema both client-side (form validation) and
 * server-side (route handler `safeParse`) so validation rules live once.
 */

export { Email, PhoneNumber, ZipCode } from "./fields";
export { SubmissionPayload, type SubmissionPayloadT } from "./submission";
export {
  InviteCodePayload,
  normalizeInviteCode,
  type InviteCodePayloadT,
} from "./invite";
export {
  CREDIT_SCORE_RANGES,
  NegotiationPayload,
  type CreditScoreRange,
  type NegotiationPayloadT,
} from "./negotiation";
export {
  RequestOtpPayload,
  VerifyOtpPayload,
  type RequestOtpPayloadT,
  type VerifyOtpPayloadT,
} from "./auth";
