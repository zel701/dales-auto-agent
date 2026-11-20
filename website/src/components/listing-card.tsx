"use client";

import type { Listing } from "@/types";

function formatPrice(n: number | null | undefined): string {
  if (n == null || n === 0) return "N/A";
  return `$${n.toLocaleString()}`;
}

type Props = {
  listing: Listing;
  selectable?: boolean;
  selected?: boolean;
  onToggle?: () => void;
};

export function ListingCard({ listing, selectable = false, selected = false, onToggle }: Props) {
  const interactive = selectable && onToggle;
  const containerClasses = [
    "flex items-center gap-4 rounded-xl bg-white p-4 shadow-sm transition-all sm:p-5",
    interactive ? "cursor-pointer" : "",
    selected ? "ring-2 ring-pink shadow-md" : "hover:shadow-md",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      onClick={interactive ? onToggle : undefined}
      className={containerClasses}
    >
      {selectable && (
        <div className="flex items-center">
          <div
            className={`flex h-6 w-6 items-center justify-center rounded border-2 transition-colors ${
              selected ? "border-pink bg-pink" : "border-gray-300"
            }`}
          >
            {selected && (
              <svg
                className="h-4 w-4 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={3}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            )}
          </div>
        </div>
      )}

      {listing.photo_url && (
        <div className="shrink-0">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={listing.photo_url}
            alt={`${listing.year} ${listing.make} ${listing.model}`}
            className="h-32 w-48 rounded-lg object-cover bg-background sm:h-36 sm:w-56"
          />
        </div>
      )}

      <div className="flex flex-1 flex-col justify-between gap-1">
        <div>
          <h3 className="font-semibold text-dark">
            {listing.year} {listing.make} {listing.model} {listing.trim}
          </h3>
          <p className="text-sm text-foreground/60">
            {listing.exterior_color}
            {listing.dealer_name && ` · ${listing.dealer_name}`}
            {listing.dealer_city &&
              `, ${listing.dealer_city}, ${listing.dealer_state}`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="font-bold text-dark text-lg">
            {formatPrice(listing.msrp || listing.price)}
          </span>
          {listing.msrp && listing.price && listing.price !== listing.msrp && (
            <span className="text-foreground/50">
              Asking: {formatPrice(listing.price)}
            </span>
          )}
          {listing.distance_miles != null && (
            <span className="text-foreground/40">
              {Math.round(listing.distance_miles)} mi away
            </span>
          )}
          {listing.days_on_lot != null && listing.days_on_lot > 60 && (
            <span className="rounded bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
              {listing.days_on_lot} days on lot
            </span>
          )}
        </div>
      </div>

      {listing.vdp_url && (
        <div className="flex items-center">
          <a
            href={listing.vdp_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center justify-center rounded-lg bg-pink px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-pink-dark whitespace-nowrap"
          >
            View Listing
          </a>
        </div>
      )}
    </div>
  );
}
