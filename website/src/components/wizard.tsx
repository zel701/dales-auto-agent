"use client";

import { motion, AnimatePresence } from "framer-motion";
import { ProgressBar } from "./progress-bar";
import { StepCard } from "./step-card";
import { OptionGrid } from "./option-grid";
import { EmailStep } from "./email-step";
import { ZipcodeStep } from "./zipcode-step";
import { Confirmation } from "./confirmation";
import { useWizard } from "./use-wizard";
import {
  models,
  getTrims,
  getColors,
  comingSoonBrands,
  radiusOptions,
} from "@/data/cars";

const TOTAL_STEPS = 7;

const variants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -300 : 300,
    opacity: 0,
  }),
};

export function Wizard() {
  const {
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
  } = useWizard();

  if (isComplete) {
    return <Confirmation selections={selections} onReset={reset} />;
  }

  const makeOptions = [{ label: "Toyota", value: "Toyota" }];
  const comingSoonOptions = comingSoonBrands.map((b) => ({
    label: b,
    value: b,
  }));
  const modelOptions = models.map((m) => ({ label: m, value: m }));
  const trimOptions = getTrims(selections.model).map((t) => ({
    label: t,
    value: t,
  }));
  const colorOptions = getColors(selections.model, selections.trims).map((c) => {
    const notes: string[] = [];
    if (selections.trims.length > 1 && c.grades.length < selections.trims.length) {
      notes.push(`${c.grades.join(", ")} only`);
    }
    if (c.extraCost && c.msrp > 0) {
      notes.push(`+$${c.msrp}`);
    }
    return {
      label: c.name,
      value: c.name,
      hex: c.hex ?? undefined,
      sublabel: notes.length ? notes.join(" · ") : undefined,
    };
  });
  const radiusOpts = radiusOptions.map((r) => ({
    label: r.label,
    value: r.value,
  }));

  return (
    <>
      <ProgressBar step={step} total={TOTAL_STEPS} />

      {step > 0 && (
        <button
          onClick={goBack}
          className="fixed left-4 top-6 z-50 flex items-center gap-1 rounded-full bg-white/80 px-3 py-1.5 text-sm text-foreground/60 shadow-sm backdrop-blur-sm transition-colors hover:text-dark sm:left-8"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back
        </button>
      )}

      <AnimatePresence mode="wait" custom={direction}>
        <motion.div
          key={step}
          custom={direction}
          variants={variants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ duration: 0.3, ease: "easeInOut" }}
        >
          {step === 0 && (
            <StepCard
              title="What's your car's make?"
              subtitle="Select the manufacturer of your vehicle"
            >
              <OptionGrid
                options={makeOptions}
                onSelect={(v) => goNext("make", v)}
                comingSoon={comingSoonOptions}
              />
            </StepCard>
          )}

          {step === 1 && (
            <StepCard
              title="Which Toyota model?"
              subtitle="Select your specific model"
            >
              <OptionGrid
                options={modelOptions}
                onSelect={(v) => goNext("model", v)}
              />
            </StepCard>
          )}

          {step === 2 && (
            <StepCard
              title="What trim levels work for you?"
              subtitle={`Toyota ${selections.model} — pick one or more`}
            >
              <OptionGrid
                multiSelect
                options={trimOptions}
                onContinue={(vs) => goNext("trims", vs)}
              />
            </StepCard>
          )}

          {step === 3 && (
            <StepCard
              title="What colors work for you?"
              subtitle={`Colors offered on ${selections.model} ${selections.trims.join("/")} — pick one or more`}
            >
              <OptionGrid
                multiSelect
                options={colorOptions}
                onContinue={(vs) => goNext("colors", vs)}
              />
            </StepCard>
          )}

          {step === 4 && (
            <StepCard
              title="What's your zip code?"
              subtitle="We'll search for inventory near you"
            >
              <ZipcodeStep
                onSubmit={(v) => goNext("zipcode", v)}
              />
            </StepCard>
          )}

          {step === 5 && (
            <StepCard
              title="How far are you willing to travel?"
              subtitle="Select your search radius"
            >
              <OptionGrid
                options={radiusOpts}
                onSelect={(v) => goNext("radius", v)}
              />
            </StepCard>
          )}

          {step === 6 && (
            <StepCard
              title="Where should we send your analysis?"
              subtitle={`Toyota ${selections.model} ${selections.trims.join("/")} in ${selections.colors.join("/")}`}
            >
              <EmailStep
                onSubmit={handleSubmit}
                busy={submitting}
                error={submitError}
                onClearError={clearSubmitError}
              />
            </StepCard>
          )}
        </motion.div>
      </AnimatePresence>
    </>
  );
}
