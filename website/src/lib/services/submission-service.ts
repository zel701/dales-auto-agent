/** Submission service: forward car preferences to the agent for search + analysis. */

import { analyzeListings } from "@/lib/clients/agent-client";
import { logger } from "@/lib/logger";
import type { SubmissionPayloadT } from "@/lib/schemas";

export type SubmitResult = {
  success: boolean;
  listingsFound: number;
  dryRun?: boolean;
};

export async function submitCar(
  data: SubmissionPayloadT,
  inviteCode: string
): Promise<SubmitResult> {
  const { make, model, trims, colors, zipcode, radius, email } = data;

  const analyzeResult = await analyzeListings({
    make,
    model,
    trims,
    colors,
    zipcode,
    radius,
    email,
    invite_code: inviteCode,
  });

  logger.info("Analysis complete", {
    email,
    num_found: analyzeResult.num_found,
    dry_run: analyzeResult.dry_run,
    results_id: analyzeResult.results_id,
  });

  return {
    success: true,
    listingsFound: analyzeResult.num_found ?? 0,
    dryRun: analyzeResult.dry_run,
  };
}
