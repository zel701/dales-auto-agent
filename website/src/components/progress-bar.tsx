"use client";

export function ProgressBar({ step, total }: { step: number; total: number }) {
  const progress = (step / total) * 100;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 h-1 bg-gray-200">
      <div
        className="h-full bg-pink transition-all duration-500 ease-out"
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}
