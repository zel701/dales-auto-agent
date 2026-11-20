"use client";

import { useState, useCallback } from "react";
import { submitAnalysis } from "@/lib/submit-analysis";
import type { Selections } from "@/types";

export type SubmitError = { code: string; message: string };

const TOTAL_STEPS = 7;

const EMPTY_SELECTIONS: Selections = {
  make: "",
  model: "",
  trims: [],
  colors: [],
  zipcode: "",
  radius: "",
  email: "",
};

export function useWizard() {
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState(1);
  const [selections, setSelections] = useState<Selections>(EMPTY_SELECTIONS);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<SubmitError | null>(null);

  const goNext = useCallback(
    <K extends keyof Selections>(field: K, value: Selections[K]) => {
      setSelections((prev) => {
        const updated = { ...prev, [field]: value };
        // Colors depend on the selected trims (and trims on the model), so
        // changing an upstream step invalidates the downstream selections.
        if (field === "model") {
          updated.trims = [];
          updated.colors = [];
        } else if (field === "trims") {
          updated.colors = [];
        }
        return updated;
      });
      setDirection(1);
      setStep((s) => s + 1);
    },
    []
  );

  const goBack = useCallback(() => {
    if (step > 0) {
      setDirection(-1);
      setStep((s) => s - 1);
    }
  }, [step]);

  const handleSubmit = useCallback(
    async (email: string) => {
      const payload = { ...selections, email };
      setSelections(payload);
      setSubmitting(true);
      setSubmitError(null);

      const outcome = await submitAnalysis(payload);
      setSubmitting(false);

      // "accepted" means no verdict arrived in time, which can only happen once
      // validation has passed and the slow analysis is underway — so it
      // confirms just like an explicit 2xx.
      if (outcome.status === "error") {
        setSubmitError({ code: outcome.code, message: outcome.message });
        return;
      }

      setDirection(1);
      setStep(TOTAL_STEPS);
    },
    [selections]
  );

  const clearSubmitError = useCallback(() => setSubmitError(null), []);

  const reset = useCallback(() => {
    setSelections(EMPTY_SELECTIONS);
    setStep(0);
    setDirection(1);
    setSubmitError(null);
  }, []);

  const isComplete = step === TOTAL_STEPS;

  return {
    step,
    direction,
    selections,
    isComplete,
    submitting,
    submitError,
    goNext,
    goBack,
    handleSubmit,
    clearSubmitError,
    reset,
  };
}
