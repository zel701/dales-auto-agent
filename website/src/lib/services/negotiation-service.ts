/** Negotiation service: forward selected listings to the agent. */

import { submitNegotiation } from "@/lib/clients/agent-client";
import type { NegotiationPayloadT } from "@/lib/schemas";
import type { NegotiateResult } from "@/lib/clients/agent-client";

export type { NegotiateResult };

export async function requestNegotiation(
  data: NegotiationPayloadT
): Promise<NegotiateResult> {
  return submitNegotiation(data);
}
