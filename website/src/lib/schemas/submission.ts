/** Schema for POST /api/submit request body. Mirrors the wizard form. */

import { z } from "zod";
import { Email, ZipCode } from "./fields";
import { getColors, getTrims, toyotaModels } from "@/data/cars";

export const SubmissionPayload = z
  .object({
    make: z.string().min(1, "Make is required"),
    model: z.string().min(1, "Model is required"),
    trims: z.array(z.string().min(1)).min(1, "Pick at least one trim"),
    colors: z.array(z.string().min(1)).min(1, "Pick at least one color"),
    zipcode: ZipCode,
    radius: z.string().min(1, "Radius is required"),
    email: Email,
  })
  .superRefine((data, ctx) => {
    // Validate against the Toyota catalog: trims must exist on the model and
    // colors must be offered on at least one of the selected trims.
    if (data.make !== "Toyota") {
      ctx.addIssue({
        code: "custom",
        path: ["make"],
        message: `Unsupported make: ${data.make}`,
      });
      return;
    }
    if (!toyotaModels[data.model]) {
      ctx.addIssue({
        code: "custom",
        path: ["model"],
        message: `Unknown Toyota model: ${data.model}`,
      });
      return;
    }
    const validTrims = new Set(getTrims(data.model));
    const badTrim = data.trims.find((t) => !validTrims.has(t));
    if (badTrim) {
      ctx.addIssue({
        code: "custom",
        path: ["trims"],
        message: `${data.model} has no "${badTrim}" trim`,
      });
      return;
    }
    const validColors = new Set(
      getColors(data.model, data.trims).map((c) => c.name)
    );
    const badColor = data.colors.find((c) => !validColors.has(c));
    if (badColor) {
      ctx.addIssue({
        code: "custom",
        path: ["colors"],
        message: `"${badColor}" is not offered on ${data.model} ${data.trims.join("/")}`,
      });
    }
  });

export type SubmissionPayloadT = z.infer<typeof SubmissionPayload>;
