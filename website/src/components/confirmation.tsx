"use client";

type Selections = {
  make: string;
  model: string;
  trims: string[];
  colors: string[];
  zipcode: string;
  radius: string;
  email: string;
};

export function Confirmation({
  selections,
  onReset,
}: {
  selections: Selections;
  onReset: () => void;
}) {
  return (
    <div className="flex min-h-screen w-full items-center justify-center px-4">
      <div className="w-full max-w-lg rounded-xl bg-white p-8 text-center shadow-[0_30px_18px_rgba(0,0,0,0.06)] sm:p-12">
        <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-pink/10">
          <svg
            className="h-10 w-10 text-pink"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>

        <h2 className="mb-3 font-serif text-3xl font-bold text-dark">
          You&apos;re all set!
        </h2>

        <p className="mb-2 text-lg text-foreground/80">
          Toyota {selections.model} {selections.trims.join("/")}
        </p>
        <p className="mb-1 text-sm text-foreground/50">
          {selections.colors.join("/")} exterior
        </p>
        <p className="mb-6 text-sm text-foreground/50">
          Searching within {selections.radius} miles of {selections.zipcode}
        </p>

        <div className="mb-8 rounded-lg bg-background px-6 py-4">
          <p className="text-sm text-foreground/60">
            We&apos;ll send your purchase strategy to {selections.email}{" "}
            shortly.
          </p>
        </div>

        <button
          onClick={onReset}
          className="text-sm font-medium text-pink transition-colors hover:text-pink-dark"
        >
          Analyze another car
        </button>
      </div>
    </div>
  );
}
