"use client";

import { useState } from "react";
import { ZipCode } from "@/lib/schemas";

export function ZipcodeStep({
  onSubmit,
}: {
  onSubmit: (zipcode: string) => void;
}) {
  const [zipcode, setZipcode] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const result = ZipCode.safeParse(zipcode);
    if (!result.success) {
      setError(result.error.issues[0]?.message ?? "Invalid zip code");
      return;
    }

    onSubmit(result.data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <p className="text-foreground/70">
        We&apos;ll search for available inventory near you.
      </p>
      <div>
        <input
          type="text"
          inputMode="numeric"
          maxLength={5}
          value={zipcode}
          onChange={(e) => setZipcode(e.target.value.replace(/\D/g, ""))}
          placeholder="e.g. 90210"
          className="w-full border-b-2 border-gray-200 bg-transparent py-3 text-lg text-dark outline-none transition-colors duration-300 placeholder:text-gray-300 focus:border-pink"
          autoFocus
        />
        {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
      </div>
      <button
        type="submit"
        className="w-full rounded-lg bg-pink px-8 py-4 text-sm font-bold uppercase tracking-wider text-white transition-colors duration-300 hover:bg-pink-dark sm:w-auto"
      >
        Continue
      </button>
    </form>
  );
}
