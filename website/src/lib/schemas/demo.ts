import { z } from "zod";

export const DemoStateSchema = z.object({
  revision: z.number().int().nonnegative(),
  stage: z.number().int().min(1).max(5),
  status: z.enum(["approval", "dealer_reply", "appointment_set", "stalled"]),
  subject: z.string(),
  draft: z.string(),
  latest_reply: z.string().nullable(),
  appointment: z.string().nullable(),
  error: z.string().nullable(),
});

export const DemoRequest = z.discriminatedUnion("action", [
  z.object({ action: z.literal("start") }),
  z.object({ action: z.enum(["send", "reply", "restart"]), revision: z.number().int().nonnegative() }),
]);

export type DemoState = z.infer<typeof DemoStateSchema>;
export type DemoRequestData = z.infer<typeof DemoRequest>;
