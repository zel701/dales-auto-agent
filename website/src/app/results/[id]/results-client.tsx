"use client";

import { useState } from "react";
import { ListingCard } from "@/components/listing-card";
import {
  OrderDetailsModal,
  type OrderDetails,
} from "@/components/order-details-modal";
import type { Listing, SearchData } from "@/types";

function listingId(l: Listing): string {
  return l.marketcheck_id || l.vin || "";
}

export function ResultsClient({
  data,
  resultsId,
}: {
  data: SearchData;
  resultsId: string;
}) {
  const { car_info, listings } = data;
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [accountMessage, setAccountMessage] = useState("");
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectAll() {
    if (selected.size === listings.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(listings.map(listingId)));
    }
  }

  function openModal() {
    if (selected.size === 0) return;
    setError("");
    setModalOpen(true);
  }

  async function submitOrder(details: OrderDetails) {
    setSubmitting(true);
    setError("");
    try {
      const res = await fetch("/api/negotiate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          results_id: resultsId,
          selected_listing_ids: Array.from(selected),
          ...details,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const message =
          typeof data.error === "object"
            ? data.error?.message
            : data.error;
        setError(message || "Something went wrong. Please try again.");
        return;
      }
      const data = (await res.json().catch(() => ({}))) as {
        account_message?: string;
      };
      setAccountMessage(data.account_message ?? "");
      setModalOpen(false);
      setSubmitted(true);
    } catch {
      setError("Could not connect. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-lg rounded-xl bg-white p-8 text-center shadow-lg sm:p-12">
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
            Request Submitted!
          </h2>
          <p className="mb-2 text-lg text-foreground/80">
            We&apos;ll negotiate the best deal on{" "}
            {selected.size} listing{selected.size > 1 ? "s" : ""} for you.
          </p>
          <p className="text-sm text-foreground/50">
            We&apos;ll send updates to {data.email}
          </p>
          {accountMessage && (
            <div className="mt-6 rounded-lg bg-pink/5 p-4 text-left text-sm text-foreground/70">
              {accountMessage}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 py-12">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 text-center">
          <h1 className="mb-2 font-serif text-3xl font-bold text-dark sm:text-4xl">
            {car_info.make} {car_info.model} {car_info.trims.join("/")}
          </h1>
          <p className="text-foreground/60">
            {car_info.colors.join("/")} &middot; Within {car_info.radius} miles of{" "}
            {car_info.zipcode} &middot; {listings.length} listing
            {listings.length !== 1 ? "s" : ""} found
          </p>
        </div>

        <div className="mb-4 flex items-center justify-between">
          <button
            onClick={selectAll}
            className="text-sm font-medium text-pink hover:text-pink-dark transition-colors"
          >
            {selected.size === listings.length ? "Deselect All" : "Select All"}
          </button>
          <p className="text-sm text-foreground/50">
            {selected.size} selected
          </p>
        </div>

        <div className="space-y-4">
          {listings.map((listing) => {
            const id = listingId(listing);
            return (
              <ListingCard
                key={id}
                listing={listing}
                selectable
                selected={selected.has(id)}
                onToggle={() => toggle(id)}
              />
            );
          })}
        </div>

        <div className="sticky bottom-0 mt-8 rounded-xl bg-white p-4 shadow-lg border border-gray-100">
          {error && (
            <p className="mb-3 text-center text-sm text-red-500">{error}</p>
          )}
          <button
            onClick={openModal}
            disabled={selected.size === 0 || submitting}
            className={`w-full rounded-lg py-4 text-lg font-bold text-white transition-all ${
              selected.size > 0
                ? "bg-pink hover:bg-pink-dark cursor-pointer"
                : "bg-gray-300 cursor-not-allowed"
            }`}
          >
            {selected.size > 0
              ? `Negotiate ${selected.size} Listing${selected.size > 1 ? "s" : ""} For Me`
              : "Select Listings to Continue"}
          </button>
        </div>
      </div>

      <OrderDetailsModal
        open={modalOpen}
        onClose={() => (submitting ? null : setModalOpen(false))}
        onSubmit={submitOrder}
        submitting={submitting}
        count={selected.size}
      />
    </div>
  );
}
