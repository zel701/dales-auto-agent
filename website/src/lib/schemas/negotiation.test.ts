import { describe, it, expect } from "vitest";
import { NegotiationPayload } from "./negotiation";

const VALID = {
  results_id: "9f1c2d3e-0000-4000-8000-000000000000",
  selected_listing_ids: ["1HGCM82633A004352"],
  first_name: "Alex",
  phone: "(555) 123-4567",
  need_by_date: "2026-10-01",
  payment_method: "cash" as const,
  delivery_method: "pickup" as const,
};

describe("NegotiationPayload", () => {
  it("accepts a valid cash order with no credit range", () => {
    expect(NegotiationPayload.safeParse(VALID).success).toBe(true);
  });

  it("normalizes a punctuated phone number to bare digits", () => {
    const r = NegotiationPayload.safeParse(VALID);
    expect(r.data?.phone).toBe("5551234567");
  });

  it("strips the US country code from an 11-digit number", () => {
    const r = NegotiationPayload.safeParse({ ...VALID, phone: "+1 555 123 4567" });
    expect(r.data?.phone).toBe("5551234567");
  });

  it("rejects a phone number that is too short", () => {
    const r = NegotiationPayload.safeParse({ ...VALID, phone: "555-4567" });
    expect(r.success).toBe(false);
    expect(r.error?.issues[0]?.message).toMatch(/valid 10-digit US phone/);
  });

  it("trims the first name", () => {
    const r = NegotiationPayload.safeParse({ ...VALID, first_name: "  Alex  " });
    expect(r.data?.first_name).toBe("Alex");
  });

  it("rejects a blank first name", () => {
    const r = NegotiationPayload.safeParse({ ...VALID, first_name: "   " });
    expect(r.success).toBe(false);
    expect(r.error?.issues[0]?.message).toMatch(/First name is required/);
  });

  it("requires a credit score range when financing", () => {
    const r = NegotiationPayload.safeParse({ ...VALID, payment_method: "finance" });
    expect(r.success).toBe(false);
    expect(r.error?.issues[0]?.message).toMatch(/Credit score range is required/);
  });

  it("accepts a financed order carrying a credit score range", () => {
    const r = NegotiationPayload.safeParse({
      ...VALID,
      payment_method: "finance",
      credit_score_range: "720_779",
    });
    expect(r.success).toBe(true);
  });

  it("rejects an unknown credit score range", () => {
    const r = NegotiationPayload.safeParse({
      ...VALID,
      payment_method: "finance",
      credit_score_range: "excellent",
    });
    expect(r.success).toBe(false);
  });
});
