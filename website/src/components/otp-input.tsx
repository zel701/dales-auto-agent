"use client";

import { useEffect, useRef } from "react";

/** 6-digit code input with auto-advance, paste, and backspace-back. */
export function OtpInput({
  value,
  onChange,
  onComplete,
  disabled = false,
}: {
  value: string;
  onChange: (next: string) => void;
  onComplete?: (code: string) => void;
  disabled?: boolean;
}) {
  const refs = useRef<Array<HTMLInputElement | null>>([]);

  useEffect(() => {
    if (value.length === 6 && onComplete) onComplete(value);
  }, [value, onComplete]);

  function setDigit(index: number, digit: string) {
    const sanitized = digit.replace(/\D/g, "").slice(0, 1);
    const arr = value.padEnd(6, " ").split("");
    arr[index] = sanitized || " ";
    const next = arr.join("").replace(/\s+$/, "");
    onChange(next.replace(/\s/g, ""));
    if (sanitized && index < 5) refs.current[index + 1]?.focus();
  }

  function handlePaste(e: React.ClipboardEvent<HTMLInputElement>) {
    const pasted = e.clipboardData
      .getData("text")
      .replace(/\D/g, "")
      .slice(0, 6);
    if (!pasted) return;
    e.preventDefault();
    onChange(pasted);
    const last = Math.min(pasted.length, 5);
    refs.current[last]?.focus();
  }

  function handleKeyDown(
    e: React.KeyboardEvent<HTMLInputElement>,
    index: number
  ) {
    if (e.key === "Backspace" && !value[index] && index > 0) {
      refs.current[index - 1]?.focus();
    }
    if (e.key === "ArrowLeft" && index > 0) refs.current[index - 1]?.focus();
    if (e.key === "ArrowRight" && index < 5)
      refs.current[index + 1]?.focus();
  }

  return (
    <div className="flex justify-center gap-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <input
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={value[i] ?? ""}
          onChange={(e) => setDigit(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(e, i)}
          onPaste={handlePaste}
          disabled={disabled}
          className="h-14 w-12 rounded-lg border-2 border-gray-200 bg-white text-center font-mono text-2xl text-dark outline-none transition-colors focus:border-pink disabled:opacity-50"
          autoFocus={i === 0}
        />
      ))}
    </div>
  );
}
